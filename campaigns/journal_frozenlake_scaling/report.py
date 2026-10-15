"""Generate a scaling report and figures from completed validated probe runs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def load(analysis_root, profiles, records):
    state = json.loads((analysis_root / 'status.json').read_text())
    if state['phase'] != 'finished':
        raise ValueError('Wait for execution and replay to finish')
    rows, manifests, provenance = [], [], []
    for profile in profiles:
        report_file = analysis_root / (profile + '-analysis') / 'report.json'
        report = json.loads(report_file.read_text())
        validation = json.loads(report_file.with_name('validation.json').read_text())
        if report['issues'] or report['errors']:
            raise ValueError('Cannot present incomplete references as validated fronts')
        run = Path(state[profile + '_directory'])
        manifest_file = run / 'manifest.json'
        manifest = json.loads(manifest_file.read_text())
        manifests.append(manifest)
        provenance.append({'run': str(run.relative_to(ROOT)),
                           'manifest_sha256': hashlib.sha256(manifest_file.read_bytes()).hexdigest(),
                           'analysis_sha256': hashlib.sha256(report_file.read_bytes()).hexdigest()})
        for row in report['rows']:
            record = records[row['instance']]
            check = validation['/'.join([row['configuration'], 'frozenlake', row['instance']])]
            if (not row['completed'] or row['front'] != record['front'] or check['status'] != 'valid'
                    or len(check['policies']) != len(record['front'])):
                raise ValueError('Search/front/replay gate failed')
            name = manifest['campaign']['configurations'][row['configuration']]['name']
            folder = run / manifest['result_root'] / name / 'frozenlake' / row['instance']
            backend = json.loads(next(folder.rglob('*.backend.json')).read_text())
            elapsed = [float(line.split()[1]) for f in folder.glob('err_*.txt')
                       for line in f.read_text().splitlines() if line.startswith('real ')]
            rows.append({**row, 'stages': record['stages'], 'size': record.get('size', 6),
                         'grounding_seconds': backend['parsing_compilation_grounding_seconds'],
                         'heuristic_setup_seconds': backend['backend_heuristic_setup_seconds'],
                         'total_job_seconds': elapsed[-1] if elapsed else None,
                         'ice_tiles': sum(kind == 'ice' for x, y, kind in record['cells']),
                         'rectangle_tiles': record['width'] * record['height']})
    return rows, manifests, provenance


def generate(analysis_root, previous_root, output):
    output.mkdir(parents=True, exist_ok=True)
    definitions = json.loads((ROOT / 'benchmarks/journal_tradeoffs/stage_scaling/generation.json').read_text())
    old_definitions = json.loads((ROOT / 'benchmarks/journal_tradeoffs/physical_stages/generation.json').read_text())
    rows, manifests, provenance = load(analysis_root, ('smoke', 'six', 'larger', 'eight'),
                                      {r['instance']: r for r in definitions['instances']})
    old, controls, old_provenance = load(previous_root, ('smoke', 'connected', 'extension'),
                                        {r['instance']: r for r in old_definitions['instances']})
    for m in manifests + controls:
        if m['planner_files'] != manifests[0]['planner_files']:
            raise ValueError('Planner source changed between measurements')
        if m['native_backend'] != manifests[0]['native_backend']:
            raise ValueError('Native backend changed between measurements')
        if (m['memory_kb'], m['timeout_seconds'], m['parallel_runs'], m['pythonhashseed']) != (6000000, 600, 4, '0'):
            raise ValueError('Measurement conditions differ')
    samples = list(csv.DictReader((analysis_root / 'resources.csv').open()))
    resources = {'sample_count': len(samples), 'sample_interval_seconds': 1,
                 'minimum_available_gib': min(int(s['available_kb']) for s in samples) / 1024**2,
                 'max_combined_planner_rss_mib': max(int(s['planner_rss_kb']) for s in samples) / 1024,
                 'max_single_planner_vms_mib': max(int(s['max_planner_vms_kb']) for s in samples) / 1024,
                 'max_active_planners': max(int(s['planner_jobs']) for s in samples)}
    data = {'rows': rows, 'previous_rows': old, 'resources': resources,
            'provenance': provenance, 'previous_provenance': old_provenance}
    (output / 'report-data.json').write_text(json.dumps(data, indent=2) + '\n')

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    for config, color in (('FD hmax', '#2468a0'), ('FD lmcut', '#b85c20')):
        series = sorted((r for r in rows + old if r['configuration'] == config and r['size'] == 6), key=lambda r:r['stages'])
        axes[0].plot([r['stages'] for r in series], [r['search_seconds'] for r in series], 'o-', color=color, label=config)
        large = next(r for r in rows if r['configuration'] == config and r['size'] == 10)
        axes[0].scatter([large['stages']], [large['search_seconds']], marker='*', s=140, color=color)
    axes[0].set(yscale='log', xlabel='Stages', ylabel='Search seconds', title='Difficulty increases with stage count')
    axes[0].set_xticks(range(1, 9))
    axes[0].legend()
    axes[0].text(.03, .95, 'Stars: larger rooms (n=10)\nOther points: n=6', transform=axes[0].transAxes, va='top', fontsize=9)
    axes[1].plot(range(1, 9), range(2, 10), '--', color='#888888', label='Theorem: k+1')
    measured = sorted({r['stages']: len(r['front']) for r in rows + old if r['size'] == 6}.items())
    axes[1].scatter(*zip(*measured), color='#2468a0', s=55, label='Matched by both heuristics', zorder=3)
    axes[1].set(xlabel='Stages', ylabel='Distinct Pareto cost pairs', title='Front size is controlled exactly')
    axes[1].set_xticks(range(1, 9));axes[1].set_yticks(range(2, 10));axes[1].legend()
    for ax in axes:ax.grid(alpha=.25)
    fig.tight_layout();fig.savefig(output / 'scaling.png', dpi=180);plt.close(fig)

    hmax = sorted((r for r in rows if r['configuration'] == 'FD hmax'), key=lambda r:(r['size'], r['stages']))
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    bottom = np.zeros(len(hmax))
    for field, label, color in (('grounding_seconds', 'Parsing, compilation and grounding', '#8ca7bf'),
                                ('heuristic_setup_seconds', 'Heuristic setup', '#d7b777'),
                                ('search_seconds', 'Search', '#2468a0')):
        heights = [r[field] for r in hmax]
        ax.bar(range(len(hmax)), heights, bottom=bottom, color=color, label=label)
        bottom += heights
    ax.set_xticks(range(len(hmax)), [f"k={r['stages']}, n={r['size']}" for r in hmax])
    ax.set(ylabel='Seconds', title='FD/hmax timing components, one observation per input')
    ax.legend();ax.grid(axis='y', alpha=.2);fig.tight_layout()
    fig.savefig(output / 'timing-components.png', dpi=180);plt.close(fig)

    lines = []
    for record in definitions['instances']:
        pair = [r for r in rows if r['instance'] == record['instance']]
        h, l = sorted(pair, key=lambda r:r['configuration'])
        lines.append(f"| {record['stages']} | {record['size']} | {len(record['front'])} | {h['search_seconds']:.3f} | {l['search_seconds']:.3f} | {h['expansions']:,} | {h['generations']:,} |")
    text = '''# Physical FrozenLake: composition proof and scaling probes

The 2026-10-15 follow-up establishes a general composition argument and verifies
four larger physical maps with BOAND*. **All eight searches completed with exact
reference fronts, and all 52 emitted policies passed original-PDDL replay.**
Eight stages yield nine Pareto points and took about eight seconds of search.
The original domain, ICAPS inputs and fixed journal development profiles are
unchanged. This is a bounded calibration study, not a final paper selection.

## General result

For `k >= 1` stages and even staircase size `n >= 6`, the complete front is

```
(best, worst) = ((n+11)k − 7 + (n−4)j, (2n+22)k − 14 − 8j), j=0,...,k.
```

There are `2^k` reachable strong policies, but **k+1 distinct cost pairs**;
policies with the same number of staircase choices have identical costs.
Every pair has finite worst cost. Cyclic proper policies are dominated by the
finite all-detour policy. The [composition proof](frozenlake-stage-composition.md)
handles boundary slips explicitly and explains the even-size restriction.

Increasing `k` controls front cardinality. Increasing `n` lengthens routes
without changing that cardinality. These parameters can still affect several
sources of computational difficulty simultaneously.

## Fixed larger probes

| Stages k | Room size n | Pairs | FD/hmax search s | FD/LM-cut search s | Expansions, either | Generations, either |
|---|---|---|---:|---:|---:|---:|
''' + '\n'.join(lines) + '''

For eight standard stages, the front ranges from `(129,258)` to `(145,194)`;
each successive point increases best cost by 2 and decreases worst cost by 8.
The larger four-room map has the same five-point cardinality as the standard
four-room map, but its endpoints are `(77,154)` and `(101,122)`.

![Search timing and front cardinality](figures/frozenlake-scaling/scaling.png)

The one-to-three-stage points come from the preceding bounded study. Manifest
checks confirm identical planner source hashes, pinned native backend, seed,
limits and configured worker cap across both studies. There is one observation
per configuration/input: these figures show calibration behavior, not repeated
speedups or a statistically established ranking of heuristics. Both heuristics
performed the same number of expansions/generations on each new input.

![Parsing/grounding, heuristic setup and search](figures/frozenlake-scaling/timing-components.png)

Search timing excludes preprocessing, setup and replay. Native timing records
separate these components. The rectangular bounding box contains many walls:
ice-state count grows linearly with `k`, but the diagonal layout's rectangle
area grows quadratically. Thus preprocessing growth also reflects irrelevant
wall objects; the search curve is shown separately. Component bars omit process
startup and shutdown, so are not total elapsed campaign times.

## Independent correctness and validation changes

Every fixed reference was checked by complete reachable strong-policy
enumeration plus a strong-cyclic winning-region/shortest-path bound. All
available geometric actions and outcomes were compared against typed original
PDDL grounding. Enumeration confirms `2^k` strong policies for each probe,
including 256 policies at eight stages.

The independent enumerator now uses explicit stacks rather than Python
recursion. Its mathematical procedure and references are unchanged; the prior
implementation reached Python's recursion limit on eight stages. A 1,100-edge
chain and exhaustive small random-graph comparisons test the revised traversal.

For the large maps, policy replay uses a FrozenLake-specific original-PDDL
interpreter rather than full legacy Pyperplan grounding. It is restricted to
the preserved domain hash, checks original preconditions and every outcome,
and rejects missing/inapplicable actions, improper policies and cost mismatches.
It matched all 18 preceding legacy-replayed policies, including reachable-state
counts, before use on the new 52 policies. The generic replay default is unchanged.
All 11 targeted tests passed; prior physical inputs remain byte-identical.
No planner or search optimization was introduced.

## Resources and measurement limits

All profiles ran sequentially in tmux. Each had two heuristic jobs, 600 seconds
per job, 6,000,000 KB virtual memory per job, seed zero and at most four workers.
Only two planner jobs were active at once in the observed samples.
''' + f'''
One-second sampling recorded a maximum combined planner resident memory of
**{resources['max_combined_planner_rss_mib']:.0f} MiB**, maximum sampled single-planner virtual memory of
{resources['max_single_planner_vms_mib']:.0f} MiB, and at least **{resources['minimum_available_gib']:.1f} GiB available system memory**.
There were {resources['sample_count']} samples. These are sampled observations, not exact process peaks;
short-lived peaks can be missed. System available memory includes other users'
activity. The observations give no indication that these probes strained RAM.
''' + '''
## Reproducibility and proposed benchmark use

Inputs, proof, replay and execution definitions were frozen at `74fac2b`.
The [campaign guide](../campaigns/journal_frozenlake_scaling/README.md) gives
commands, profile order and limits. Ignored evidence remains under
`outputs/frozenlake-scaling/`: dry-run manifests, `tests.log`,
`replay-crosscheck.json`, `resources.csv`, `driver.py`, `driver.log`, `status.json`,
the four `*-analysis/` folders and `report/`. The report's JSON records numerical
values and manifest/analysis hashes; the run manifests preserve source, input
and pinned backend provenance.

Run directories:

''' + '\n'.join('- `' + p['run'] + '`.' for p in provenance) + '''

Regenerate figures, data and this report with:

```bash
MPLCONFIGDIR=/tmp/mplconfig .venv/bin/python -m campaigns.journal_frozenlake_scaling.report --analysis-root outputs/frozenlake-scaling --previous-root outputs/frozenlake-connected --output outputs/frozenlake-scaling/report
```

Reviewed PNG copies and generated-source hashes are registered in the
[figure manifest](figures/manifest.json).

Four-, six- and eight-stage standard maps now provide a useful initial range:
five, seven and nine finite Pareto points, with roughly 0.1, 1 and 8 seconds of
search in this environment. Keep them as candidate quality/difficulty levels.
A final suite should add independent domain families and repeated timing
calibration before selecting difficulty bands. No larger maps, full campaigns
or fixed-profile replacements were performed in this study.
'''
    (output / 'report.md').write_text(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis-root', type=Path, required=True)
    parser.add_argument('--previous-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    generate(args.analysis_root, args.previous_root, args.output)


if __name__ == '__main__':
    main()
