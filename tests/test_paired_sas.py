"""Complement encoding preserves transitions and relaxations without name inference."""
from dataclasses import replace
import unittest
from pyperplan.task import Operator
from planner.backends.downward import ROOT, FactStateTask, paired_sas, boolean_sas
from planner.backends.grounding import GroundedTask


class PairedEncodingTests(unittest.TestCase):
    def task(self, pre=frozenset(), goals=frozenset({'(g)'})):
        return GroundedTask('pair', frozenset({'(p)', '(not_p)', '(g)'}),
                            frozenset({'(not_p)'}), goals,
                            (Operator('(set)', pre, {'(p)'}, {'(not_p)'}),
                             Operator('(reset)', {'(p)'}, {'(not_p)'}, {'(p)'}),
                             Operator('(finish)', {'(not_p)'}, {'(g)'}, set())),
                            {}, {'(p)': '(not_p)'})

    def test_only_declared_pairs_are_merged(self):
        task = self.task()
        sas, names, negatives = paired_sas(task)
        self.assertEqual(len(names), 2)
        self.assertEqual(set(names) | set(negatives.values()), set(task.facts))
        plain = replace(task, complement_pairs={})
        old, old_names = boolean_sas(plain)
        self.assertEqual(paired_sas(plain), (old, old_names, {}))

    def test_contradictory_conditions_leave_the_pair_unmerged(self):
        for task in (self.task(pre=frozenset({'(p)', '(not_p)'})),
                     self.task(goals=frozenset({'(p)', '(not_p)'}))):
            old, names = boolean_sas(task)
            self.assertEqual(paired_sas(task), (old, names, {}))

    @unittest.skipUnless((ROOT/'outputs/fast-downward/build/search/_downward_native.so').is_file(),
                         'Optional native dependency')
    def test_paired_and_legacy_transitions_values_and_hashes_match(self):
        task = self.task()
        for heuristic in ('hmax', 'lmcut'):
            paired = FactStateTask(task, heuristic)
            legacy = FactStateTask(replace(task, complement_pairs={}), heuristic)
            pending = [paired.initial_state]; seen = set()
            for state in pending:
                if state in seen: continue
                seen.add(state)
                self.assertEqual(paired.goal_reached(state), legacy.goal_reached(state))
                self.assertEqual(paired.evaluate(state), legacy.evaluate(state))
                actual, expected = paired.get_successor_states(state), legacy.get_successor_states(state)
                self.assertEqual([(op.name, child) for op, child in actual],
                                 [(op.name, child) for op, child in expected])
                for _, child in actual:
                    self.assertEqual('(p)' in child, '(not_p)' not in child)
                    pending.append(child)
