"""Execute and then independently validate/compare the selected full campaign."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

from experiment_support.resource_monitor import monitored_run
from experiment_support.execution import atomic_json
from experiment_support.models import REPOSITORY_ROOT
from .campaign import CAMPAIGN
from .analysis import compare


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--profile',choices=CAMPAIGN.profiles,default='paper')
    args=parser.parse_args()
    folder=REPOSITORY_ROOT/'outputs'/CAMPAIGN.campaign_id/datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%SZ')
    folder.mkdir(parents=True,exist_ok=False)
    status=folder/'status.json';atomic_json(status,{'state':'executing','profile':args.profile})
    print(f'Controller artifacts: {folder}',flush=True)
    try:
        code=monitored_run([sys.executable,'-m','experiment_support.run',CAMPAIGN.campaign_id,'--profile',args.profile],
                           folder/'execution.log',folder/'resources.json')
        text=(folder/'execution.log').read_text()
        manifests=[line.removeprefix('Manifest: ') for line in text.splitlines() if line.startswith('Manifest: ')]
        directory=Path(manifests[-1]).parent if manifests else None
        if code!=0 or directory is None:
            raise RuntimeError(f'Campaign execution failed with exit {code}; see {folder}/execution.log')
        shutil.copyfile(folder/'resources.json',directory/'resources.json')
        atomic_json(status,{'state':'validating','run_directory':str(directory),'profile':args.profile})
        report=compare(directory)
        atomic_json(status,{'state':'finished','run_directory':str(directory),'profile':args.profile,
                            'comparison_status':report['status'],'report':str(directory/'comparison/report.md')})
        print(f'Comparison report: {directory}/comparison/report.md',flush=True)
        if report['status']!='checked':raise SystemExit(2)
    except Exception as error:
        atomic_json(status,{'state':'failed','error':str(error),'profile':args.profile})
        raise


if __name__=='__main__':main()
