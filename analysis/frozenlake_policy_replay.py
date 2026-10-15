"""Replay BOAND position policies against parsed original FrozenLake PDDL.

Specialized to the unchanged ICAPS FrozenLake domain. No planner grounder is
used: original_actions checks types, preconditions and every PDDL effect.
"""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import re
import resource

from pddl import parse_problem
from pddl.logic.predicates import Predicate
from analysis.frozenlake_tradeoffs import evaluate
from analysis.serial_tradeoff_oracle import original_actions
from planner.policy import CYCLE_COST

DOMAIN_SHA256 = '756541601e1720cf8767b50ee4b48500d4b750e269d73821be3ebda2c5ee1f96'


def replay(request):
    domain, problem = Path(request['domain_path']), Path(request['problem_path'])
    if hashlib.sha256(domain.read_bytes()).hexdigest() != DOMAIN_SHA256:
        raise ValueError('This replay supports only the unchanged ICAPS FrozenLake domain')
    parsed = parse_problem(str(problem))
    initial = [f for f in parsed.init if isinstance(f, Predicate) and f.name == 'at']
    if (len(initial) != 1 or len(initial[0].terms) != 1 or not isinstance(parsed.goal, Predicate)
            or parsed.goal.name != 'at' or len(parsed.goal.terms) != 1):
        raise ValueError('Expected one initial position and one position goal')
    initial, goal = initial[0].terms[0].name, parsed.goal.terms[0].name
    actions = {s: {a['action']: tuple(a['outcomes']) for a in choices}
               for s, choices in original_actions(domain, problem).items()}
    results = []
    for file, expected in request['policies']:
        lines = [line for line in Path(file).read_text().splitlines() if line.strip()]
        if len(lines) % 2:
            raise ValueError('Unpaired policy lines')
        strategy = {}
        for state_line, action_line in zip(lines[::2], lines[1::2]):
            state = re.fullmatch(r'If holds: \(at ([a-z0-9_]+)\)', state_line)
            action = re.fullmatch(r'Execute: \(([^()]+)\)', action_line)
            if state is None or action is None or state[1] in strategy:
                raise ValueError('Expected unique single-position policy rules')
            strategy[state[1]] = action[1]
        graph, seen, pending = {}, {initial}, deque([initial])
        while pending:
            source = pending.popleft()
            if source == goal:
                continue
            selected = actions.get(source, {}).get(strategy.get(source))
            if selected is None:
                raise ValueError(f'Missing or inapplicable original-PDDL action at {source}')
            graph[source] = selected
            for target in selected:
                if target not in seen:
                    seen.add(target)
                    pending.append(target)
        pair = evaluate(graph, initial, goal)
        if pair is None:
            raise ValueError('Policy is not proper')
        best, worst = pair
        worst = CYCLE_COST if worst == float('inf') else worst
        if [best, worst] != expected:
            raise ValueError(f'Original replay costs {(best, worst)} disagree with {expected}')
        results.append({'policy': str(file), 'best': best, 'worst': worst, 'reachable_states': len(seen)})
    return {'status': 'valid', 'policies': results, 'method': 'original-pddl-frozenlake-actions'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    request = json.loads(args.request.read_text())
    resource.setrlimit(resource.RLIMIT_AS, (request['memory_kb'] * 1024,) * 2)
    try:
        result = replay(request)
    except Exception as error:
        result = {'status': 'invalid', 'error': f'{type(error).__name__}: {error}'}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    if result['status'] != 'valid':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
