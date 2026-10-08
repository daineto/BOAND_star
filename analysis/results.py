"""Read planner artifacts without trusting the external runner's summary.csv."""
from dataclasses import dataclass
from pathlib import Path
import json

import pandas as pd


STAT_FIELDS = ("best", "worst", "size", "time", "iterations", "expansions", "generations", "max_open")


def parse_stats_line(line):
    values = line.strip().split(";")
    if len(values) != len(STAT_FIELDS):
        raise ValueError(f"Expected eight statistics fields, got {len(values)}: {line!r}")
    return {name: float(value) if name == "time" else int(value)
            for name, value in zip(STAT_FIELDS, values)}


def read_stats(file):
    return tuple(parse_stats_line(line) for line in Path(file).read_text().splitlines() if line.strip())


@dataclass(frozen=True)
class Run:
    configuration: str
    domain: str
    instance: str
    directory: Path
    stats: tuple
    discovery_order: int

    @property
    def complete(self):
        # Same completion criterion as the original notebook.
        return bool(self.stats) and self.stats[-1]["best"] == -1

    @property
    def first_solution(self):
        return self.stats[0] if self.stats and self.stats[0]["best"] != -1 else None

    @property
    def status(self):
        if self.complete:
            return "complete"
        if self.first_solution:
            return "partial"
        return "no_stats"

    @property
    def execution(self):
        file = self.directory / "execution.json"
        return json.loads(file.read_text()) if file.is_file() else None


def attempt_directories(root):
    """Select the latest finished attempt, or latest attempt if none finished.

    Legacy archives retain their original layout and discovery order.
    """
    root = Path(root).resolve()
    for directory in root.parents:
        file = directory / "manifest.json"
        if not file.is_file():
            continue
        manifest = json.loads(file.read_text())
        if (directory / manifest.get("result_root", "")).resolve() != root:
            continue
        selected = {}
        for run in manifest["runs"]:
            attempts = []
            for attempt in run.get("attempts", []):
                folder = (directory / attempt["directory"]).resolve()
                if not folder.is_relative_to(directory):
                    raise ValueError("Attempt directory escapes the run directory")
                record = folder / "execution.json"
                state = json.loads(record.read_text()) if record.exists() else attempt.get("execution", {})
                attempts.append((folder, state.get("state") == "finished"))
            finished = [folder for folder, done in attempts if done]
            if attempts:
                selected[run["configuration"], run["domain"], run["instance"]] = (
                    finished[-1] if finished else attempts[-1][0])
        return selected
    return {}


def load_results(root, configurations=None, domains=None):
    """Index runs by configuration/domain/instance, retaining legacy discovery order.

    Only the supplied result root and canonical configuration/domain names are read.
    """
    if configurations is None or domains is None:
        # Compatibility default; new campaigns pass both arguments explicitly.
        from campaigns.icaps2025.campaign import PAPER_CONFIGURATIONS, PAPER_DOMAINS
        configurations = PAPER_CONFIGURATIONS if configurations is None else configurations
        domains = PAPER_DOMAINS if domains is None else domains
    runs = {}
    selected = attempt_directories(root)
    for label, configuration in configurations.items():
        directory = Path(root) / configuration.name
        if not directory.is_dir():
            raise FileNotFoundError(f"No results for {configuration.name}: {directory}")
        for domain in domains:
            parent = directory / domain
            if not parent.is_dir():
                continue
            for order, instance in enumerate(p for p in parent.iterdir() if p.is_dir()):
                name = instance.name
                instance = selected.get((configuration.name, domain, name), instance)
                file = instance / "solutions" / f"{parent.name}_{name}.sol" / f"{name}.stats"
                stats = read_stats(file) if file.is_file() else ()
                runs[label, domain, name] = Run(label, domain, name, instance, stats, order)
    return runs


def results_table(runs):
    """One row per run, including missing/partial statistics and first/final values."""
    rows = []
    for run in runs.values():
        row = {"configuration": run.configuration, "domain": run.domain, "instance": run.instance,
               "status": run.status, "source": str(run.directory), "discovery_order": run.discovery_order}
        row.update({f"first_{key}": value for key, value in (run.first_solution or {}).items()})
        row.update({f"final_{key}": value for key, value in (run.stats[-1] if run.complete else {}).items()})
        rows.append(row)
    return pd.DataFrame(rows)


def domain_runs(runs, label, domain):
    return sorted((run for run in runs.values() if run.configuration == label and run.domain == domain),
                  key=lambda run: run.discovery_order)



def __getattr__(name):
    # Preserve imports used by pre-migration analysis scripts.
    if name in {"heuristic_points", "quality_points", "coverage_table", "dataset_diagnostics", "COVERAGE_CONFIGURATIONS"}:
        from campaigns.icaps2025 import analysis
        return getattr(analysis, name)
    raise AttributeError(name)
