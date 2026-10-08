"""Contracts for immutable strategy sharing across sibling policies."""
import unittest
from planner.strategy import Strategy
from planner.policy import Policy


class StrategySharingTests(unittest.TestCase):
    def test_siblings_share_parent_and_keep_independent_assignments(self):
        root = Strategy({'s': ('start', ())})
        left = root.extend('a', ('left', ()))
        right = root.extend('b', ('right', ()))
        self.assertIs(left.parent, root)
        self.assertIs(right.parent, root)
        self.assertEqual(dict(root.items()), {'s': ('start', ())})
        self.assertIsNone(left.get('b'))
        self.assertIsNone(right.get('a'))
        self.assertEqual(list(left), ['s', 'a'])
        self.assertEqual(left['a'], ('left', ()))
        self.assertEqual(left, {'s': ('start', ()), 'a': ('left', ())})
        self.assertNotEqual(left, right)
        self.assertIs(root.copy(), root)
        with self.assertRaises(TypeError):
            left['a'] = ('changed', ())
        with self.assertRaises(KeyError):
            left['absent']

    def test_chain_preserves_insertion_order_and_mapping_values(self):
        strategy = Strategy()
        expected = {}
        for state in range(50):
            strategy = strategy.extend(state, (f'action-{state}', ()))
            expected[state] = (f'action-{state}', ())
        self.assertEqual(list(strategy.items()), list(expected.items()))
        self.assertEqual(len(strategy), len(expected))
        self.assertEqual(dict(strategy), expected)
        policy = Policy(strategy, {51}, {52})
        clone = policy.copy()
        self.assertIs(clone.strategy, policy.strategy)
        clone.pending.clear()
        self.assertEqual(policy.pending, {51})
