"""Ground original PDDL independently and enumerate stationary graph policies."""
import itertools
from pathlib import Path

from pddl import parse_domain, parse_problem
from analysis.prp_replay import OriginalTask, ground
from analysis.frozenlake_tradeoffs import evaluate


def original_actions(domain, problem):
    task = OriginalTask.__new__(OriginalTask)
    task.domain = parse_domain(str(domain))
    task.problem = parse_problem(str(problem))
    task.actions = {a.name: a for a in task.domain.actions}
    task.static = frozenset(ground(f, {}) for f in task.problem.init if f.name != 'at')
    kinds = {o.name: next(iter(o.type_tags)) for o in task.problem.objects}
    # Obtain relations from parsed PDDL rather than generator action lists.
    adjacency = {direction: {} for direction in ('right', 'left', 'up', 'down')}
    for predicate, terms in task.static:
        forward, reverse = ('right', 'left') if predicate == 'left-of' else ('up', 'down')
        a, b = terms
        adjacency[forward].setdefault(a, []).append(b)
        adjacency[reverse].setdefault(b, []).append(a)
    result = {}
    for source, kind in kinds.items():
        if kind != 'ice':
            continue
        state = frozenset({('at', (source,))})
        choices = []
        for direction, neighbors in adjacency.items():
            for near in neighbors.get(source, []):
                if kinds[near] != 'ice':
                    continue
                for far in neighbors.get(near, []):
                    far_kind = kinds[far]
                    if far_kind not in ('ice', 'wall', 'pit'):
                        continue
                    name = direction if far_kind == 'ice' else f'{direction}-to-{far_kind}'
                    label = ' '.join([name, source, near, far])
                    action, binding = task.bound_action(label)
                    if not task.holds(action.precondition, state, binding):
                        raise ValueError(f'Unexpected inapplicable grounded action {label}')
                    successors = {(state - deletes) | adds for adds, deletes in task.effects(action.effect, state, binding)}
                    outcomes = sorted(next(iter(s))[1][0] for s in successors)
                    if any(len(s) != 1 for s in successors):
                        raise ValueError('Expected one position per outcome')
                    choices.append({'action': label, 'outcomes': outcomes})
        result[source] = sorted(choices, key=lambda a:a['action'])
    for name, kind in kinds.items():
        if kind == 'pit':
            result[name] = []
    return result


def enumerate_front(actions, initial, goal, max_policies=200000):
    keys = [s for s in actions if s != goal]
    choices = [[tuple(a['outcomes']) for a in actions[s]] or [(s,)] for s in keys]
    count = 1
    for values in choices:
        count *= len(values)
    if count > max_policies:
        raise ValueError(f'{count} assignments exceeds limit {max_policies}')
    costs = set()
    for policy in itertools.product(*choices):
        pair = evaluate(dict(zip(keys, policy)), initial, goal)
        if pair is not None:
            costs.add(pair)
    front = sorted(p for p in costs if not any(q != p and q[0] <= p[0] and q[1] <= p[1] for q in costs))
    return front, count
