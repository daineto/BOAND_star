import math
import random
import unittest
from planner.policy import Policy, CYCLE_COST
from planner.heuristics import CachedStateHeuristic, MinSumBestCaseHeuristic, MaxSumWorstCaseHeuristic, DeltaSizeHeuristic
from planner.search import compute_f_value


class BoundEvaluationTests(unittest.TestCase):
    def test_random_bounds_agree_with_separate_estimators(self):
        rng=random.Random(42)
        for _ in range(500):
            n=rng.randrange(1,15)
            p=Policy({}, {i for i in range(n) if rng.random()<.5}, {i for i in range(n) if rng.random()<.25})
            p.best_ancestors={0:'dummy',**{i:rng.randrange(i) for i in range(1,n)}}
            p.worst_costs={i:rng.choice([i,CYCLE_COST]) for i in range(n)}
            p.cyclic=rng.choice([False,True])
            values={i:rng.choice([0,1,2,9,math.inf]) for i in range(n)}
            for h in (lambda node:values[node.state],CachedStateHeuristic(lambda node:values[node.state],maxsize=2)):
                ordered=sorted(values[state] for state in p.pending)
                size=max((value+i for i,value in enumerate(ordered)),default=0)
                expected=(MinSumBestCaseHeuristic(h).get_f_value(p),MaxSumWorstCaseHeuristic(h).get_f_value(p),size)
                self.assertEqual(DeltaSizeHeuristic(h).get_f_value(p),size)
                self.assertEqual(compute_f_value(p,None,h),expected)

    def test_overlapping_outgoing_inputs_evaluate_each_state_once(self):
        calls=[]
        p=Policy({}, {0,1}, {1,2});p.best_ancestors={0:'dummy',1:0,2:1};p.worst_costs={0:0,1:1,2:2}
        compute_f_value(p,None,lambda node:calls.append(node.state) or 0)
        self.assertCountEqual(calls,[0,1,2])
