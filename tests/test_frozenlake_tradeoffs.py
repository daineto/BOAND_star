import json
import unittest
from pathlib import Path

from analysis.frozenlake_tradeoffs import evaluate, frontier
from analysis.prp_replay import OriginalTask, ground
from pddl import parse_domain, parse_problem


class FrozenLakeTradeoffTests(unittest.TestCase):
    def test_complete_example_fronts(self):
        path = Path(__file__).resolve().parents[1] / 'campaigns/journal_development/examples/frozenlake/grids.json'
        for item in json.loads(path.read_text())['instances']:
            cells = {(x, y): kind for x, y, kind in item['cells']}
            pairs, count = frontier(cells, tuple(item['start']), tuple(item['goal']))
            assert [list(pair) for pair in pairs] == item['front']
            assert count == item['policies_enumerated']


    def test_grid_movements_match_original_pddl(self):
        root = Path(__file__).resolve().parents[1]
        folder = root / 'campaigns/journal_development/examples/frozenlake'
        records = json.loads((folder / 'grids.json').read_text())['instances']
        for number, item in enumerate(records, 1):
            task = OriginalTask.__new__(OriginalTask)
            task.domain = parse_domain(str(root / 'benchmarks/icaps2025/frozenlake/domain.pddl'))
            task.problem = parse_problem(str(folder / f'tradeoff-{number:02d}.pddl'))
            task.actions = {action.name: action for action in task.domain.actions}
            task.static = frozenset(ground(fact, {}) for fact in task.problem.init if fact.name != 'at')
            cells = {(x, y): kind for x, y, kind in item['cells']}
            def label(point):
                return 'tile_' + '_'.join(str(v) if v >= 0 else f'm{-v}' for v in point)
            for source, kind in cells.items():
                if kind != 'ice':
                    continue
                state = frozenset({('at', (label(source),))})
                for direction, dx, dy in [('right', 1, 0), ('left', -1, 0), ('up', 0, 1), ('down', 0, -1)]:
                    near = (source[0] + dx, source[1] + dy)
                    far = (source[0] + 2 * dx, source[1] + 2 * dy)
                    if cells.get(near, 'wall') != 'ice':
                        continue
                    far_kind = cells.get(far, 'wall')
                    name = direction if far_kind == 'ice' else f'{direction}-to-{far_kind}'
                    action, binding = task.bound_action(' '.join([name, label(source), label(near), label(far)]))
                    self.assertTrue(task.holds(action.precondition, state, binding))
                    actual = {(state - deletes) | adds for adds, deletes in task.effects(action.effect, state, binding)}
                    destinations = [near] if far_kind == 'wall' else [near, far]
                    expected = {frozenset({('at', (label(point),))}) for point in destinations}
                    self.assertEqual(actual, expected)

    def test_oracle_properness_and_costs(self):
        assert evaluate({0: (1, 2), 1: (2,)}, 0, 2) == (1, 2)
        assert evaluate({0: (0, 1)}, 0, 1) == (1, float('inf'))
        assert evaluate({0: (1, 2), 1: (1,)}, 0, 2) is None
        assert evaluate({}, 0, 0) == (0, 0)
