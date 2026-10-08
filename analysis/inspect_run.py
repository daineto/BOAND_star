"""Inspect raw run artifacts and compare statistics without comparing timing."""
import argparse
from collections import Counter
import json
from pathlib import Path

from .results import load_results
from experiment_support.campaigns import load_campaign, resolve_dataset


def inspect(root, campaign_id="icaps2025", profile=None):
    campaign = load_campaign(campaign_id)
    result_root, identity = resolve_dataset(campaign, root)
    profile = profile or identity.get("profile") or ("mini" if "mini" in campaign.profiles else "paper")
    specification = campaign.profiles[profile]
    configurations = {name: campaign.configurations[name] for name in specification.configurations}
    domains = specification.domains or tuple(dict.fromkeys(e["domain"] for e in
                json.loads(campaign.instance_manifest.read_text())["instances"]))
    runs = load_results(result_root, configurations, domains)
    simple_keys = len(configurations) == 1 and len(domains) == 1
    report = {"root": identity["path"], "campaign": campaign_id, "profile": profile, "instances": len(runs),
              "status_counts": dict(Counter(run.status for run in runs.values())), "runs": {}}
    if "instance_manifest_migration" in identity:
        report["instance_manifest_migration"] = identity["instance_manifest_migration"]
    for run in runs.values():
        stderr = run.directory / f"err_{run.directory.parent.name}_{run.instance}.txt"
        stdout = run.directory / f"out_{run.directory.parent.name}_{run.instance}.txt"
        err = stderr.read_text() if stderr.exists() else ""
        out = stdout.read_text() if stdout.exists() else ""
        key = run.instance if simple_keys else f"{run.configuration}/{run.domain}/{run.instance}"
        report["runs"][key] = {
            "status": run.status, "solutions": len(list(run.directory.rglob("*.boand.*.out"))),
            "costs": [[row["best"], row["worst"]] for row in run.stats if row["best"] != -1],
            "traceback": "Traceback" in err, "memory_error": "MemoryError" in err,
            "heuristic_rejected": "heuristic must be" in out,
            "statistics": run.stats,
        }
        if run.execution:
            report["runs"][key]["execution"] = run.execution
    executions = [run.execution for run in runs.values() if run.execution]
    if executions:
        report["execution_counts"] = dict(Counter(record["state"] for record in executions))
    return report


def compare(current, reference):
    differences = {}
    lhs, rhs = current["runs"], reference["runs"]
    for instance in sorted(lhs.keys() | rhs.keys()):
        if instance not in lhs or instance not in rhs:
            differences[instance] = {"missing_from": "current" if instance not in lhs else "reference"}
            continue
        changes = {}
        for field in ("status", "solutions", "costs", "traceback", "memory_error", "heuristic_rejected"):
            if lhs[instance][field] != rhs[instance][field]:
                changes[field] = {"current": lhs[instance][field], "reference": rhs[instance][field]}
        a = [{key: value for key, value in row.items() if key != "time"} for row in lhs[instance]["statistics"]]
        b = [{key: value for key, value in row.items() if key != "time"} for row in rhs[instance]["statistics"]]
        if a != b:
            changes["non_time_statistics"] = {"current": a, "reference": b}
        if changes:
            differences[instance] = changes
    return {"reference_root": reference["root"], "different_instances": len(differences),
            "differences": differences}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Generated run directory or results/<campaign-id>/published/.")
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--campaign", default="icaps2025")
    parser.add_argument("--profile", help="Default: recorded run profile, or mini for the ICAPS archive")
    args = parser.parse_args()
    report = inspect(args.root, args.campaign, args.profile)
    if args.reference:
        report["comparison"] = compare(report, inspect(args.reference, args.campaign, report["profile"]))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
