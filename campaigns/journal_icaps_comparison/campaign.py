"""Versioned comparison; published ICAPS definitions remain immutable."""
from pathlib import Path
from experiment_support.models import Campaign, Configuration, Profile
from campaigns.journal_development.campaign import DOMAINS, SMOKE_INSTANCES

CONFIGURATIONS = {
    'FD hmax': Configuration('bw', 'hmax', 'MinSum', 'MaxSum', 'Delta', 'largestg',
                             timeout=600, backend='downward-direct'),
    'FD lmcut': Configuration('bw', 'lmcut', 'MinSum', 'MaxSum', 'Delta', 'largestg',
                              timeout=600, backend='downward-direct'),
}
CAMPAIGN = Campaign(
    campaign_id='journal_icaps_comparison', version='1', configurations=CONFIGURATIONS,
    profiles={'paper': Profile(tuple(CONFIGURATIONS)),
              'smoke': Profile(tuple(CONFIGURATIONS), instances=SMOKE_INSTANCES)},
    instance_manifest=Path(__file__).with_name('instances.json'),
    timeout_seconds=600, memory_kb=6_000_000, default_workers=4,
    analysis_module='campaigns.journal_icaps_comparison.analysis',
)
