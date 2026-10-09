"""Graph rebuilding must not copy bounds that it immediately replaces."""
import unittest
from types import SimpleNamespace
from planner.policy import Policy
from planner.search import extend_policy, update_g_brute


class NoCopy(dict):
    def copy(self):
        raise AssertionError('Discarded bound dictionary was copied')


class DeferredBoundsTests(unittest.TestCase):
    def test_shorter_merge_rebuilds_without_copying_parent_bounds(self):
        edges = {0: [1, 2], 1: [3], 3: [4]}
        p = Policy({s: ('move', [SimpleNamespace(apply=lambda _, c=c: c) for c in children])
                    for s, children in edges.items()}, {2, 4}, set())
        task = SimpleNamespace(initial_state=0, goal_reached=lambda _: False)
        update_g_brute(p, task)
        p.best_costs = NoCopy(p.best_costs)
        p.worst_costs = NoCopy(p.worst_costs)
        child = extend_policy(p, 2, 'move', [SimpleNamespace(apply=lambda _: 4)], {4}, task)
        self.assertEqual(child.get_best_g(4), 2)
        self.assertEqual(child.get_worst_g(4), 3)
        self.assertEqual(p.get_best_g(4), 3)
        self.assertNotIn(2, p.strategy)
