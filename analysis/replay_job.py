"""Bounded independent policy replay in a separate process."""
import argparse
import json
from pathlib import Path
import resource
import tempfile
import os
import re


def replay(request):
    from pddl import parse_domain, parse_problem
    from planner.preprocessing import get_alloutcome_determinization
    from analysis.validate_policies import parse_policy, validate_policy
    with tempfile.TemporaryDirectory(prefix='boand-replay-') as tmp:
        old = Path.cwd()
        try:
            os.chdir(tmp)
            task = get_alloutcome_determinization(parse_domain(request['domain_path']),
                                                parse_problem(request['problem_path']))
        finally:
            os.chdir(old)
    actions = {}
    for op in task.operators:
        actions.setdefault(re.sub(r'_detdup_[0-9]*', '', op.name), []).append(op)
    results = []
    for file, expected in request['policies']:
        strategy = parse_policy(file)
        # The independent replay only needs the selected action's outcomes.
        # Keep Python applicability/effects; avoid scanning unrelated actions.
        class SelectedActionTask:
            initial_state = task.initial_state
            goal_reached = task.goal_reached

            def get_successor_states(self, state):
                return [(op, op.apply(state)) for op in actions.get(strategy.get(state), ())
                        if op.preconditions <= state]
        result = validate_policy(SelectedActionTask(), strategy)
        if [result['best'], result['worst']] != expected:
            raise ValueError(f'{file}: replay costs {result} disagree with {expected}')
        results.append({'policy': file, **result})
    return {'status': 'valid', 'policies': results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('request', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    request = json.loads(args.request.read_text())
    resource.setrlimit(resource.RLIMIT_AS, (request['memory_kb'] * 1024,) * 2)
    try:
        result = replay(request)
    except ValueError as error:
        result = {'status': 'invalid', 'error': str(error)}
    except Exception as error:
        result = {'status': 'validation_error', 'error': f'{type(error).__name__}: {error}'}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    if result['status'] != 'valid':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
