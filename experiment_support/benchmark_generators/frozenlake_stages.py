"""Physical rectangular FrozenLake stages: staircase versus slipping detour."""
import argparse
import hashlib
import json
from pathlib import Path

from .frozenlake import DOMAIN, render


def grid(stages):
    if not isinstance(stages, int) or isinstance(stages, bool) or stages < 1:
        raise ValueError('Stages must be a positive integer')
    ice, starts, ends = set(), [], []

    def line(source, target):
        dx = (target[0] > source[0]) - (target[0] < source[0])
        dy = (target[1] > source[1]) - (target[1] < source[1])
        if dx and dy:
            raise ValueError('Only axis-aligned corridors are allowed')
        ice.add(source)
        while source != target:
            source = source[0] + dx, source[1] + dy
            ice.add(source)

    for stage in range(stages):
        x, y = 16 * stage, 6 * stage
        starts.append((x, y))
        ends.append((x + 6, y + 6))
        # Six up/right turns: twelve deterministic steps when used in isolation.
        source = (x, y)
        for step in range(6):
            bend = x + step, y + step + 1
            line(source, bend)
            source = x + step + 1, y + step + 1
            line(bend, source)
        # A twenty-edge detour with four straight runs (2, 8, 8, 2).
        path = [(x, y), (x - 2, y), (x - 2, y + 8),
                (x + 6, y + 8), (x + 6, y + 6)]
        for source, target in zip(path, path[1:]):
            line(source, target)
        if stage:
            previous, entry = ends[stage - 1], starts[stage]
            # Four runs (2, 2, 8, 2) separate neighboring rooms. Boundary
            # overshoots are real domain outcomes and must be checked by oracle.
            path = [previous, (previous[0] + 2, previous[1]),
                    (previous[0] + 2, previous[1] - 2),
                    (entry[0], entry[1] - 2), entry]
            for source, target in zip(path, path[1:]):
                line(source, target)
    min_x = min(x for x, y in ice) - 1
    min_y = min(y for x, y in ice) - 1
    ice = {(x - min_x, y - min_y) for x, y in ice}
    width = max(x for x, y in ice) + 2
    height = max(y for x, y in ice) + 2
    return {'instance': f'staircase-k{stages:02d}', 'family': 'physical-staircase-stages',
            'stages': stages, 'width': width, 'height': height,
            'start': [starts[0][0] - min_x, starts[0][1] - min_y],
            'goal': [ends[-1][0] - min_x, ends[-1][1] - min_y],
            'stage_entries': [[x - min_x, y - min_y] for x, y in starts],
            'stage_exits': [[x - min_x, y - min_y] for x, y in ends],
            'cells': [[x, y, 'ice' if (x, y) in ice else 'wall']
                      for x in range(width) for y in range(height)],
            'scope': 'ordinary rectangular FrozenLake; original domain unchanged'}


def grid_actions(record):
    """Independent geometric movement model; compare with parsed original PDDL."""
    ice = {(x, y) for x, y, kind in record['cells'] if kind == 'ice'}
    actions = {}
    for source in sorted(ice):
        choices = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            near = source[0] + dx, source[1] + dy
            far = source[0] + 2 * dx, source[1] + 2 * dy
            if near in ice:
                choices.append((near, far) if far in ice else (near,))
        actions[source] = choices
    return actions


def generate(output):
    from analysis.reachable_policy_oracle import exact_front
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite {output}')
    output.mkdir(parents=True)
    (output / 'domain.pddl').write_bytes(DOMAIN.read_bytes())
    records = []
    for stages in (1, 2, 3):
        record = grid(stages)
        result = exact_front(grid_actions(record), tuple(record['start']), tuple(record['goal']))
        record['front'] = result['front']
        record['reference'] = 'complete independent reachable-policy oracle, including cyclic proper bound'
        record['oracle'] = {k: v for k, v in result.items() if k not in ('front', 'seconds')}
        text = render(record)
        record['pddl_sha256'] = hashlib.sha256(text.encode()).hexdigest()
        (output / f'{record["instance"]}.pddl').write_text(text)
        records.append(record)
    metadata = {'schema_version': 1, 'generator_version': 1,
                'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'renderer_sha256': hashlib.sha256(Path(__file__).with_name('frozenlake.py').read_bytes()).hexdigest(),
                'oracle_sha256': hashlib.sha256(Path(__file__).resolve().parents[2].joinpath('analysis/reachable_policy_oracle.py').read_bytes()).hexdigest(),
                'domain_sha256': hashlib.sha256(DOMAIN.read_bytes()).hexdigest(),
                'scope': 'Bounded physical composition checks; not a finalized benchmark selection.',
                'instances': records}
    (output / 'generation.json').write_text(json.dumps(metadata, indent=2, allow_nan=False) + '\n')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(f'Generated {len(generate(args.output)["instances"])} physical stage checks')


if __name__ == '__main__':
    main()
