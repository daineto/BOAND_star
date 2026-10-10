"""Durable, resumable PRP execution; all artifacts stay inside the BOAND repo."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from experiment_support.campaigns import read_instances,input_path,digest
from experiment_support.execution import atomic_json,run_lock,stop_session
from .campaign import CAMPAIGN

ROOT=Path(__file__).resolve().parents[2]
DEFAULT_PLANNER=Path('/media/datos/aineto/planners/bin/prp')


def provenance(planner):
    source=planner.parent.parent/'planner-for-relevant-policies'
    git=['git','-c',f'safe.directory={source}','-C',str(source)]
    files=[planner,*source.glob('src/prp'),*source.glob('src/search/downward*'),*source.glob('src/search/unitcost'),*source.glob('src/preprocess/preprocess')]
    files += list((source/'src/translate').rglob('*.py'))
    files=[p for p in files if p.is_file()]
    return {'source':str(source),'revision':subprocess.check_output([*git,'rev-parse','HEAD'],text=True).strip(),
            'source_status':subprocess.check_output([*git,'status','--short'],text=True),
            'files_sha256':{str(p):digest(p) for p in files}}


def execute(directory,entries,planner,validate=True):
    manifest=json.loads((directory/'manifest.json').read_text());expected=manifest['planner_provenance']['files_sha256']
    if any(digest(p)!=h for p,h in expected.items()):raise ValueError('External planner changed since manifest')
    active=set();lock=threading.Lock();samples=[];stop=threading.Event()
    def monitor():
        while not stop.is_set():
            memory={line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:','SwapTotal:','SwapFree:'))}
            with lock:jobs=len(active)
            samples.append({'available_kb':memory['MemAvailable'],'swap_used_kb':memory['SwapTotal']-memory['SwapFree'],'active_jobs':jobs,'monotonic':time.monotonic(),'loadavg':os.getloadavg()})
            atomic_json(directory/'resources.json',samples);stop.wait(1)
    thread=threading.Thread(target=monitor,daemon=True);thread.start()
    def job(entry):
        folder=directory/entry['domain']/entry['instance'];folder.mkdir(parents=True,exist_ok=True)
        result=folder/'execution.json'
        if result.exists() and json.loads(result.read_text()).get('state')=='finished':return str(folder),'reused'
        command=[str(planner),str(input_path(entry['domain_path'])),str(input_path(entry['problem_path'])),*CAMPAIGN.configurations['PRP'].flags]
        request={'folder':str(folder),'command':command,'memory_kb':CAMPAIGN.memory_kb,'timeout_seconds':CAMPAIGN.timeout_seconds}
        atomic_json(folder/'request.json',request)
        process=subprocess.Popen([sys.executable,'-m','experiment_support.external_job',str(folder/'request.json'),str(result)],cwd=ROOT,start_new_session=True,stdout=subprocess.DEVNULL,stderr=(folder/'worker.log').open('w'))
        with lock:active.add(process.pid)
        atomic_json(folder/'running.json',{'pid':process.pid,'started_at':datetime.now(timezone.utc).isoformat()})
        try:code=process.wait()
        finally:
            stop_session(process.pid)
            with lock:active.discard(process.pid)
        if not result.exists():atomic_json(result,{'state':'finished','termination':'worker_error','returncode':code})
        return str(folder),json.loads(result.read_text())['termination']
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            for number,future in enumerate(as_completed([pool.submit(job,e) for e in entries]),1):
                folder,status=future.result();atomic_json(directory/'status.json',{'state':'executing','finished':number,'total':len(entries)})
                print(f'{number}/{len(entries)} {folder}: {status}',flush=True)
    except BaseException:
        with lock:pids=list(active)
        for pid in pids:stop_session(pid)
        raise
    finally:stop.set();thread.join()
    if any(digest(p)!=h for p,h in expected.items()):raise ValueError('External planner changed during execution')
    for relative,sha in manifest.get('execution_source_sha256',{}).items():
        if digest(ROOT/relative)!=sha:raise ValueError(f'Comparison source changed during execution: {relative}')
    read_instances(CAMPAIGN,manifest['profile'])  # Recheck frozen input hashes.
    if validate:
        atomic_json(directory/'status.json',{'state':'validating','finished':len(entries),'total':len(entries)})
        def check(entry):
            folder=directory/entry['domain']/entry['instance'];result=folder/'validation.json'
            if result.exists():return
            if not (folder/'policy.out').exists():atomic_json(result,{'status':'no_policy'});return
            request={'folder':str(folder),'domain_path':str(input_path(entry['domain_path'])),'problem_path':str(input_path(entry['problem_path'])),'memory_kb':6000000}
            atomic_json(folder/'replay-request.json',request)
            with (folder/'replay.log').open('w') as log:
                code=subprocess.run(['timeout','--kill-after=5','600',sys.executable,'-m','analysis.prp_replay',str(folder/'replay-request.json'),str(result)],cwd=ROOT,stdout=log,stderr=log).returncode
            if not result.exists():atomic_json(result,{'status':'validation_timeout' if code==124 else 'validation_error','returncode':code})
        with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(check,entries))
    atomic_json(directory/'status.json',{'state':'finished','finished':len(entries),'total':len(entries)})


def main():
    p=argparse.ArgumentParser();p.add_argument('--profile',choices=('smoke','paper'),default='paper');p.add_argument('--planner',type=Path,default=DEFAULT_PLANNER);p.add_argument('--dry-run',action='store_true');p.add_argument('--resume',type=Path);args=p.parse_args()
    entries=read_instances(CAMPAIGN,args.profile)
    manifest={'campaign_id':CAMPAIGN.campaign_id,'version':CAMPAIGN.version,'profile':args.profile,'timeout_seconds':600,'memory_kb':6000000,'workers':4,'pythonhashseed':'0','configuration_flags':CAMPAIGN.configurations['PRP'].flags,'instances':entries,'planner':str(args.planner),'planner_provenance':provenance(args.planner),'boand_source':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
    source_files=[Path('experiment_support/external_job.py'),Path('analysis/prp_replay.py'),*Path('campaigns/journal_prp_comparison').glob('*.py')]
    manifest['execution_source_sha256']={str(p):digest(ROOT/p) for p in source_files}
    if args.dry_run:print(json.dumps(manifest,indent=2));return
    if os.environ.get('PYTHONHASHSEED')!='0':raise ValueError('Set PYTHONHASHSEED=0')
    directory=(args.resume or ROOT/'runs'/CAMPAIGN.campaign_id/(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%SZ')+'-'+args.profile)).resolve();directory.mkdir(parents=True,exist_ok=True)
    if args.resume:
        old=json.loads((directory/'manifest.json').read_text())
        for key in ('instances','profile','configuration_flags','planner_provenance','timeout_seconds','memory_kb','workers','execution_source_sha256'):
            if old[key]!=manifest[key]:raise ValueError(f'Resume mismatch: {key}')
    else:
        atomic_json(directory/'manifest.json',manifest)
        for relative in manifest['execution_source_sha256']:
            file=directory/'source'/relative;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes((ROOT/relative).read_bytes())
    print(f'Run directory: {directory}',flush=True)
    with run_lock(directory):execute(directory,entries,args.planner)
    print(f'Finished: {directory}',flush=True)

if __name__=='__main__':main()
