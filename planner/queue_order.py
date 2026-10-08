"""Queue priority tuples for single- and bi-objective search."""
from abc import ABC, abstractmethod
import heapq


class OpenListSorter(ABC):
    @abstractmethod
    def push(self, open_list, f_best, f_worst, f_size, policy):
        pass


class BestWorstOpenListSorter(OpenListSorter):
    def push(self, open_list, f_best, f_worst, f_size, policy):
        heapq.heappush(open_list, ((f_best,f_worst,f_size),policy))


class WorstBestOpenListSorter(OpenListSorter):
    def push(self, open_list, f_best, f_worst, f_size, policy):
        heapq.heappush(open_list, ((f_worst,f_best,f_size),policy))


class BestOpenListSorter(OpenListSorter):
    def push(self, open_list, f_best, f_worst, f_size, policy):
        heapq.heappush(open_list, ((f_best,0,f_size),policy))


class WorstOpenListSorter(OpenListSorter):
    def push(self, open_list, f_best, f_worst, f_size, policy):
        heapq.heappush(open_list, ((f_worst,0,f_size),policy))
