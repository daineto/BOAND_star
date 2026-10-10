"""A new paper can be discovered, frozen and dry-run without runner edits."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from experiment_support.freeze_inputs import freeze
from experiment_support.models import REPOSITORY_ROOT


class TemplateTests(unittest.TestCase):
    def test_new_campaign_smoke_manifest(self):
        with tempfile.TemporaryDirectory(prefix="campaign_validation_", dir=REPOSITORY_ROOT / "campaigns") as temporary:
            folder = Path(temporary)
            identifier = folder.name
            for source in (REPOSITORY_ROOT / "docs" / "campaign-template").glob("*.py"):
                (folder / source.name).write_text(source.read_text().replace("new_paper", identifier))
            manifest = folder / "instances.json"
            freeze(identifier, [("frozenlake", "benchmarks/icaps2025/frozenlake")], manifest)
            with self.assertRaises(FileExistsError):
                freeze(identifier, [("frozenlake", "benchmarks/icaps2025/frozenlake")], manifest)
            result = subprocess.run([sys.executable, "-B", "-m", "experiment_support.run", identifier,
                                     "--profile", "smoke", "--dry-run"], cwd=REPOSITORY_ROOT,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["campaign"]["id"], identifier)
            self.assertEqual(data["run_count"], 1)
            self.assertEqual(data["runs"][0]["instance"], "motivating")
            self.assertFalse((REPOSITORY_ROOT / "runs" / identifier).exists())


if __name__ == "__main__":
    unittest.main()
