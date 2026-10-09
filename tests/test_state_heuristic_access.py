import math
import unittest
from unittest.mock import Mock, patch
from planner.policy import Policy
from planner.heuristics import CachedStateHeuristic, MinSumBestCaseHeuristic, MaxSumWorstCaseHeuristic, DeltaSizeHeuristic
from planner.search import compute_f_value


class StateHeuristicAccessTests(unittest.TestCase):
    def policy(self):
        p=Policy({}, {'a','b'}, {'g'})
        p.best_costs={'s': 0, 'a': 1, 'b': 2, 'g': 3}
        p.worst_costs={'s':0,'a':1,'b':2,'g':3}
        return p

    def test_cache_hits_create_no_temporary_search_nodes(self):
        values={'a':2,'b':4,'g':0}
        underlying=Mock(side_effect=lambda node:values[node.state])
        h=CachedStateHeuristic(underlying)
        for state in values:h.evaluate(state)
        with patch('planner.search.SearchNode', side_effect=AssertionError('temporary node')), patch('planner.heuristics.SearchNode', side_effect=AssertionError('temporary node')):
            p=self.policy()
            self.assertEqual(compute_f_value(p,None,h),(3,6,5))
            self.assertEqual(tuple(cls(h).get_f_value(p) for cls in (MinSumBestCaseHeuristic,MaxSumWorstCaseHeuristic,DeltaSizeHeuristic)),(3,6,5))
        self.assertEqual(underlying.call_count,3)

    def test_plain_node_heuristic_remains_supported(self):
        values={'a':2,'b':math.inf,'g':0}
        h=lambda node:values[node.state]
        p=self.policy()
        self.assertEqual(compute_f_value(p,None,h),(3,math.inf,math.inf))
        self.assertEqual(tuple(cls(h).get_f_value(p) for cls in (MinSumBestCaseHeuristic,MaxSumWorstCaseHeuristic,DeltaSizeHeuristic)),(3,math.inf,math.inf))
