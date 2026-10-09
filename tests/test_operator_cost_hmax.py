"""Check operator-cost reuse against stock hmax and an independent fixed point."""
import math
import random
import unittest
from pyperplan.task import Task, Operator
from pyperplan.search.searchspace import SearchNode
from pyperplan.heuristics.relaxation import hMaxHeuristic
from planner.relaxation import OperatorCostHMaxHeuristic


def oracle(task, state):
    distance = {f: (0 if f in state else math.inf) for f in task.facts}
    changed = True
    while changed:
        changed = False
        for op in task.operators:
            cost = max((distance[f] for f in op.preconditions), default=0) + 1
            for f in op.add_effects:
                if cost < distance[f]:
                    distance[f] = cost
                    changed = True
    return max((distance[f] for f in task.goals), default=0)


class OperatorCostTests(unittest.TestCase):
    def test_repeated_states_match_stock_and_independent_relaxation(self):
        rng = random.Random(50)
        for case in range(200):
            facts = frozenset(range(rng.randrange(2, 15)))
            operators = [Operator(str(i), {f for f in facts if rng.random() < .2},
                                  {f for f in facts if rng.random() < .3},
                                  {f for f in facts if rng.random() < .1}) for i in range(20)]
            task = Task(str(case), facts, frozenset(), {f for f in facts if rng.random() < .3}, operators)
            stock, candidate = hMaxHeuristic(task), OperatorCostHMaxHeuristic(task)
            for _ in range(10):
                state = frozenset(f for f in facts if rng.random() < .3)
                node = SearchNode(state, None, None, 0)
                expected = oracle(task, state)
                self.assertEqual(stock(node), expected)
                self.assertEqual(candidate(node), expected)
