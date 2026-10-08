"""ICAPS 2025 data-selection rules and the six published plot specifications."""
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path

import matplotlib
from matplotlib import pyplot as plt
import pandas as pd

from analysis.results import (domain_runs, load_results, results_table)
from analysis.plots import (HeuristicPlot, QualityPlot, plot_heuristic, plot_coverage, plot_quality)
from experiment_support.campaigns import digest, resolve_dataset
from experiment_support.models import REPOSITORY_ROOT
from experiment_support.provenance import source_state, source_patch, runtime_information
from .campaign import CAMPAIGN, PAPER_CONFIGURATIONS, PAPER_DOMAINS

HEURISTIC_PLOTS = (
    HeuristicPlot("SumMin", "MinSum", "AND* best", "MinSum_SumMin_best.pdf"),
    HeuristicPlot("BOAND bw2", "BOAND bw", "BOAND* best-worst", "MinSum_SumMin_bw.pdf"),
    HeuristicPlot("BOAND wb2", "BOAND wb", "BOAND* worst-best", "MinSum_SumMin_wb.pdf"),
)
QUALITY_PLOTS = (
    QualityPlot("BOAND bw", "MaxSum", "best", "AND* worst", "best.pdf"),
    QualityPlot("BOAND wb", "MinSum", "worst", "AND* best", "worst.pdf"),
)
PLANNER_LABELS = {"BOAND bw": "BOAND* best-worst", "BOAND wb": "BOAND* worst-best",
                  "MaxSum": "AND* worst", "AND best": "AND* best"}


def heuristic_points(runs, left, right, domains=PAPER_DOMAINS, pairing="legacy"):
    """Completed search times, with incomplete/missing runs plotted at timeout.

    legacy preserves the old notebook's independently collected ordering. instance
    explicitly joins identities and is a separate analysis correction.
    """
    points = []
    for domain in domains:
        lhs, rhs = domain_runs(runs, left, domain), domain_runs(runs, right, domain)
        if pairing == "legacy":
            if len(lhs) != len(rhs):
                raise ValueError(f"Unequal legacy comparison lengths in {domain}: {left}={len(lhs)}, {right}={len(rhs)}")
            pairs = zip(lhs, rhs)
        elif pairing == "instance":
            lmap, rmap = {r.instance: r for r in lhs}, {r.instance: r for r in rhs}
            pairs = ((lmap.get(name), rmap.get(name)) for name in sorted(lmap.keys() | rmap.keys()))
        else:
            raise ValueError(f"Unknown pairing: {pairing}")
        for a, b in pairs:
            points.append({"domain": domain, "left_instance": a.instance if a else None,
                           "right_instance": b.instance if b else None,
                           "x": a.stats[-1]["time"] if a and a.complete else PAPER_CONFIGURATIONS[left].timeout,
                           "y": b.stats[-1]["time"] if b and b.complete else PAPER_CONFIGURATIONS[right].timeout})
    return pd.DataFrame(points, columns=["domain", "left_instance", "right_instance", "x", "y"])


def quality_points(runs, bi_objective, single_objective, criterion, domains=PAPER_DOMAINS):
    # Preserve first-solution selection, including partial frontier computations.
    points = []
    for domain in domains:
        for run in domain_runs(runs, bi_objective, domain):
            other = runs.get((single_objective, domain, run.instance))
            if run.first_solution and other and other.first_solution:
                points.append({"domain": domain, "instance": run.instance,
                               "x": other.first_solution[criterion], "y": run.first_solution[criterion]})
    return pd.DataFrame(points, columns=["domain", "instance", "x", "y"])


COVERAGE_CONFIGURATIONS = ("BOAND bw", "BOAND wb", "MaxSum", "AND best")


def coverage_table(runs, domains=PAPER_DOMAINS):
    rows = []
    for domain in domains:
        # Expose the actual union rather than copying paper instance counts.
        names = {run.instance for run in runs.values() if run.domain == domain}
        row = {"Domain": domain, "Instances": len(names)}
        row.update({label: sum(run.complete for run in domain_runs(runs, label, domain))
                    for label in COVERAGE_CONFIGURATIONS})
        rows.append(row)
    table = pd.DataFrame(rows).set_index("Domain")
    table.loc["Total"] = table.sum()
    return table.astype(int)


