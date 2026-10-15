"""Regenerate recovery-route figures and phase-separated numerical summaries."""
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path

from analysis.results import read_stats
from experiment_support.campaigns import digest


def generate(evaluation, output):
    evaluation, output = Path(evaluation).resolve(), Path(output).resolve()
    status = json.loads((evaluation / 'status.json').read_text())
    if status['phase'] != 'finished':
        raise ValueError('Wait for execution and policy validation to finish')
    output.mkdir(parents=True, exist_ok=True)
    report = json.loads((evaluation / 'pilot-analysis/report.json').read_text())
    if report['issues'] or report['malformed_stats']:
        raise ValueError('Cannot publish an evaluation with unresolved validation errors')
    dataset = Path(status['pilot_directory'])
    manifest = json.loads((dataset / 'manifest.json').read_text())
    jobs = {(j['configuration'], j['instance']): j for j in manifest['runs']}
    configurations = manifest['campaign']['configurations']
    configuration_names = {label: data['name'] for label, data in configurations.items()}
    rows, arrivals, windows = [], [], {}
    for row in report['rows']:
        job = jobs[configuration_names[row['configuration']], row['instance']]
        folder = dataset / job['attempts'][-1]['directory']
        execution = json.loads((folder / 'execution.json').read_text())
        backend_file = next((folder / 'solutions').glob('*/*.backend.json'))
        backend = json.loads(backend_file.read_text())
        stats_file = next((folder / 'solutions').glob('*/*.stats'))
        stats = read_stats(stats_file)
        solutions = [s for s in stats if s['best'] >= 0]
        finite = [s for s in solutions if s['worst'] != 999999]
        enriched = {**row,
                    'parsing_compilation_grounding_seconds': backend['parsing_compilation_grounding_seconds'],
                    'backend_heuristic_setup_seconds': backend['backend_heuristic_setup_seconds'],
                    'invocation_wall_seconds': (datetime.fromisoformat(execution['ended_at']) -
                                                datetime.fromisoformat(execution['started_at'])).total_seconds(),
                    'first_finite_policy_seconds': min((s['time'] for s in finite), default=None),
                    'last_policy_seconds': max((s['time'] for s in solutions), default=None),
                    'max_open': stats[-1]['max_open'] if row['completed'] else None,
                    'backend_record_sha256': digest(backend_file), 'stats_sha256': digest(stats_file)}
        rows.append(enriched)
        reference = set(map(tuple, row['front']))
        seen = set()
        for s in solutions:
            pair = s['best'], s['worst']
            if pair in reference and pair not in seen:
                seen.add(pair)
                arrivals.append({'configuration': row['configuration'], 'instance': row['instance'],
                                 'height': row['height'], 'tail': row['tail'], 'time': s['time'],
                                 'reference_pairs_found': len(seen), 'best': s['best'], 'worst': s['worst']})
    for profile in ('smoke', 'pilot'):
        run = Path(status[f'{profile}_directory'])
        data = json.loads((run / 'manifest.json').read_text())
        executions = [json.loads((run / job['attempts'][-1]['directory'] / 'execution.json').read_text())
                      for job in data['runs']]
        start = min(datetime.fromisoformat(e['started_at']) for e in executions)
        end = max(datetime.fromisoformat(e['ended_at']) for e in executions)
        validations = json.loads((evaluation / f'{profile}-analysis/validation.json').read_text())
        windows[profile] = {'execution_window_seconds': (end - start).total_seconds(),
                            'jobs': len(executions),
                            'successful_executions': sum(e['returncode'] == 0 for e in executions),
                            'replayed_policies': sum(len(v.get('policies', [])) for v in validations.values()),
                            'validation_statuses': sorted({v['status'] for v in validations.values()})}
    resources = json.loads((evaluation / 'resources.json').read_text())
    samples = resources['samples']
    summary = {'source_revision': manifest['source']['revision'], 'windows': windows,
               'controller_wall_seconds': (datetime.fromisoformat(status['ended_at']) -
                                           datetime.fromisoformat(status['started_at'])).total_seconds(),
               'pilot_sum_search_seconds': sum(r['search_seconds'] for r in rows if r['completed']),
               'minimum_available_gib': min(s['available_kb'] for s in samples) / 1024**2,
               'swap_used_kb_range': [min(s['swap_used_kb'] for s in samples), max(s['swap_used_kb'] for s in samples)],
               'maximum_observed_planner_hwm_kb': max((p['observed_hwm_kb'] for p in resources['planner_peaks'].values()), default=None),
               'sampled_planner_processes': len(resources['planner_peaks']),
               'limitations': ['One observation per case/configuration; not a speedup comparison.',
                               'Execution windows exclude preparation/replay; controller wall includes both stages.',
                               'Preprocessing/setup metrics exclude some process startup overhead.',
                               'Sampled HWM can miss processes or underestimate final peaks; not exact per-instance memory.'],
               'sources_sha256': {str(p): digest(p) for p in
                   (evaluation / 'status.json', evaluation / 'resources.json',
                    evaluation / 'pilot-analysis/report.json', dataset / 'manifest.json')},
               'report_generator_sha256': digest(Path(__file__))}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    for name, data in [('timings.csv', rows), ('quality-arrivals.csv', arrivals)]:
        with (output / name).open('w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    colors = {'FD hmax': '#2878a8', 'FD lmcut': '#c27625'}
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for config in configuration_names:
        for tail, style in [('cyclic', '-'), ('pit', '--')]:
            subset = sorted((r for r in rows if r['configuration'] == config and r['tail'] == tail and r['completed']), key=lambda r:r['height'])
            label = f'{config}, {tail}'
            axes[0].plot([r['height'] for r in subset], [r['search_seconds'] for r in subset], style + 'o', color=colors[config], label=label)
            axes[1].plot([r['height'] for r in subset], [r['expansions'] for r in subset], style + 'o', color=colors[config], label=label)
    axes[0].set(xlabel='Grid height (width = 3)', ylabel='Completed search time (s)', yscale='log')
    axes[1].set(xlabel='Grid height (width = 3)', ylabel='Expansions', yscale='log')
    for ax in axes:
        ax.grid(alpha=.2);ax.legend(fontsize=8)
    complete_three = all(r['completed'] and r['front_size'] == 3 for r in rows)
    fig.suptitle('Recovery-route family: three Pareto pairs at every tested height' if complete_three
                 else 'Recovery-route family: completed searches; inspect CSV for coverage failures')
    fig.tight_layout()
    for extension in ('png', 'pdf', 'svg'):
        fig.savefig(output / f'recovery-scaling.{extension}', dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for tail, ax in zip(('cyclic', 'pit'), axes):
        for config in configuration_names:
            subset = sorted((a for a in arrivals if a['configuration'] == config and a['height'] == 10 and a['tail'] == tail), key=lambda a:a['time'])
            ax.step([1e-5] + [a['time'] for a in subset], [0] + [a['reference_pairs_found'] for a in subset], where='post', label=config, color=colors[config])
        complete = all(r['completed'] for r in rows if r['height'] == 10 and r['tail'] == tail)
        ax.set(xscale='log', xlabel='Search time (s)', ylabel='Final-front pairs recovered' if complete else 'Known-front pairs recovered',
               yticks=(0, 1, 2, 3), title=f'3×10, {"ice" if tail == "cyclic" else "pit"} lower tile')
        ax.grid(alpha=.2);ax.legend()
    fig.tight_layout()
    for extension in ('png', 'pdf', 'svg'):
        fig.savefig(output / f'quality-over-time.{extension}', dpi=180)
    plt.close(fig)
    print(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evaluation', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    generate(args.evaluation, args.output)


if __name__ == '__main__':
    main()
