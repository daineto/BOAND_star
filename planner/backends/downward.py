"""Experimental native execution of the existing grounded STRIPS task.

This stage deliberately retains Pyperplan grounding. Boolean SAS variables
preserve every grounded operator, including no-op and dead-end outcomes.
"""
from functools import lru_cache
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def native_provenance():
    """Refuse stale bindings or a binary built for a different dependency/ABI."""
    directory = ROOT / "outputs/fast-downward"
    file = directory / "build-provenance.json"
    if not file.is_file():
        raise RuntimeError("Build the native backend with .venv/bin/python -m planner.backends.native.build")
    metadata = json.loads(file.read_text())
    here = Path(__file__).with_name("native")
    pin = json.loads((here / "upstream.json").read_text())
    if any(metadata.get(key) != value for key, value in pin.items()):
        raise RuntimeError("Native dependency differs from the pin; rebuild")
    if metadata.get("python_abi") != sys.implementation.cache_tag:
        raise RuntimeError("Native Python ABI differs; rebuild")
    for name in ("bridge.cc", "build.py", "upstream.json"):
        if metadata.get("binding_hashes", {}).get(name) != hashlib.sha256((here / name).read_bytes()).hexdigest():
            raise RuntimeError(f"Native binding {name} changed; rebuild")
    module = directory / "build/search/_downward_native.so"
    if metadata.get("module_sha256") != hashlib.sha256(module.read_bytes()).hexdigest():
        raise RuntimeError("Native binary differs from its build provenance; rebuild")
    return metadata


