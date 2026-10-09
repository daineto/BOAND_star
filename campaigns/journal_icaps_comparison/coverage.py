"""Compare completed-search coverage with a local Pyperplan baseline."""
import argparse
import csv
import json
from pathlib import Path

from analysis.comparison_support import selected_results, search_complete
from experiment_support.campaigns import read_instances, resolve_dataset
from experiment_support.configurations import PAPER_CONFIGURATIONS
from campaigns.icaps2025.campaign import CAMPAIGN as ICAPS
from .campaign import CAMPAIGN


def generate(baseline, current, output):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt

    baseline, current, output = map(lambda p: Path(p).resolve(), (baseline, current, output))
    output.mkdir(parents=True, exist_ok=True)
    identities = {(e['domain'], e['instance']) for e in read_instances(CAMPAIGN, 'paper')}
    old, old_errors = selected_results(resolve_dataset(ICAPS, baseline)[0],
                                      {'Pyperplan hmax': PAPER_CONFIGURATIONS['BOAND bw']}, identities)
    new, new_errors = selected_results(resolve_dataset(CAMPAIGN, current)[0],
                                      CAMPAIGN.configurations, identities)
    if old_errors or new_errors:
        raise ValueError(f'Malformed statistics: {old_errors}, {new_errors}')
    rows = []
    counts = {}
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    styles = [('Pyperplan hmax', old, '#666666', '--'),
              ('FD hmax', new, '#0072B2', '-'), ('FD lmcut', new, '#D55E00', '-')]
    for label, runs, color, linestyle in styles:
        times = []
        for (configuration, domain, instance), run in sorted(runs.items()):
            if configuration != label:
                continue
            complete = search_complete(run, historical=label == 'Pyperplan hmax')
            seconds = run.stats[-1]['time'] if complete else None
            if seconds is not None:
                if seconds < 0 or seconds > 600:
                    raise ValueError(f'Completion time outside plot horizon: {label}/{domain}/{instance}: {seconds}')
                times.append(seconds)
            rows.append({'configuration': label, 'domain': domain, 'instance': instance,
                         'completed': complete, 'search_seconds': seconds})
        times.sort()
        counts[label] = len(times)
        # Match the published curve: sorted completed-search times, linear
        # connections between observations, and a plateau to the timeout.
        ax.plot([max(1e-6, t) for t in times] + [600],
                list(range(1, len(times) + 1)) + [len(times)],
                label=f'{label.replace("lmcut", "LM-cut")} ({len(times)})',
                color=color, linestyle=linestyle, linewidth=1.8)
    ax.set(xscale='log', xlim=(1e-4, 600), ylim=(0, len(identities)),
           xlabel='Elapsed search time (s)', ylabel='Coverage (completed searches)')
    ax.set_xticks([1e-4, 1e-3, .01, .1, 1, 10, 100, 600],
                 [r'$10^{-4}$', r'$10^{-3}$', r'$10^{-2}$', r'$10^{-1}$', '1', '10', '100', '600'])
    ax.grid(alpha=.3)
    ax.legend(loc='lower right', framealpha=.95)
    fig.tight_layout()
    for extension in ('pdf', 'svg', 'png'):
        fig.savefig(output / f'coverage-over-time.{extension}', dpi=200)
    plt.close(fig)
    with (output / 'coverage-data.csv').open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=rows[0])
        writer.writeheader(); writer.writerows(rows)
    metadata = {'baseline_run': str(baseline), 'current_run': str(current),
                'instances': len(identities), 'counts': counts,
                'definition': 'Completed searches by final elapsed search time, including unsolvable cases; preprocessing excluded.',
                'curve': 'Published-style sorted observations connected linearly, plateau to 600 seconds.',
                'limitations': ['One measurement per instance; no variability estimate.',
                               'Baseline: 8,000,000 KB/two workers; current: 6,000,000 KB/four workers.',
                               'Baseline predates journal optimizations and correctness fixes as well as native migration.',
                               'Legacy baseline completion uses final statistics marker; 79 completions lack exit codes.',
                               'Zero times are plotted at one microsecond; raw CSV values are unchanged.']}
    (output / 'coverage-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps(metadata, indent=2))
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', required=True, type=Path)
    parser.add_argument('--current', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    generate(args.baseline, args.current, args.output)


if __name__ == '__main__':
    main()
