"""Preserve historical pending selection when removing its unused priority heap."""
import heapq
import random
import unittest
from planner.policy import Policy
from planner.state_selection import LargestGStateSelector

class SelectorCleanupTests(unittest.TestCase):
    def test_matches_historical_selection_and_remaining_pending(self):
        rng = random.Random(41)
        for _ in range(500):
            states = [frozenset({str(i)}) for i in range(rng.randrange(1, 30))]
            pending = {state for state in states if rng.random() < .7} or {states[0]}
            policy = Policy({}, pending, set())
            policy.worst_costs = {state: rng.randrange(100) for state in pending}
            reference = policy.copy()
            heap = []
            for state in reference.pending:
                heapq.heappush(heap, (-reference.get_worst_g(state), state))
            reference.pending.remove(state)
            self.assertEqual(LargestGStateSelector().select_pending_state(policy, None), state)
            self.assertEqual(policy.pending, reference.pending)