def dataset_diagnostics(runs):
    records = []
    for domain in PAPER_DOMAINS:
        for label in PAPER_CONFIGURATIONS:
            selected = domain_runs(runs, label, domain)
            records.append({"configuration": label, "domain": domain, "instances": len(selected),
                            "complete": sum(run.complete for run in selected),
                            "partial": sum(run.status == "partial" for run in selected)})
    return pd.DataFrame(records)

def generate_paper_outputs(runs, output_directory, pairing="legacy", dataset=None):
    """Export six PDFs, their point data, Table 1 and dataset diagnostics."""
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    figures = {}
    with matplotlib.rc_context({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 13}):
        for specification in HEURISTIC_PLOTS:
            points = heuristic_points(runs, specification.left, specification.right, pairing=pairing)
            points.to_csv(output / Path(specification.filename).with_suffix(".csv"), index=False)
            figures[specification.filename] = plot_heuristic(points, specification)
        figures["coverage.pdf"] = plot_coverage(runs, PAPER_CONFIGURATIONS, COVERAGE_CONFIGURATIONS, PLANNER_LABELS)
        for specification in QUALITY_PLOTS:
            points = quality_points(runs, specification.bi_objective, specification.single_objective,
                                    specification.criterion)
            points.to_csv(output / Path(specification.filename).with_suffix(".csv"), index=False)
            figures[specification.filename] = plot_quality(points, specification)
        for filename, figure in figures.items():
            figure.savefig(output / filename, bbox_inches="tight")
    table = coverage_table(runs)
    table.to_csv(output / "coverage_table.csv")
    (output / "coverage_table.md").write_text(table.to_markdown() + "\n")
    results_table(runs).to_csv(output / "runs.csv", index=False)
    dataset_diagnostics(runs).to_csv(output / "dataset_diagnostics.csv", index=False)
    (output / "analysis_settings.txt").write_text(
        f"heuristic_pairing={pairing}\nquality=first solution, including partial runs\n"
        "coverage=final best=-1 marker\ncycle_cost_display=1200\n"
        "time=elapsed search time, excluding preprocessing\n")
    identity = resolve_dataset(CAMPAIGN, dataset)[1] if dataset is not None else {
        "kind": "in_memory", "sources": sorted({str(run.directory.parent.parent.parent) for run in runs.values()})}
    statistics_hashes = {}
    for run in runs.values():
        file = run.directory / "solutions" / f"{run.directory.parent.name}_{run.instance}.sol" / f"{run.instance}.stats"
        if file.is_file():
            statistics_hashes[f"{run.configuration}/{run.domain}/{run.instance}"] = digest(file)
    (output / "analysis_source.patch").write_bytes(source_patch(exclude=output))
    (output / "analysis_manifest.json").write_text(json.dumps({
        "schema_version": 1, "campaign": CAMPAIGN.campaign_id, "campaign_version": CAMPAIGN.version,
        "dataset": identity, "pairing": pairing, "statistics_sha256": statistics_hashes,
        "analysis_source": source_state(), "analysis_source_patch_sha256": digest(output / "analysis_source.patch"),
        "environment": runtime_information(), "output_files": list(figures) + ["coverage_table.csv"],
    }, indent=2) + "\n")
    return figures, table


def load_paper_results(dataset="published"):
    root, identity = resolve_dataset(CAMPAIGN, dataset)
    if identity.get("profile") not in (None, "paper"):
        raise ValueError("The six paper outputs require a paper-profile dataset; use inspect_run for mini")
    return load_results(root, PAPER_CONFIGURATIONS, PAPER_DOMAINS)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate ICAPS 2025 figures and Table 1 from one dataset.")
    parser.add_argument("--dataset", "--results", dest="dataset", default="published",
                        help="published, a self-contained run directory, or a legacy configuration root")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pairing", choices=("legacy", "instance"), default="legacy")
    args = parser.parse_args(argv)
    _, identity = resolve_dataset(CAMPAIGN, args.dataset)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    output = args.output or (Path(identity['path']) / "analysis" / stamp if identity['kind'] == 'run'
                             else REPOSITORY_ROOT / "outputs" / CAMPAIGN.campaign_id / "published" / stamp)
    figures, table = generate_paper_outputs(load_paper_results(args.dataset), output, args.pairing, args.dataset)
    print(table.to_string())
    print(f"Wrote {len(figures)} plots and Table 1 to {output.resolve()}")
    for figure in figures.values():
        plt.close(figure)


if __name__ == "__main__":
    main()
