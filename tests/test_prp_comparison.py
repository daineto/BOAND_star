import json
from pathlib import Path
import tempfile
import unittest
from analysis.prp_replay import replay, OriginalTask
from campaigns.journal_prp_comparison.campaign import CAMPAIGN
from campaigns.icaps2025.campaign import CAMPAIGN as ICAPS
from experiment_support.campaigns import read_instances

class PRPReplayTests(unittest.TestCase):
    def test_frozen_selection_and_limits(self):
        self.assertEqual(read_instances(CAMPAIGN,'paper'),read_instances(ICAPS,'BOAND_bw'))
        self.assertEqual((CAMPAIGN.timeout_seconds,CAMPAIGN.memory_kb,CAMPAIGN.default_workers),(600,6000000,4))
        self.assertEqual(len(read_instances(CAMPAIGN,'smoke')),14)

    def test_revalidation_cannot_overlap_an_unfinished_campaign(self):
        from campaigns.journal_prp_comparison.replay import revalidate
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);(folder/'status.json').write_text('{"state":"validating"}')
            with self.assertRaisesRegex(ValueError,'original execution/replay'):
                revalidate(folder)

    def fixture(self,folder,cycle=True):
        (folder/'domain.pddl').write_text('''(define (domain d) (:requirements :strips :non-deterministic)
          (:predicates (x) (g))
          (:action a :parameters () :precondition (x)
           :effect (oneof (and (g) (not (x))) (and)))
          (:action bad :parameters () :precondition (x) :effect (and)))''')
        (folder/'problem.pddl').write_text('(define (problem p) (:domain d) (:init (x)) (:goal (g)))')
        (folder/'output').write_text('''begin_variable
var7
-1
2
Atom x()
<none of those>
end_variable
begin_variable
var3
-1
2
Atom g()
<none of those>
end_variable
''')
        (folder/'policy.out').write_text('If holds: var7:0\nExecute: a / SC / d=1\nIf holds: var3:0\nExecute: goal / SC / d=0\n')
        (folder/'policy.fsap').write_text('')

    def test_original_pddl_all_outcomes_and_name_based_variables(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);self.fixture(folder)
            result=replay(folder/'domain.pddl',folder/'problem.pddl',folder)
            self.assertEqual((result['best'],result['worst'],result['reachable_states']),(1,999999,2))

    def test_forbidden_action_and_exported_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);self.fixture(folder)
            text=(folder/'policy.out').read_text();(folder/'policy.out').write_text('If holds: var7:0\nExecute: bad / SC / d=0\n'+text)
            (folder/'policy.fsap').write_text('If holds: var7:0\nForbid: bad\n')
            self.assertEqual(replay(folder/'domain.pddl',folder/'problem.pddl',folder)['best'],1)
            (folder/'policy.fsap').write_text('')
            with self.assertRaisesRegex(ValueError,'cannot reach'):replay(folder/'domain.pddl',folder/'problem.pddl',folder)

    def test_indexed_forbidden_rules_preserve_union_and_empty_conditions(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);self.fixture(folder)
            (folder/'policy.fsap').write_text(
                'If holds: var7:0 var3:1\nForbid: bad\n'*3+
                'If holds: var7:1 var3:1\nForbid: a\n'+
                'If holds:\nForbid: never-used\n')
            task=OriginalTask(folder/'domain.pddl',folder/'problem.pddl',folder)
            for state in (task.initial,frozenset({('g',())}),frozenset()):
                original={name for clauses,name in task.fsaps if task.condition(clauses,state)}
                indexed={name for guard,items in task.fsap_groups.items() if task.condition(guard,state)
                         for clauses,name in items if task.condition(clauses,state)}
                self.assertEqual(original,indexed)
            self.assertEqual(replay(folder/'domain.pddl',folder/'problem.pddl',folder)['best'],1)

    def test_inapplicable_policy_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);self.fixture(folder)
            p=folder/'domain.pddl';p.write_text(p.read_text().replace(':precondition (x)',':precondition (g)'))
            with self.assertRaisesRegex(ValueError,'Inapplicable'):replay(p,folder/'problem.pddl',folder)

    def test_weak_policy_with_a_successful_branch_is_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);self.fixture(folder)
            p=folder/'domain.pddl'
            p.write_text(p.read_text().replace('(x) (g)', '(x) (g) (trap)').replace(
                '(and)))', '(and (trap) (not (x)))))', 1).replace(
                ':action bad :parameters () :precondition (x)',
                ':action bad :parameters () :precondition (trap)'))
            # A successful outcome exists, but another outcome enters a closed
            # trap. Covering that trap with a self-loop does not make it proper.
            (folder/'policy.out').write_text((folder/'policy.out').read_text()+
                'If holds: var7:1 var3:1\nExecute: bad / SC / d=1\n')
            with self.assertRaisesRegex(ValueError,'cannot reach a goal'):
                replay(p,folder/'problem.pddl',folder)

    def test_case_insensitive_pddl_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);self.fixture(folder)
            p=folder/'domain.pddl';p.write_text(p.read_text().replace('(x)','(X)').replace('(g)','(G)'))
            p=folder/'problem.pddl';p.write_text(p.read_text().replace('(x)','(X)').replace('(g)','(G)'))
            self.assertEqual(replay(folder/'domain.pddl',p,folder)['best'],1)

    def test_quality_treats_cycle_as_infinity(self):
        from campaigns.journal_prp_comparison.analysis import dominates, relation
        self.assertTrue(dominates((3,7),(3,999999)))
        self.assertFalse(dominates((2,999999),(3,7)))
        self.assertEqual(relation((2,999999),[(3,7)]),'incomparable')
        self.assertEqual(relation((3,999999),[(3,7)]),'dominated_by_boand')
        self.assertEqual(relation((3,7),[(3,7)]),'on_front')

    def test_initial_goal_has_zero_cost(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);self.fixture(folder)
            p=folder/'problem.pddl';p.write_text(p.read_text().replace('(:init (x))','(:init (x) (g))'))
            result=replay(folder/'domain.pddl',p,folder);self.assertEqual((result['best'],result['worst']),(0,0))

if __name__=='__main__':unittest.main()
