"""Definition 1: physical staircase/detour stages, original movement semantics."""
from pathlib import Path
from experiment_support.models import Campaign, Configuration, Profile

CONFIGURATIONS = {f'FD {heuristic}': Configuration(
    'bw', heuristic, 'MinSum', 'MaxSum', 'Delta', 'largestg',
    timeout=600, backend='downward-direct') for heuristic in ('hmax', 'lmcut')}
CAMPAIGN = Campaign(
    campaign_id='journal_frozenlake_stages', version='1', configurations=CONFIGURATIONS,
    profiles={name: Profile(tuple(CONFIGURATIONS), instances=(('frozenlake', f'staircase-k{stages:02d}'),))
              for name, stages in (('smoke', 1), ('connected', 2), ('extension', 3))},
    instance_manifest=Path(__file__).with_name('instances.json'),
    timeout_seconds=600, memory_kb=6000000, default_workers=4,
    analysis_module='campaigns.journal_frozenlake_stages.analysis',
)
