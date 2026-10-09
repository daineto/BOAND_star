"""Grounding preservation against independent explicit tiny transition graphs."""
from contextlib import redirect_stdout
from io import StringIO
from itertools import product
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from pyperplan.task import Task, Operator
from analysis.validate_policies import validate_policy
from planner.backends.downward import FactStateTask, ROOT
from planner.backends.grounding import ground_compiled_pddl
from planner.search import boand_star, grouped_successors
from tests.test_downward_backend import reachable_graph, exact_distances


def pddl_task(task, directory):
    def conjunction(facts):
        return '(and ' + ' '.join(sorted(facts)) + ')'
    actions = []
    for op in task.operators:
        effects = [*op.add_effects, *(f'(not {f})' for f in op.del_effects)]
        actions.append(f'(:action {op.name[1:-1]} :parameters () '
                       f':precondition {conjunction(op.preconditions)} '
                       f':effect {conjunction(effects)})')
    domain = Path(directory, 'domain.pddl')
    problem = Path(directory, 'problem.pddl')
    domain.write_text('(define (domain tiny) (:requirements :strips) (:predicates '
                      + ' '.join(sorted(task.facts)) + ') ' + ' '.join(actions) + ')')
    problem.write_text('(define (problem tiny) (:domain tiny) (:init '
                       + ' '.join(sorted(task.initial_state)) + ') (:goal '
                       + conjunction(task.goals) + '))')
    return domain, problem


@unittest.skipUnless((ROOT / 'outputs/fast-downward/build/search/_downward_native.so').is_file(),
                     'Build the optional pinned native dependency')
