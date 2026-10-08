import math
import unittest
from unittest.mock import Mock
from pyperplan.task import Operator, Task
from pyperplan.heuristics.relaxation import hMaxHeuristic
from planner.heuristics import CachedStateHeuristic
from planner.search import cached_dead_end_actions, grouped_successors


class EarlyDeadEndTests(unittest.TestCase):
    def test_one_dead_outcome_is_enough_and_finite_goal_is_safe(self):
        ready = frozenset({'ready'}); trap = frozenset({'trap'})
        progress = Operator('(move_detdup_0)', {'ready'}, {'goal'}, {'ready'})
        failure = Operator('(move_detdup_1)', {'ready'}, {'trap'}, {'ready'})
        finish = Operator('(finish)', {'ready'}, {'goal'}, {'ready'})
        task = Task('mixed', {'ready','trap','goal'}, ready, {'goal'}, [progress,failure,finish])
        h = CachedStateHeuristic(hMaxHeuristic(task))
        self.assertEqual(h.evaluate(trap), math.inf)
        grouped = Mock(side_effect=lambda state:grouped_successors(task,state))
        check = cached_dead_end_actions(grouped,h)
        self.assertTrue(check(ready,'(move)'))
        self.assertFalse(check(ready,'(finish)'))
        self.assertTrue(check(ready,'(move)'))
        self.assertEqual(grouped.call_count,2)
        self.assertEqual(h.evaluate(frozenset({'goal'})),0)

    def test_cache_is_task_local_and_bounded(self):
        state = frozenset({'s'})
        outcomes = lambda state:({'a':{state}}, {})
        first = cached_dead_end_actions(outcomes,CachedStateHeuristic(lambda node:math.inf),maxsize=1)
        second = cached_dead_end_actions(outcomes,CachedStateHeuristic(lambda node:0),maxsize=1)
        self.assertTrue(first(state,'a'))
        self.assertFalse(second(state,'a'))
        first(frozenset({'other'}),'a')
        self.assertEqual(first.cache_info().currsize,1)
