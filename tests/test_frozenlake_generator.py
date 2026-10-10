from pathlib import Path
import tempfile
import unittest

from experiment_support.benchmark_generators.frozenlake import DOMAIN, generate, grid, pilot, render
from campaigns.journal_tradeoffs.analysis import pareto
from campaigns.journal_tradeoffs.campaign import CAMPAIGN
from experiment_support.campaigns import read_instances


class FrozenLakeGeneratorTests(unittest.TestCase):
    def test_generation_is_reproducible_and_preserves_domain(self):
        with tempfile.TemporaryDirectory() as folder:
            left, right = Path(folder) / 'left', Path(folder) / 'right'
            self.assertEqual(generate(left), generate(right))
            self.assertEqual((left / 'domain.pddl').read_bytes(), DOMAIN.read_bytes())
            for file in left.iterdir():
                self.assertEqual(file.read_bytes(), (right / file.name).read_bytes())
            with self.assertRaises(FileExistsError):
                generate(left)

    def test_pilot_identity_and_seed_contract(self):
        records = pilot()
        self.assertEqual(len(records), 19)
        self.assertEqual(len({r['instance'] for r in records}), 19)
        self.assertEqual(grid('random', 5, 6, 1), grid('random', 5, 6, 1))
        self.assertNotEqual(grid('random', 5, 6, 1)['cells'], grid('random', 5, 6, 2)['cells'])
        for record in records:
            self.assertIn(f'(problem {record["instance"]})', render(record))

    def test_campaign_manifest_and_resource_contract(self):
        self.assertEqual(len(read_instances(CAMPAIGN, 'pilot')), 19)
        self.assertEqual(len(read_instances(CAMPAIGN, 'smoke')), 3)
        self.assertEqual((CAMPAIGN.timeout_seconds, CAMPAIGN.memory_kb, CAMPAIGN.default_workers),
                         (600, 6000000, 4))
        self.assertEqual(len(CAMPAIGN.configurations), 2)

    def test_front_analysis_preserves_infinite_tradeoff(self):
        self.assertEqual(pareto([(2, 999999), (4, 4), (5, 5), (4, 4)]), [(2, 999999), (4, 4)])
        self.assertEqual(pareto([(2, 999999), (2, 6), (3, 5)]), [(2, 6), (3, 5)])


if __name__ == '__main__':
    unittest.main()
