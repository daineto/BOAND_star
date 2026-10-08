"""Equivalent size bounds including duplicates, empty sets and infinity."""
import math
import random
from types import SimpleNamespace
import unittest
from planner.policy import Policy
from planner.heuristics import CachedStateHeuristic, DeltaSizeHeuristic
from planner.search import compute_f_value

class SizeBoundTests(unittest.TestCase):
    def test_closed_form_matches_ascending_reference(self):
        rng = random.Random(38)
        cases = [[], [0], [3, 3, 3], [math.inf], [1, math.inf, 2]]
        cases += [[rng.choice([0, 1, 5, 100, math.inf]) for _ in range(rng.randrange(40))]
                  for _ in range(1000)]
        for values in cases:
            ordered = sorted(values)
            expected = max((h + i for i, h in enumerate(ordered)), default=0)
            policy = Policy({}, set(range(len(values))), set())
            policy.best_ancestors = {s: 'dummy' for s in policy.pending}
            policy.worst_costs = {s: 0 for s in policy.pending}
            heuristic = CachedStateHeuristic(lambda node: values[node.state])
            self.assertEqual(DeltaSizeHeuristic(heuristic).get_f_value(policy), expected)
            self.assertEqual(compute_f_value(policy, SimpleNamespace(), heuristic)[2], expected)
