"""Definition 1: unchanged domain, exact base references, untested scaling."""
from pathlib import Path
from experiment_support.models import Campaign, Configuration, Profile

CONFIGURATIONS = {
    f'FD {h}': Configuration('bw', h, 'MinSum', 'MaxSum', 'Delta', 'largestg',
                            timeout=600, backend='downward-direct') for h in ('hmax', 'lmcut')
}
CAMPAIGN = Campaign(
    campaign_id='journal_frozenlake_recovery', version='1', configurations=CONFIGURATIONS,
    profiles={'smoke': Profile(tuple(CONFIGURATIONS), instances=tuple(
                  ('frozenlake', f'recovery-3x5-{tail}') for tail in ('cyclic', 'pit'))),
              'pilot': Profile(tuple(CONFIGURATIONS))},
    instance_manifest=Path(__file__).with_name('instances.json'),
    timeout_seconds=600, memory_kb=6_000_000, default_workers=4,
    analysis_module='campaigns.journal_frozenlake_recovery.analysis',
)
