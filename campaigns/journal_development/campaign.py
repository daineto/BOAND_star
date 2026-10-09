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
# Fixed timing selection; the smoke correctness selection remains unchanged.
PERFORMANCE_INSTANCES = (
    ("beam-walk", "p7"),
    ("blocksworld-ex", "p13"),
    ("chain-of-rooms", "p24"),
    ("doors", "p8"),
    ("elevators", "p04"),
    ("frozenlake", "p19"),
    ("islands", "p16"),
    ("mod_first_responders", "p_2_2"),
    ("st_tires", "p08"),
    ("tireworld", "p06"),
    ("tireworld-truck", "p7"),
)
CAMPAIGN = Campaign(
    campaign_id="journal_development",
    version="9",
    configurations={
        "BOAND bw": Configuration("bw", "hmax", "MinSum", "MaxSum", "Delta", "largestg", timeout=30),
        "BOAND downward hmax": Configuration("bw", "hmax", "MinSum", "MaxSum", "Delta", "largestg", timeout=30, backend="downward-strips"),
        "BOAND downward lmcut": Configuration("bw", "lmcut", "MinSum", "MaxSum", "Delta", "largestg", timeout=30, backend="downward-strips"),
        "BOAND pyperplan lmcut": Configuration("bw", "lmcut", "MinSum", "MaxSum", "Delta", "largestg", timeout=30),
        "BOAND grounded hmax": Configuration("bw", "hmax", "MinSum", "MaxSum", "Delta", "largestg", timeout=30, backend="downward-grounded"),
        "BOAND grounded lmcut": Configuration("bw", "lmcut", "MinSum", "MaxSum", "Delta", "largestg", timeout=30, backend="downward-grounded"),
        "BOAND direct hmax": Configuration("bw", "hmax", "MinSum", "MaxSum", "Delta", "largestg", timeout=30, backend="downward-direct"),
        "BOAND direct lmcut": Configuration("bw", "lmcut", "MinSum", "MaxSum", "Delta", "largestg", timeout=30, backend="downward-direct"),
    },
    profiles={
        "smoke-pyperplan-hmax": Profile(("BOAND bw",), instances=SMOKE_INSTANCES),
        "performance-pyperplan-hmax": Profile(("BOAND bw",), instances=PERFORMANCE_INSTANCES),
        "smoke": Profile(("BOAND direct hmax",), instances=SMOKE_INSTANCES),
        "performance": Profile(("BOAND direct hmax",), instances=PERFORMANCE_INSTANCES),
        "smoke-downward-hmax": Profile(("BOAND downward hmax",), instances=SMOKE_INSTANCES),
        "performance-downward-hmax": Profile(("BOAND downward hmax",), instances=PERFORMANCE_INSTANCES),
        "smoke-downward-lmcut": Profile(("BOAND downward lmcut",), instances=SMOKE_INSTANCES),
        "performance-downward-lmcut": Profile(("BOAND downward lmcut",), instances=PERFORMANCE_INSTANCES),
        "smoke-pyperplan-lmcut": Profile(("BOAND pyperplan lmcut",), instances=SMOKE_INSTANCES),
        "performance-pyperplan-lmcut": Profile(("BOAND pyperplan lmcut",), instances=PERFORMANCE_INSTANCES),
        "smoke-grounded-hmax": Profile(("BOAND grounded hmax",), instances=SMOKE_INSTANCES),
        "performance-grounded-hmax": Profile(("BOAND grounded hmax",), instances=PERFORMANCE_INSTANCES),
        "smoke-grounded-lmcut": Profile(("BOAND grounded lmcut",), instances=SMOKE_INSTANCES),
        "performance-grounded-lmcut": Profile(("BOAND grounded lmcut",), instances=PERFORMANCE_INSTANCES),
        "smoke-direct-hmax": Profile(("BOAND direct hmax",), instances=SMOKE_INSTANCES),
        "smoke-direct-lmcut": Profile(("BOAND direct lmcut",), instances=SMOKE_INSTANCES),
        "performance-direct-hmax": Profile(("BOAND direct hmax",), instances=PERFORMANCE_INSTANCES),
        "performance-direct-lmcut": Profile(("BOAND direct lmcut",), instances=PERFORMANCE_INSTANCES),
    },
    instance_manifest=Path(__file__).with_name("instances.json"),
    timeout_seconds=30,
    memory_kb=6_000_000,
    default_workers=4,
)
