"""Execution outcomes, attempt selection and strict resume compatibility."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from analysis.results import load_results
from experiment_support.execution import atomic_json, instrument_script, run_job, run_lock, session_groups
from experiment_support.models import Configuration
from experiment_support.resume import pending_runs, recover_legacy, validate_resume


class ExecutionTests(unittest.TestCase):
    def wrapper(self, directory, command):
        script = directory / "wrapper.py"
        script.write_text("import os\nos.system(" + repr(command) + ")\n")
        instrument_script(script, directory / "exit-code.txt")
        return script

    def test_finished_execution_is_independent_of_search_completion(self):
        for code, termination in [(0, "success"), (124, "timeout"), (1, "planner_error")]:
            with self.subTest(code=code), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                record = run_job(self.wrapper(directory, f"exit {code}"), directory, threading.Event())
                self.assertEqual(record["state"], "finished")
                self.assertEqual(record["returncode"], code)
                self.assertEqual(record["termination"], termination)
                self.assertFalse(list(directory.glob("*.stats")))

    def test_memory_failure_is_finished_and_not_retried(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "err_domain_p01.txt").write_text("MemoryError\n")
            record = run_job(self.wrapper(directory, "exit 1"), directory, threading.Event())
            self.assertEqual(record["termination"], "memory_error")
            manifest = {"runs": [{"configuration": "c", "domain": "d", "instance": "i",
                                   "attempts": [{"directory": "."}]}]}
            self.assertEqual(pending_runs(directory, manifest), [])

    def test_interruption_stops_process_and_remains_pending(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            stop = threading.Event()
            timer = threading.Timer(0.4, stop.set)
            timer.start()
            try:
                record = run_job(self.wrapper(directory, "timeout --signal=HUP 60 sleep 60"), directory, stop)
            finally:
                timer.cancel()
            self.assertEqual(record["state"], "interrupted")
            self.assertNotEqual(record["wrapper_returncode"], 0)
            self.assertEqual(session_groups(record["pid"]), set())

    def test_wrapper_setup_failure_is_retryable(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            script = directory / "broken.py"
            script.write_text("raise RuntimeError('setup failed')\n")
            record = run_job(script, directory, threading.Event())
            self.assertEqual(record["state"], "infrastructure_error")

    def test_concurrent_controller_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            with run_lock(temporary):
                with self.assertRaisesRegex(ValueError, "active execution"):
                    with run_lock(temporary):
                        pass


class ResumeTests(unittest.TestCase):
    def test_legacy_recovery_requires_collection_and_timing_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            root = directory / "results"
            rows = []
            blob = {"c": {"d": {}}}
            for name in ("finished", "ambiguous", "never_started"):
                folder = root / "c" / "d" / name
                folder.mkdir(parents=True)
                rows.append({"configuration": "c", "domain": "d", "instance": name})
                blob["c"]["d"][name] = {"num_solutions": -1} if name != "never_started" else {}
                (folder / f"err_d_{name}.txt").write_text(
                    "real 600.01\nuser 590.00\nsys 1.00\n" if name == "finished" else "")
            atomic_json(root / "blob.json", blob)
            manifest = {"result_root": "results", "runs": rows}
            self.assertEqual(recover_legacy(directory, manifest, write=False), 1)
            self.assertFalse(list(root.rglob("execution.json")))
            self.assertEqual([r["instance"] for r in pending_runs(directory, manifest)],
                             ["ambiguous", "never_started"])

    def test_latest_finished_attempt_wins_without_changing_discovery_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            config = Configuration("bw", "hmax", "MinSum", "MaxSum", "Delta", "largestg")
            roots = [directory / "results" / config.name / "d" / "p01",
                     directory / "attempts" / "second" / config.name / "d" / "p01",
                     directory / "attempts" / "third" / config.name / "d" / "p01"]
            for index, root in enumerate(roots):
                solution = root / "solutions" / "d_p01.sol"
                solution.mkdir(parents=True)
                (solution / "p01.stats").write_text(f"{index + 1};10;3;1;2;3;4;5\n")
                atomic_json(root / "execution.json", {"state": "finished" if index < 2 else "pending"})
            atomic_json(directory / "manifest.json", {"result_root": "results", "runs": [
                {"configuration": config.name, "domain": "d", "instance": "p01",
                 "attempts": [{"directory": str(root.relative_to(directory))} for root in roots]}]})
            run = load_results(directory / "results", {"c": config}, ("d",))["c", "d", "p01"]
            self.assertEqual(run.directory, roots[1])
            self.assertEqual(run.first_solution["best"], 2)
            self.assertEqual(run.discovery_order, 0)

    def test_resume_checks_science_runtime_and_source_but_allows_worker_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "provenance").mkdir()
            (directory / "provenance" / "requirements.freeze.txt").write_bytes(b"dependencies\n")
            old = {"campaign": {"id": "c", "version": "1"}, "profile": "paper",
                   "scientific_settings": {"timeout_seconds": 600, "memory_kb": 8000000, "hash": "inputs"},
                   "execution_settings": {"workers": 2, "python": sys.executable, "python_version": "3",
                                          "pythonhashseed": "0", "versions": {"pddl": "1"}},
                   "planner_files": {"search.py": "source"}, "runs": [{
                       "configuration": "c", "domain": "d", "instance": "i", "domain_path": "d.pddl",
                       "problem_path": "i.pddl", "domain_sha256": "d", "problem_sha256": "i",
                       "command": "python planner.py d.pddl i.pddl old-output -m bw"}]}
            current = deepcopy(old)
            current["execution_settings"]["workers"] = 1
            current["runs"][0]["command"] = "python planner.py d.pddl i.pddl new-output -m bw"
            with patch("experiment_support.resume.subprocess.check_output", return_value=b"dependencies\n"), \
                    patch("experiment_support.resume.planner_files", return_value={"search.py": "source"}):
                self.assertEqual(validate_resume(directory, old, current), {"search.py": "source"})
                for field, value in [("pythonhashseed", "unset"), ("versions", {"pddl": "2"})]:
                    changed = deepcopy(current)
                    changed["execution_settings"][field] = value
                    with self.assertRaisesRegex(ValueError, "runtime differs"):
                        validate_resume(directory, old, changed)
                changed = deepcopy(current)
                changed["scientific_settings"]["hash"] = "other inputs"
                with self.assertRaisesRegex(ValueError, "inputs or resource"):
                    validate_resume(directory, old, changed)
                changed = deepcopy(current)
                changed["runs"][0]["command"] += " --other-flag"
                with self.assertRaisesRegex(ValueError, "command differs"):
                    validate_resume(directory, old, changed)
            with patch("experiment_support.resume.subprocess.check_output", return_value=b"dependencies\n"), \
                    patch("experiment_support.resume.planner_files", return_value={"search.py": "changed"}):
                with self.assertRaisesRegex(ValueError, "source differs"):
                    validate_resume(directory, old, current)


if __name__ == "__main__":
    unittest.main()
