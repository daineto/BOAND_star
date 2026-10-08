"""Policy-cost estimates extracted without changing their calculations."""
from abc import ABC, abstractmethod
from functools import lru_cache
import math
from pyperplan.heuristics.heuristic_base import Heuristic
from pyperplan.search.searchspace import SearchNode
from .policy import Policy, CYCLE_COST


class CachedStateHeuristic(Heuristic):
    """Memoize task-local hmax/lmcut values, which depend only on the state."""
    def __init__(self, heuristic, maxsize=65_536):
        self.evaluate = lru_cache(maxsize=maxsize)(
            lambda state: heuristic(SearchNode(state, None, None, 0))
        )

    def __call__(self, node):
        return self.evaluate(node.state)


class FondHeuristic(ABC):
    def __init__(self, cp_heuristic: Heuristic) -> None:
        # super().__init__()
        self.cp_heuristic = cp_heuristic
    @abstractmethod
    def get_f_value(self, policy: Policy):
        pass


class BlindBestCaseHeuristic(FondHeuristic):
    def get_f_value(self, policy: Policy,):
        Out = policy.pending.union(policy.goal_states)
        f_best = min([policy.get_best_g(state) for state in Out], default=math.inf)
        return f_best


class MinSumBestCaseHeuristic(FondHeuristic):
    def get_f_value(self, policy: Policy):
        Out = policy.pending.union(policy.goal_states)

        h_values = {state: self.cp_heuristic(SearchNode(state, None, None, 0)) for state in Out}

        f_best = min([policy.get_best_g(state) + h_values[state] for state in Out], default=math.inf)

        return f_best


class SumMinBestCaseHeuristic(FondHeuristic):
    def get_f_value(self, policy: Policy):
        Out = policy.pending.union(policy.goal_states)

        g_values = [policy.get_best_g(state) for state in Out]
        h_values = [self.cp_heuristic(SearchNode(state, None, None, 0)) for state in Out]

        f_best = min(g_values, default=math.inf) + min(h_values, default=math.inf)

        return f_best


class BlindWorstCaseHeuristic(FondHeuristic):
    def get_f_value(self, policy: Policy):
        Out = policy.pending.union(policy.goal_states)

        f_worst = max([policy.get_worst_g(state) for state in Out], default=math.inf)

        return f_worst


class MaxSumWorstCaseHeuristic(FondHeuristic):
    def get_f_value(self, policy: Policy):
        Out = policy.pending.union(policy.goal_states)

        h_values = {state: self.cp_heuristic(SearchNode(state, None, None, 0)) for state in Out}

        f_worst_values = []
        for state in Out:
            g_worst = policy.get_worst_g(state)
            h = h_values[state]
            if g_worst == CYCLE_COST:
                f_worst_values += [max(CYCLE_COST, h)]
            else:
                f_worst_values += [g_worst + h]
        f_worst = max(f_worst_values, default=math.inf)

        # DEADLOCK in the policy: it cannot become proper
        if policy.cyclic and f_worst < CYCLE_COST:
            f_worst = math.inf

        return f_worst


class DeltaSizeHeuristic(FondHeuristic):
    def get_f_value(self, policy: Policy):
        Out = policy.pending.union(policy.goal_states)

        h_values = {state: self.cp_heuristic(SearchNode(state, None, None, 0)) for state in Out}

        h_vector = sorted([h_values[state] for state in policy.pending])
        if len(h_vector) > 0:
            f_size = max([h_vector[i] + i for i in range(len(h_vector))])
        else:
            f_size = 0

        return f_size


class ZeroSizeHeuristic(FondHeuristic):
    def get_f_value(self, policy: Policy):
        return 0