class GroundingTests(unittest.TestCase):
    def translate(self, task, tmp):
        with redirect_stdout(StringIO()):
            return ground_compiled_pddl(*pddl_task(task, tmp))

    def compare(self, task, grounded):
        graph = reachable_graph(task)
        exact = exact_distances(task, graph)
        for heuristic in ('hmax', 'lmcut'):
            native = FactStateTask(grounded, heuristic)
            for state, transitions in graph.items():
                projected = state & grounded.facts
                self.assertEqual(grounded.goal_reached(projected), task.goal_reached(state))
                expected = {(op.name, child & grounded.facts) for op, child in transitions}
                self.assertEqual({(op.name, child) for op, child in grounded.get_successor_states(projected)}, expected)
            # Visit through the native registry before evaluating identifiers.
            native_graph = reachable_graph(native)
            self.assertEqual(set(native_graph), {s & grounded.facts for s in graph})
            for state in graph:
                projected = state & grounded.facts
                self.assertEqual(native.goal_reached(projected), task.goal_reached(state))
                self.assertEqual({(op.name, child) for op, child in native_graph[projected]},
                                 {(op.name, child & grounded.facts) for op, child in graph[state]})
                self.assertLessEqual(native.evaluate(projected), exact.get(state, float('inf')))

    def test_random_explicit_transition_graphs_and_admissibility(self):
        rng = random.Random(26061)
        with tempfile.TemporaryDirectory() as tmp:
            for case in range(80):
                facts = tuple(f'(f{i})' for i in range(rng.randint(1, 4)))
                sample = lambda: {f for f in facts if rng.random() < .35}
                operators = [Operator(f'(a{i})', sample(), sample(), sample()) for i in range(5)]
                task = Task(str(case), set(facts), frozenset(sample()), frozenset(sample()), operators)
                with self.subTest(case=case):
                    self.compare(task, self.translate(task, tmp))

    def test_noop_outcome_and_unreachable_goal_do_not_replace_graph(self):
        task = Task('static-goal', {'(g)', '(x)'}, frozenset(), frozenset({'(g)'}),
                    [Operator('(a_detdup_1)', set(), {'(x)'}, set()),
                     Operator('(a_detdup_2)', set(), set(), set())])
        with tempfile.TemporaryDirectory() as tmp:
            grounded = self.translate(task, tmp)
            self.assertEqual(len(grounded.operators), 2)
            self.assertEqual(grounded.goals, {'(g)'})
            self.compare(task, grounded)

    def test_typed_parameters_static_preconditions_and_repeated_arguments(self):
        domain = '''(define (domain typed) (:requirements :strips :typing)
          (:types location) (:predicates (at ?x - location) (edge ?x ?y - location))
          (:action move :parameters (?x ?y - location)
            :precondition (and (at ?x) (edge ?x ?y))
            :effect (and (not (at ?x)) (at ?y)))
          (:action wait :parameters (?x - location)
            :precondition (at ?x) :effect (and)))'''
        problem = '''(define (problem typed) (:domain typed) (:objects a b - location)
          (:init (at a) (edge a b) (edge b a) (edge a a)) (:goal (at b)))'''
        with tempfile.TemporaryDirectory() as tmp:
            d, p = Path(tmp, 'domain.pddl'), Path(tmp, 'problem.pddl')
            d.write_text(domain); p.write_text(problem)
            with redirect_stdout(StringIO()):
                grounded = ground_compiled_pddl(d, p)
            task = Task('typed', {'(at a)', '(at b)'}, frozenset({'(at a)'}), frozenset({'(at b)'}),
                        [Operator(f'(move {x} {y})', {f'(at {x})'}, {f'(at {y})'}, {f'(at {x})'})
                         for x, y in [('a', 'b'), ('b', 'a'), ('a', 'a')]] +
                        [Operator(f'(wait {x})', {f'(at {x})'}, set(), set()) for x in ('a', 'b')])
            self.compare(task, grounded)

    def test_fond_pareto_fronts_against_exhaustive_policy_oracle(self):
        rng = random.Random(26062)
        with tempfile.TemporaryDirectory() as tmp:
            for case in range(30):
                facts = ('(x)', '(g)')
                sample = lambda: {f for f in facts if rng.random() < .4}
                ops = [Operator(f'(a{a}_detdup_{o})', {'(x)'} if a == 0 and case % 3 == 0 else set(),
                                sample(), sample()) for a in range(2) for o in (1, 2)]
                task = Task(str(case), set(facts), frozenset(), frozenset({'(g)'}), ops)
                grounded = self.translate(task, tmp)
                states = [s for s in reachable_graph(task) if not task.goal_reached(s)]
                costs = set()
                for choices in product(*[[None, *grouped_successors(task, s)[0]] for s in states]):
                    policy = {s: a for s, a in zip(states, choices) if a is not None}
                    try:
                        result = validate_policy(task, policy)
                    except ValueError:
                        continue
                    costs.add((result['best'], result['worst']))
                expected = {c for c in costs if not any(d != c and d[0] <= c[0] and d[1] <= c[1]
                                                      for d in costs)}
                for heuristic in ('hmax', 'lmcut'):
                    with self.subTest(case=case, heuristic=heuristic), \
                            patch('planner.search.parse_domain'), patch('planner.search.parse_problem'), \
                            patch('planner.backends.grounding.get_downward_determinization', return_value=grounded):
                        boand_star('domain.pddl', 'problem.pddl', tmp, use_selector='largestg',
                                   backend='downward-grounded', use_cp_heuristic=heuristic)
                        rows = Path(tmp, 'problem.stats').read_text().splitlines()
                        self.assertEqual({(float(r.split(';')[0]), float(r.split(';')[1]))
                                          for r in rows if not r.startswith('-1;')}, expected)

    def test_conditional_effects_and_negative_preconditions_fail_explicitly(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, p = Path(tmp, 'domain.pddl'), Path(tmp, 'problem.pddl')
            p.write_text('(define (problem t) (:domain t) (:init) (:goal (g)))')
            for pre, effect in [('(not (x))', '(g)'), ('(and)', '(when (x) (g))')]:
                d.write_text('(define (domain t) (:requirements :adl) (:predicates (x) (g)) '
                             f'(:action a :parameters () :precondition {pre} :effect {effect}))')
                with self.assertRaises(ValueError):
                    ground_compiled_pddl(d, p)
