from dataclasses import dataclass
from pathlib import Path
from experiment_support.models import Campaign,Profile
from campaigns.journal_development.campaign import SMOKE_INSTANCES

@dataclass(frozen=True)
class ExternalConfiguration:
    timeout:int=600
    name:str='PRP_seed0'
    flags:tuple=('--random-seed','0','--dump-policy','2','--trials','0','--jic-limit','600')

CAMPAIGN=Campaign(campaign_id='journal_prp_comparison',version='1',configurations={'PRP':ExternalConfiguration()},
 profiles={'paper':Profile(('PRP',)),'smoke':Profile(('PRP',),instances=SMOKE_INSTANCES)},
 instance_manifest=Path(__file__).with_name('instances.json'),timeout_seconds=600,memory_kb=6000000,default_workers=4,
 analysis_module='campaigns.journal_prp_comparison.analysis')
