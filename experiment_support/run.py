"""Run a named campaign: python -m experiment_support.run icaps2025 --dry-run."""
import argparse
import json
from pathlib import Path
from .campaigns import available_campaigns, load_campaign
from .runner import add_execution_arguments, launch, resume


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", choices=available_campaigns())
    parser.add_argument("--profile", help="Campaign profile (default: paper; resume uses the recorded profile).")
    parser.add_argument("--resume", type=Path, help="Resume an existing run directory.")
    add_execution_arguments(parser)
    args = parser.parse_args()
    campaign = load_campaign(args.campaign)
    if args.resume:
        if args.profile or args.output_root:
            parser.error("--resume uses the recorded profile and directory; omit --profile and --output-root")
        result = resume(args.campaign, args.resume, args.workers, args.dry_run)
        if args.dry_run:
            print(json.dumps(result, indent=2))
        return
    args.profile = args.profile or "paper"
    if args.profile not in campaign.profiles:
        parser.error(f"Unknown profile; choose from {', '.join(campaign.profiles)}")
    launch(args.campaign, args.profile, args.output_root, args.workers, args.dry_run)


if __name__ == "__main__":
    main()
