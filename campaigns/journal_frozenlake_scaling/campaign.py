"""Definition 1: four predeclared physical FrozenLake scaling probes."""
from pathlib import Path
from experiment_support.models import Campaign, Configuration, Profile

CONFIGURATIONS = {f'FD {heuristic}': Configuration(
    'bw', heuristic, 'MinSum', 'MaxSum', 'Delta', 'largestg',
    timeout=600, backend='downward-direct') for heuristic in ('hmax', 'lmcut')}
CAMPAIGN = Campaign(
    campaign_id='journal_frozenlake_scaling', version='1', configurations=CONFIGURATIONS,
    profiles={name: Profile(tuple(CONFIGURATIONS), instances=(('frozenlake', instance),))
              for name, instance in (('smoke', 'staircase-k04'), ('six', 'staircase-k06'),
                                     ('larger', 'staircase-k04-n10'), ('eight', 'staircase-k08'))},
    instance_manifest=Path(__file__).with_name('instances.json'),
    timeout_seconds=600, memory_kb=6000000, default_workers=4,
    analysis_module='campaigns.journal_frozenlake_scaling.analysis',
)
