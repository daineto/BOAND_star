from types import SimpleNamespace
import unittest
from planner.policy import Policy
from planner.strategy import Strategy
from planner.search import extend_policy, update_g_brute


class StrategySharingTests(unittest.TestCase):
    def test_sibling_isolation_order_and_native_materialization(self):
        base = {0:('a', ())}
        left = Strategy(base, 1, ('b', ()))
        right = Strategy(base, 1, ('c', ()))
        self.assertIs(left.copy(), left)
        self.assertEqual(list(left), [0,1])
        self.assertEqual(dict(left.items()), left.materialize())
        self.assertNotEqual(left, right)
        materialized = left.materialize()
        materialized[0] = ('changed', ())
        self.assertEqual(base[0], ('a', ()))
        self.assertEqual(right.get(1), ('c', ()))

    def test_extension_keeps_parent_mapping_and_sibling_bounds_isolated(self):
        root = frozenset({'root'}); child = frozenset({'child'}); goal = frozenset({'goal'})
        parent = Policy({}, set(), set())
        parent.best_ancestors = {root:'dummy'}; parent.worst_costs = {root:0}
        op = SimpleNamespace(apply=lambda _:child)
        task = SimpleNamespace(initial_state=root,goal_reached=lambda s:s==goal)
        left = extend_policy(parent, root, 'a', [op], {child}, task)
        right = extend_policy(parent, root, 'b', [op], {child}, task)
        self.assertIs(left.strategy.base, parent.strategy)
        self.assertIs(right.strategy.base, parent.strategy)
        self.assertEqual(parent.strategy, {})
        left.worst_costs[child] = 9
        self.assertEqual(right.get_worst_g(child), 1)
        update_g_brute(right, task)
        self.assertEqual(right.get_best_g(child), 1)
        self.assertEqual(right.get_worst_g(child), 1)
