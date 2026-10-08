"""Scientific coverage and failure detection for the journal smoke suite."""
import json
import signal
from types import SimpleNamespace
import unittest

from campaigns.journal_development.campaign import CAMPAIGN, DOMAINS
from campaigns.journal_development.smoke import check_outcome, deadline
from experiment_support.campaigns import load_campaign, read_instances
from experiment_support.runner import build_environment, campaign_manifest


class JournalSmokeTests(unittest.TestCase):
    def test_inputs_and_execution_contract(self):
        icaps = load_campaign("icaps2025")
        frozen = json.loads(CAMPAIGN.instance_manifest.read_text())["instances"]
        self.assertEqual(frozen, read_instances(icaps, "paper"))
        selected = read_instances(CAMPAIGN, "smoke")
        self.assertEqual({e["domain"] for e in selected}, set(DOMAINS))
        self.assertEqual(set(DOMAINS), {e["domain"] for e in frozen})
        manifest = campaign_manifest(build_environment("smoke", campaign_id=CAMPAIGN.campaign_id), "smoke")
        self.assertEqual(manifest["run_count"], 14)
        self.assertEqual(manifest["memory_kb"], 6_000_000)
        self.assertEqual(manifest["parallel_runs"], 4)
        outcomes = json.loads(CAMPAIGN.instance_manifest.with_name("expected.json").read_text())
        self.assertEqual(outcomes["campaign_version"], CAMPAIGN.version)
        expected = outcomes["costs"]
        self.assertEqual(set(expected), {f"{e['domain']}/{e['instance']}" for e in selected})
        self.assertEqual(sum(not costs for costs in expected.values()), 2)
        self.assertEqual(sum(len(costs) > 1 for costs in expected.values()), 2)
        self.assertTrue(any(worst == 999999 for costs in expected.values() for _, worst in costs))

    def run_record(self, complete=True, returncode=0, costs=()):
        return SimpleNamespace(complete=complete,
                               execution={"state": "finished", "returncode": returncode},
                               stats=[{"best": b, "worst": w} for b, w in costs])

    def test_timeout_is_not_unsolvability_even_with_completion_marker(self):
        with self.assertRaisesRegex(ValueError, "unsuccessful execution"):
            check_outcome("example", self.run_record(returncode=124), [])

    def test_missing_completion_is_not_unsolvability(self):
        with self.assertRaisesRegex(ValueError, "search did not complete"):
            check_outcome("example", self.run_record(complete=False), [])
        check_outcome("example", self.run_record(), [])

    def test_frontier_comparison_ignores_emission_order_but_catches_missing_solution(self):
        expected = [[5, 12], [7, 11]]
        check_outcome("example", self.run_record(costs=[(7, 11), (5, 12)]), expected)
        with self.assertRaisesRegex(ValueError, "expected costs"):
            check_outcome("example", self.run_record(costs=[(5, 12)]), expected)

    def test_deadline_fails_and_restores_signal_handler(self):
        previous = signal.getsignal(signal.SIGALRM)
        with self.assertRaisesRegex(TimeoutError, "wall-time budget"):
            with deadline(60):
                signal.raise_signal(signal.SIGALRM)
        self.assertEqual(signal.getsignal(signal.SIGALRM), previous)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
