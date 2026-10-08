"""Independent graph contracts for policy cost recomputation."""
from functools import lru_cache
import random
from types import SimpleNamespace
import unittest

from planner.policy import Policy, CYCLE_COST
from planner.search import extend_policy, update_g_brute


def policy_for(edges, size):
    policy = Policy({state: ('move', [SimpleNamespace(apply=lambda _, child=child: child)
                                   for child in children]) for state, children in edges.items()}, set(), set())
    policy.best_ancestors = {0: 'dummy', **{state: state - 1 for state in range(1, size)}}
    policy.worst_costs = {state: policy.get_best_g(state) for state in policy.best_ancestors}
    return policy


def enumerated_worst(edges):
    """Small-graph oracle: enumerate simple paths, then propagate cycle effects."""
    values = {0: 0}
    loopy = set()
    frontier = [(0, ())]
    while frontier:
        state, path = frontier.pop()
        if state in path:
            loopy.update(path[path.index(state):])
            continue
        values[state] = max(values.get(state, -1), len(path))
        for child in edges.get(state, ()):
            frontier.append((child, path + (state,)))
    pending = list(loopy)
    for state in pending:
        for child in edges.get(state, ()):
            if child not in loopy:
                loopy.add(child)
                pending.append(child)
    values.update(dict.fromkeys(loopy, CYCLE_COST))
    return values


class PolicyGraphTests(unittest.TestCase):
    def test_worst_bounds_match_independent_path_oracle(self):
        rng = random.Random(0)
        for case in range(100):
            size = rng.randrange(2, 8)
            edges = {state: [state + 1] for state in range(size - 1)}
            for state in edges:
                edges[state] += [child for child in range(size) if child != state + 1
                                 and rng.random() < .15]
            policy = policy_for(edges, size)
            update_g_brute(policy, SimpleNamespace(initial_state=0))
            expected = enumerated_worst(edges)
            self.assertEqual({state: policy.get_worst_g(state) for state in expected}, expected)
            self.assertEqual(policy.cyclic, CYCLE_COST in expected.values())

    def test_cycle_descendants_and_independent_finite_branch(self):
        policy = policy_for({0: [1, 3], 1: [2], 2: [1, 4]}, 5)
        policy.best_ancestors = {0: 'dummy', 1: 0, 2: 1, 3: 0, 4: 2}
        policy.worst_costs = {state: policy.get_best_g(state) for state in policy.best_ancestors}
        update_g_brute(policy, SimpleNamespace(initial_state=0))
        self.assertEqual([policy.get_worst_g(state) for state in range(5)],
                         [0, CYCLE_COST, CYCLE_COST, 1, CYCLE_COST])
        self.assertEqual([policy.get_best_g(state) for state in range(5)], [0, 1, 2, 1, 3])

    def test_cycle_through_root_marks_every_reachable_state(self):
        policy = policy_for({0: [1], 1: [0, 2]}, 3)
        update_g_brute(policy, SimpleNamespace(initial_state=0))
        self.assertEqual([policy.get_worst_g(state) for state in range(3)], [CYCLE_COST] * 3)
        self.assertEqual(policy.get_best_g(0), 0)

    def test_convergent_dag_keeps_distinct_shortest_and_longest_bounds(self):
        policy = policy_for({0: [1, 2], 1: [3], 2: [4], 4: [3], 3: [5]}, 6)
        policy.best_ancestors = {0: 'dummy', 1: 0, 2: 0, 3: 1, 4: 2, 5: 3}
        policy.worst_costs = {state: policy.get_best_g(state) for state in policy.best_ancestors}
        update_g_brute(policy, SimpleNamespace(initial_state=0))
        self.assertEqual((policy.get_best_g(5), policy.get_worst_g(5)), (3, 4))
        self.assertFalse(policy.cyclic)

    def test_extension_preserves_cycle_costs_and_isolates_numeric_bounds(self):
        policy = policy_for({0: [1], 1: [0, 2]}, 3)
        task = SimpleNamespace(initial_state=0, goal_reached=lambda state: False)
        update_g_brute(policy, task)
        op = SimpleNamespace(apply=lambda state: 3)
        child = extend_policy(policy, 2, 'finish', [op], {3}, task)
        self.assertEqual((child.get_best_g(3), child.get_worst_g(3)), (3, CYCLE_COST))
        self.assertNotIn(3, policy.best_ancestors)
        self.assertNotIn(3, policy.worst_costs)
        self.assertNotIn(2, policy.strategy)

    def test_task_outcome_cache_is_reused_and_remains_read_only(self):
        outcomes = {0: {1}, 1: {0, 2}}
        task = SimpleNamespace(initial_state=0)
        task.policy_outcomes = lru_cache(maxsize=2)(lambda state, action: outcomes[state])
        policy = policy_for({0: [1], 1: [0, 2]}, 3)
        for state in policy.strategy:
            def unexpected_apply(_):
                raise AssertionError('Cached outcomes must replace action application')
            policy.strategy[state] = ('move', [SimpleNamespace(apply=unexpected_apply)])
        for _ in range(2):
            update_g_brute(policy, task)
            self.assertEqual((policy.get_best_g(2), policy.get_worst_g(2)), (2, CYCLE_COST))
        self.assertEqual(outcomes, {0: {1}, 1: {0, 2}})
        self.assertEqual(task.policy_outcomes.cache_info().currsize, 2)
        self.assertEqual(task.policy_outcomes.cache_info().hits, 2)

    def test_empty_strategy_keeps_root_costs(self):
        policy = policy_for({}, 1)
        update_g_brute(policy, SimpleNamespace(initial_state=0))
        self.assertEqual((policy.get_best_g(0), policy.get_worst_g(0)), (0, 0))
        self.assertFalse(policy.cyclic)
