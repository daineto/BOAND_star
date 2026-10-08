"""Properness and escape-route contracts independent of cost bounds."""
import random
from types import SimpleNamespace
import unittest
from planner.policy import Policy


def make_policy(edges, goal):
    strategy = {s: ('move', [SimpleNamespace(apply=lambda _, child=c: child) for c in children])
                for s, children in edges.items()}
    return Policy(strategy, set(), {goal}), SimpleNamespace(initial_state=0, goal_reached=lambda s:s == goal)


def escape_oracle(edges, goal):
    # Independent forward traversal from EACH reachable state.
    reachable = {0}
    work = [0]
    for state in work:
        for child in edges.get(state, ()):
            if child not in reachable:
                reachable.add(child)
                work.append(child)
    for start in reachable:
        seen = {start}; work = [start]
        for state in work:
            for child in edges.get(state, ()):
                if child not in seen:
                    seen.add(child); work.append(child)
        if goal not in seen:
            return False
    return True


class PropernessTests(unittest.TestCase):
    def test_cycle_can_escape_through_root(self):
        policy, task = make_policy({0:[1,2], 1:[0]}, 2)
        self.assertTrue(policy.is_proper(task))

    def test_goal_branch_does_not_rescue_trapped_cycle(self):
        policy, task = make_policy({0:[1,2], 1:[1]}, 2)
        self.assertFalse(policy.is_proper(task))

    def test_pending_and_empty_outcome_are_not_proper(self):
        for edges in ({0:[1,2]}, {0:[1,2], 1:[]}):
            policy, task = make_policy(edges, 2)
            self.assertFalse(policy.is_proper(task))

    def test_random_closed_graphs_match_forward_oracle(self):
        rng = random.Random(26)
        for _ in range(500):
            size = rng.randrange(2,10)
            edges = {s: [c for c in range(size) if rng.random()<.25] for s in range(size-1)}
            policy, task = make_policy(edges, size-1)
            self.assertEqual(policy.is_proper(task), escape_oracle(edges, size-1), edges)

    def test_cached_outcomes_and_uncached_agree(self):
        edges = {0:[1,2], 1:[0]}
        policy, task = make_policy(edges, 2)
        task.policy_outcomes = lambda s,a:edges[s]
        self.assertTrue(policy.is_proper(task))

if __name__ == '__main__': unittest.main()
