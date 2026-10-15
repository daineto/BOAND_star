"""Serial trade-off gadgets and a diagnostic encoding in FrozenLake relations.

The topology encoding is deliberately NOT a rectangular FrozenLake map.
It retains the domain actions but uses non-geometric directional relations.
"""
import argparse
import hashlib
import json
from pathlib import Path

from .frozenlake import DOMAIN, render as render_grid
from .frozenlake_recovery import grid as recovery_grid


def expected_front(stages, gap=1):
    if stages < 1 or gap < 1:
        raise ValueError('Stages and gap must be positive')
    return [(4 * stages - 1 + 2 * gap * j,
             (4 + 6 * gap) * stages - 1 - 2 * gap * j) for j in range(stages + 1)]


def topology(stages, gap=1):
    front = expected_front(stages, gap)
    objects, relations, actions = {}, [], {}

    def ice(name):
        objects[name] = 'ice'
        actions.setdefault(name, [])
        return name

    def forced(source, target, axis):
        wall = f'wall_{axis}_{target}'
        objects[wall] = 'wall'
        predicate, action = ('left-of', 'right-to-wall') if axis == 'h' else ('down-of', 'up-to-wall')
        for relation in [(predicate, source, target), (predicate, target, wall)]:
            if relation not in relations:
                relations.append(relation)
        actions[source].append({'action': f'{action} {source} {target} {wall}', 'outcomes': [target]})

    entries = [ice(f'stage_{i}_entry') for i in range(stages)]
    exits = [ice(f'stage_{i}_exit') for i in range(stages)]
    for stage in range(stages):
        root, exit = entries[stage], exits[stage]
        for mode, best, worst in [('fast', 3, 3 + 6 * gap), ('safe', 3 + 2 * gap, 3 + 4 * gap)]:
            near = ice(f's{stage}_{mode}_near')
            far = ice(f's{stage}_{mode}_far')
            relations.extend([('left-of', root, near), ('left-of', near, far)])
            actions[root].append({'action': f'right {root} {near} {far}', 'outcomes': [near, far]})
            # This reverse action is genuinely admitted by the unchanged domain.
            # If selected on a reachable far outcome it creates a cycle through
            # the fixed root decision; its best cost cannot beat the near path.
            actions[far].append({'action': f'left {far} {near} {root}', 'outcomes': [near, root]})
            for branch, first, length in [('short', near, best - 1), ('long', far, worst - 1)]:
                path = [first] + [ice(f's{stage}_{mode}_{branch}_{j}') for j in range(length - 1)] + [exit]
                for j, (source, target) in enumerate(zip(path, path[1:])):
                    forced(source, target, 'v' if j % 2 == 0 else 'h')
        if stage + 1 < stages:
            forced(exit, entries[stage + 1], 'v')
    return {'instance': f'serial-k{stages:02d}-g{gap}', 'family': 'serial-topology',
            'stages': stages, 'gap': gap, 'initial': entries[0], 'goal': exits[-1],
            'objects': objects, 'relations': relations, 'actions': actions,
            'front': [list(p) for p in front], 'reference': 'analytic composition; independently enumerated small cases',
            'geometry': 'non-geometric diagnostic topology; not a rectangular lake'}


def render_topology(record):
    objects = '\n'.join(f'  {name} - {kind}' for name, kind in record['objects'].items())
    facts = '\n'.join(f'  ({predicate} {left} {right})' for predicate, left, right in record['relations'])
    return (f'(define (problem {record["instance"]}) (:domain icylake)\n'
            f'(:objects\n{objects}\n)\n(:init (at {record["initial"]})\n{facts}\n)\n'
            f'(:goal (at {record["goal"]}))\n)\n')


def geometric_attempt(stages):
    """Two bounded physical-port trials; no analytic front is assumed."""
    if stages not in (1, 2):
        raise ValueError('Only the declared one/two-room port trials are defined')
    room = recovery_grid(5, 'pit')
    cells = {(x, y): kind for x, y, kind in room['cells']}
    placed = {(x + 6, y): kind for (x, y), kind in cells.items()}
    if stages == 2:
        placed.update(cells)
    corridor = {(x, -1) for x in range(-2, 6)} | {(5, 0), (5, 1)} | {(-2, y) for y in range(3)} | {(-1, 2)}
    for point in corridor:
        if placed.get(point, 'wall') != 'wall':
            raise ValueError('Connector overwrites a room tile')
        placed[point] = 'ice'
    # Translate into the ordinary rectangular-grid renderer's coordinates.
    width, height = 11, 6
    shifted = {(x + 2, y + 1): kind for (x, y), kind in placed.items()}
    return {'instance': f'physical-port-{stages}', 'family': 'physical-port-attempt',
            'stages': stages, 'width': width, 'height': height,
            'start': [8, 3], 'goal': [1, 3] if stages == 1 else [2, 2],
            'cells': [[x, y, shifted.get((x, y), 'wall')] for x in range(width) for y in range(height)],
            'reference': 'unknown; diagnostic port attachment, no additivity assumed'}


def generate(output):
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite {output}')
    output.mkdir(parents=True)
    records = [topology(k) for k in range(1, 5)] + [topology(2, 2)]
    records += [geometric_attempt(k) for k in (1, 2)]
    for folder in ('serial-topology', 'physical-ports'):
        (output / folder).mkdir()
        (output / folder / 'domain.pddl').write_bytes(DOMAIN.read_bytes())
    for record in records:
        abstract = record['family'] == 'serial-topology'
        text = render_topology(record) if abstract else render_grid(record)
        record['pddl_sha256'] = hashlib.sha256(text.encode()).hexdigest()
        folder = 'serial-topology' if abstract else 'physical-ports'
        (output / folder / f'{record["instance"]}.pddl').write_text(text)
    metadata = {'schema_version': 1, 'generator_version': 1,
                'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'domain_sha256': hashlib.sha256(DOMAIN.read_bytes()).hexdigest(),
                'scope': 'Composition proof diagnostics, distinct from geometric FrozenLake benchmarks.',
                'instances': records}
    (output / 'generation.json').write_text(json.dumps(metadata, indent=2) + '\n')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(f'Generated {len(generate(args.output)["instances"])} diagnostics')


if __name__ == '__main__':
    main()
