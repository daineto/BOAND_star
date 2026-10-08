"""Canonical campaign and archive labels preserve the published coverage."""
from pathlib import Path
import tempfile
import unittest

from analysis.results import load_results
from campaigns.icaps2025.analysis import load_paper_results, coverage_table
from campaigns.icaps2025.campaign import CAMPAIGN
from experiment_support.campaigns import read_instances


class CanonicalDomainTests(unittest.TestCase):
    def test_frozen_inputs_use_canonical_runtime_label(self):
        entries = read_instances(CAMPAIGN, "paper")
        self.assertEqual(len(entries), 196)
        self.assertEqual(sum(e["domain"] == "beam-walk" for e in entries), 11)
        self.assertNotIn("bream-walk", {e["domain"] for e in entries})

    def test_canonical_domain_statistics(self):
        configuration = CAMPAIGN.configurations["BOAND bw"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / configuration.name / "beam-walk" / "p01" / "solutions" / "beam-walk_p01.sol"
            directory.mkdir(parents=True)
            (directory / "p01.stats").write_text("-1;-1;-1;2;3;4;5;6\n")
            run = load_results(root, {"main": configuration}, ("beam-walk",))["main", "beam-walk", "p01"]
            self.assertTrue(run.complete)
            self.assertEqual(run.stats[0]["time"], 2)

    def test_published_coverage_is_preserved(self):
        runs = load_paper_results()
        self.assertTrue(any(r.domain == "beam-walk" and r.stats for r in runs.values()))
        self.assertFalse(any(r.domain == "bream-walk" for r in runs.values()))
        table = coverage_table(runs)
        self.assertEqual(table.loc["beam-walk"].tolist(), [11, 8, 7, 8, 8])
        self.assertEqual(table.loc["Total"].tolist(), [205, 124, 120, 134, 122])


if __name__ == "__main__":
    unittest.main()
