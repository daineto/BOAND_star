"""Shared campaign runner; frozen scientific definitions live under campaigns/."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import shutil
import sys
from uuid import uuid4

from planning_experiments.data_structures import Domain, Environment, Planner
from planning_experiments.launch_experiments import Executor

from .campaigns import input_path, load_campaign, read_instances
from .models import REPOSITORY_ROOT
from .provenance import resolved_definition, runtime_information, save_snapshot, source_state
from .execution import atomic_json, execute_jobs, instrument_script, run_lock, timestamp
from .resume import job_key, pending_runs, planner_files, recover_legacy, validate_resume


class MyPlannerWrapper(Planner):
    def __init__(self, configuration):
        super().__init__(configuration.name, str(REPOSITORY_ROOT / "planner"))
        self.configuration = configuration

    def get_cmd(self, domain_path, instance_path, solution_path):
        return shlex.join((sys.executable, str(Path(self.planner_path) / "planner.py"),
                           str(domain_path), str(instance_path), str(solution_path),
                           *self.configuration.flags))


class FrozenCollector:
    def __init__(self, entries):
        self.pairs = [(str(input_path(e["domain_path"])), str(input_path(e["problem_path"]))) for e in entries]

    def collect_instances(self, _directory):
        return list(self.pairs)


def build_environment(profile, output_root=None, campaign_id="icaps2025", workers=None):
    campaign = load_campaign(campaign_id)
    entries = read_instances(campaign, profile)
    root = Path(output_root or REPOSITORY_ROOT / "runs" / campaign_id)
    environment = Environment(str(root.resolve()), name="EVALUATION")
    environment.campaign = campaign
    environment.instance_entries = entries
    domains = []
    for name in dict.fromkeys(e["domain"] for e in entries):
        selected = [e for e in entries if e["domain"] == name]
        domains.append(Domain(name, str(input_path(selected[0]["domain_path"]).parent), FrozenCollector(selected)))
    for label in campaign.profiles[profile].configurations:
        environment.add_run(system=MyPlannerWrapper(campaign.configurations[label]), domains=domains)
    environment.set_time(campaign.timeout_seconds)
    environment.set_memory(campaign.memory_kb)
    parallel = campaign.default_workers if workers is None else workers
    if parallel <= 0:
        raise ValueError("Worker count must be positive")
    environment.set_parallel_processes(parallel)
    return environment


def campaign_manifest(environment, profile):
    campaign = environment.campaign
    hashes = {(e["domain"], e["instance"]): e for e in environment.instance_entries}
    runs = []
    for planner, details in environment.run_dictionary.items():
        for domain in details["DOMAINS"]:
            for domain_path, problem_path in domain.instances:
                name = Path(problem_path).stem
                runs.append({"configuration": planner.name, "domain": domain.name, "instance": name,
                             "domain_path": domain_path, "problem_path": problem_path,
                             "domain_sha256": hashes[domain.name, name]["domain_sha256"],
                             "problem_sha256": hashes[domain.name, name]["problem_sha256"],
                             "command": planner.get_cmd(domain_path, problem_path, "<solution_path>")})
    runtime = runtime_information()
    return {"schema_version": 1, "campaign": resolved_definition(campaign), "profile": profile,
            "scientific_settings": {"timeout_seconds": environment.time, "memory_kb": environment.memory,
                                    "instance_manifest_sha256": campaign_manifest_hash(campaign)},
            "execution_settings": {"workers": environment.parallel_processes, **runtime},
            "source": source_state(), "output_root": environment.experiments_folder,
            "run_count": len(runs), "runs": runs,
            # Retained aliases for existing manifest consumers.
            "timeout_seconds": environment.time, "memory_kb": environment.memory,
            "parallel_runs": environment.parallel_processes, **runtime}


def campaign_manifest_hash(campaign):
    from .campaigns import digest
    return digest(campaign.instance_manifest)


class CampaignExecutor(Executor):
    """Expose the external runner's result root without changing its execution."""
    def __init__(self, environment, manifest, manifest_file):
        super().__init__(environment)
        self.manifest = manifest
        self.manifest_file = manifest_file
        self.selected_keys = {f"{planner.name}/{domain.name}/{Path(pair[1]).stem}"
                              for planner, details in environment.run_dictionary.items()
                              for domain in details["DOMAINS"] for pair in domain.instances}

    def define_paths(self, exp_id):
        super().define_paths(exp_id)
        result_root = Path(self.results_folder) / f"RUN_{exp_id}"
        directory = self.manifest_file.parent
        self.manifest.setdefault("result_root", str(result_root.relative_to(directory)))
        planners = {planner.name: planner for planner in self.environment.run_dictionary}
        for run in self.manifest["runs"]:
            if job_key(run) not in self.selected_keys:
                continue
            solution = (result_root / run["configuration"] / run["domain"] / run["instance"] /
                        "solutions" / f"{run['domain']}_{run['instance']}.sol")
            command = planners[run["configuration"]].get_cmd(run["domain_path"], run["problem_path"], solution)
            if not run.get("attempts"):
                run["solution_path"] = str(solution)
                run["command"] = command
            run.setdefault("attempts", []).append({"directory": str(solution.parent.parent.relative_to(directory)),
                                                   "command": command})
        write_manifest(self.manifest_file, self.manifest)

    def execute_scripts(self, script_list, run_folder, blob_path, script2blob, batch_id):
        from planning_experiments.save_results import save_results
        from planning_experiments.summary import create_summary
        jobs = []
        for name, script in script_list:
            identity = script2blob[name]
            folder = Path(run_folder) / identity["planner"] / identity["domain"] / identity["instance"]
            instrument_script(script, folder / "exit-code.txt")
            atomic_json(folder / "execution.json", {"schema_version": 1, "state": "pending"})
            jobs.append({"key": f"{identity['planner']}/{identity['domain']}/{identity['instance']}",
                         "script": script, "directory": str(folder), **identity})

        def finished(job, record):
            if record["state"] == "finished":
                save_results(blob_path, job["planner"], job["domain"], job["instance"])
            self.manifest["execution_progress"] = {
                "finished": len(self.manifest["runs"]) - len(pending_runs(self.manifest_file.parent, self.manifest,
                                                                         check_active=False)),
                "total": len(self.manifest["runs"]), "updated_at": timestamp()}
            write_manifest(self.manifest_file, self.manifest)

        execute_jobs(jobs, self.environment.parallel_processes, finished)
        summary = Path(run_folder) / (f"summary_{batch_id}.csv" if batch_id else "summary.csv")
        create_summary(blob_path, str(summary))


