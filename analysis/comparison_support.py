"""Shared accounting for completed searches, costs, elapsed times and replay."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from analysis.results import Run, read_stats, attempt_directories
import subprocess
import sys


def cost_set(run):
    return sorted({(row['best'], row['worst']) for row in run.stats if row['best'] >= 0})


def search_complete(run, historical=False):
    if not run.complete:
        return False
    return historical or bool(run.execution and run.execution.get('state') == 'finished'
                              and run.execution.get('returncode') == 0)


def elapsed_time(run):
    files = list(run.directory.glob('err_*.txt'))
    if files:
        for line in reversed(files[0].read_text(errors='replace').splitlines()):
            parts = line.split()
            if len(parts) == 2 and parts[0] == 'real':
                try:
                    return float(parts[1])
                except ValueError:
                    pass
    return None


def replay_runs(runs, entries, output, workers=4, memory_kb=6_000_000, seconds=600):
    """Validate every emitted incumbent, including policies from partial searches."""
    output = Path(output); output.mkdir(parents=True, exist_ok=True)

    def check(run):
        key = (run.configuration, run.domain, run.instance)
        folder = output / run.configuration / run.domain / run.instance
        folder.mkdir(parents=True, exist_ok=True)
        stats = [row for row in run.stats if row['best'] >= 0]
        policies = sorted(run.directory.rglob('*.boand.*.out'),
                          key=lambda p: int(p.name.split('.boand.',1)[1].split('.',1)[0]))
        if len(stats) != len(policies):
            return key, {'status': 'invalid', 'error': 'Policy/statistics counts differ'}
        if not policies:
            return key, {'status': 'no_policies', 'policies': []}
        entry = entries[run.domain, run.instance]
        request = {'domain_path': entry['domain_path'], 'problem_path': entry['problem_path'],
                   'memory_kb': memory_kb,
                   'policies': [(str(f), [s['best'], s['worst']]) for f, s in zip(policies, stats)]}
        file = folder / 'request.json'; file.write_text(json.dumps(request, indent=2) + '\n')
        result = folder / 'result.json'
        result.unlink(missing_ok=True)
        with (folder / 'stdout.log').open('w') as stdout, (folder / 'stderr.log').open('w') as stderr:
            code = subprocess.run(['timeout', '--kill-after=5', str(seconds), sys.executable,
                                   '-m', 'analysis.replay_job', str(file), str(result)],
                                  stdout=stdout, stderr=stderr).returncode
        if result.exists():
            data = json.loads(result.read_text())
        else:
            data = {'status': 'validation_timeout' if code == 124 else 'validation_error',
                    'returncode': code}
        return key, data

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(pool.map(check, runs.values()))


def selected_results(root, configurations, identities):
    """Retain every selected case and report malformed statistics as failures."""
    root = Path(root)
    selected = attempt_directories(root)
    runs, errors = {}, {}
    for label, config in configurations.items():
        for order, (domain, instance) in enumerate(sorted(identities)):
            folder = selected.get((config.name, domain, instance), root/config.name/domain/instance)
            file = folder/'solutions'/f'{domain}_{instance}.sol'/f'{instance}.stats'
            try:
                stats = read_stats(file) if file.exists() else ()
            except (ValueError, OSError) as error:
                stats = ()
                errors[label,domain,instance] = str(error)
            runs[label,domain,instance] = Run(label,domain,instance,folder,stats,order)
    return runs, errors
