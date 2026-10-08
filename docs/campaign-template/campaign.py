"""Copy this directory to campaigns/<id>/ and set a unique campaign ID."""
from pathlib import Path
from experiment_support.models import Campaign, Configuration, Profile

CAMPAIGN = Campaign(
    campaign_id="new_paper",  # Match the directory name; use letters, digits, underscores.
    version="1",
    configurations={"main": Configuration("bw", "hmax", "MinSum", "MaxSum", "Delta", "largestg")},
    profiles={
        "paper": Profile(("main",)),
        "smoke": Profile(("main",), instances=(("frozenlake", "motivating"),)),
    },
    instance_manifest=Path(__file__).with_name("instances.json"),
    timeout_seconds=600,
    memory_kb=8_000_000,
    default_workers=2,
    analysis_module="campaigns.new_paper.analysis",  # Update to match the ID.
)