def write_manifest(file, manifest):
    temporary = file.with_suffix(".tmp")
    temporary.write_text(json.dumps(manifest, indent=2) + "\n")
    temporary.replace(file)


def launch(campaign_id, profile="paper", output_root=None, workers=None, dry_run=False):
    environment = build_environment(profile, output_root, campaign_id, workers)
    manifest = campaign_manifest(environment, profile)
    if dry_run:
        print(json.dumps(manifest, indent=2))
        return manifest
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    identifier = f"{stamp}-{profile}-{uuid4().hex[:8]}"
    directory = Path(environment.experiments_folder) / identifier
    directory.mkdir(parents=True, exist_ok=False)
    environment.experiments_folder = str(directory)
    manifest.update(run_id=identifier, output_root=str(directory), status="preparing")
    manifest["planner_files"] = planner_files()
    file = directory / "manifest.json"
    write_manifest(file, manifest)
    print(f"Manifest: {file}", flush=True)
    with run_lock(directory):
        manifest["provenance_files"] = save_snapshot(directory, environment.campaign, environment.instance_entries)
        execute(environment, manifest, file)
    print(f"Run directory: {directory}", flush=True)
    return manifest


def execute(environment, manifest, file):
    try:
        manifest["status"] = "running"
        write_manifest(file, manifest)
        CampaignExecutor(environment, manifest, file).run_experiments()
    except BaseException:
        manifest["status"] = "interrupted_or_failed"
        write_manifest(file, manifest)
        raise
    manifest["status"] = "execution_finished" if not pending_runs(file.parent, manifest) else "incomplete"
    write_manifest(file, manifest)


def resume(campaign_id, directory, workers=None, dry_run=False):
    directory = Path(directory).resolve()
    file = directory / "manifest.json"
    with run_lock(directory, create=not dry_run):
        manifest = json.loads(file.read_text())
        environment = build_environment(manifest["profile"], campaign_id=campaign_id, workers=workers)
        current = campaign_manifest(environment, manifest["profile"])
        recorded = validate_resume(directory, manifest, current)
        # Perform legacy recovery on a copy in dry-run mode, without writing records.
        recovered = recover_legacy(directory, manifest, write=not dry_run)
        pending = pending_runs(directory, manifest)
        if dry_run:
            selected = {job_key(run) for run in pending}
            return {"run_directory": str(directory), "finished": len(manifest["runs"]) - len(pending),
                    "pending": [job_key(r) for r in pending], "recovered_legacy_completions": recovered,
                    "execution_settings": current["execution_settings"],
                    "scientific_settings": current["scientific_settings"],
                    "runs": [run for run in current["runs"] if job_key(run) in selected]}
        print(f"Resume: {len(manifest['runs']) - len(pending)} finished, {len(pending)} pending; "
              f"{recovered} recovered legacy completions", flush=True)
        if not pending:
            manifest["status"] = "execution_finished"
            write_manifest(file, manifest)
            return manifest
        attempt_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ") + "-" + uuid4().hex[:8]
        attempt = directory / "attempts" / attempt_id
        attempt.mkdir(parents=True)
        (attempt / "manifest.before.json").write_bytes(file.read_bytes())
        for package in ("experiment_support", "analysis"):
            destination = attempt / "execution-source" / package
            destination.mkdir(parents=True)
            for source in (REPOSITORY_ROOT / package).glob("*.py"):
                shutil.copyfile(source, destination / source.name)
        atomic_json(attempt / "execution-source" / "source-state.json", source_state())
        manifest["planner_files"] = recorded
        manifest.setdefault("resumptions", []).append({"id": attempt_id, "started_at": timestamp(),
            "execution_settings": current["execution_settings"], "pending_jobs": [job_key(r) for r in pending],
            "execution_source_sha256": {str(p.relative_to(attempt)): digest_file(p)
                                        for p in (attempt / "execution-source").rglob("*") if p.is_file()}})
        selected = {job_key(run) for run in pending}
        for planner, details in list(environment.run_dictionary.items()):
            domains = []
            for domain in details["DOMAINS"]:
                pairs = [pair for pair in domain.instances
                         if f"{planner.name}/{domain.name}/{Path(pair[1]).stem}" in selected]
                if pairs:
                    domain.instances = pairs
                    domains.append(domain)
            details["DOMAINS"] = domains
            if not domains:
                del environment.run_dictionary[planner]
        environment.experiments_folder = str(attempt)
        write_manifest(file, manifest)
        execute(environment, manifest, file)
        return manifest


def digest_file(file):
    from .campaigns import digest
    return digest(file)


def add_execution_arguments(parser):
    parser.add_argument("--output-root", type=Path, help="Parent for unique run directories (default: runs/<campaign-id>).")
    parser.add_argument("--workers", type=int, help="Execution worker count; default 2 for ICAPS 2025 on this 32 GB host.")
    parser.add_argument("--dry-run", action="store_true", help="Verify input hashes and print the manifest without writing files.")
