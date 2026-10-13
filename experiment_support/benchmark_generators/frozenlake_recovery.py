"""Version-1 recovery-route family; preserves the original FrozenLake domain."""
import argparse
import hashlib
import json
from pathlib import Path

from .frozenlake import DOMAIN, render


def grid(height=5, tail='cyclic'):
    if height < 5 or tail not in ('cyclic', 'pit'):
        raise ValueError('Height must be >= 5; tail must be cyclic or pit')
    cells = {(x, y): 'wall' for x in range(3) for y in range(height)}
    for x in range(3):
        for y in range(2, height):
            cells[x, y] = 'ice'
    cells[2, height - 1] = 'wall'
    cells[0, 0] = 'ice' if tail == 'cyclic' else 'pit'
    cells[0, 1] = cells[1, 1] = 'ice'
    record = {'instance': f'recovery-3x{height}-{tail}', 'family': 'recovery-routes',
              'width': 3, 'height': height, 'tail': tail,
              'start': [0, 2], 'goal': [0, 1],
              'cells': [[x, y, kind] for (x, y), kind in cells.items()],
              'reference_status': 'pending'}
    if height == 5:
        record['front'] = ([[1, 999999], [3, 9], [5, 7]] if tail == 'cyclic'
                           else [[2, 999999], [3, 9], [5, 7]])
        record['reference_status'] = 'independent-exact; planner-validation-pending'
        record['policy_assignments'] = 4608 if tail == 'cyclic' else 3072
    return record


def candidates():
    return [grid(height, tail) for height in (5, 6, 7, 8, 10)
            for tail in ('cyclic', 'pit')]


def generate(output):
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite collection: {output}')
    output.mkdir(parents=True)
    (output / 'domain.pddl').write_bytes(DOMAIN.read_bytes())
    records = candidates()
    for record in records:
        text = render(record)
        record['pddl_sha256'] = hashlib.sha256(text.encode()).hexdigest()
        (output / f'{record["instance"]}.pddl').write_text(text)
    metadata = {'schema_version': 1, 'generator_version': 1,
                'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'renderer_sha256': hashlib.sha256(Path(__file__).with_name('frozenlake.py').read_bytes()).hexdigest(),
                'domain_sha256': hashlib.sha256(DOMAIN.read_bytes()).hexdigest(),
                'selection': 'Predeclared recovery-route follow-up; no planner runs yet.',
                'instances': records}
    (output / 'generation.json').write_text(json.dumps(metadata, indent=2) + '\n')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(f'Generated {len(generate(args.output)["instances"])} inputs in {args.output}')


if __name__ == '__main__':
    main()
