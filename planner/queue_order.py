"""Queue priority tuples for single- and bi-objective search."""
from abc import ABC, abstractmethod
import heapq


class OpenEntry:
    """Avoid structural policy equality while preserving historical tie order.

    BOAND* generates each strategy once. Distinct queued policies therefore
    compare unequal; only identical policy objects need an equality shortcut.
    Keep the existing policy less-than rule for equal priority values.
    """
    __slots__ = ("priority", "policy")

    def __init__(self, priority, policy):
        self.priority = priority
        self.policy = policy

    def __lt__(self, other):
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.policy is not other.policy and self.policy < other.policy


class OpenListSorter(ABC):
    @abstractmethod
    def push(self, open_list, f_best, f_worst, f_size, policy):
        pass


class BestWorstOpenListSorter(OpenListSorter):
    def push(self, open_list, f_best, f_worst, f_size, policy):
        heapq.heappush(open_list, OpenEntry((f_best,f_worst,f_size), policy))


class WorstBestOpenListSorter(OpenListSorter):
    def push(self, open_list, f_best, f_worst, f_size, policy):
        heapq.heappush(open_list, OpenEntry((f_worst,f_best,f_size), policy))


class BestOpenListSorter(OpenListSorter):
    def push(self, open_list, f_best, f_worst, f_size, policy):
        heapq.heappush(open_list, OpenEntry((f_best,0,f_size), policy))


class WorstOpenListSorter(OpenListSorter):
    def push(self, open_list, f_best, f_worst, f_size, policy):
        heapq.heappush(open_list, OpenEntry((f_worst,0,f_size), policy))
