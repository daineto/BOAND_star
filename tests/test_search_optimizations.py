"""Correctness contracts for measured planner optimizations."""
import math
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from pyperplan.search.searchspace import SearchNode
from pyperplan.task import Operator, Task
from planner.heuristics import CachedStateHeuristic, MinSumBestCaseHeuristic, MaxSumWorstCaseHeuristic, DeltaSizeHeuristic
from planner.policy import Policy, CYCLE_COST
from planner.search import compute_f_value, grouped_successors, update_g_brute


class HeuristicCacheTests(unittest.TestCase):
    def test_equal_states_share_values_including_zero_and_infinity(self):
        underlying = Mock(side_effect=lambda node: math.inf if 'dead' in node.state else 0)
        cached = CachedStateHeuristic(underlying)
        for state, expected in [(frozenset({'goal'}), 0), (frozenset({'dead'}), math.inf)]:
            for _ in range(3):
                self.assertEqual(cached(SearchNode(frozenset(state), None, None, 0)), expected)
        self.assertEqual(underlying.call_count, 2)

    def test_cache_is_bounded_and_task_local(self):
        first = CachedStateHeuristic(lambda node: len(node.state), maxsize=1)
        second = CachedStateHeuristic(lambda node: 99)
        node = SearchNode(frozenset({'a'}), None, None, 0)
        self.assertEqual(first(node), 1)
        self.assertEqual(second(node), 99)
        first(SearchNode(frozenset({'a', 'b'}), None, None, 0))
        self.assertEqual(first.evaluate.cache_info().currsize, 1)
        self.assertEqual(first(node), 1)
        self.assertEqual(first.evaluate.cache_info().misses, 3)


class JointBoundTests(unittest.TestCase):
    def test_joint_bounds_equal_separate_estimates_for_cycles_deadlocks_and_infinity(self):
        for cyclic, ancestor_cycle, unreachable in [(False, False, False), (True, True, False),
                                                    (True, False, False), (False, False, True)]:
            with self.subTest(cyclic=cyclic, ancestor_cycle=ancestor_cycle, unreachable=unreachable):
                policy = Policy({}, {'a', 'b'}, {'g'})
                policy.best_ancestors = {'s': 'dummy', 'a': 's', 'b': 'a', 'g': 'b'}
                policy.worst_ancestors = policy.best_ancestors.copy()
                if ancestor_cycle:
                    policy.worst_ancestors['s'] = 's'
                policy.cyclic = cyclic
                values = {'a': 3, 'b': math.inf if unreachable else 1, 'g': 0}
                heuristic = lambda node: values[node.state]
                separate = tuple(cls(heuristic).get_f_value(policy) for cls in
                                 (MinSumBestCaseHeuristic, MaxSumWorstCaseHeuristic, DeltaSizeHeuristic))
                self.assertEqual(compute_f_value(policy, None, heuristic), separate)

    def test_closed_and_empty_frontiers_keep_default_bounds(self):
        policy = Policy({}, set(), {'s'})
        policy.best_ancestors = policy.worst_ancestors = {'s': 'dummy'}
        heuristic = lambda node: 0
        self.assertEqual(compute_f_value(policy, None, heuristic), (0, 0, 0))
        policy.goal_states.clear()
        self.assertEqual(compute_f_value(policy, None, heuristic), (math.inf, math.inf, 0))


class SuccessorGroupingTests(unittest.TestCase):
    def test_all_outcomes_noops_and_distinct_actions_are_preserved(self):
        state = frozenset({'ready'})
        noop = Operator('(move_detdup_0)', {'ready'}, set(), set())
        progress = Operator('(move_detdup_1)', {'ready'}, {'done'}, {'ready'})
        other = Operator('(finish)', {'ready'}, {'done'}, {'ready'})
        blocked = Operator('(blocked)', {'absent'}, set(), set())
        task = Task('example', {'ready', 'done', 'absent'}, state, {'done'},
                    [noop, progress, other, blocked])
        successors, operators = grouped_successors(task, state)
        self.assertEqual(list(successors), ['(move)', '(finish)'])
        self.assertEqual(successors['(move)'], {state, frozenset({'done'})})
        self.assertEqual(operators['(move)'], {noop, progress})
        self.assertEqual(operators['(finish)'], {other})
        self.assertEqual(grouped_successors(task, frozenset({'done'})), ({}, {}))


class AncestorUpdateTests(unittest.TestCase):
    def policy(self, edges, ancestors):
        strategy = {state: ('move', [SimpleNamespace(apply=lambda _, target=target: target)
                                    for target in targets]) for state, targets in edges.items()}
        policy = Policy(strategy, set(), set())
        policy.best_ancestors = ancestors.copy()
        policy.worst_ancestors = ancestors.copy()
        return policy

    def test_convergent_paths_keep_shortest_and_longest_costs(self):
        policy = self.policy({'s': ['a', 'b'], 'a': ['g'], 'b': ['c'], 'c': ['g']},
                             {'s': 'dummy', 'a': 's', 'b': 's', 'c': 'b', 'g': 'a'})
        update_g_brute(policy, SimpleNamespace(initial_state='s'))
        self.assertEqual(policy.get_best_g('g'), 2)
        self.assertEqual(policy.get_worst_g('g'), 3)
        self.assertFalse(policy.cyclic)

    def test_self_loop_retains_cycle_cost(self):
        policy = self.policy({'s': ['s', 'g']}, {'s': 'dummy', 'g': 's'})
        update_g_brute(policy, SimpleNamespace(initial_state='s'))
        self.assertEqual(policy.get_best_g('g'), 1)
        self.assertEqual(policy.get_worst_g('g'), CYCLE_COST)
        self.assertTrue(policy.cyclic)

    def test_convergent_visits_reuse_action_outcomes(self):
        calls = []
        op = SimpleNamespace(apply=lambda state: calls.append(state) or 'g')
        policy = self.policy({'s': ['a', 'b'], 'a': ['c'], 'b': ['c']},
                             {'s': 'dummy', 'a': 's', 'b': 's', 'c': 'a', 'g': 'c'})
        policy.strategy['c'] = ('finish', [op])
        update_g_brute(policy, SimpleNamespace(initial_state='s'))
        self.assertEqual(policy.get_best_g('g'), 3)
        self.assertEqual(policy.get_worst_g('g'), 3)
        self.assertEqual(calls, ['c'])


if __name__ == '__main__':
    unittest.main()
