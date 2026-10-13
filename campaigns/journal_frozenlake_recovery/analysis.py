"""Post-run validation; never claim complete fronts from partial searches."""
import argparse
import csv
import json
import math
from pathlib import Path

from analysis.comparison_support import cost_set, replay_runs, search_complete, selected_results
from experiment_support.campaigns import digest, input_path, read_instances, resolve_dataset
from .campaign import CAMPAIGN

ROOT = Path(__file__).resolve().parents[2]


def pareto(pairs):
    def numeric(pair):
        return tuple(math.inf if value == 999999 else value for value in pair)
    pairs = sorted(set(map(tuple, pairs)))
    return [p for p in pairs if not any(q != p and all(a <= b for a, b in zip(numeric(q), numeric(p)))
                                      for q in pairs)]


def analyze(dataset, output):
    dataset, output = Path(dataset).resolve(), Path(output).resolve()
    manifest = json.loads((dataset / 'manifest.json').read_text())
    if manifest['status'] != 'execution_finished':
        raise ValueError('Wait until all campaign executions finish before replaying policies')
    entries = read_instances(CAMPAIGN, manifest['profile'])
    runs, errors = selected_results(resolve_dataset(CAMPAIGN, dataset)[0], CAMPAIGN.configurations,
                                   {(e['domain'], e['instance']) for e in entries})
    inputs = {(e['domain'], e['instance']): {**e, 'domain_path': str(input_path(e['domain_path'])),
              'problem_path': str(input_path(e['problem_path']))} for e in entries}
    output.mkdir(parents=True, exist_ok=True)
    receipt = {'manifest_sha256': digest(dataset / 'manifest.json'),
               'validator_sha256': {name: digest(ROOT / name) for name in
                   ('analysis/replay_job.py', 'analysis/validate_policies.py', 'planner/preprocessing.py')},
               'policy_sha256': {str(p): digest(p) for run in runs.values()
                                for p in sorted(run.directory.rglob('*.boand.*.out'))}}
    validation_file, receipt_file = output / 'validation.json', output / 'validation-provenance.json'
    if validation_file.exists() and receipt_file.exists() and json.loads(receipt_file.read_text()) == receipt:
        checks = json.loads(validation_file.read_text())
    else:
        checks = {'/'.join(k): v for k, v in replay_runs(runs, inputs, output / 'replay').items()}
        validation_file.write_text(json.dumps(checks, indent=2) + '\n')
        receipt_file.write_text(json.dumps(receipt, indent=2) + '\n')
    metadata = json.loads((ROOT / 'benchmarks/journal_tradeoffs/frozenlake_recovery/generation.json').read_text())
    grids = {r['instance']: r for r in metadata['instances']}
    rows, issues, references = [], [], []
    for _, instance in sorted(inputs):
        grid = grids[instance]
        completed_fronts, known = [], []
        for config in CAMPAIGN.configurations:
            key = config, 'frozenlake', instance
            run = runs[key]
            check = checks.get('/'.join(key), {})
            emitted = cost_set(run)
            valid = check.get('status') == ('valid' if emitted else 'no_policies')
            completed = search_complete(run) and valid
            if manifest['profile'] == 'smoke' and not completed:
                issues.append({'instance': instance, 'configuration': config,
                               'error': 'Smoke search did not complete with successful validation'})
            front = pareto(emitted) if valid else []
            known += front
            if completed:
                completed_fronts.append(front)
                if 'front' in grid and front != list(map(tuple, grid['front'])):
                    issues.append({'instance': instance, 'configuration': config, 'error': 'Exact base front mismatch'})
            if emitted and not valid:
                issues.append({'instance': instance, 'configuration': config, 'error': check})
            rows.append({'instance': instance, 'configuration': config, 'height': grid['height'],
                         'tail': grid['tail'], 'completed': completed, 'solved': bool(front),
                         'front': front, 'front_size': len(front),
                         'search_seconds': run.stats[-1]['time'] if completed else None,
                         'first_solution_seconds': run.first_solution['time'] if run.first_solution else None,
                         'expansions': run.stats[-1]['expansions'] if run.stats else None,
                         'generations': run.stats[-1]['generations'] if run.stats else None,
                         'termination': (run.execution or {}).get('termination'),
                         'validation': check.get('status')})
        if completed_fronts and any(f != completed_fronts[0] for f in completed_fronts):
            issues.append({'instance': instance, 'error': 'Completed heuristic fronts disagree'})
        front = grid.get('front', completed_fronts[0] if completed_fronts else pareto(known))
        certainty = 'independent-exact' if 'front' in grid else 'boand-complete' if completed_fronts else 'best-known-partial'
        references.append({'instance': instance, 'front': front, 'certainty': certainty})
    report = {'campaign': CAMPAIGN.campaign_id, 'version': CAMPAIGN.version,
              'manifest_sha256': receipt['manifest_sha256'], 'analysis_sha256': digest(Path(__file__)),
              'rows': rows, 'references': references, 'issues': issues,
              'malformed_stats': {str(k): v for k, v in errors.items()},
              'limitations': ['Single measurements do not establish repeatable speedups.',
                              'Larger fronts are independently unverified unless explicitly labeled exact.',
                              'Infinity is represented by sentinel 999999, never a finite cost.',
                              'Peak memory is unavailable from this runner.']}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    with (output / 'runs.csv').open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    if issues or errors:
        raise ValueError('Recovery-route validation failed; inspect report.json')
    print(json.dumps(references, indent=2))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    analyze(args.dataset, args.output)


if __name__ == '__main__':
    main()
