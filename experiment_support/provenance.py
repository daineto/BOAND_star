"""Record the actual source tree, dependencies and scientific run definition."""
from dataclasses import asdict
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

from .campaigns import digest
from .models import REPOSITORY_ROOT


def git(*arguments, root=REPOSITORY_ROOT):
    return subprocess.check_output(["git", "-c", f"safe.directory={root.resolve()}", *arguments], cwd=root)


def source_state():
    return {"revision": git("rev-parse", "HEAD").decode().strip(),
            "branch": git("branch", "--show-current").decode().strip(),
            "dirty": bool(git("status", "--porcelain")),
            "status": git("status", "--porcelain").decode(),
            "submodules": git("submodule", "status", "--recursive").decode().splitlines()}


def source_patch(root=REPOSITORY_ROOT, exclude=None):
    patches = [git("diff", "--binary", "HEAD", root=root)]
    # Include newly added source, even when the user deliberately has not committed.
    for raw in git("ls-files", "--others", "--exclude-standard", "-z", root=root).split(b"\0"):
        if not raw:
            continue
        file = os.fsdecode(raw)
        if exclude is not None and (root / file).resolve().is_relative_to(exclude.resolve()):
            continue
        result = subprocess.run(["git", "diff", "--binary", "--no-index", "--", "/dev/null", file],
                                cwd=root, capture_output=True)
        if result.returncode not in (0, 1):
            raise RuntimeError(result.stderr.decode())
        patches.append(result.stdout)
    return b"".join(patches)


def resolved_definition(campaign):
    return {"schema_version": campaign.schema_version, "id": campaign.campaign_id,
            "version": campaign.version, "configurations": {
                label: {**asdict(configuration), "name": configuration.name}
                for label, configuration in campaign.configurations.items()},
            "profiles": {name: asdict(profile) for name, profile in campaign.profiles.items()},
            "timeout_seconds": campaign.timeout_seconds, "memory_kb": campaign.memory_kb,
            "default_workers": campaign.default_workers,
            "analysis_module": campaign.analysis_module,
            "archive_root": str(campaign.archive_root) if campaign.archive_root else None,
            "instance_manifest_sha256": digest(campaign.instance_manifest)}


def runtime_information():
    versions = {package: metadata.version(package) for package in
                ("pddl", "pyperplan", "unified-planning", "planning-experiments", "numpy", "pandas", "matplotlib")}
    return {"python": sys.executable, "python_version": platform.python_version(),
            "platform": platform.platform(), "cpu": platform.processor(), "cpu_count": os.cpu_count(),
            "physical_memory_bytes": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"),
            "pythonhashseed": os.environ.get("PYTHONHASHSEED", "unset"), "versions": versions}


def save_snapshot(directory, campaign, instances):
    snapshots = directory / "provenance"
    snapshots.mkdir()
    (snapshots / "campaign.json").write_text(json.dumps(resolved_definition(campaign), indent=2) + "\n")
    (snapshots / "instances.json").write_text(json.dumps(instances, indent=2) + "\n")
    migration_file = campaign.instance_manifest.with_name("manifest-migrations.json")
    if migration_file.is_file():
        (snapshots / migration_file.name).write_bytes(migration_file.read_bytes())
    (snapshots / "source.patch").write_bytes(source_patch(exclude=directory))
    (snapshots / "requirements.freeze.txt").write_bytes(
        subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
    source = REPOSITORY_ROOT / "campaigns" / campaign.campaign_id / "campaign.py"
    (snapshots / "campaign.py").write_bytes(source.read_bytes())
    for entry in git("ls-files", "--stage", "-z").decode().split("\0"):
        if not entry.startswith("160000 "):
            continue
        relative = entry.split("\t", 1)[1]
        root = REPOSITORY_ROOT / relative
        subdirectory = snapshots / "submodules" / relative
        subdirectory.mkdir(parents=True)
        state = {"revision": git("rev-parse", "HEAD", root=root).decode().strip(),
                 "status": git("status", "--porcelain", root=root).decode()}
        (subdirectory / "state.json").write_text(json.dumps(state, indent=2) + "\n")
        (subdirectory / "source.patch").write_bytes(source_patch(root=root))
    return {str(file.relative_to(snapshots)): digest(file) for file in snapshots.rglob("*") if file.is_file()}
