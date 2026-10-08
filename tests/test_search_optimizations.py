"""Correctness contracts for measured planner optimizations."""
import math
import unittest
from unittest.mock import Mock

from pyperplan.search.searchspace import SearchNode
from planner.heuristics import CachedStateHeuristic


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


if __name__ == '__main__':
    unittest.main()
