"""Replay composition diagnostics; preserve abstract/geometric distinctions."""
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
    if manifest['status'] != 'execution_finished':raise ValueError('Wait for all executions before replay')
    entries = read_instances(CAMPAIGN, manifest['profile'])
    runs, errors = selected_results(resolve_dataset(CAMPAIGN, dataset)[0], CAMPAIGN.configurations,
                                   {(e['domain'], e['instance']) for e in entries})
    # The generic result reader emits placeholders for configurations excluded
    # by a profile; retain only actual scheduled identities.
    labels = CAMPAIGN.profiles[manifest['profile']].configurations
    runs = {key: value for key, value in runs.items() if key[0] in labels}
    errors = {key: value for key, value in errors.items() if key[0] in labels}
    inputs = {(e['domain'], e['instance']): {**e, 'domain_path': str(input_path(e['domain_path'])),
              'problem_path': str(input_path(e['problem_path']))} for e in entries}
    output.mkdir(parents=True, exist_ok=True)
    checks = {'/'.join(k): v for k, v in replay_runs(runs, inputs, output / 'replay').items()}
    (output / 'validation.json').write_text(json.dumps(checks, indent=2) + '\n')
    definitions = json.loads((ROOT / 'benchmarks/journal_tradeoffs/serial_composition/generation.json').read_text())
    records = {r['instance']: r for r in definitions['instances']}
    rows, issues = [], []
    for key, run in sorted(runs.items()):
        config, domain, instance = key
        record = records[instance]
        check = checks.get('/'.join(key), {})
        emitted = cost_set(run)
        valid = check.get('status') == ('valid' if emitted else 'no_policies')
        completed = search_complete(run) and valid
        if emitted and not valid:issues.append({'instance': instance, 'error': check})
        if domain == 'serial-topology':
            if not completed or emitted != list(map(tuple, record['front'])):
                issues.append({'instance': instance, 'configuration': config,
                               'error': 'Composition reference not established', 'front': emitted})
        rows.append({'configuration': config, 'domain': domain, 'instance': instance,
                     'completed': completed, 'front': emitted if valid else [],
                     'search_seconds': run.stats[-1]['time'] if completed else None,
                     'expansions': run.stats[-1]['expansions'] if run.stats else None,
                     'generations': run.stats[-1]['generations'] if run.stats else None,
                     'validation': check.get('status'), 'termination': (run.execution or {}).get('termination'),
                     'scope': record.get('geometry', 'ordinary rectangular FrozenLake port trial')})
    report = {'campaign': CAMPAIGN.campaign_id, 'version': CAMPAIGN.version,
              'profile': manifest['profile'], 'rows': rows, 'issues': issues,
              'errors': {str(k): v for k, v in errors.items()}, 'analysis_sha256': digest(Path(__file__)),
              'manifest_sha256': digest(dataset / 'manifest.json'),
              'limitations': ['Topological diagnostics are not geometric FrozenLake instances.',
                              'Single timing observations are not repeatable speedup estimates.']}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(rows, indent=2))
    if issues or errors:raise ValueError('Composition validation failed')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True);parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv);analyze(args.dataset, args.output)


if __name__ == '__main__':main()
