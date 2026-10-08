"""Properness and escape-route contracts independent of cost bounds."""
import random
from types import SimpleNamespace
import unittest
from planner.policy import Policy
from planner.search import extension_has_escape


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


def all_have_escape(edges):
    # Independent fixed-point oracle for escape to ANY unmapped state.
    good = {c for children in edges.values() for c in children if c not in edges}
    while True:
        added = {s for s, children in edges.items() if any(c in good for c in children)}
        if added <= good:
            return set(edges) <= good
        good |= added


class EarlyDeadlockTests(unittest.TestCase):
    def test_cycles_with_and_without_escape(self):
        parent, task = make_policy({0:[1,2]}, 3)
        self.assertTrue(extension_has_escape(parent, 1, {0}, task))
        self.assertFalse(extension_has_escape(parent, 1, {1}, task))
        self.assertTrue(extension_has_escape(parent, 1, {1,3}, task))
        parent, task = make_policy({0:[1]}, 3)
        self.assertFalse(extension_has_escape(parent, 1, {0}, task))

    def test_incremental_escape_matches_independent_fixed_point(self):
        rng = random.Random(27)
        tested = 0
        for _ in range(2000):
            size = rng.randrange(2,9)
            count = rng.randrange(1,size)
            edges = {s:[c for c in range(size) if rng.random()<.3] for s in range(count)}
            if not all_have_escape(edges):
                continue
            parent, task = make_policy(edges, size-1)
            children = {c for c in range(size) if rng.random()<.3}
            expected = all_have_escape({**edges, count:list(children)})
            self.assertEqual(extension_has_escape(parent, count, children, task), expected)
            task.policy_outcomes = lambda state, action:edges[state]
            self.assertEqual(extension_has_escape(parent, count, children, task), expected)
            tested += 1
        self.assertGreater(tested, 500)

if __name__ == '__main__': unittest.main()
