"""Correctness contracts for measured planner optimizations."""
import math
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from pyperplan.search.searchspace import SearchNode
from planner.heuristics import CachedStateHeuristic
from planner.policy import Policy, CYCLE_COST
from planner.search import update_g_brute


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


if __name__ == '__main__':
    unittest.main()
