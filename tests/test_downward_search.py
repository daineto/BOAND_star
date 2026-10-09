"""Exhaustive tiny-policy oracle for backend and heuristic integration."""
from itertools import product
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from pyperplan.task import Task, Operator
from planner.backends.downward import ROOT
from planner.search import boand_star, grouped_successors
from analysis.validate_policies import validate_policy
from tests.test_downward_backend import reachable_graph


@unittest.skipUnless((ROOT / 'outputs/fast-downward/build/search/_downward_native.so').is_file(),
                     'Build the optional pinned native backend to run integration checks')
class NativeSearchTests(unittest.TestCase):
    def test_tiny_fond_pareto_fronts_against_all_policies(self):
        rng = random.Random(26060)
        for case in range(60):
            facts = {'x', 'goal'}
            sample = lambda: {f for f in sorted(facts) if rng.random() < .4}
            operators = [Operator(f'(a{action}_detdup_{outcome})',
                                 {'x'} if action == 0 and case % 3 == 0 else set(), sample(), sample())
                         for action in range(2) for outcome in range(2)]
            task = Task(str(case), facts, frozenset(), frozenset({'goal'}), operators)
            states = [state for state in reachable_graph(task) if not task.goal_reached(state)]
            options = [[None, *grouped_successors(task, state)[0]] for state in states]
            costs = set()
            for assignments in product(*options):
                strategy = {state: action for state, action in zip(states, assignments) if action is not None}
                try:
                    result = validate_policy(task, strategy)
                except ValueError:
                    continue
                costs.add((result['best'], result['worst']))
            expected = {cost for cost in costs if not any(other != cost and other[0] <= cost[0]
                        and other[1] <= cost[1] for other in costs)}
            for backend, heuristic in product(('pyperplan', 'downward-strips'), ('hmax', 'lmcut')):
                with self.subTest(case=case, backend=backend, heuristic=heuristic), tempfile.TemporaryDirectory() as tmp:
                    with patch('planner.search.parse_domain'), patch('planner.search.parse_problem'), \
                            patch('planner.search.get_alloutcome_determinization', return_value=task):
                        boand_star('domain.pddl', 'problem.pddl', tmp, use_selector='largestg',
                                   backend=backend, use_cp_heuristic=heuristic)
                    rows = Path(tmp, 'problem.stats').read_text().splitlines()
                    actual = {(float(row.split(';')[0]), float(row.split(';')[1])) for row in rows
                              if not row.startswith('-1;')}
                    self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