@lru_cache(maxsize=1)
def native_module():
    provenance = native_provenance()
    file = ROOT / "outputs/fast-downward/build/search/_downward_native.so"
    if not file.is_file():
        raise RuntimeError("Build the native backend with .venv/bin/python -m planner.backends.native.build")
    spec = importlib.util.spec_from_file_location("_downward_native", file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.build_provenance = provenance
    return module


def boolean_sas(task):
    """Lossless unit-cost encoding; Pyperplan's add effects win over deletes."""
    facts = sorted(set(task.facts) | set(task.initial_state) | set(task.goals) |
                   {fact for op in task.operators for fact in
                    op.preconditions | op.add_effects | op.del_effects})
    indices = {fact: index for index, fact in enumerate(facts)}
    # FD's SAS reader requires at least one effect per operator and one goal.
    # An immutable true variable gives no-ops an identity effect and represents
    # an empty goal without changing any original fact or relaxed cost.
    auxiliary = len(facts)
    lines = ["begin_version", "3", "end_version", "begin_metric", "0", "end_metric", str(len(facts) + 1)]
    for index, fact in enumerate(facts):
        lines += ["begin_variable", f"var{index}", "-1", "2", f"NegatedAtom {fact}", f"Atom {fact}", "end_variable"]
    lines += ["begin_variable", "boand_identity", "-1", "2", "NegatedAtom boand_identity", "Atom boand_identity", "end_variable"]
    lines += ["0", "begin_state", *[str(int(fact in task.initial_state)) for fact in facts], "1",
              "end_state", "begin_goal", str(len(task.goals) or 1)]
    lines += ([f"{indices[fact]} 1" for fact in sorted(task.goals)] if task.goals
              else [f"{auxiliary} 1"])
    lines += ["end_goal", str(len(task.operators))]
    for op in task.operators:
        effects = {fact: 0 for fact in op.del_effects - op.add_effects}
        effects.update({fact: 1 for fact in op.add_effects})
        prevail = sorted(op.preconditions - effects.keys())
        lines += ["begin_operator", op.name, str(len(prevail))]
        lines += [f"{indices[fact]} 1" for fact in prevail]
        lines += [str(len(effects) or 1)]
        lines += [f"0 {indices[fact]} {1 if fact in op.preconditions else -1} {value}"
                  for fact, value in sorted(effects.items())]
        if not effects:
            lines += [f"0 {auxiliary} 1 1"]
        lines += ["1", "end_operator"]
    lines += ["0"]  # no axioms
    return "\n".join(lines) + "\n", tuple(facts)


class NativeOperator:
    __slots__ = ("name", "index", "task", "_hash")

    def __init__(self, task, index, operator):
        self.task, self.index, self.name = task, index, operator.name
        self._hash = hash(operator)

    def __hash__(self):
        return self._hash

    def apply(self, state):
        for index, child in self.task._successors(state):
            if index == self.index:
                return child
        raise ValueError(f"Inapplicable native operator: {self.name}")


class DownwardTask:
    """Integer-state task compatible with BOAND*'s task operations."""

    def __init__(self, grounded, heuristic="hmax"):
        self.native = native_module()
        sas, self.fact_names = boolean_sas(grounded)
        self.handle = self.native.load(sas, heuristic)
        self.initial_state = 0
        self.operators = tuple(NativeOperator(self, index, op)
                               for index, op in enumerate(grounded.operators))
        self._successors = lru_cache(maxsize=65_536)(
            lambda state: self.native.successors(self.handle, state))
        self.goal_reached = lru_cache(maxsize=65_536)(
            lambda state: self.native.goal(self.handle, state))
        self.heuristic = heuristic
        self.backend_provenance = self.native.build_provenance

    def get_successor_states(self, state):
        # Match the grounded operator order; the native index groups tests.
        return [(self.operators[index], child) for index, child in sorted(self._successors(state))]

    def state_facts(self, state):
        return frozenset(self.fact_names[index] for index in self.native.facts(self.handle, state)
                         if index < len(self.fact_names))

    def __call__(self, node):
        return self.evaluate(node.state)

    def evaluate(self, state):
        return self.native.evaluate(self.handle, state)


class FactStateTask:
    """Preserve Python state hashes and search order while executing natively."""

    def __init__(self, grounded, heuristic="hmax"):
        self.engine = DownwardTask(grounded, heuristic)
        self.initial_state = grounded.initial_state
        self.ids = {self.initial_state: 0}
        self.decoded = {0: self.initial_state}
        self.operators = tuple(NativeOperator(self, index, op)
                               for index, op in enumerate(grounded.operators))
        self.backend_provenance = self.engine.backend_provenance
        self._successors = lru_cache(maxsize=65_536)(self._generate)

    def _generate(self, state):
        result = []
        for index, child in sorted(self.engine._successors(self.ids[state])):
            if child not in self.decoded:
                decoded = self.engine.state_facts(child)
                self.decoded[child] = decoded
                self.ids[decoded] = child
            result.append((index, self.decoded[child]))
        return result

    def get_successor_states(self, state):
        return [(self.operators[index], child) for index, child in self._successors(state)]

    def goal_reached(self, state):
        return self.engine.goal_reached(self.ids[state])

    def evaluate(self, state):
        return self.engine.evaluate(self.ids[state])

    def __call__(self, node):
        return self.evaluate(node.state)


class NativeState:
    """Task-local identity with the legacy fact-set hash and tie comparison."""
    __slots__ = ('index', '_task', '_hash')

    def __init__(self, index, task, state_hash):
        self.index, self._task, self._hash = index, task, state_hash

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        if not isinstance(other, NativeState):
            return NotImplemented
        return self._task is other._task and self.index == other.index

    def __lt__(self, other):
        if not isinstance(other, NativeState):
            return NotImplemented
        return self._task.state_facts(self) < other._task.state_facts(other)


class HandleStateTask(FactStateTask):
    """Retain compact identities instead of permanent Python fact-set copies."""

    def __init__(self, grounded, heuristic='hmax'):
        self.engine = DownwardTask(grounded, heuristic)
        self.initial_state = NativeState(0, self, hash(grounded.initial_state))
        self.states = {0: self.initial_state}
        self.operators = tuple(NativeOperator(self, index, op)
                               for index, op in enumerate(grounded.operators))
        self.backend_provenance = self.engine.backend_provenance
        self._successors = lru_cache(maxsize=65_536)(self._generate)

    def _generate(self, state):
        result = []
        for index, child in sorted(self.engine._successors(state.index)):
            if child not in self.states:
                self.states[child] = NativeState(child, self, hash(self.engine.state_facts(child)))
            result.append((index, self.states[child]))
        return result

    def state_facts(self, state):
        return self.engine.state_facts(state.index)

    def goal_reached(self, state):
        return self.engine.goal_reached(state.index)

    def evaluate(self, state):
        return self.engine.evaluate(state.index)
