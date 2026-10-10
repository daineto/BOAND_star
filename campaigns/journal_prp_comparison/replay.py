"""Revalidate fixed PRP exports, preserving the previous validator's evidence."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from experiment_support.campaigns import digest
from experiment_support.execution import atomic_json

ROOT=Path(__file__).resolve().parents[2]


def revalidate(run,workers=4):
    run=Path(run).resolve()
    if json.loads((run/'status.json').read_text())['state']!='finished':
        raise ValueError('Wait for the original execution/replay pass to finish')
    folder=run/'revalidation'/('guard-indexed-'+datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%SZ'));folder.mkdir(parents=True,exist_ok=True)
    source=ROOT/'analysis/prp_replay.py';sha=digest(source)
    atomic_json(folder/'provenance.json',{'validator_sha256':sha,'runner_sha256':digest(Path(__file__)),'workers':workers,'memory_kb':6000000,'timeout_seconds':600})
    (folder/'validator-source.py').write_bytes(source.read_bytes())
    (folder/'runner-source.py').write_bytes(Path(__file__).read_bytes())
    requests=list(run.glob('*/*/replay-request.json'))
    # Check a previously successful large case first, then the expensive cases.
    order={'p12':0,'p13':1,'p14':2,'p15':3}
    requests.sort(key=lambda p:(order.get(p.parent.name,4) if p.parent.parent.name=='doors' else 5,str(p)))
    def check(request):
        output=folder/request.parent.parent.name/request.parent.name;output.mkdir(parents=True,exist_ok=True)
        result=output/'validation.json';result.unlink(missing_ok=True);started=time.monotonic()
        with (output/'replay.log').open('w') as log:
            code=subprocess.run(['timeout','--kill-after=5','600',sys.executable,'-m','analysis.prp_replay',str(request),str(result)],cwd=ROOT,stdout=log,stderr=log).returncode
        if not result.exists():atomic_json(result,{'status':'validation_timeout' if code==124 else 'validation_error','returncode':code})
        atomic_json(output/'execution.json',{'returncode':code,'wall_seconds':time.monotonic()-started,'validator_sha256':sha})
        return request,result
    checked=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for number,future in enumerate(as_completed([pool.submit(check,p) for p in requests]),1):
            request,result=future.result();checked.append((request,result))
            atomic_json(folder/'status.json',{'state':'validating','finished':number,'total':len(requests)})
            print(f'{number}/{len(requests)} {request.parent.parent.name}/{request.parent.name}: {json.loads(result.read_text())["status"]}',flush=True)
    if digest(source)!=sha:raise ValueError('Validator changed during replay')
    problems=[];resolved=[]
    for request,result in checked:
        old_file=request.parent/'validation.json';old=json.loads(old_file.read_text());new=json.loads(result.read_text())
        backup=folder/'previous-validation'/request.parent.parent.name/request.parent.name/'validation.json'
        backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old_file,backup)
        if old['status'] in ('valid','invalid'):
            if old['status']!=new['status'] or old['status']=='valid' and any(old[key]!=new[key] for key in ('best','worst','reachable_states')):
                problems.append(str(request.parent))
        elif new['status']=='valid':resolved.append(str(request.parent))
    atomic_json(folder/'equivalence.json',{'previous_checked':len(checked),'problems':problems,'resolved':resolved})
    if problems:raise ValueError(f'Indexed replay differs from completed previous checks: {problems}')
    for request,result in checked:
        new=json.loads(result.read_text());new['validator_sha256']=sha
        atomic_json(request.parent/'validation.json',new)
    atomic_json(folder/'status.json',{'state':'finished','finished':len(checked),'total':len(requests),'resolved':resolved})
    print('Revalidation applied; regenerate the comparison analysis.',flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--workers',type=int,choices=range(1,5),default=4);args=p.parse_args()
    if os.environ.get('PYTHONHASHSEED')!='0':raise ValueError('Set PYTHONHASHSEED=0')
    revalidate(args.run,args.workers)

if __name__=='__main__':main()
