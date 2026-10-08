"""Run a development profile within 60 seconds and check its policies and costs."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import signal
import tempfile
from time import perf_counter

from .campaign import CAMPAIGN, DOMAINS


@contextmanager
def deadline(seconds, suite="Smoke"):
    def expired(_signum, _frame):
        raise TimeoutError(f"{suite} suite exceeded its {seconds}-second wall-time budget")

    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def check_outcome(key, run, expected):
    execution = run.execution or {}
    if execution.get("state") != "finished" or execution.get("returncode") != 0:
        raise ValueError(f"{key}: unsuccessful execution: {execution}")
    if not run.complete:
        raise ValueError(f"{key}: search did not complete")
    costs = sorted([row["best"], row["worst"]] for row in run.stats if row["best"] != -1)
    if costs != expected:
        raise ValueError(f"{key}: expected costs {expected}, got {costs}")


def check_run(directory, profile="smoke"):
    from analysis.results import load_results
    from analysis.validate_policies import parse_policy, validate_policy
    from experiment_support.campaigns import input_path, read_instances, resolve_dataset
    from pddl import parse_domain, parse_problem
    from planner.preprocessing import get_alloutcome_determinization

    directory = Path(directory).resolve()
    manifest = json.loads((directory / "manifest.json").read_text())
    if profile not in ("smoke", "performance"):
        raise ValueError(f"Unknown development validation profile: {profile}")
    if manifest["profile"] != profile:
        raise ValueError(f"Expected a {profile}-profile run")
    root, _ = resolve_dataset(CAMPAIGN, directory)
    expected_file = "expected.json" if profile == "smoke" else "performance-expected.json"
    expected = json.loads(Path(__file__).with_name(expected_file).read_text())
    if expected["schema_version"] != 1 or expected["campaign_version"] != CAMPAIGN.version:
        raise ValueError("Expected outcomes use a different campaign version")
    entries = {f"{e['domain']}/{e['instance']}": e for e in read_instances(CAMPAIGN, profile)}
    runs = {f"{r.domain}/{r.instance}": r for r in load_results(root, CAMPAIGN.configurations, DOMAINS).values()}
    if runs.keys() != entries.keys() or runs.keys() != expected["costs"].keys():
        raise ValueError("Results, profile selection and expected outcomes must contain exactly the same instances")
    report = {"instances": len(runs), "domains": len(DOMAINS), "validated_policies": 0, "runs": {}}
    cwd = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="journal-policy-check-") as temporary:
        try:
            os.chdir(temporary)
            for key, run in runs.items():
                check_outcome(key, run, expected["costs"][key])
                stderr = (run.directory / f"err_{run.domain}_{run.instance}.txt").read_text()
                if "Traceback" in stderr or "MemoryError" in stderr:
                    raise ValueError(f"{key}: error in planner stderr")
                solutions = [row for row in run.stats if row["best"] != -1]
                policies = sorted(run.directory.rglob("*.boand.*.out"))
                if len(policies) != len(solutions):
                    raise ValueError(f"{key}: policy/statistics count mismatch")
                if policies:
                    entry = entries[key]
                    task = get_alloutcome_determinization(
                        parse_domain(str(input_path(entry["domain_path"]))),
                        parse_problem(str(input_path(entry["problem_path"]))),
                    )
                    for file, row in zip(policies, solutions):
                        costs = validate_policy(task, parse_policy(file))
                        if (costs["best"], costs["worst"]) != (row["best"], row["worst"]):
                            raise ValueError(f"{file}: replay costs disagree with statistics")
                        report["validated_policies"] += 1
                report["runs"][key] = {"costs": expected["costs"][key], "search_seconds": run.stats[-1]["time"],
                                      "statistics": run.stats[-1], "execution": run.execution}
        finally:
            os.chdir(cwd)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("smoke", "performance"), default="smoke",
                        help="Fixed correctness or performance selection (default: smoke)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dataset", type=Path, help="Validate an existing profile run without rerunning planners")
    mode.add_argument("--dry-run", action="store_true", help="Print the manifest without running planners")
    args = parser.parse_args()
    if args.dry_run:
        from experiment_support.runner import launch
        launch(CAMPAIGN.campaign_id, args.profile, dry_run=True)
        return
    if not args.dataset and os.environ.get("PYTHONHASHSEED") != "0":
        parser.error("Set PYTHONHASHSEED=0 for controlled comparisons")
    start = perf_counter()
    try:
        with deadline(60, args.profile.capitalize()):
            if args.dataset:
                directory = args.dataset.resolve()
            else:
                from experiment_support.runner import launch
                directory = Path(launch(CAMPAIGN.campaign_id, args.profile)["output_root"])
            report = check_run(directory, args.profile)
            report["wall_seconds"] = perf_counter() - start
            report["timed_scope"] = "validation only" if args.dataset else "launch, execution and validation"
            report["profile"] = args.profile
            file = directory / f"{args.profile}-validation.json"
            file.write_text(json.dumps(report, indent=2) + "\n")
    except (ValueError, TimeoutError) as error:
        parser.exit(1, f"{args.profile.capitalize()} validation failed: {error}\n")
    print(f"Passed: {report['instances']} instances, {report['domains']} domains, "
          f"{report['validated_policies']} policies; {report['wall_seconds']:.2f}s ({report['timed_scope']}).")
    print(f"Validation report: {file}")


if __name__ == "__main__":
    main()
