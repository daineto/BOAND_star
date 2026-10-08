"""Scheduling and analysis contracts; no expensive planner runs in unit tests."""
import tempfile
import subprocess
import sys
import unittest
from pathlib import Path

from analysis.results import Run, coverage_table, heuristic_points, load_results, quality_points
from experiment_support.configurations import (
    MEMORY_KB, MINI_CONFIGURATIONS, PAPER_CONFIGURATIONS, PARALLEL_RUNS, TIMEOUT_SECONDS,
)
from experiment_support.runner import build_environment


def row(best, worst=10, time=1):
    return {"best": best, "worst": worst, "size": 3, "time": time,
            "iterations": 4, "expansions": 5, "generations": 6, "max_open": 7}


class CampaignTests(unittest.TestCase):
    def test_direct_planner_import_from_another_directory(self):
        root = Path(__file__).resolve().parents[1]
        script = root / "planner" / "planner.py"
        # Reproduce the script-directory search path that exposed stdlib shadowing.
        code = "import sys, runpy; sys.path.insert(0, sys.argv[1]); runpy.run_path(sys.argv[2], run_name='import_check')"
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, "-B", "-c", code, str(script.parent), str(script)],
                                    cwd=directory, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_mini_contract(self):
        env = build_environment("mini")
        self.assertEqual(env.get_nruns(), 31)
        self.assertEqual((env.time, env.memory, env.parallel_processes), (600, 8_000_000, 2))
        planner, details = next(iter(env.run_dictionary.items()))
        self.assertEqual(planner.name, "bw_hmax_MinSum_MaxSum_Delta_largestg_600")
        self.assertEqual([d.name for d in details["DOMAINS"]], ["frozenlake"])
        self.assertIn("-ch hmax", planner.get_cmd(*details["DOMAINS"][0].instances[0], "/tmp/out"))

    def test_boand_bw_contract(self):
        env = build_environment("BOAND_bw")
        mini = build_environment("mini")
        self.assertEqual(env.get_nruns(), 196)
        self.assertEqual((env.time, env.memory, env.parallel_processes), (600, 8_000_000, 2))
        planner, details = next(iter(env.run_dictionary.items()))
        self.assertEqual(len(env.run_dictionary), 1)
        self.assertEqual(planner.name, next(iter(mini.run_dictionary)).name)
        self.assertEqual(len(details["DOMAINS"]), 11)

    def test_paper_contract(self):
        env = build_environment("paper")
        self.assertEqual(len(env.run_dictionary), 8)
        self.assertEqual(env.get_nruns(), 8 * 196)
        self.assertEqual((env.time, env.memory, env.parallel_processes),
                         (TIMEOUT_SECONDS, MEMORY_KB, PARALLEL_RUNS))
        self.assertTrue(all(c.classical == "hmax" for c in PAPER_CONFIGURATIONS.values()))


class AnalysisTests(unittest.TestCase):
    def test_canonical_configuration_results(self):
        configuration = MINI_CONFIGURATIONS["BOAND bw"]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            directory = root / configuration.name / "frozenlake" / "p01" / "solutions" / "frozenlake_p01.sol"
            directory.mkdir(parents=True)
            (directory / "p01.stats").write_text("4;10;3;1.5;4;5;6;7\n-1;-1;-1;2;4;5;6;7\n")
            run = load_results(root, MINI_CONFIGURATIONS, ("frozenlake",))["BOAND bw", "frozenlake", "p01"]
            self.assertTrue(run.complete)
            self.assertEqual(run.first_solution["best"], 4)

    def test_partial_quality_and_completed_coverage(self):
        runs = {}
        for label, stats in (("BOAND bw", (row(4),)), ("MaxSum", (row(7), row(-1)))):
            runs[label, "frozenlake", "p01"] = Run(label, "frozenlake", "p01", Path("/tmp"), stats, 0)
        table = coverage_table(runs, ("frozenlake",))
        self.assertEqual(table.loc["Total", "BOAND bw"], 0)
        self.assertEqual(table.loc["Total", "MaxSum"], 1)
        points = quality_points(runs, "BOAND bw", "MaxSum", "best", ("frozenlake",))
        self.assertEqual(points[["x", "y"]].values.tolist(), [[7, 4]])

    def test_pairing_correction_is_explicit(self):
        runs = {}
        for label, identities in (("SumMin", ("a", "b")), ("MinSum", ("b", "a"))):
            for order, name in enumerate(identities):
                runs[label, "frozenlake", name] = Run(label, "frozenlake", name, Path("/tmp"), (row(-1),), order)
        legacy = heuristic_points(runs, "SumMin", "MinSum", ("frozenlake",))
        joined = heuristic_points(runs, "SumMin", "MinSum", ("frozenlake",), "instance")
        self.assertFalse((legacy.left_instance == legacy.right_instance).all())
        self.assertTrue((joined.left_instance == joined.right_instance).all())

    def test_archive_totals(self):
        root = Path(__file__).resolve().parents[1]
        table = coverage_table(load_results(root / "results" / "icaps2025" / "published"))
        self.assertEqual(table.loc["Total", ["BOAND bw", "BOAND wb", "MaxSum", "AND best"]].tolist(),
                         [124, 120, 134, 122])


if __name__ == "__main__":
    unittest.main()
