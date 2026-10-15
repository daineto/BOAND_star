"""Definition 1 explicitly separates abstract topology from physical grid trials."""
from pathlib import Path
from experiment_support.models import Campaign, Configuration, Profile

CONFIGURATIONS = {f'FD {h}': Configuration('bw', h, 'MinSum', 'MaxSum', 'Delta', 'largestg',
                                        timeout=600, backend='downward-direct') for h in ('hmax', 'lmcut')}
EXACT = tuple(('serial-topology', f'serial-k{k:02d}-g1') for k in (1, 2, 3)) + (('serial-topology', 'serial-k02-g2'),)
CAMPAIGN = Campaign(
    campaign_id='journal_serial_tradeoffs', version='1', configurations=CONFIGURATIONS,
    profiles={'smoke': Profile(tuple(CONFIGURATIONS), instances=EXACT),
              'embedding': Profile(('FD hmax',), domains=('physical-ports',)),
              'pilot': Profile(tuple(CONFIGURATIONS), domains=('serial-topology',))},
    instance_manifest=Path(__file__).with_name('instances.json'),
    timeout_seconds=600, memory_kb=6000000, default_workers=4,
    analysis_module='campaigns.journal_serial_tradeoffs.analysis',
)
