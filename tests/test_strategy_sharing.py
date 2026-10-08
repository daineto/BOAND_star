"""Isolation and lookup-depth contracts for shared strategies."""
import unittest
from planner.strategy import Strategy

class StrategySharingTests(unittest.TestCase):
    def test_siblings_and_flattened_descendants_are_independent(self):
        root = Strategy({'s': ('start', ())})
        left = root.extend('a', ('left', ()))
        right = root.extend('b', ('right', ()))
        self.assertIs(left.parent, root)
        self.assertIs(right.parent, root)
        self.assertEqual(list(left), ['s', 'a'])
        self.assertIsNone(left.get('b'))
        self.assertIsNone(right.get('a'))
        flat = left.extend('c', ('next', ())).extend('d', ('end', ()))
        self.assertEqual(list(flat), ['s', 'a', 'c', 'd'])
        self.assertEqual(dict(root), {'s': ('start', ())})
        self.assertEqual(dict(right), {'s': ('start', ()), 'b': ('right', ())})
        self.assertIs(flat.copy(), flat)
        with self.assertRaises(TypeError):
            flat['a'] = ('changed', ())

    def test_long_chain_keeps_values_order_and_bounded_lookup_depth(self):
        strategy = Strategy()
        expected = {}
        for state in range(50):
            strategy = strategy.extend(state, (f'action-{state}', ()))
            expected[state] = (f'action-{state}', ())
            self.assertLessEqual(strategy.depth, 2)
            self.assertEqual(list(strategy.items()), list(expected.items()))
            self.assertEqual(strategy, expected)
