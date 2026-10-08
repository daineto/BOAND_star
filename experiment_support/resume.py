"""Compatibility checks and conservative recovery of interrupted campaigns."""
import io
import json
from pathlib import Path
import re
import subprocess
import shlex
import tarfile
import tempfile

from .campaigns import digest
from .execution import active_record, atomic_json, timestamp
from .models import REPOSITORY_ROOT
from .provenance import git


SOURCE_EXCLUDES = {".git", "__pycache__", ".venv", "build", "dist", ".tox"}


def planner_files(root=REPOSITORY_ROOT / "planner"):
    return {str(file.relative_to(root)): digest(file) for file in sorted(root.rglob("*.py"))
            if not any(part in SOURCE_EXCLUDES for part in file.relative_to(root).parts)}


def historical_planner_files(directory, manifest):
    """Recover Python source from recorded Git revision and dirty-tree patches."""
    snapshot = directory / "provenance"
    for relative, expected in manifest["provenance_files"].items():
        if digest(snapshot / relative) != expected:
            raise ValueError(f"Recorded provenance was altered: {relative}")
    with tempfile.TemporaryDirectory(prefix="boand-resume-source-") as temporary:
        root = Path(temporary)

        def restore(repository, revision, destination, patch, prefix=None):
            archive = git("archive", revision, *([prefix] if prefix else []), root=repository)
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                for member in tar:
                    if member.isfile() and member.name.endswith(".py"):
                        target = (destination / member.name).resolve()
                        if not target.is_relative_to(destination.resolve()):
                            raise ValueError("Unsafe source archive")
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(tar.extractfile(member).read())
            # Apply only Python-source changes, including originally untracked modules.
            if not patch.read_bytes().strip():
                return
            result = subprocess.run(["git", "apply", "--include=" + (prefix + "/" if prefix else "") + "*.py",
                                     str(patch.resolve())], cwd=destination, capture_output=True)
            if result.returncode:
                raise ValueError("Cannot recover historical planner source: " + result.stderr.decode())

        restore(REPOSITORY_ROOT, manifest["source"]["revision"], root, snapshot / "source.patch", "planner")
        modules = snapshot / "submodules"
        for state_file in modules.rglob("state.json"):
            relative = state_file.parent.relative_to(modules)
            if not relative.is_relative_to(Path("planner")):
                continue
            state = json.loads(state_file.read_text())
            destination = root / relative
            destination.mkdir(parents=True, exist_ok=True)
            restore(REPOSITORY_ROOT / relative, state["revision"], destination,
                    state_file.with_name("source.patch"))
        return planner_files(root / "planner")


def validate_resume(directory, manifest, current):
    if manifest["campaign"]["id"] != current["campaign"]["id"]:
        raise ValueError("Resume campaign differs")
    if manifest["campaign"]["version"] != current["campaign"]["version"]:
        raise ValueError("Resume campaign version differs")
    if manifest["profile"] != current["profile"]:
        raise ValueError("Resume profile differs")
    if manifest["scientific_settings"] != current["scientific_settings"]:
        raise ValueError("Resume inputs or resource limits differ")
    fields = ("configuration", "domain", "instance", "domain_path", "problem_path", "domain_sha256", "problem_sha256")
    old = [{k: run[k] for k in fields} for run in manifest["runs"]]
    new = [{k: run[k] for k in fields} for run in current["runs"]]
    if old != new:
        raise ValueError("Resume input selection or configurations differ")
    for previous, selected in zip(manifest["runs"], current["runs"]):
        # Configuration names alone are insufficient: verify the actual flags.
        old_command = shlex.split(previous["command"])
        new_command = shlex.split(selected["command"])
        if old_command[:4] + old_command[5:] != new_command[:4] + new_command[5:]:
            raise ValueError("Resume planner command differs")
    runtime = current["execution_settings"]
    for field in ("python", "python_version", "pythonhashseed", "versions"):
        if manifest["execution_settings"][field] != runtime[field]:
            raise ValueError(f"Resume runtime differs: {field}")
    freeze = subprocess.check_output([runtime["python"], "-m", "pip", "freeze", "--all"])
    if freeze != (directory / "provenance" / "requirements.freeze.txt").read_bytes():
        raise ValueError("Resume installed dependencies differ")
    recorded = manifest.get("planner_files")
    if recorded is None:
        recorded = historical_planner_files(directory, manifest)
    recorded = {path: value for path, value in recorded.items()
                if not SOURCE_EXCLUDES.intersection(Path(path).parts)}
    if recorded != planner_files():
        raise ValueError("Resume planner source differs")
    return recorded


def job_key(run):
    return f"{run['configuration']}/{run['domain']}/{run['instance']}"


def recover_legacy(directory, manifest, write=True):
    """Import only externally collected jobs with a complete timing footer."""
    if not manifest.get("result_root") or all(run.get("attempts") for run in manifest["runs"]):
        return 0
    root = directory / manifest["result_root"]
    if not root.resolve().is_relative_to(directory.resolve()):
        raise ValueError("Result root escapes the run directory")
    blob = json.loads((root / "blob.json").read_text())
    recovered = 0
    for run in manifest["runs"]:
        if run.get("attempts"):
            continue
        folder = root / run["configuration"] / run["domain"] / run["instance"]
        stderr = folder / f"err_{run['domain']}_{run['instance']}.txt"
        metadata = blob.get(run["configuration"], {}).get(run["domain"], {}).get(run["instance"], {})
        errors = stderr.read_text() if stderr.is_file() else ""
        timing = re.search(r"(?:^|\n)real [0-9.]+\nuser [0-9.]+\nsys [0-9.]+\s*$", errors)
        finished = "num_solutions" in metadata and bool(timing)
        record = {"schema_version": 1, "state": "finished" if finished else "unconfirmed",
                  "legacy_import": True, "imported_at": timestamp(), "returncode": None,
                  "termination": "legacy_exit_unknown",
                  "evidence": "collector record and complete timing footer" if finished else "completion not established"}
        if write:
            atomic_json(folder / "execution.json", record)
        run["attempts"] = [{"directory": str(folder.relative_to(directory)), "legacy": True,
                            "execution": record}]
        recovered += finished
    return recovered


def pending_runs(directory, manifest, check_active=True):
    pending = []
    for run in manifest["runs"]:
        finished = False
        for attempt in run.get("attempts", []):
            folder = (directory / attempt["directory"]).resolve()
            if not folder.is_relative_to(directory.resolve()):
                raise ValueError("Attempt directory escapes the run directory")
            state_file = folder / "execution.json"
            state = json.loads(state_file.read_text()) if state_file.exists() else attempt.get("execution", {})
            if state:
                if check_active and active_record(state):
                    raise ValueError(f"A job is still active: {job_key(run)}")
                finished |= state["state"] == "finished"
        if not finished:
            pending.append(run)
    return pending
