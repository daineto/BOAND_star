from types import SimpleNamespace
import unittest
from planner.state_selection import RecentStateSelector


class RecentSelectionTests(unittest.TestCase):
    def test_latest_assignment_with_pending_outcome_is_selected(self):
        edges={0:[1,3],1:[2],2:[4]}
        policy=SimpleNamespace(strategy={0:('a',()),1:('a',()),2:('a',())},pending={3,4})
        selector=RecentStateSelector(lambda state, action:edges[state],0)
        self.assertEqual(selector.select_pending_state(policy,None),4)
        self.assertEqual(policy.pending,{3})
        self.assertEqual(selector.select_pending_state(policy,None),3)
        self.assertEqual(policy.pending,set())

    def test_initial_policy_selects_initial_state(self):
        policy=SimpleNamespace(strategy={},pending={0})
        selector=RecentStateSelector(lambda state,action:(),0)
        self.assertEqual(selector.select_pending_state(policy,None),0)
        self.assertEqual(policy.pending,set())
