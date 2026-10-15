import json
from pathlib import Path
import tempfile
import unittest

from analysis.serial_tradeoff_oracle import enumerate_front, original_actions
from experiment_support.benchmark_generators.frozenlake import DOMAIN
from experiment_support.benchmark_generators.serial_tradeoffs import expected_front, generate, topology, render_topology


class SerialTradeoffTests(unittest.TestCase):
    def test_composition_matches_all_original_pddl_actions(self):
        with tempfile.TemporaryDirectory() as folder:
            for k, gap in [(1, 1), (2, 1), (3, 1), (4, 1), (2, 2)]:
                record = topology(k, gap)
                file = Path(folder) / 'problem.pddl';file.write_text(render_topology(record))
                actual = original_actions(DOMAIN, file)
                for state, choices in record['actions'].items():
                    self.assertEqual({(a['action'], tuple(sorted(a['outcomes']))) for a in choices},
                                     {(a['action'], tuple(a['outcomes'])) for a in actual[state]})
                front, assignments = enumerate_front(actual, record['initial'], record['goal'])
                self.assertEqual(front, expected_front(k, gap))
                self.assertEqual(len(front), k + 1)
                self.assertEqual(assignments, 8**k)
                self.assertTrue(all(w < float('inf') for b, w in front))

    def test_generation_is_reproducible_and_domain_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            first, second = Path(folder) / 'first', Path(folder) / 'second'
            self.assertEqual(generate(first), generate(second))
            for file in first.rglob('*'):
                if file.is_file():
                    self.assertEqual(file.read_bytes(), (second / file.relative_to(first)).read_bytes())
            self.assertEqual((first / 'serial-topology/domain.pddl').read_bytes(), DOMAIN.read_bytes())
            self.assertEqual((first / 'physical-ports/domain.pddl').read_bytes(), DOMAIN.read_bytes())
            with self.assertRaises(FileExistsError):generate(first)

    def test_declared_front_sizes_and_connector_offset(self):
        self.assertEqual(expected_front(2), [(7, 19), (9, 17), (11, 15)])
        self.assertEqual(expected_front(2, 2), [(7, 31), (11, 27), (15, 23)])
        for k in (1, 2, 4, 8, 16):
            front = expected_front(k)
            self.assertEqual(len(front), k + 1)
            self.assertEqual({b + w for b, w in front}, {14 * k - 2})
        with self.assertRaises(ValueError):expected_front(0)
