"""Bounds and sibling-isolation contracts for incremental policy extensions."""
import random
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from planner.policy import Policy, CYCLE_COST
from planner.search import extend_policy, update_g_brute


def mapped_policy(edges):
    strategy = {state: ('move', [SimpleNamespace(apply=lambda _, child=child: child)
                                for child in children]) for state, children in edges.items()}
    policy = Policy(strategy, set(), set())
    task = SimpleNamespace(initial_state=0, goal_reached=lambda _: False)
    update_g_brute(policy, task)
    return policy, task


class IncrementalBoundsTests(unittest.TestCase):
    def test_dominated_merge_reuses_bounds_and_keeps_sibling_independent(self):
        parent, task = mapped_policy({0: [1, 2, 5], 1: [3], 3: [4], 4: [5]})
        before_best = parent.best_ancestors.copy()
        before_worst = parent.worst_costs.copy()
        with patch('planner.search.update_g_brute', side_effect=AssertionError('Unnecessary graph rebuild')):
            child = extend_policy(parent, 2, 'merge', [SimpleNamespace(apply=lambda _: 5)], {5}, task)
        for state in parent.best_ancestors:
            self.assertEqual((child.get_best_g(state), child.get_worst_g(state)),
                             (parent.get_best_g(state), parent.get_worst_g(state)))
        self.assertEqual(parent.best_ancestors, before_best)
        self.assertEqual(parent.worst_costs, before_worst)
        self.assertNotIn(2, parent.strategy)
        sibling = extend_policy(parent, 2, 'other', [SimpleNamespace(apply=lambda _: 6)], {6}, task)
        self.assertNotIn(6, child.best_ancestors)
        self.assertNotIn(6, parent.best_ancestors)
        self.assertEqual(sibling.get_best_g(6), 2)

    def test_already_cyclic_target_keeps_cycle_cost(self):
        parent, task = mapped_policy({0: [1, 2], 1: [0, 3]})
        with patch('planner.search.update_g_brute', side_effect=AssertionError('Unnecessary graph rebuild')):
            child = extend_policy(parent, 2, 'merge', [SimpleNamespace(apply=lambda _: 3)], {3}, task)
        self.assertEqual(child.get_worst_g(3), CYCLE_COST)
        self.assertEqual(child.get_best_g(3), 2)
        self.assertTrue(child.cyclic)

    def test_shorter_paths_propagate_through_implicitly_shortened_descendants(self):
        parent, task = mapped_policy({0: [1, 2, 8], 1: [7], 7: [3], 3: [4], 4: [6],
                                      8: [9], 9: [10], 10: [11], 11: [6]})
        # Both old routes to 6 have length five; choose the independent route.
        parent.best_ancestors[6] = 11
        self.assertEqual(parent.get_best_g(6), 5)
        with patch('planner.search.update_g_brute', side_effect=AssertionError('Unnecessary graph rebuild')):
            child = extend_policy(parent, 2, 'shortcut', [SimpleNamespace(apply=lambda _: 3)], {3}, task)
        self.assertEqual((child.get_best_g(3), child.get_best_g(4), child.get_best_g(6)), (2, 3, 4))
        self.assertEqual(child.worst_costs, parent.worst_costs)
        self.assertEqual(parent.get_best_g(6), 5)
        eager = child.copy()
        update_g_brute(eager, task)
        for state in eager.best_ancestors:
            self.assertEqual(child.get_best_g(state), eager.get_best_g(state))

    def test_random_extensions_match_full_graph_recomputation(self):
        rng = random.Random(0)
        for case in range(100):
            size = rng.randrange(3, 10)
            parent, task = mapped_policy({})
            for state in range(size - 1):
                children = {state + 1} | {other for other in range(size) if rng.random() < .15}
                operators = [SimpleNamespace(apply=lambda _, child=child: child) for child in children]
                previous_best = parent.best_ancestors.copy()
                previous_worst = parent.worst_costs.copy()
                child = extend_policy(parent, state, 'move', operators, children, task)
                eager = child.copy()
                update_g_brute(eager, task)
                self.assertEqual(child.cyclic, eager.cyclic)
                for known in eager.best_ancestors:
                    self.assertEqual((child.get_best_g(known), child.get_worst_g(known)),
                                     (eager.get_best_g(known), eager.get_worst_g(known)), (case, state, known))
                self.assertEqual(parent.best_ancestors, previous_best)
                self.assertEqual(parent.worst_costs, previous_worst)
                parent = child
