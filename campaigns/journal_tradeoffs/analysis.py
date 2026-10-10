"""Pilot quality and difficulty analysis with explicit reference certainty."""
import argparse
import csv
import json
import math
from pathlib import Path
from analysis.comparison_support import cost_set, replay_runs, search_complete, selected_results
from analysis.frozenlake_tradeoffs import frontier as exhaustive_frontier
from experiment_support.campaigns import digest, input_path, read_instances, resolve_dataset
from planner.policy import CYCLE_COST
from .campaign import CAMPAIGN

ROOT = Path(__file__).resolve().parents[2]


def pareto(pairs):
    def numeric(pair):
        return tuple(math.inf if x == CYCLE_COST else x for x in pair)
    pairs = sorted(set(map(tuple, pairs)))
    return [p for p in pairs if not any(q != p and all(a <= b for a, b in zip(numeric(q), numeric(p))) for q in pairs)]


def analyze(dataset, output):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    directory, output = Path(dataset).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((directory / 'manifest.json').read_text())
    entries = read_instances(CAMPAIGN, manifest['profile'])
    ids = {(e['domain'], e['instance']) for e in entries}
    runs, errors = selected_results(resolve_dataset(CAMPAIGN, directory)[0], CAMPAIGN.configurations, ids)
    inputs = {(e['domain'], e['instance']): {**e, 'domain_path': str(input_path(e['domain_path'])),
               'problem_path': str(input_path(e['problem_path']))} for e in entries}
    validation_file = output / 'policy-validation.json'
    if validation_file.exists():
        validations = json.loads(validation_file.read_text())
    else:
        validations = {'/'.join(k): v for k, v in replay_runs(runs, inputs, output / 'replay', workers=4).items()}
        validation_file.write_text(json.dumps(validations, indent=2) + '\n')
    generation = json.loads((ROOT / 'benchmarks/journal_tradeoffs/frozenlake/generation.json').read_text())
    grids = {r['instance']: r for r in generation['instances']}
    rows, instances, issues = [], [], []
    for instance in sorted(i for _, i in ids):
        grid = grids[instance]
        cells = {(x, y): kind for x, y, kind in grid['cells']}
        try:
            oracle, assignments = exhaustive_frontier(cells, tuple(grid['start']), tuple(grid['goal']))
            oracle = [(b, CYCLE_COST if math.isinf(w) else w) for b, w in oracle]
        except ValueError as error:
            oracle, assignments = None, str(error)
        complete_fronts, known = [], []
        for config in CAMPAIGN.configurations:
            key = config, 'frozenlake', instance
            run = runs[key]
            check = validations.get('/'.join(key), {})
            has_policy = bool(cost_set(run))
            valid = check.get('status') == ('valid' if has_policy else 'no_policies')
            completed = search_complete(run) and valid
            front = pareto(cost_set(run)) if has_policy and valid else []
            if completed:
                complete_fronts.append(front)
            known += front
            if oracle is not None and completed and front != oracle:
                issues.append({'instance': instance, 'configuration': config, 'error': 'oracle disagreement',
                               'boand_front': front, 'oracle_front': oracle})
            if has_policy and not valid:
                issues.append({'instance': instance, 'configuration': config, 'error': check})
            rows.append({'instance': instance, 'configuration': config, 'family': grid['family'],
                         'width': grid['width'], 'height': grid['height'],
                         'ice_cells': sum(k == 'ice' for k in cells.values()),
                         'completed': completed, 'solved': bool(front), 'front': front,
                         'front_size': len(front), 'validation': check.get('status'),
                         'termination': (run.execution or {}).get('termination'),
                         'search_seconds': run.stats[-1]['time'] if completed and run.stats else None,
                         'last_recorded_search_seconds': run.stats[-1]['time'] if run.stats else None,
                         'first_solution_seconds': run.first_solution['time'] if run.first_solution else None,
                         'expansions': run.stats[-1].get('expansions') if run.stats else None,
                         'generations': run.stats[-1].get('generations') if run.stats else None})
        if complete_fronts and any(f != complete_fronts[0] for f in complete_fronts):
            issues.append({'instance': instance, 'error': 'completed heuristic fronts disagree'})
        reference = oracle if oracle is not None else complete_fronts[0] if complete_fronts else pareto(known)
        certainty = 'independent-exact' if oracle is not None else 'boand-complete' if complete_fronts else 'best-known-partial'
        finite = [p for p in reference if p[1] != CYCLE_COST]
        best_spread = max((p[0] for p in reference), default=0) - min((p[0] for p in reference), default=0)
        worst_spread = max((p[1] for p in finite), default=0) - min((p[1] for p in finite), default=0)
        instances.append({'instance': instance, 'family': grid['family'], 'seed': grid['seed'],
                          'width': grid['width'], 'height': grid['height'], 'front': reference,
                          'front_size': len(reference), 'finite_points': len(finite),
                          'cyclic_points': len(reference) - len(finite), 'certainty': certainty,
                          'policy_assignments': assignments, 'best_spread': best_spread,
                          'finite_worst_spread': worst_spread})
    for name, records in [('instances.csv', instances), ('runs.csv', rows)]:
        with (output / name).open('w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    summary = {c: {'completed': sum(r['completed'] for r in rows if r['configuration'] == c),
                   'solved': sum(r['solved'] for r in rows if r['configuration'] == c),
                   'non_singleton_completed': sum(r['completed'] and r['front_size'] > 1 for r in rows if r['configuration'] == c)}
               for c in CAMPAIGN.configurations}
    report = {'campaign': CAMPAIGN.campaign_id, 'version': CAMPAIGN.version,
              'dataset': str(directory), 'manifest_sha256': digest(directory / 'manifest.json'),
              'analysis_sha256': digest(Path(__file__)), 'summary': summary, 'instances': instances,
              'issues': issues, 'malformed_stats': {str(k): v for k, v in errors.items()},
              'limits': {'seconds': 600, 'memory_kb': 6000000, 'workers': 4},
              'limitations': ['One run per configuration; timings characterize difficulty, not repeatable speedups.',
                             'Partial reference fronts are best known and may be incomplete.',
                             'Infinity is excluded from finite trade-off magnitudes.']}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for config in CAMPAIGN.configurations:
        subset = [r for r in rows if r['configuration'] == config and r['completed'] and r['search_seconds'] is not None]
        axes[0].scatter([r['ice_cells'] for r in subset], [max(r['search_seconds'], 1e-6) for r in subset], label=config, alpha=.7)
    axes[0].set(xlabel='Ice cells', ylabel='Completed search time (s)', yscale='log');axes[0].legend()
    axes[1].bar(range(len(instances)), [r['front_size'] for r in instances], color=['#d28d39' if r['certainty']=='best-known-partial' else '#397a97' for r in instances])
    axes[1].set_xticks(range(len(instances)), [r['instance'] for r in instances], rotation=90, fontsize=7)
    axes[1].set(ylabel='Reference cost pairs', title='Orange: incomplete reference; blue: complete')
    fig.tight_layout()
    for extension in ('png', 'pdf', 'svg'):
        fig.savefig(output / f'pilot-quality-difficulty.{extension}', dpi=180)
    plt.close(fig)
    lines = ['# FrozenLake pilot results', '', 'These are candidate inputs, not the final journal benchmark.', '',
             '| Configuration | Completed | Solved | Completed non-singleton fronts |', '| --- | ---: | ---: | ---: |']
    for config, result in summary.items():
        lines.append(f'| {config} | {result["completed"]}/{len(instances)} | {result["solved"]} | {result["non_singleton_completed"]} |')
    lines += ['', '![Quality and difficulty](pilot-quality-difficulty.png)', '',
              '| Instance | Reference front | Certainty |', '| --- | --- | --- |']
    for record in instances:
        pretty = ', '.join(f'({b}, {"∞" if w == CYCLE_COST else w})' for b, w in record['front']) or 'No policy'
        lines.append(f'| {record["instance"]} | {pretty} | {record["certainty"]} |')
    lines += ['', 'Limits: 600 seconds/job, 6,000,000 KB virtual memory/job, four workers, PYTHONHASHSEED=0.',
              'Search times exclude preprocessing; single measurements are not speedup evidence.',
              'Original-PDDL replay validates every emitted policy, including incumbents from incomplete searches.',
              f'Correctness issues: {len(issues)}; malformed statistics: {len(errors)}.',
              'Complete BOAND fronts rely on its optimality guarantees; only small oracle fronts are independently exhaustive.']
    (output / 'report.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps(summary, indent=2))
    if issues or errors:
        raise ValueError('Pilot correctness issues; inspect report.json')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    analyze(args.dataset, args.output)


if __name__ == '__main__':
    main()
