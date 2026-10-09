"""Compact native handles preserve state identity, hashes and transitions."""
import random
import unittest
from pyperplan.task import Task, Operator
from planner.backends.downward import ROOT, FactStateTask, HandleStateTask


@unittest.skipUnless((ROOT / 'outputs/fast-downward/build/search/_downward_native.so').is_file(),
                     'Build the optional native backend')
class NativeHandleTests(unittest.TestCase):
    def test_random_tasks_match_fact_states(self):
        rng = random.Random(260610)
        for case in range(40):
            facts = tuple(f'f{i}' for i in range(4))
            sample = lambda: {f for f in facts if rng.random() < .35}
            task = Task(str(case), set(facts), frozenset(sample()), frozenset(sample()),
                        [Operator(f'(a{i})', sample(), sample(), sample()) for i in range(5)])
            for heuristic in ('hmax', 'lmcut'):
                compact, reference = HandleStateTask(task, heuristic), FactStateTask(task, heuristic)
                pending = [compact.initial_state]; seen = set()
                for state in pending:
                    if state in seen: continue
                    seen.add(state); decoded = compact.state_facts(state)
                    self.assertEqual(hash(state), hash(decoded))
                    self.assertEqual(compact.goal_reached(state), reference.goal_reached(decoded))
                    self.assertEqual(compact.evaluate(state), reference.evaluate(decoded))
                    actual = compact.get_successor_states(state)
                    expected = reference.get_successor_states(decoded)
                    self.assertEqual([(op.name, compact.state_facts(child)) for op, child in actual],
                                     [(op.name, child) for op, child in expected])
                    self.assertEqual([compact.state_facts(child) for child in {c for _,c in actual}],
                                     list({c for _,c in expected}))
                    for op, child in actual:
                        self.assertIs(op.apply(state), child)
                        pending.append(child)
                self.assertNotEqual(compact.initial_state, HandleStateTask(task).initial_state)
