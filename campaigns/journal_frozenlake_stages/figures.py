"""Render physical stage maps and checked fronts from saved analysis results."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def generate(analysis_root, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    records = json.loads((ROOT / 'benchmarks/journal_tradeoffs/physical_stages/generation.json').read_text())['instances']
    reports = [json.loads((Path(analysis_root) / (profile + '-analysis') / 'report.json').read_text())
               for profile in ('smoke', 'connected', 'extension')]
    for report in reports:
        if report['issues'] or report['errors'] or not all(r['completed'] for r in report['rows']):
            raise ValueError('Only validated complete fronts can be plotted as BOAND results')
    record = records[1]
    matrix = np.zeros((record['height'], record['width']))
    for x, y, kind in record['cells']:
        matrix[y, x] = kind == 'ice'
    fig, ax = plt.subplots(figsize=(13, 7.7))
    ax.imshow(matrix, origin='lower', cmap=ListedColormap(['#dce1e6', '#ffffff']), vmin=0, vmax=1)
    fast, safe, connector = '#cf7425', '#25895e', '#347bb9'
    for entry, exit in zip(record['stage_entries'], record['stage_exits']):
        x, y = entry
        detour = [(x, y), (x - 2, y), (x - 2, y + 8), (x + 6, y + 8), (x + 6, y + 6)]
        staircase = [(x, y)]
        for step in range(6):
            staircase.extend([(x + step, y + step + 1), (x + step + 1, y + step + 1)])
        for path, color in ((detour, fast), (staircase, safe)):
            ax.plot(*zip(*path), color=color, lw=3, solid_capstyle='round')
    previous, entry = record['stage_exits'][0], record['stage_entries'][1]
    path = [previous, (previous[0] + 2, previous[1]), (previous[0] + 2, previous[1] - 2),
            (entry[0], entry[1] - 2), entry]
    ax.plot(*zip(*path), color=connector, lw=3)
    for point, text in [(record['start'], 'Start'), (previous, 'Exit 1'),
                        (entry, 'Entry 2'), (record['goal'], 'Goal')]:
        ax.plot(*point, 'o', color='#233748', ms=8)
        ax.annotate(text, point, xytext=(0, -20), textcoords='offset points', ha='center', fontsize=11,
                    bbox=dict(fc='white', ec='none', alpha=.92, pad=1.5))
    ax.set_xticks(np.arange(-.5, record['width'], 1), minor=True)
    ax.set_yticks(np.arange(-.5, record['height'], 1), minor=True)
    ax.grid(which='minor', color='#a7b1ba', lw=.35, alpha=.5)
    ax.tick_params(which='both', bottom=False, left=False, labelbottom=False, labelleft=False)
    ax.set_title('Two connected stages in an ordinary rectangular FrozenLake map', fontsize=16, pad=16)
    handles = [Line2D([0], [0], color=c, lw=3, label=t) for c, t in (
        (fast, 'Detour: best 10, worst 20 in isolation'),
        (safe, 'Staircase: best 12, worst 12 in isolation'),
        (connector, 'Connecting corridor'))]
    fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.5, .035), ncol=1, frameon=False, fontsize=11)
    fig.text(.5, .015, 'Colored lines trace corridors, not actions. Slips can cross labeled entry/exit cells; only the final goal is terminal.',
             ha='center', fontsize=10)
    fig.subplots_adjust(bottom=.21, top=.92)
    fig.savefig(output / 'physical-map.png', dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    rows = []
    for record, report in zip(records, reports):
        expected = record['front']
        if not all(row['front'] == expected for row in report['rows']):
            raise ValueError('Saved planner front disagrees with independent reference')
        ax.plot(*zip(*expected), 'o-', label=f"{record['stages']} stage(s): {len(expected)} pairs")
        rows.extend(report['rows'])
    ax.set(xlabel='Best-case cost', ylabel='Worst-case cost',
           title='Physical maps: exact fronts matched by both BOAND* heuristics')
    ax.grid(alpha=.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / 'physical-fronts.png', dpi=180)
    plt.close(fig)
    (output / 'plotted-data.json').write_text(json.dumps(rows, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    generate(args.analysis_root, args.output)


if __name__ == '__main__':
    main()
