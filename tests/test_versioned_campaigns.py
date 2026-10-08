"""Frozen-input isolation, schema checks, run provenance and compatibility."""
from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiment_support.campaigns import digest, load_campaign, read_instances, resolve_dataset
from experiment_support.models import Campaign, Configuration, Profile
from experiment_support.runner import CampaignExecutor, build_environment, campaign_manifest, launch
from analysis.inspect_run import inspect


class FrozenInputTests(unittest.TestCase):
    def fixture(self, root):
        (root / "domain.pddl").write_text("domain")
        (root / "p01.pddl").write_text("problem")
        entry = {"domain": "example", "instance": "p01", "domain_path": "domain.pddl",
                 "problem_path": "p01.pddl", "domain_sha256": digest(root / "domain.pddl"),
                 "problem_sha256": digest(root / "p01.pddl")}
        file = root / "instances.json"
        file.write_text(json.dumps({"schema_version": 1, "campaign_id": "example", "instances": [entry]}))
        return Campaign("example", "1", {"main": Configuration("bw", "hmax", "MinSum", "MaxSum", "Delta", "largestg")},
                        {"paper": Profile(("main",)), "smoke": Profile(("main",), instances=(("example", "p01"),))}, file)

    def test_added_file_does_not_expand_frozen_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.fixture(root)
            before = read_instances(campaign, "paper", root)
            (root / "p02.pddl").write_text("unrelated later benchmark")
            self.assertEqual(read_instances(campaign, "paper", root), before)
            self.assertEqual(read_instances(campaign, "smoke", root), before)

    def test_changed_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.fixture(root)
            (root / "p01.pddl").write_text("changed input")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                read_instances(campaign, "paper", root)

    def test_campaign_schema_and_timeout_are_checked(self):
        campaign = load_campaign("icaps2025")
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            replace(campaign, schema_version=999).validate()
        with self.assertRaisesRegex(ValueError, "one timeout"):
            replace(campaign, timeout_seconds=60).validate()

    def test_exact_manifest_migration_keeps_old_runs_readable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.fixture(root)
            old_hash = digest(campaign.instance_manifest)
            data = json.loads(campaign.instance_manifest.read_text())
            data["instances"][0]["domain"] = "corrected_label"
            campaign.instance_manifest.write_text(json.dumps(data))
            new_hash = digest(campaign.instance_manifest)
            run = root / "old-run"
            (run / "results").mkdir(parents=True)
            manifest = {"schema_version": 1, "campaign": {"id": "example", "version": "1",
                        "instance_manifest_sha256": old_hash}, "profile": "paper", "result_root": "results"}
            file = run / "manifest.json"
            file.write_text(json.dumps(manifest))
            recorded_run_hash = digest(file)
            with self.assertRaisesRegex(ValueError, "another frozen"):
                resolve_dataset(campaign, run)
            ledger = {"schema_version": 1, "campaign_id": "example", "campaign_version": "1",
                      "migrations": [{"from_sha256": old_hash, "to_sha256": new_hash,
                                      "reason": "Domain label correction"}]}
            (root / "manifest-migrations.json").write_text(json.dumps(ledger))
            results, identity = resolve_dataset(campaign, run)
            self.assertEqual(results, run / "results")
            self.assertEqual(identity["instance_manifest_migration"]["from_sha256"], old_hash)
            self.assertEqual(digest(file), recorded_run_hash)
            # An unrecorded formatting or content change must still be rejected.
            campaign.instance_manifest.write_text(campaign.instance_manifest.read_text() + "\n")
            with self.assertRaisesRegex(ValueError, "another frozen"):
                resolve_dataset(campaign, run)

    def test_manifest_migration_rejects_unlisted_source_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.fixture(root)
            current_hash = digest(campaign.instance_manifest)
            ledger = {"schema_version": 1, "campaign_id": "example", "campaign_version": "1",
                      "migrations": [{"from_sha256": "a" * 64, "to_sha256": current_hash}]}
            (root / "manifest-migrations.json").write_text(json.dumps(ledger))
            run = root / "old-run"
            (run / "results").mkdir(parents=True)
            (run / "manifest.json").write_text(json.dumps({"schema_version": 1,
                "campaign": {"id": "example", "version": "1", "instance_manifest_sha256": "b" * 64},
                "profile": "paper", "result_root": "results"}))
            with self.assertRaisesRegex(ValueError, "another frozen"):
                resolve_dataset(campaign, run)


