import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from analysis.frozenlake_policy_replay import replay
from analysis.reachable_policy_oracle import exact_front
from analysis.serial_tradeoff_oracle import original_actions
from experiment_support.benchmark_generators.frozenlake import DOMAIN, label, render
from experiment_support.benchmark_generators.frozenlake_stages import grid, grid_actions
from experiment_support.benchmark_generators.frozenlake_stage_scaling import CASES, predicted_front


class ScalingTests(unittest.TestCase):
    def test_fixed_probes_from_original_pddl(self):
        base = Path('benchmarks/journal_tradeoffs/stage_scaling')
        frozen = json.loads((base / 'generation.json').read_text())
        self.assertEqual([(r['stages'], r['size']) for r in frozen['instances']], list(CASES))
        for record in frozen['instances']:
            k, n = record['stages'], record['size']
            self.assertEqual(render(grid(k, n)), (base / (record['instance'] + '.pddl')).read_text())
            a = original_actions(base / 'domain.pddl', base / (record['instance'] + '.pddl'))
            geometry = grid_actions(record)
            self.assertEqual({s: sorted(tuple(c['outcomes']) for c in cs) for s, cs in a.items()},
                             {label(s): sorted(tuple(sorted(label(t) for t in ts)) for ts in choices)
                              for s, choices in geometry.items()})
            result = exact_front({s: [tuple(c['outcomes']) for c in cs] for s, cs in a.items()},
                                 label(record['start']), label(record['goal']))
            self.assertEqual(result['front'], predicted_front(k, n))
            self.assertEqual(result['strong_policies'], 2 ** k)
            self.assertEqual(result['minimum_proper_best'], predicted_front(k, n)[0][0])

    def test_prior_inputs_are_byte_identical(self):
        base = Path('benchmarks/journal_tradeoffs/physical_stages')
        for k in (1, 2, 3):
            self.assertEqual(render(grid(k)), (base / f'staircase-k{k:02d}.pddl').read_text())
        for n in (0, 5, 7, 6.0, True):
            with self.assertRaises(ValueError):
                grid(1, n)
            with self.assertRaises(ValueError):
                predicted_front(1, n)

    def test_long_graph_has_no_python_recursion_limit(self):
        actions = {s: [(s + 1,)] for s in range(1100)}
        result = exact_front(actions, 0, 1100)
        self.assertEqual(result['front'], [(1100, 1100)])
        self.assertEqual(result['strong_policies'], 1)

    def test_original_replay_accepts_valid_and_rejects_bad_policy(self):
        record = grid(1)
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            problem, policy = base / 'problem.pddl', base / 'policy.out'
            problem.write_text(render(record))
            actions = original_actions(DOMAIN, problem)
            x, y = record['start']
            path = []
            for dx, dy, length in ((-1, 0, 2), (0, 1, 8), (1, 0, 8), (0, -1, 2)):
                for _ in range(length):
                    source, target = (x, y), (x + dx, y + dy)
                    direction = {(1, 0): 'right', (-1, 0): 'left', (0, 1): 'up', (0, -1): 'down'}[dx, dy]
                    selected = next(a['action'] for a in actions[label(source)]
                                    if a['action'].split()[0].split('-')[0] == direction
                                    and label(target) in a['outcomes'])
                    path.extend([f'If holds: (at {label(source)})', f'Execute: ({selected})'])
                    x, y = target
            policy.write_text('\n'.join(path) + '\n')
            request = {'domain_path': str(DOMAIN), 'problem_path': str(problem),
                       'policies': [(str(policy), [10, 20])]}
            valid = replay(request)
            self.assertEqual(valid['status'], 'valid')
            self.assertEqual(valid['policies'][0]['reachable_states'], 21)
            request['policies'] = [(str(policy), [10, 19])]
            with self.assertRaises(ValueError):
                replay(request)
            request['policies'] = [(str(policy), [10, 20])]
            policy.write_text('\n'.join(path[2:]) + '\n')
            with self.assertRaises(ValueError):
                replay(request)
            bad_domain = base / 'domain.pddl'
            bad_domain.write_bytes(DOMAIN.read_bytes() + b'\n')
            request['domain_path'] = str(bad_domain)
            with self.assertRaises(ValueError):
                replay(request)


if __name__ == '__main__':
    unittest.main()
