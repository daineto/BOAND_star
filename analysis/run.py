"""Dispatch paper-specific analysis: python -m analysis.run icaps2025."""
import argparse
from importlib import import_module
from experiment_support.campaigns import available_campaigns, load_campaign


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", choices=available_campaigns())
    args, remaining = parser.parse_known_args()
    campaign = load_campaign(args.campaign)
    if campaign.analysis_module is None:
        parser.error(f"{args.campaign} does not declare an analysis entry point")
    import_module(campaign.analysis_module).main(remaining)


if __name__ == "__main__":
    main()
