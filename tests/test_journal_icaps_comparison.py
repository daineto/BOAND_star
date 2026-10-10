"""Full-campaign selection and conservative historical comparison accounting."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from pyperplan.task import Task, Operator
from analysis.comparison_support import search_complete, selected_results, replay_runs
from analysis.replay_job import replay
from analysis.results import Run
from campaigns.icaps2025.campaign import CAMPAIGN as HISTORICAL
from campaigns.journal_icaps_comparison.campaign import CAMPAIGN, DOMAINS
from campaigns.journal_icaps_comparison.analysis import compare, HISTORY
from experiment_support.campaigns import read_instances


def stat(best=1, worst=1, seconds=1):
    return dict(best=best,worst=worst,size=1,time=seconds,iterations=2,expansions=1,generations=1,max_open=1)


def fixture_run(folder,label,cost=(1,1),complete=True,code=0):
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'execution.json').write_text(json.dumps({'state':'finished','returncode':code,
                                                  'termination':'timeout' if code==124 else 'success'}))
    rows=(stat(*cost),stat(-1,-1,2)) if complete else (stat(*cost),)
    return Run(label,'beam-walk','p1',folder,rows,0)


class FullComparisonTests(unittest.TestCase):
    def test_full_selection_preserves_exact_published_entries(self):
        old=read_instances(HISTORICAL,'BOAND_bw');new=read_instances(CAMPAIGN,'paper')
        self.assertEqual(new,old);self.assertEqual(len(new),196)
        self.assertEqual({e['domain'] for e in new},set(DOMAINS))
        self.assertEqual(len(CAMPAIGN.configurations)*len(new),392)
        self.assertEqual((CAMPAIGN.timeout_seconds,CAMPAIGN.memory_kb,CAMPAIGN.default_workers),(600,6000000,4))
        self.assertEqual({c.backend for c in CAMPAIGN.configurations.values()},{'downward-direct'})
        self.assertEqual({c.classical for c in CAMPAIGN.configurations.values()},{'hmax','lmcut'})
        self.assertEqual(len(read_instances(CAMPAIGN,'smoke')),14)

    def test_missing_or_malformed_stats_never_count_as_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=next(iter(CAMPAIGN.configurations.values()))
            folder=Path(tmp)/config.name/'beam-walk'/'p1'/'solutions'/'beam-walk_p1.sol'
            folder.mkdir(parents=True);(folder/'p1.stats').write_text('malformed\n')
            runs,errors=selected_results(tmp,{'x':config},{('beam-walk','p1')})
            self.assertTrue(errors);self.assertFalse(search_complete(runs['x','beam-walk','p1']))
            historic=Run('x','beam-walk','p1',Path(tmp),(stat(-1,-1),),0)
            self.assertTrue(search_complete(historic,historical=True))
            self.assertFalse(search_complete(historic))

    def test_independent_selected_action_replay_checks_all_outcomes(self):
        task=Task('cyclic',{'(x)','(g)'},frozenset({'(x)'}),frozenset({'(g)'}),
                  [Operator('(a_detdup_1)',{'(x)'},{'(g)'},set()),
                   Operator('(a_detdup_2)',{'(x)'},set(),set()),
                   Operator('(unrelated)',set(),set(),{'(x)'})])
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'p.boand.001.out';file.write_text('If holds: (x)\nExecute: (a)\n')
            request={'domain_path':'d','problem_path':'p','policies':[(str(file),[1,999999])]}
            with patch('pddl.parse_domain'),patch('pddl.parse_problem'),patch('planner.preprocessing.get_alloutcome_determinization',return_value=task):
                self.assertEqual(replay(request)['status'],'valid')
                request['policies']=[(str(file),[1,1])]
                with self.assertRaises(ValueError):replay(request)

    def test_replay_timeout_cannot_reuse_a_stale_valid_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);run=fixture_run(root/'run','FD hmax')
            (run.directory/'p.boand.001.out').write_text('If holds: (x)\nExecute: (a)\n')
            folder=root/'checks'/'FD hmax'/'beam-walk'/'p1';folder.mkdir(parents=True)
            (folder/'result.json').write_text('{"status":"valid"}')
            entries={('beam-walk','p1'):{'domain_path':'d','problem_path':'p'}}
            with patch('analysis.comparison_support.subprocess.run',return_value=SimpleNamespace(returncode=124)):
                result=replay_runs({('FD hmax','beam-walk','p1'):run},entries,root/'checks')
            self.assertEqual(result['FD hmax','beam-walk','p1']['status'],'validation_timeout')

    def comparison_fixture(self,tmp,partial=False):
        root=Path(tmp);(root/'manifest.json').write_text('{"profile":"paper"}')
        current={(label,'beam-walk','p1'):fixture_run(root/label,label,(1,1) if partial or label=='FD hmax' else (2,2),
                    complete=not(partial and label=='FD hmax'),code=124 if partial and label=='FD hmax' else 0)
                 for label in CAMPAIGN.configurations}
        old={(HISTORY,'beam-walk','p1'):fixture_run(root/'history',HISTORY,(1,1) if partial else (3,3))}
        entries=[{'domain':'beam-walk','instance':'p1','domain_path':'benchmarks/icaps2025/beam-walk/domain.pddl',
                  'problem_path':'benchmarks/icaps2025/beam-walk/p1.pddl'}]
        with patch('campaigns.journal_icaps_comparison.analysis.resolve_dataset',return_value=(root,{})), \
             patch('campaigns.journal_icaps_comparison.analysis.read_instances',return_value=entries), \
             patch('campaigns.journal_icaps_comparison.analysis.selected_results',side_effect=[(current,{}),(old,{})]), \
             patch('campaigns.journal_icaps_comparison.analysis.replay_runs',return_value={k:{'status':'valid'} for k in current}), \
             patch('campaigns.journal_icaps_comparison.analysis.plots'):
            return compare(root)

    def test_cost_disagreements_are_flagged_and_excluded_from_speedups(self):
        with tempfile.TemporaryDirectory() as tmp:report=self.comparison_fixture(tmp)
        self.assertEqual(report['status'],'needs_investigation')
        self.assertEqual(len(report['native_cost_disagreements']),1)
        self.assertEqual(len(report['historical_cost_differences']),2)
        self.assertTrue(all(v['paired_completed_equal_cost_instances']==0 for v in report['historical_timing'].values()))

    def test_valid_timeout_incumbent_is_solved_but_not_completed(self):
        with tempfile.TemporaryDirectory() as tmp:report=self.comparison_fixture(tmp,partial=True)
        hmax=report['counts']['FD hmax']
        self.assertEqual((hmax['completed_searches'],hmax['verified_solved'],hmax['timeouts']),(0,1,1))
        self.assertEqual(report['historical_timing']['FD hmax']['paired_completed_equal_cost_instances'],0)
        self.assertEqual(report['status'],'checked')
