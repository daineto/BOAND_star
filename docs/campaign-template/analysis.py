"""Minimal analysis scaffold; add this paper's scientific plot/table rules here."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from analysis.results import load_results, results_table
from experiment_support.campaigns import resolve_dataset
from .campaign import CAMPAIGN


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, help="A run directory or published archive")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    root, identity = resolve_dataset(CAMPAIGN, args.dataset)
    domains = tuple(dict.fromkeys(entry["domain"] for entry in
                                 json.loads(CAMPAIGN.instance_manifest.read_text())["instances"]))
    # Select the configurations actually executed by this run's profile.
    labels = CAMPAIGN.profiles[identity.get("profile", "paper")].configurations
    configurations = {label: CAMPAIGN.configurations[label] for label in labels}
    runs = load_results(root, configurations, domains)
    args.output.mkdir(parents=True, exist_ok=True)
    results_table(runs).to_csv(args.output / "runs.csv", index=False)
    (args.output / "analysis_manifest.json").write_text(json.dumps({
        "schema_version": 1, "campaign": CAMPAIGN.campaign_id, "version": CAMPAIGN.version,
        "dataset": identity, "generated_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2) + "\n")
    print(f"Exported {len(runs)} runs to {args.output}")
