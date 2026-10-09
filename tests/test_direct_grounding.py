"""Negative compilation checked against independent signed-state transitions."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import random
import tempfile
import unittest

from planner.backends.grounding import ground_compiled_pddl
from planner.backends.downward import FactStateTask, ROOT


@unittest.skipUnless((ROOT/'outputs/fast-downward/build/search/_downward_native.so').is_file(), 'Optional FD dependency')
class DirectTests(unittest.TestCase):
    def test_signed_transitions_and_complement_invariant(self):
        rng = random.Random(26063)
        with tempfile.TemporaryDirectory() as tmp:
            domain, problem = Path(tmp,'d.pddl'), Path(tmp,'p.pddl')
            for case in range(100):
                facts = ('x','y','g')
                sample = lambda: {f for f in facts if rng.random()<.35}
                initial = sample(); goals = sample(); neg_goals = sample()-goals
                ops = [(sample(),sample(),sample(),sample()) for _ in range(5)]
                ops = [(pre,neg-pre,add,delete) for pre,neg,add,delete in ops]
                def conjunction(pos,neg=()):
                    return '(and '+ ' '.join([*(f'({f})' for f in sorted(pos)),*(f'(not ({f}))' for f in sorted(neg))])+')'
                actions = ' '.join(f'(:action a{i} :parameters () :precondition {conjunction(pre,neg)} :effect {conjunction(add,delete)})' for i,(pre,neg,add,delete) in enumerate(ops))
                domain.write_text('(define (domain t) (:requirements :strips :negative-preconditions) (:predicates (x) (y) (g)) '+actions+')')
                problem.write_text('(define (problem t) (:domain t) (:init '+' '.join(f'({f})' for f in sorted(initial))+') (:goal '+conjunction(goals,neg_goals)+'))')
                with redirect_stdout(StringIO()):
                    grounded=ground_compiled_pddl(domain,problem,direct=True)
                for heuristic in ('hmax','lmcut'):
                    native=FactStateTask(grounded,heuristic); pending=[native.initial_state];seen=set()
                    while pending:
                        state=pending.pop()
                        if state in seen:continue
                        seen.add(state)
                        fixed={f for f in initial if f'({f})' not in grounded.facts}
                        positive={f for f in facts if f'({f})' in state}|fixed
                        self.assertEqual(native.goal_reached(state),goals<=positive and not neg_goals&positive)
                        for f in facts:
                            if f'(not_{f})' in grounded.facts:
                                self.assertEqual(f'(not_{f})' in state,f not in positive)
                        expected={(f'(a{i})',frozenset((positive-delete)|add)) for i,(pre,neg,add,delete) in enumerate(ops) if pre<=positive and not neg&positive}
                        actual=native.get_successor_states(state)
                        self.assertEqual({(op.name,frozenset({f for f in facts if f'({f})' in child}|fixed)) for op,child in actual},expected,(case,heuristic,state))
                        pending.extend(child for _,child in actual)

    def test_aliased_parameter_effects_use_add_wins_before_complementing(self):
        with tempfile.TemporaryDirectory() as tmp:
            d,p=Path(tmp,'d.pddl'),Path(tmp,'p.pddl')
            d.write_text('''(define (domain t) (:requirements :typing :negative-preconditions)
              (:types item) (:predicates (f ?x - item) (g))
              (:action write :parameters (?x ?y - item) :precondition (and)
               :effect (and (f ?x) (not (f ?y))))
              (:action check :parameters (?x - item) :precondition (not (f ?x)) :effect (g)))''')
            p.write_text('(define (problem t) (:domain t) (:objects a - item) (:init) (:goal (g)))')
            with redirect_stdout(StringIO()):task=ground_compiled_pddl(d,p,direct=True)
            child=next(child for op,child in task.get_successor_states(task.initial_state) if op.name=='(write a a)')
            self.assertIn('(f a)',child);self.assertNotIn('(not_f a)',child)
            self.assertNotIn('(check a)',{op.name for op,_ in task.get_successor_states(child)})

    def test_negative_fond_fronts_against_exhaustive_policy_oracle(self):
        from itertools import product
        from unittest.mock import patch
        from pyperplan.task import Task, Operator
        from analysis.validate_policies import validate_policy
        from planner.search import boand_star, grouped_successors
        from tests.test_downward_backend import reachable_graph
        rng = random.Random(26064)
        with tempfile.TemporaryDirectory() as tmp:
            d,p=Path(tmp,'d.pddl'),Path(tmp,'p.pddl')
            for case in range(30):
                facts=('x','g'); operators=[]; clauses=[]
                initial={f for f in ('x',) if rng.random()<.3}
                encoded_initial=frozenset(f'({f})' if f in initial else f'(not_{f})' for f in facts)
                for action in range(2):
                    pre={f for f in facts if rng.random()<.25}
                    neg={f for f in facts if rng.random()<.35}-pre
                    for outcome in (1,2):
                        add={f for f in facts if rng.random()<.4}
                        delete={f for f in facts if rng.random()<.4}-add
                        name=f'a{action}_detdup_{outcome}'
                        operators.append(Operator(f'({name})',
                            {f'({f})' for f in pre}|{f'(not_{f})' for f in neg},
                            {f'({f})' for f in add}|{f'(not_{f})' for f in delete},
                            {f'({f})' for f in delete}|{f'(not_{f})' for f in add}))
                        condition=' '.join([*(f'({f})' for f in sorted(pre)),*(f'(not ({f}))' for f in sorted(neg))])
                        effects=' '.join([*(f'({f})' for f in sorted(add)),*(f'(not ({f}))' for f in sorted(delete))])
                        clauses.append(f'(:action {name} :parameters () :precondition (and {condition}) :effect (and {effects}))')
                d.write_text('(define (domain t) (:requirements :strips :negative-preconditions) (:predicates (x) (g)) '+' '.join(clauses)+')')
                p.write_text('(define (problem t) (:domain t) (:init '+' '.join(f'({f})' for f in sorted(initial))+') (:goal (g)))')
                with redirect_stdout(StringIO()):grounded=ground_compiled_pddl(d,p,direct=True)
                reference=Task('oracle',{f'({f})' for f in facts}|{f'(not_{f})' for f in facts},encoded_initial,frozenset({'(g)'}),operators)
                states=[s for s in reachable_graph(reference) if not reference.goal_reached(s)]
                costs=set()
                for assignments in product(*[[None,*grouped_successors(reference,s)[0]] for s in states]):
                    try:result=validate_policy(reference,{s:a for s,a in zip(states,assignments) if a is not None})
                    except ValueError:continue
                    costs.add((result['best'],result['worst']))
                expected={c for c in costs if not any(other!=c and other[0]<=c[0] and other[1]<=c[1] for other in costs)}
                for heuristic in ('hmax','lmcut'):
                    with patch('planner.search.parse_domain'),patch('planner.search.parse_problem'),patch('planner.backends.grounding.get_direct_determinization',return_value=grounded):
                        boand_star('d.pddl','p.pddl',tmp,backend='downward-direct',use_cp_heuristic=heuristic,use_selector='largestg')
                    rows=Path(tmp,'p.stats').read_text().splitlines()
                    self.assertEqual({(float(row.split(';')[0]),float(row.split(';')[1])) for row in rows if not row.startswith('-1;')},expected,(case,heuristic))
