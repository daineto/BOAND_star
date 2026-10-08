"""Frozen ICAPS 2025 revision 1: the paper's eight plotted configurations."""
from pathlib import Path
from experiment_support.models import Campaign, Configuration, Profile, REPOSITORY_ROOT


def configuration(metric, best, worst, size, selector):
    return Configuration(metric, "hmax", best, worst, size, selector)


PAPER_CONFIGURATIONS = {
    "SumMin": configuration("b", "SumMin", "Blind", "Zero", "random"),
    "MinSum": configuration("b", "MinSum", "Blind", "Zero", "random"),
    "BOAND bw2": configuration("bw", "SumMin", "MaxSum", "Delta", "largestg"),
    "BOAND bw": configuration("bw", "MinSum", "MaxSum", "Delta", "largestg"),
    "BOAND wb2": configuration("wb", "SumMin", "MaxSum", "Delta", "largestg"),
    "BOAND wb": configuration("wb", "MinSum", "MaxSum", "Delta", "largestg"),
    "MaxSum": configuration("w", "Blind", "MaxSum", "Zero", "random"),
    "AND best": configuration("b", "MinSum", "Blind", "Delta", "random"),
}
DOMAIN_DIRECTORIES = {
    "beam-walk": "beam-walk", "blocksworld-ex": "blocksworld-ex",
    "chain-of-rooms": "chain-of-rooms", "doors": "doors", "elevators": "elevators",
    "frozenlake": "frozenlake", "islands": "islands", "mod_first_responders": "mod_first_responders",
    "st_tires": "st_tires", "tireworld": "tireworld", "tireworld-truck": "tireworld-truck",
}
PAPER_DOMAINS = tuple(DOMAIN_DIRECTORIES)
MINI_DOMAINS = ("frozenlake",)
MINI_CONFIGURATIONS = {"BOAND bw": PAPER_CONFIGURATIONS["BOAND bw"]}
CAMPAIGN = Campaign(
    campaign_id="icaps2025", version="1", configurations=PAPER_CONFIGURATIONS,
    profiles={"paper": Profile(tuple(PAPER_CONFIGURATIONS)),
              "BOAND_bw": Profile(tuple(MINI_CONFIGURATIONS)),
              "BOAND_bw_tireworld": Profile(tuple(MINI_CONFIGURATIONS), domains=("tireworld",)),
              "mini": Profile(tuple(MINI_CONFIGURATIONS), domains=MINI_DOMAINS)},
    instance_manifest=Path(__file__).with_name("instances.json"),
    archive_root=REPOSITORY_ROOT / "results" / "icaps2025" / "published",
    analysis_module="campaigns.icaps2025.analysis",
)
