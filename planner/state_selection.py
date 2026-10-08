"""Pending-state selection, preserving historical ordering behavior."""
from abc import ABC, abstractmethod
import heapq
from pyperplan.heuristics.heuristic_base import Heuristic
from pyperplan.search.searchspace import SearchNode
from .policy import Policy


class StateSelector(ABC):
    @abstractmethod
    def select_pending_state(self, policy:Policy, heuristic: Heuristic):
        pass


class RandomStateSelector(StateSelector):
    def select_pending_state(self, policy:Policy, heuristic: Heuristic):
        state = policy.pending.pop()
        return state


class BoundsFirstStateSelector(StateSelector):
    def select_pending_state(self, policy:Policy, heuristic: Heuristic):
        prio_list = []
        if len(policy.goal_states) == 0:
            for state in policy.pending:
                heapq.heappush(prio_list, (policy.get_best_g(state) + heuristic(SearchNode(state, None, None, 0)),state))
        else:
            for state in policy.pending:
                heapq.heappush(prio_list, (-(policy.get_best_g(state) + heuristic(SearchNode(state, None, None, 0))),state))
        g,state = heapq.heappop(prio_list)
        policy.pending.remove(state)

        return state


class LargestGStateSelector(StateSelector):
    def select_pending_state(self, policy:Policy, heuristic: Heuristic):
        prio_list = []
        for state in policy.pending:
            heapq.heappush(prio_list, (-policy.get_worst_g(state),state))
        policy.pending.remove(state)

        return state


class BestStateSelector(StateSelector):
    def select_pending_state(self, policy:Policy, heuristic: Heuristic):
        prio_list = []
        for state in policy.pending:
            heapq.heappush(prio_list, (policy.get_best_g(state) + heuristic(SearchNode(state, None, None, 0)),state))
        policy.pending.remove(state)

        return state
