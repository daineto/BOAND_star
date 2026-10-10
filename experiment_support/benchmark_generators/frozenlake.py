"""Version-1 FrozenLake pilot generation; original domain semantics unchanged."""
import argparse
import hashlib
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[2]
DOMAIN = ROOT / 'benchmarks/icaps2025/frozenlake/domain.pddl'
EXAMPLES = ROOT / 'campaigns/journal_development/examples/frozenlake/grids.json'


def label(point):
    return 'tile_' + '_'.join(str(v) if v >= 0 else f'm{-v}' for v in point)


def render(record):
    width, height = record['width'], record['height']
    cells = {(x, y): kind for x, y, kind in record['cells']}
    assert len(cells) == width * height
    assert cells[tuple(record['start'])] == cells[tuple(record['goal'])] == 'ice'
    for x in range(width):
        cells[x, -1] = cells[x, height] = 'wall'
    for y in range(height):
        cells[-1, y] = cells[width, y] = 'wall'
    objects = '\n'.join(f'  {label(s)} - {kind}' for s, kind in sorted(cells.items()))
    facts = [f'  (at {label(record["start"])})']
    facts += [f'  (left-of {label((x, y))} {label((x + 1, y))})'
              for y in range(height) for x in range(-1, width)]
    facts += [f'  (down-of {label((x, y))} {label((x, y + 1))})'
              for x in range(width) for y in range(-1, height)]
    return (f'(define (problem {record["instance"]}) (:domain icylake)\n'
            f'(:objects\n{objects}\n)\n(:init\n' + '\n'.join(facts)
            + f'\n)\n(:goal (at {label(record["goal"])}))\n)\n')


def grid(family, width, height, seed=0):
    cells = {(x, y): 'ice' for x in range(width) for y in range(height)}
    start, goal = (0, 0), (width - 1, height - 1)
    if family == 'corner':
        cells[0, 0] = 'wall'
        start, goal = (width - 1, height - 1), (width - 2, height - 1)
    elif family == 'staggered':
        for y in range(2, height - 1, 3):
            cells[1 if (y // 3) % 2 == 0 else width - 2, y] = 'wall'
    elif family == 'random':
        rng = random.Random(seed)
        cells = {s: rng.choices(['ice', 'wall', 'pit'], [.78, .18, .04])[0] for s in cells}
        cells[start] = cells[goal] = 'ice'
    elif family == 'barrier':
        for x in range(width):
            cells[x, height // 2] = 'pit'
    elif family != 'open':
        raise ValueError(f'Unknown family: {family}')
    return {'instance': f'{family}-{width}x{height}-s{seed}', 'family': family,
            'width': width, 'height': height, 'seed': seed,
            'start': list(start), 'goal': list(goal),
            'cells': [[x, y, kind] for (x, y), kind in cells.items()]}


def pilot():
    records = []
    for number, original in enumerate(json.loads(EXAMPLES.read_text())['instances'], 1):
        records.append({**original, 'instance': f'verified-{number:02d}',
                        'family': 'verified', 'seed': 0, 'source': str(EXAMPLES.relative_to(ROOT))})
    # Dimensions/seeds fixed before timing; retain failures and singleton controls.
    records += [grid('corner', 3, h) for h in (4, 5, 6, 8, 10)]
    records += [grid('staggered', 4, h) for h in (6, 8, 10)]
    records += [grid('random', w, h, seed) for w, h in ((4, 5), (5, 6)) for seed in range(3)]
    records += [grid('open', 3, 3), grid('barrier', 5, 5)]
    return records


def generate(output):
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite generated collection: {output}')
    output.mkdir(parents=True)
    (output / 'domain.pddl').write_bytes(DOMAIN.read_bytes())
    records = pilot()
    for record in records:
        record['pddl_sha256'] = hashlib.sha256(render(record).encode()).hexdigest()
        (output / f'{record["instance"]}.pddl').write_text(render(record))
    metadata = {'schema_version': 1, 'generator_version': 1,
                'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'domain_sha256': hashlib.sha256(DOMAIN.read_bytes()).hexdigest(),
                'examples_sha256': hashlib.sha256(EXAMPLES.read_bytes()).hexdigest(),
                'selection': 'Predeclared pilot candidates; final benchmark selection pending review.',
                'instances': records}
    (output / 'generation.json').write_text(json.dumps(metadata, indent=2) + '\n')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(f'Generated {len(generate(args.output)["instances"])} candidates in {args.output}')


if __name__ == '__main__':
    main()
