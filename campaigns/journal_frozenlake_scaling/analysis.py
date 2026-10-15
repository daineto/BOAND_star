"""Validate physical-stage fronts and replay all emitted original-PDDL policies."""
import argparse
import json
from pathlib import Path

from analysis.comparison_support import cost_set, replay_runs, search_complete, selected_results
from experiment_support.campaigns import digest, input_path, read_instances, resolve_dataset
from .campaign import CAMPAIGN

ROOT = Path(__file__).resolve().parents[2]


def analyze(dataset, output):
    dataset, output = Path(dataset).resolve(), Path(output).resolve()
    manifest = json.loads((dataset / 'manifest.json').read_text())
    if manifest['status'] != 'execution_finished':
        raise ValueError('Wait for all executions before replay')
    entries = read_instances(CAMPAIGN, manifest['profile'])
    runs, errors = selected_results(resolve_dataset(CAMPAIGN, dataset)[0], CAMPAIGN.configurations,
                                   {(e['domain'], e['instance']) for e in entries})
    inputs = {(e['domain'], e['instance']): {
        **e, 'domain_path': str(input_path(e['domain_path'])),
        'problem_path': str(input_path(e['problem_path']))} for e in entries}
    output.mkdir(parents=True, exist_ok=True)
    checks = {'/'.join(k): v for k, v in replay_runs(runs, inputs, output / 'replay',
        replay_module='analysis.frozenlake_policy_replay').items()}
    (output / 'validation.json').write_text(json.dumps(checks, indent=2) + '\n')
    definitions = ROOT / 'benchmarks/journal_tradeoffs/stage_scaling/generation.json'
    records = {r['instance']: r for r in json.loads(definitions.read_text())['instances']}
    rows, issues = [], []
    for key, run in sorted(runs.items()):
        config, domain, instance = key
        check = checks.get('/'.join(key), {})
        emitted = cost_set(run)
        valid = check.get('status') == 'valid'
        completed = search_complete(run) and valid
        reference = list(map(tuple, records[instance]['front']))
        if not completed or emitted != reference:
            issues.append({'identity': list(key), 'error': 'Expected complete front not established',
                           'front': emitted, 'reference': reference, 'validation': check.get('status')})
        rows.append({'configuration': config, 'instance': instance,
                     'completed': completed, 'front': emitted if valid else [],
                     'search_seconds': run.stats[-1]['time'] if completed else None,
                     'expansions': run.stats[-1]['expansions'] if run.stats else None,
                     'generations': run.stats[-1]['generations'] if run.stats else None,
                     'validation': check.get('status'),
                     'termination': (run.execution or {}).get('termination')})
    report = {'campaign': CAMPAIGN.campaign_id, 'version': CAMPAIGN.version,
              'profile': manifest['profile'], 'rows': rows, 'issues': issues,
              'errors': {str(k): v for k, v in errors.items()},
              'analysis_sha256': digest(Path(__file__)),
              'manifest_sha256': digest(dataset / 'manifest.json'),
              'reference_sha256': digest(definitions),
              'limitations': ['Single observations validate behavior; they do not establish repeatable speedups.',
                              'General costs follow the composition proof; timing is measured only on these fixed cases.']}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(rows, indent=2), flush=True)
    if issues or errors:
        raise ValueError('Physical stage validation did not establish the reference fronts')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    analyze(args.dataset, args.output)


if __name__ == '__main__':
    main()
