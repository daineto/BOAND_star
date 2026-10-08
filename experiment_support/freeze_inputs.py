"""Explicitly freeze a new campaign's inputs; never discover inputs at launch."""
import argparse
import json
from pathlib import Path

from planning_experiments.data_structures import Domain
from .campaigns import digest
from .models import REPOSITORY_ROOT


def freeze(campaign_id, domain_directories, output):
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite frozen inputs: {output}; create a new campaign revision")
    entries = []
    for label, relative in domain_directories:
        directory = (REPOSITORY_ROOT / relative).resolve()
        if not directory.is_relative_to(REPOSITORY_ROOT):
            raise ValueError("Benchmark directories must be inside the repository")
        domain = Domain(label, str(directory))
        if not domain.instances:
            raise ValueError(f"No instances in {directory}")
        for domain_path, problem_path in domain.instances:
            item = {"domain": label, "instance": Path(problem_path).stem}
            for kind, path in (("domain", domain_path), ("problem", problem_path)):
                item[f"{kind}_path"] = Path(path).relative_to(REPOSITORY_ROOT).as_posix()
                item[f"{kind}_sha256"] = digest(path)
            entries.append(item)
    if len({(e['domain'], e['instance']) for e in entries}) != len(entries):
        raise ValueError("Duplicate instance identities")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"schema_version": 1, "campaign_id": campaign_id,
                                 "dataset_version": "1", "instances": entries}, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--domain", action="append", required=True, metavar="LABEL=REPOSITORY_PATH")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    directories = []
    for item in args.domain:
        label, separator, directory = item.partition("=")
        if not label or not separator or not directory:
            parser.error("--domain must be LABEL=REPOSITORY_PATH")
        directories.append((label, directory))
    freeze(args.campaign, directories, args.output)


if __name__ == "__main__":
    main()
