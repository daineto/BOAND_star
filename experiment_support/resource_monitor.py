"""Sample planner high-water RSS and machine resources during a campaign."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from .execution import atomic_json
from .resume import planner_files


def planner_samples(peaks):
    active=0
    for process in Path('/proc').iterdir():
        if not process.name.isdigit(): continue
        try:
            args=(process/'cmdline').read_bytes().decode().split('\0')
            pos=next(i for i,arg in enumerate(args) if arg.endswith('/planner/planner.py'))
            problem=Path(args[pos+2]);heuristic=args[args.index('-ch')+1]
            key=f'{heuristic}/{problem.parent.name}/{problem.stem}'
            status=(process/'status').read_text()
            peak=next(int(line.split()[1]) for line in status.splitlines() if line.startswith('VmHWM:'))
            peaks[key]=max(peak,peaks.get(key,0));active+=1
        except (OSError,UnicodeError,StopIteration,ValueError,IndexError): pass
    return active


def system_sample():
    mem={line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
    cpu=[int(value) for value in Path('/proc/stat').read_text().splitlines()[0].split()[1:]]
    return {'monotonic':time.monotonic(),'available_kb':mem['MemAvailable'],
            'swap_used_kb':mem['SwapTotal']-mem['SwapFree'],'loadavg':os.getloadavg(),
            'cpu_total_ticks':sum(cpu[:8]),'cpu_idle_ticks':cpu[3]+cpu[4]}


def monitored_run(command, log, resources):
    """Guard planner source; forward interruption to the durable runner."""
    log,resources=Path(log),Path(resources)
    log.parent.mkdir(parents=True,exist_ok=True)
    before=planner_files();peaks={};samples=[];started=time.monotonic();last_sample=last_guard=last_write=started
    failure=None
    with log.open('w') as stream:
        process=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,
                                 env={**os.environ,'PYTHONHASHSEED':'0'})
        try:
            while process.poll() is None:
                active=planner_samples(peaks);now=time.monotonic()
                if now-last_sample>=1 or not samples:
                    samples.append({**system_sample(),'active_planner_jobs':active});last_sample=now
                if now-last_guard>=15:
                    if planner_files()!=before:
                        failure='Planner source changed during the campaign'
                        process.send_signal(signal.SIGINT)
                        process.wait()
                        break
                    last_guard=now
                if now-last_write>=5:
                    atomic_json(resources,{'planner_peaks_kb':peaks,'system_resources':samples,
                                           'sample_interval_seconds':.05,'status':'running'})
                    last_write=now
                time.sleep(.05)
        except BaseException:
            if process.poll() is None:
                process.send_signal(signal.SIGINT);process.wait()
            raise
        finally:
            samples.append(system_sample())
            atomic_json(resources,{'planner_peaks_kb':peaks,'system_resources':samples,
                                   'sample_interval_seconds':.05,'returncode':process.poll(),
                                   'wall_seconds':time.monotonic()-started,'failure':failure,'status':'finished'})
    if failure: raise RuntimeError(failure)
    return process.returncode
