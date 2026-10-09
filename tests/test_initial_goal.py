"""An initially satisfied goal needs no action, independently of the backend."""
from itertools import product
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pyperplan.task import Operator, Task
from analysis.validate_policies import validate_policy
from planner.backends.downward import ROOT
from planner.search import boand_star


class InitialGoalTests(unittest.TestCase):
    def test_empty_policy_is_the_zero_cost_solution(self):
        backends = ['pyperplan']
        if (ROOT / 'outputs/fast-downward/build/search/_downward_native.so').is_file():
            backends.append('downward-strips')
        for backend, heuristic, metric, kind in product(backends, ('hmax', 'lmcut'),
                                                       ('b', 'w', 'bw', 'wb'),
                                                       ('no-actions', 'noop', 'delete-goal', 'empty-goal')):
            operators = [] if kind == 'no-actions' else [Operator('(act)', set(), set(),
                {'(g)'} if kind == 'delete-goal' else set())]
            task = Task(kind, {'(g)'}, frozenset({'(g)'}),
                        frozenset() if kind == 'empty-goal' else frozenset({'(g)'}), operators)
            oracle = validate_policy(task, {})
            self.assertEqual((oracle['best'], oracle['worst']), (0, 0))
            with self.subTest(backend=backend, heuristic=heuristic, metric=metric, kind=kind), tempfile.TemporaryDirectory() as tmp:
                with patch('planner.search.parse_domain'), patch('planner.search.parse_problem'), \
                        patch('planner.search.get_alloutcome_determinization', return_value=task):
                    policies = boand_star('d.pddl', 'p.pddl', tmp, backend=backend,
                        use_cp_heuristic=heuristic, use_metric=metric, use_selector='largestg')
                self.assertEqual(len(policies), 1)
                self.assertEqual(policies[0].strategy, {})
                self.assertEqual(Path(tmp, 'p.boand.001.out').read_text(), '')
                row = Path(tmp, 'p.stats').read_text().splitlines()[0].split(';')
                self.assertEqual(row[:3], ['0', '0', '0'])
                self.assertEqual(row[5:7], ['0', '0'])
                self.assertEqual(validate_policy(task, policies[0].strategy)['best'], 0)
