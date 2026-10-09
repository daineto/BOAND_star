"""Native transition equivalence and independent shortest-path admissibility."""
from collections import deque
import math
from pathlib import Path
import random
import tempfile
import unittest

from pyperplan.task import Task, Operator
from pyperplan.search.searchspace import SearchNode
from planner.backends.downward import DownwardTask, FactStateTask, boolean_sas, ROOT, native_provenance
from planner.relaxation import OperatorCostHMaxHeuristic
from planner.output import write_stats


def reachable_graph(task):
    graph = {}
    pending = deque([task.initial_state])
    while pending:
        state = pending.popleft()
        if state in graph:
            continue
        graph[state] = task.get_successor_states(state)
        pending.extend(child for _, child in graph[state] if child not in graph)
    return graph


def exact_distances(task, graph):
    reverse = {state: [] for state in graph}
    for state, edges in graph.items():
        for _, child in edges:
            reverse[child].append(state)
    distances = {state: 0 for state in graph if task.goal_reached(state)}
    pending = deque(distances)
    while pending:
        child = pending.popleft()
        for state in reverse[child]:
            if state not in distances:
                distances[state] = distances[child] + 1
                pending.append(state)
    return distances


class EncodingTests(unittest.TestCase):
    def test_integral_lmcut_costs_use_the_integer_statistics_format(self):
        stats = {"best": [128.0], "worst": [999999.0], "size": [2], "time": [.1],
                 "iterations": [3], "expansions": [2], "generations": [4], "max_open": [1]}
        with tempfile.TemporaryDirectory() as tmp:
            write_stats(stats, 'case', tmp)
            self.assertEqual(Path(tmp, 'case.stats').read_text(), '128;999999;2;0.1;3;2;4;1\n')

    def test_add_wins_and_noop_is_preserved(self):
        task = Task('overlap', {'a'}, frozenset({'a'}), frozenset({'a'}),
                    [Operator('both', {'a'}, {'a'}, {'a'}), Operator('noop', set(), set(), set())])
        sas, facts = boolean_sas(task)
        self.assertEqual(facts, ('a',))
        self.assertIn('both\n0\n1\n0 0 1 1\n', sas)
        self.assertIn('noop\n0\n1\n0 1 1 1\n', sas)


@unittest.skipUnless((ROOT / 'outputs/fast-downward/build/search/_downward_native.so').is_file(),
                     'Build the optional pinned native backend to run integration checks')
class NativeBackendTests(unittest.TestCase):
    def compare(self, task):
        graph = reachable_graph(task)
        exact = exact_distances(task, graph)
        native_hmax = DownwardTask(task, 'hmax')
        native_lmcut = DownwardTask(task, 'lmcut')
        reference = OperatorCostHMaxHeuristic(task)
        for native in (native_hmax, native_lmcut):
            pending = deque([0]); seen = set()
            while pending:
                identifier = pending.popleft()
                if identifier in seen:
                    continue
                seen.add(identifier)
                state = native.state_facts(identifier)
                self.assertIn(state, graph)
                self.assertEqual(native.goal_reached(identifier), task.goal_reached(state))
                transitions = native.get_successor_states(identifier)
                expected = [(op.name, child) for op, child in graph[state]]
                actual = [(op.name, native.state_facts(child)) for op, child in transitions]
                self.assertEqual(actual, expected)
                value = native.evaluate(identifier)
                self.assertLessEqual(value, exact.get(state, math.inf))
                if math.isinf(value):
                    self.assertNotIn(state, exact)
                if native.heuristic == 'hmax' and task.goals:
                    self.assertEqual(value, reference(SearchNode(state, None, None, 0)))
                for op, child in transitions:
                    self.assertEqual(op.apply(identifier), child)
                    pending.append(child)
            self.assertEqual(len(seen), len(graph))

    def test_random_small_tasks(self):
        rng = random.Random(2606)
        for index in range(120):
            facts = tuple(f'f{i}' for i in range(rng.randint(1, 5)))
            sample = lambda: {f for f in facts if rng.random() < .35}
            task = Task(str(index), set(facts), frozenset(sample()),
                        frozenset(sample() or {facts[0]}),
                        [Operator(f'op{i}', sample(), sample(), sample()) for i in range(rng.randint(0, 10))])
            self.compare(task)

    def test_noop_deadend_empty_precondition_and_empty_goal(self):
        for goals in (frozenset(), frozenset({'goal'})):
            self.compare(Task('edge-cases', {'goal', 'trap'}, frozenset(), goals,
                [Operator('noop', set(), set(), set()),
                 Operator('finish', set(), {'goal'}, set()),
                 Operator('trap', set(), {'trap'}, set())]))

    def test_empty_task(self):
        self.compare(Task('empty', set(), frozenset(), frozenset(), []))

    def test_invalid_state_and_capsule_raise(self):
        native = DownwardTask(Task('x', {'g'}, frozenset(), frozenset({'g'}), []))
        with self.assertRaises(ValueError):
            native.evaluate(100)
        with self.assertRaises(ValueError):
            native.native.goal(object(), 0)
        with self.assertRaises(ValueError):
            DownwardTask(Task('x', {'g'}, frozenset(), frozenset({'g'}), []), 'unsupported')

    def test_fact_boundary_retains_hashes_and_operator_order(self):
        operators = [Operator('finish', set(), {'g'}, set()), Operator('noop', set(), set(), set())]
        original = Task('boundary', {'g'}, frozenset(), frozenset({'g'}), operators)
        task = FactStateTask(original)
        self.assertEqual(hash(task.initial_state), hash(original.initial_state))
        self.assertEqual([hash(op) for op in task.operators], [hash(op) for op in operators])
        self.assertEqual([(op.name, child) for op, child in task.get_successor_states(task.initial_state)],
                         [(op.name, child) for op, child in original.get_successor_states(original.initial_state)])
        self.assertEqual(native_provenance()['revision'], '7ea2755269ff9398279b30f5c848e32ba6047c9c')


if __name__ == '__main__':
    unittest.main()
