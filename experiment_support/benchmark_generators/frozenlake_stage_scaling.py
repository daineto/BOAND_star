"""Fixed follow-up: vary physical stage count and room size separately."""
import argparse
import hashlib
import json
from pathlib import Path

from .frozenlake import DOMAIN, render
from .frozenlake_stages import grid, grid_actions
from analysis.reachable_policy_oracle import exact_front

CASES = ((4, 6), (6, 6), (8, 6), (4, 10))


def predicted_front(stages, size=6):
    # Validate the same parameter domain as the physical construction.
    if (not isinstance(stages, int) or isinstance(stages, bool) or stages < 1
            or not isinstance(size, int) or isinstance(size, bool) or size < 6 or size % 2):
        raise ValueError('Positive stage count and even size >= 6 required')
    return [((size + 11) * stages - 7 + (size - 4) * j,
             (2 * size + 22) * stages - 14 - 8 * j) for j in range(stages + 1)]


def generate(output):
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite {output}')
    output.mkdir(parents=True)
    (output / 'domain.pddl').write_bytes(DOMAIN.read_bytes())
    records = []
    for stages, size in CASES:
        record = {**grid(stages, size), 'size': size}
        result = exact_front(grid_actions(record), tuple(record['start']), tuple(record['goal']))
        if result['front'] != predicted_front(stages, size):
            raise ValueError('Independent oracle disagrees with composition theorem')
        record['front'] = result['front']
        record['oracle'] = {k: v for k, v in result.items() if k not in ('front', 'seconds')}
        record['reference'] = 'complete independent policy enumeration plus composition theorem'
        text = render(record)
        record['pddl_sha256'] = hashlib.sha256(text.encode()).hexdigest()
        (output / (record['instance'] + '.pddl')).write_text(text)
        records.append(record)
    base = Path(__file__).resolve().parents[2]
    sources = [Path(__file__), Path(__file__).with_name('frozenlake_stages.py'),
               Path(__file__).with_name('frozenlake.py'), base / 'analysis/reachable_policy_oracle.py']
    metadata = {'schema_version': 1, 'generator_version': 1,
                'sources': {str(p.relative_to(base)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                'domain_sha256': hashlib.sha256(DOMAIN.read_bytes()).hexdigest(),
                'scope': 'Four fixed geometric scaling probes; not a full campaign or final suite.',
                'instances': records}
    (output / 'generation.json').write_text(json.dumps(metadata, indent=2, allow_nan=False) + '\n')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(f'Generated {len(generate(args.output)["instances"])} fixed scaling probes')


if __name__ == '__main__':
    main()
