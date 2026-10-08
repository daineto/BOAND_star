import heapq
import unittest
from planner.queue_order import BestWorstOpenListSorter, WorstBestOpenListSorter, BestOpenListSorter, WorstOpenListSorter


class UncomparablePolicy:
    def __init__(self, size):
        self.strategy = dict.fromkeys(range(size))
    def __eq__(self, other):
        raise AssertionError("queue compared policy contents")
    def __lt__(self, other):
        raise AssertionError("queue compared policies")


class QueueOrderTests(unittest.TestCase):
    def test_larger_policy_then_fifo_without_policy_comparison(self):
        for cls in (BestWorstOpenListSorter, WorstBestOpenListSorter, BestOpenListSorter, WorstOpenListSorter):
            sorter = cls(); queue = []
            small, large, equal = [UncomparablePolicy(n) for n in (1,3,3)]
            for policy in (small,large,equal):
                sorter.push(queue,2,4,5,policy)
            for expected in (large,equal,small):
                self.assertIs(heapq.heappop(queue)[1], expected)

    def test_original_priority_precedes_policy_size(self):
        for cls in (BestWorstOpenListSorter, WorstBestOpenListSorter, BestOpenListSorter, WorstOpenListSorter):
            sorter = cls(); queue = []
            small, large = UncomparablePolicy(1), UncomparablePolicy(100)
            sorter.push(queue,1,1,1,small)
            sorter.push(queue,2,2,2,large)
            self.assertIs(heapq.heappop(queue)[1],small)
            sorter.push(queue,2,2,0,small)
            self.assertIs(heapq.heappop(queue)[1],small)
