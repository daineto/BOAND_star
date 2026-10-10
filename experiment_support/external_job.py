"""Run one external planner under a wall deadline and virtual-memory limit."""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import time
from .execution import atomic_json


def execute(request, output):
    limit=request['memory_kb']*1024;resource.setrlimit(resource.RLIMIT_AS,(limit,limit))
    folder=Path(request['folder']);start=time.monotonic();search_start=None;constructed=None
    command=['timeout','--kill-after=5',str(request['timeout_seconds']),*request['command']]
    with (folder/'stderr.log').open('w') as stderr,(folder/'stdout.log').open('w') as stdout:
        process=subprocess.Popen(command,cwd=folder,stdout=subprocess.PIPE,stderr=stderr,text=True,bufsize=1)
        for line in process.stdout:
            stdout.write(line);stdout.flush();elapsed=time.monotonic()-start
            if line.strip()=='3. Running search':search_start=elapsed
            if line.strip()=='Running the simulation...':constructed=elapsed
        code=process.wait()
    elapsed=time.monotonic()-start
    result={'state':'finished','returncode':code,'wall_seconds':elapsed,'search_start_wall_seconds':search_start,
            'construction_finished_wall_seconds':constructed,
            'first_policy_search_seconds':(constructed-search_start) if constructed is not None and search_start is not None else None,
            'policy_available_wall_seconds':elapsed if (folder/'policy.out').exists() else None,
            'peak_child_rss_kb':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            'termination':'timeout' if code in (124,137) else 'strong_cyclic' if code in (8,9) else 'memory_error' if code==6 else 'other'}
    atomic_json(output,result);return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('request',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    execute(json.loads(args.request.read_text()),args.output)

if __name__=='__main__':main()
