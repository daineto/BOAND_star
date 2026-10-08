"""Journal development suite; no full scientific campaign is defined yet."""
from pathlib import Path

from experiment_support.models import Campaign, Configuration, Profile


DOMAINS = (
    "beam-walk", "blocksworld-ex", "chain-of-rooms", "doors", "elevators",
    "frozenlake", "islands", "mod_first_responders", "st_tires",
    "tireworld", "tireworld-truck",
)
SMOKE_INSTANCES = (
    ("beam-walk", "p6"),
    ("blocksworld-ex", "p02"),
    ("blocksworld-ex", "p06"),
    ("chain-of-rooms", "p16"),
    ("doors", "p6"),
    ("elevators", "p05"),
    ("frozenlake", "motivating"),
    ("frozenlake", "p07"),
    ("islands", "p10"),
    ("mod_first_responders", "p_2_2"),
    ("st_tires", "p08"),
    ("st_tires", "p09"),
    ("tireworld", "p03"),
    ("tireworld-truck", "p6"),
)
CAMPAIGN = Campaign(
    campaign_id="journal_development",
    version="3",
    configurations={
        "BOAND bw": Configuration("bw", "hmax", "MinSum", "MaxSum", "Delta", "largestg", timeout=30),
    },
    profiles={"smoke": Profile(("BOAND bw",), instances=SMOKE_INSTANCES)},
    instance_manifest=Path(__file__).with_name("instances.json"),
    timeout_seconds=30,
    memory_kb=6_000_000,
    default_workers=4,
)
