"""Pilot definition 1: fixed exploratory inputs, not a final paper benchmark."""
from pathlib import Path
from experiment_support.models import Campaign, Configuration, Profile

CONFIGURATIONS = {
    f'FD {heuristic}': Configuration('bw', heuristic, 'MinSum', 'MaxSum', 'Delta', 'largestg',
                                    timeout=600, backend='downward-direct')
    for heuristic in ('hmax', 'lmcut')
}
CAMPAIGN = Campaign(
    campaign_id='journal_tradeoffs', version='1', configurations=CONFIGURATIONS,
    profiles={'pilot': Profile(tuple(CONFIGURATIONS)),
              'smoke': Profile(tuple(CONFIGURATIONS),
                               instances=tuple(('frozenlake', f'verified-{n:02d}') for n in range(1, 4)))},
    instance_manifest=Path(__file__).with_name('instances.json'),
    timeout_seconds=600, memory_kb=6_000_000, default_workers=4,
    analysis_module='campaigns.journal_tradeoffs.analysis',
)
