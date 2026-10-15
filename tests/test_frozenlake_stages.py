import itertools
import json
import random
import tempfile
import unittest
from pathlib import Path

from analysis.frozenlake_tradeoffs import evaluate
from analysis.reachable_policy_oracle import exact_front
from analysis.serial_tradeoff_oracle import original_actions
from experiment_support.benchmark_generators.frozenlake import DOMAIN, label, render
from experiment_support.benchmark_generators.frozenlake_stages import generate, grid, grid_actions


class ReachablePolicyOracleTests(unittest.TestCase):
    def test_against_exhaustive_stationary_policies(self):
        rng = random.Random(0)
        graphs = [
            {0: [(0, 1)], 1: []},  # proper cyclic only
            {0: [(1, 2)], 1: [], 2: []},  # a reachable dead end
            {0: [(1,), (2,)], 1: [(0,)], 2: [(3,)], 3: []},
        ]
        for _ in range(120):
            graphs.append({s: [tuple(rng.sample(range(4), rng.randint(1, 2)))
                               for _ in range(rng.randint(0, 3))] for s in range(4)})
        for actions in graphs:
            goal = max(actions)
            keys = [s for s in actions if s != goal]
            costs = set()
            for choices in itertools.product(*(actions[s] or [(s,)] for s in keys)):
                pair = evaluate(dict(zip(keys, choices)), 0, goal)
                if pair is not None:
                    costs.add(pair)
            expected = sorted(p for p in costs if not any(
                q != p and q[0] <= p[0] and q[1] <= p[1] for q in costs))
            self.assertEqual(exact_front(actions, 0, goal)['front'], expected, actions)
        self.assertEqual(exact_front({0: []}, 0, 0)['front'], [(0, 0)])

    def test_enumeration_limit_is_not_a_front(self):
        with self.assertRaises(RuntimeError):
            exact_front({0: [(1,)], 1: []}, 0, 1, max_nodes=1)


class PhysicalStageTests(unittest.TestCase):
    def test_original_pddl_actions_and_full_fronts(self):
        for stages in (1, 2, 3):
            record = grid(stages)
            geometry = grid_actions(record)
            with tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / 'problem.pddl'
                path.write_text(render(record))
                grounded = original_actions(DOMAIN, path)
            expected_actions = {label(s): sorted(tuple(sorted(label(t) for t in outcomes))
                                                 for outcomes in choices)
                                for s, choices in geometry.items()}
            actual_actions = {s: sorted(tuple(a['outcomes']) for a in choices)
                              for s, choices in grounded.items()}
            self.assertEqual(actual_actions, expected_actions)
            original_graph = {s: [tuple(a['outcomes']) for a in choices]
                              for s, choices in grounded.items()}
            result = exact_front(original_graph, label(record['start']), label(record['goal']))
            # A checked hypothesis for these three cases, not a general theorem.
            expected = [(17 * stages - 7 + 2 * j, 34 * stages - 14 - 8 * j)
                        for j in range(stages + 1)]
            self.assertEqual(result['front'], expected)
            self.assertEqual(result['minimum_proper_best'], expected[0][0])

    def test_generation_and_frozen_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            first, second = generate(output / 'first'), generate(output / 'second')
            self.assertEqual(first, second)
            self.assertEqual((output / 'first/domain.pddl').read_bytes(), DOMAIN.read_bytes())
            for record in first['instances']:
                name = record['instance'] + '.pddl'
                self.assertEqual((output / 'first' / name).read_bytes(), (output / 'second' / name).read_bytes())
            with self.assertRaises(FileExistsError):
                generate(output / 'first')
        frozen = json.loads(Path('benchmarks/journal_tradeoffs/physical_stages/generation.json').read_text())
        for record in frozen['instances']:
            self.assertEqual(record['cells'], grid(record['stages'])['cells'])
        for value in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                grid(value)


if __name__ == '__main__':
    unittest.main()
