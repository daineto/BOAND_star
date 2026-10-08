import heapq
import random
import unittest
from planner.policy import Policy
from planner.queue_order import OpenEntry, BestWorstOpenListSorter, WorstBestOpenListSorter, BestOpenListSorter, WorstOpenListSorter


class EqualityForbidden(Policy):
    def __eq__(self, other):
        raise AssertionError("queue compared strategy contents")


class QueueEntryTests(unittest.TestCase):
    def test_equal_priorities_do_not_compare_policy_equality(self):
        for cls in (BestWorstOpenListSorter, WorstBestOpenListSorter, BestOpenListSorter, WorstOpenListSorter):
            queue=[]; sorter=cls()
            for i in range(20):
                sorter.push(queue,1,2,3,EqualityForbidden({i:('move',())},set(),set()))
            self.assertEqual(len([heapq.heappop(queue) for _ in range(20)]),20)

    def test_duplicate_object_is_not_less_than_itself(self):
        policy=EqualityForbidden({},set(),set())
        self.assertFalse(OpenEntry((1,2,3),policy)<OpenEntry((1,2,3),policy))

    def test_historical_order_preserved_for_unique_strategies(self):
        rng=random.Random(32)
        for trial in range(100):
            original=[]; candidate=[]
            for i in range(200):
                priority=tuple(rng.randrange(4) for _ in range(3))
                policy=Policy({i:('move',())},set(),set())
                heapq.heappush(original,(priority,policy))
                heapq.heappush(candidate,OpenEntry(priority,policy))
                if rng.random()<.2:
                    expected=heapq.heappop(original)
                    actual=heapq.heappop(candidate)
                    self.assertEqual(actual.priority,expected[0])
                    self.assertIs(actual.policy,expected[1])
            while original:
                expected=heapq.heappop(original); actual=heapq.heappop(candidate)
                self.assertEqual(actual.priority,expected[0])
                self.assertIs(actual.policy,expected[1])
