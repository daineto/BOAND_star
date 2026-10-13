import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from analysis.frozenlake_tradeoffs import frontier
from experiment_support.benchmark_generators.frozenlake_recovery import candidates, generate, grid
from experiment_support.benchmark_generators.frozenlake import DOMAIN
from experiment_support.benchmark_generators.frozenlake import label, render
from campaigns.journal_frozenlake_recovery.campaign import CAMPAIGN
from campaigns.journal_frozenlake_recovery.analysis import analyze, pareto
from analysis.results import Run
from experiment_support.campaigns import read_instances
from analysis.prp_replay import OriginalTask, ground
from pddl import parse_domain, parse_problem


class RecoveryRouteTests(unittest.TestCase):
    def test_exact_base_fronts_include_three_distinct_choices(self):
        for tail in ('cyclic', 'pit'):
            record = grid(5, tail)
            front, count = frontier({(x, y): k for x, y, k in record['cells']},
                                    tuple(record['start']), tuple(record['goal']))
            normalized = [[b, 999999 if w == float('inf') else w] for b, w in front]
            self.assertEqual(normalized, record['front'])
            self.assertEqual(count, record['policy_assignments'])

    def test_larger_references_remain_unknown(self):
        records = candidates()
        self.assertEqual(len(records), 10)
        self.assertEqual(len({r['instance'] for r in records}), 10)
        for record in records:
            if record['height'] > 5:
                self.assertNotIn('front', record)
                self.assertEqual(record['reference_status'], 'pending')
        with self.assertRaises(ValueError):
            grid(4)

    def test_reproducible_generation_preserves_domain(self):
        with tempfile.TemporaryDirectory() as temporary:
            left, right = Path(temporary) / 'left', Path(temporary) / 'right'
            self.assertEqual(generate(left), generate(right))
            self.assertEqual((left / 'domain.pddl').read_bytes(), DOMAIN.read_bytes())
            for file in left.iterdir():
                self.assertEqual(file.read_bytes(), (right / file.name).read_bytes())
            with self.assertRaises(FileExistsError):
                generate(left)

    def test_manifest_resources_and_infinite_cost_ordering(self):
        self.assertEqual(len(read_instances(CAMPAIGN, 'smoke')), 2)
        self.assertEqual(len(read_instances(CAMPAIGN, 'pilot')), 10)
        self.assertEqual((CAMPAIGN.timeout_seconds, CAMPAIGN.memory_kb, CAMPAIGN.default_workers), (600, 6000000, 4))
        self.assertEqual(pareto([(1, 999999), (3, 9), (5, 7), (4, 10)]), [(1, 999999), (3, 9), (5, 7)])

    def test_smoke_failure_cannot_pass_using_known_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'manifest.json').write_text(json.dumps({'status': 'execution_finished', 'profile': 'smoke'}))
            instance = 'recovery-3x5-cyclic'
            entries = [{'domain': 'frozenlake', 'instance': instance,
                        'domain_path': 'benchmarks/journal_tradeoffs/frozenlake_recovery/domain.pddl',
                        'problem_path': f'benchmarks/journal_tradeoffs/frozenlake_recovery/{instance}.pddl'}]
            runs = {(config, 'frozenlake', instance): Run(config, 'frozenlake', instance, root, (), 0)
                    for config in CAMPAIGN.configurations}
            checks = {key: {'status': 'no_policies'} for key in runs}
            module = 'campaigns.journal_frozenlake_recovery.analysis'
            with patch(f'{module}.read_instances', return_value=entries), \
                 patch(f'{module}.resolve_dataset', return_value=(root, {})), \
                 patch(f'{module}.selected_results', return_value=(runs, {})), \
                 patch(f'{module}.replay_runs', return_value=checks):
                with self.assertRaisesRegex(ValueError, 'validation failed'):
                    analyze(root, root / 'analysis')
            report = json.loads((root / 'analysis/report.json').read_text())
            self.assertEqual(len(report['issues']), 2)
            self.assertTrue(all(not row['completed'] for row in report['rows']))

    def test_base_grid_movements_match_original_pddl(self):
        with tempfile.TemporaryDirectory() as temporary:
            for tail in ('cyclic', 'pit'):
                record = grid(5, tail)
                problem = Path(temporary) / 'problem.pddl'
                problem.write_text(render(record))
                task = OriginalTask.__new__(OriginalTask)
                task.domain = parse_domain(str(DOMAIN))
                task.problem = parse_problem(str(problem))
                task.actions = {a.name: a for a in task.domain.actions}
                task.static = frozenset(ground(f, {}) for f in task.problem.init if f.name != 'at')
                cells = {(x, y): kind for x, y, kind in record['cells']}
                for source, kind in cells.items():
                    if kind != 'ice':
                        continue
                    state = frozenset({('at', (label(source),))})
                    for name, dx, dy in [('right', 1, 0), ('left', -1, 0), ('up', 0, 1), ('down', 0, -1)]:
                        near = source[0] + dx, source[1] + dy
                        far = source[0] + 2 * dx, source[1] + 2 * dy
                        if cells.get(near, 'wall') != 'ice':
                            continue
                        kind = cells.get(far, 'wall')
                        action_name = name if kind == 'ice' else f'{name}-to-{kind}'
                        action, binding = task.bound_action(' '.join([action_name, label(source), label(near), label(far)]))
                        self.assertTrue(task.holds(action.precondition, state, binding))
                        actual = {(state - deletes) | adds for adds, deletes in task.effects(action.effect, state, binding)}
                        expected = {frozenset({('at', (label(p),))}) for p in ([near] if kind == 'wall' else [near, far])}
                        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
