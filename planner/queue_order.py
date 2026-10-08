"""Queue priority tuples for single- and bi-objective search."""
from abc import ABC, abstractmethod
import heapq
from itertools import count


class OpenListSorter(ABC):
    def __init__(self):
        self._serial = count()

    def _entry(self, priority, policy):
        # Preserve all objective/heuristic priorities. AND* favors larger
        # policies on ties; serial order resolves remaining ties without
        # comparing whole strategy dictionaries or Policy.__lt__.
        return ((*priority, -len(policy.strategy), next(self._serial)), policy)

    @abstractmethod
    def push(self, open_list, f_best, f_worst, f_size, policy):
        pass


class BestWorstOpenListSorter(OpenListSorter):
    def push(self, open_list, f_best, f_worst, f_size, policy):
        heapq.heappush(open_list, self._entry((f_best,f_worst,f_size), policy))


class WorstBestOpenListSorter(OpenListSorter):
    def push(self, open_list, f_best, f_worst, f_size, policy):
        heapq.heappush(open_list, self._entry((f_worst,f_best,f_size), policy))


class BestOpenListSorter(OpenListSorter):
    def push(self, open_list, f_best, f_worst, f_size, policy):
        heapq.heappush(open_list, self._entry((f_best,0,f_size), policy))


class WorstOpenListSorter(OpenListSorter):
    def push(self, open_list, f_best, f_worst, f_size, policy):
        heapq.heappush(open_list, self._entry((f_worst,0,f_size), policy))