class RunProvenanceTests(unittest.TestCase):
    def test_worker_override_preserves_scientific_settings(self):
        default = campaign_manifest(build_environment("mini"), "mini")
        serial = campaign_manifest(build_environment("mini", workers=1), "mini")
        self.assertEqual(default["scientific_settings"], serial["scientific_settings"])
        self.assertEqual(default["runs"], serial["runs"])
        self.assertEqual(serial["execution_settings"]["workers"], 1)

    def test_launch_provenance_and_result_resolution(self):
        class NoPlannerExecutor(CampaignExecutor):
            def run_experiments(self):
                self.define_paths("test")
                (Path(self.environment.experiments_folder) / self.manifest["result_root"]).mkdir(parents=True)
                for run in self.manifest["runs"]:
                    directory = self.manifest_file.parent / run["attempts"][-1]["directory"]
                    directory.mkdir(parents=True)
                    (directory / "execution.json").write_text('{"state": "finished"}')
        with tempfile.TemporaryDirectory() as temporary, patch(
                "experiment_support.runner.CampaignExecutor", NoPlannerExecutor), redirect_stdout(io.StringIO()):
            first = launch("icaps2025", "mini", temporary)
            second = launch("icaps2025", "mini", temporary)
            self.assertNotEqual(first["run_id"], second["run_id"])
            directory = Path(first["output_root"])
            self.assertEqual(first["status"], "execution_finished")
            self.assertEqual(first["run_count"], 31)
            root, identity = resolve_dataset(load_campaign("icaps2025"), directory)
            self.assertEqual(root, directory / first["result_root"])
            self.assertEqual(identity["profile"], "mini")
            with self.assertRaisesRegex(ValueError, "version differs"):
                resolve_dataset(replace(load_campaign("icaps2025"), version="2"), directory)
            reformatted = Path(temporary) / "reformatted-inputs.json"
            reformatted.write_text(load_campaign("icaps2025").instance_manifest.read_text() + "\n")
            with self.assertRaisesRegex(ValueError, "another frozen"):
                resolve_dataset(replace(load_campaign("icaps2025"), instance_manifest=reformatted), directory)
            self.assertTrue(all("<solution_path>" not in r["command"] for r in first["runs"]))
            for relative, expected in first["provenance_files"].items():
                self.assertEqual(digest(directory / "provenance" / relative), expected)
            self.assertIn("source.patch", first["provenance_files"])
            self.assertIn("requirements.freeze.txt", first["provenance_files"])
            selected = json.loads((directory / "provenance" / "instances.json").read_text())
            self.assertEqual(len(selected), 31)
            with self.assertRaisesRegex(ValueError, "another campaign"):
                resolve_dataset(replace(load_campaign("icaps2025"), campaign_id="another"), directory)


class InspectionTests(unittest.TestCase):
    def test_multiple_configurations_do_not_overwrite_same_instance(self):
        campaign = load_campaign("icaps2025")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for configuration in campaign.configurations.values():
                directory = root / configuration.name / "frozenlake" / "p01" / "solutions" / "frozenlake_p01.sol"
                directory.mkdir(parents=True)
                (directory / "p01.stats").write_text("-1;-1;-1;1;2;3;4;5\n")
            report = inspect(root, profile="paper")
            self.assertEqual(report["instances"], 8)
            self.assertEqual(len(report["runs"]), 8)
            self.assertEqual(report["status_counts"], {"complete": 8})


if __name__ == "__main__":
    unittest.main()
