"""Campaign discovery and immutable instance selection."""
import hashlib
from importlib import import_module
import json
from pathlib import Path
import re

from .models import REPOSITORY_ROOT


def load_campaign(identifier):
    if not re.fullmatch(r"[a-z][a-z0-9_]*", identifier):
        raise ValueError("Campaign IDs must use lowercase letters, digits and underscores")
    source = REPOSITORY_ROOT / "campaigns" / identifier / "campaign.py"
    if not source.is_file():
        raise ValueError(f"Unknown campaign: {identifier}")
    campaign = import_module(f"campaigns.{identifier}.campaign").CAMPAIGN.validate()
    if campaign.campaign_id != identifier:
        raise ValueError("Campaign directory and declared ID differ")
    return campaign


def available_campaigns():
    return sorted(p.parent.name for p in (REPOSITORY_ROOT / "campaigns").glob("*/campaign.py"))


def digest(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def input_path(relative, root=REPOSITORY_ROOT):
    relative = Path(relative)
    if relative.is_absolute():
        raise ValueError(f"Manifest paths must be repository-relative: {relative}")
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"Input escapes the repository: {relative}")
    return resolved


def read_instances(campaign, profile, root=REPOSITORY_ROOT):
    data = json.loads(campaign.instance_manifest.read_text())
    if data.get("schema_version") != 1 or data.get("campaign_id") != campaign.campaign_id:
        raise ValueError("Unsupported or mismatched instance manifest")
    specification = campaign.profiles[profile]
    selected = []
    identities = set()
    for entry in data["instances"]:
        key = (entry["domain"], entry["instance"])
        if key in identities:
            raise ValueError(f"Duplicate manifest instance: {key}")
        identities.add(key)
        if specification.domains is not None and entry["domain"] not in specification.domains:
            continue
        if specification.instances is not None and key not in specification.instances:
            continue
        for kind in ("domain", "problem"):
            file = input_path(entry[f"{kind}_path"], root)
            if digest(file) != entry[f"{kind}_sha256"]:
                raise ValueError(f"Input hash mismatch: {file}; do not regenerate a published manifest to hide changes")
        if input_path(entry["problem_path"], root).stem != entry["instance"]:
            raise ValueError(f"Problem filename and instance ID differ: {key}")
        selected.append(entry)
    if specification.instances is not None and not set(specification.instances) <= identities:
        raise ValueError("Smoke profile references instances absent from the manifest")
    if specification.domains is not None and not set(specification.domains) <= {e['domain'] for e in selected}:
        raise ValueError("Profile references domains absent from the manifest")
    if not selected:
        raise ValueError("Profile has no instances")
    return selected


def approved_manifest_migration(campaign, recorded_hash, current_hash):
    """Accept only an explicitly recorded, exact old-to-new manifest migration."""
    file = campaign.instance_manifest.with_name("manifest-migrations.json")
    if not file.is_file():
        return None
    ledger = json.loads(file.read_text())
    if (ledger.get("schema_version") != 1 or ledger.get("campaign_id") != campaign.campaign_id
            or ledger.get("campaign_version") != campaign.version):
        raise ValueError("Unsupported or mismatched manifest migration record")
    return next((entry for entry in ledger["migrations"]
                 if entry["from_sha256"] == recorded_hash and entry["to_sha256"] == current_hash), None)


def resolve_dataset(campaign, dataset):
    """Select one published archive or one run, without merging datasets."""
    if str(dataset) == "published":
        if campaign.archive_root is None:
            raise ValueError(f"{campaign.campaign_id} has no published archive")
        return campaign.archive_root.resolve(), {"kind": "published", "path": str(campaign.archive_root.resolve())}
    directory = Path(dataset).resolve()
    file = directory / "manifest.json"
    if file.exists():
        manifest = json.loads(file.read_text())
        if manifest.get("schema_version") != 1 or manifest["campaign"]["id"] != campaign.campaign_id:
            raise ValueError("Run belongs to another campaign or uses an unsupported run schema")
        if manifest["campaign"]["version"] != campaign.version:
            raise ValueError("Run definition version differs; use the recorded campaign revision")
        recorded_hash = manifest["campaign"]["instance_manifest_sha256"]
        current_hash = digest(campaign.instance_manifest)
        migration = None
        if recorded_hash != current_hash:
            migration = approved_manifest_migration(campaign, recorded_hash, current_hash)
            if migration is None:
                raise ValueError("Run uses another frozen instance manifest; use the recorded campaign revision")
        relative = Path(manifest.get("result_root", ""))
        if not manifest.get("result_root") or relative.is_absolute():
            raise ValueError("Run has no valid relative result root yet")
        results = (directory / relative).resolve()
        if not results.is_relative_to(directory):
            raise ValueError("Run result root escapes its directory")
        identity = {"kind": "run", "path": str(directory), "manifest_sha256": digest(file),
                    "campaign_version": manifest["campaign"]["version"], "profile": manifest["profile"]}
        if migration:
            identity["instance_manifest_migration"] = migration
        return results, identity
    if not directory.is_dir():
        raise FileNotFoundError(directory)
    return directory, {"kind": "legacy_results", "path": str(directory)}
