"""Pinned Fast Downward grounding, before classical SAS graph simplification.

Only positive STRIPS produced by the shared negative-condition compiler is
accepted. Relaxed reachability may omit unreachable operators, but every
reachable all-outcome operator (including identities) must survive. Goals are
retained even when the relaxed exploration declares the task unsolvable.
"""
from dataclasses import dataclass, field
from functools import lru_cache
import gc
import hashlib
import importlib
import subprocess
import sys
from pathlib import Path

from .downward import ROOT, native_provenance


@lru_cache(maxsize=1)
def translator_provenance():
    pin = native_provenance()
    source = ROOT / "outputs/fast-downward/source"
    command = ["git", "-c", f"safe.directory={source}", "-C", str(source)]
    revision = subprocess.check_output([*command, "rev-parse", "HEAD"], text=True).strip()
    relative = "src/translate/fast_downward"
    dirty = subprocess.check_output([*command, "status", "--porcelain", "--", relative], text=True)
    if revision != pin["revision"] or dirty:
        raise RuntimeError("Translator must be the clean pinned upstream source; rebuild/retrieve the dependency")
    directory = source / "src/translate"
    hashes = {str(file.relative_to(directory)): hashlib.sha256(file.read_bytes()).hexdigest()
              for file in sorted((directory / "fast_downward").rglob("*.py"))}
    return {"revision": revision, "files": hashes, "keep_no_ops": True,
            "encoding": "boand-boolean", "classical_sas_simplification": False,
            "negative_conditions": "unified-planning"}


def translator_modules():
    translator_provenance()
    directory = ROOT / "outputs/fast-downward/source/src/translate"
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
    package = importlib.import_module("fast_downward.translate")
    if directory not in Path(package.__file__).resolve().parents:
        raise RuntimeError("An unpinned Fast Downward translator is already imported")
    return tuple(importlib.import_module(f"fast_downward.translate.{name}")
                 for name in ("options", "pddl_parser", "normalize", "instantiate", "pddl"))


@dataclass(frozen=True)
class GroundedOperator:
    name: str
    preconditions: frozenset
    add_effects: frozenset
    del_effects: frozenset

    def __hash__(self):
        return hash((self.name, self.preconditions, self.add_effects, self.del_effects))

    def apply(self, state):
        if not self.preconditions <= state:
            raise ValueError(f"Inapplicable operator: {self.name}")
        return (state - self.del_effects) | self.add_effects


@dataclass
class GroundedTask:
    name: str
    facts: frozenset
    initial_state: frozenset
    goals: frozenset
    operators: tuple
    translation_provenance: dict
    complement_pairs: dict = field(default_factory=dict)

    def goal_reached(self, state):
        return self.goals <= state

    def get_successor_states(self, state):
        return [(op, op.apply(state)) for op in self.operators if op.preconditions <= state]


def ground_compiled_pddl(domain_file, problem_file, direct=False):
    options, parser, normalize, instantiate, pddl = translator_modules()
    options.set_options([str(domain_file), str(problem_file), "--keep-no-ops"])
    # The upstream file helper leaves streams for garbage collection; close
    # explicitly when using its parser repeatedly within a Python process.
    with Path(domain_file).open(encoding="ISO-8859-1") as domain_stream, \
            Path(problem_file).open(encoding="ISO-8859-1") as problem_stream:
        task = parser.parsing_functions.parse_task(
            parser.lisp_parser.parse_nested_list(domain_stream),
            parser.lisp_parser.parse_nested_list(problem_stream))
    complements = {}
    if direct:
        from .negative import compile_negative_conditions
        complements = compile_negative_conditions(task, pddl, instantiate)

    def literals(condition):
        if isinstance(condition, pddl.Atom):
            return [condition]
        if isinstance(condition, (pddl.Conjunction, pddl.Truth)):
            return [literal for part in condition.parts for literal in literals(part)]
        raise ValueError("FD grounding currently requires compiled positive conjunctive STRIPS")

    if task.axioms or task.use_min_cost_metric:
        raise ValueError("FD grounding does not support axioms or action-cost metrics")
    goals = literals(task.goal)
    for action in task.actions:
        literals(action.precondition)
        if action.cost or any(effect.parameters or not isinstance(effect.condition, pddl.Truth)
                              for effect in action.effects):
            raise ValueError("FD grounding does not support conditional/quantified effects or action costs")
    # A literal conjunction, including an empty one, needs no goal axiom.
    # FD's normalizer otherwise wraps Truth in a generated derived predicate.
    task.goal = pddl.Conjunction(goals)
    normalize.normalize(task)
    if task.axioms:
        raise ValueError("FD normalization introduced unsupported axioms")
    # Bypass main.pddl_to_sas: it replaces unreachable-goal tasks and applies
    # classical variable/operator pruning. Negative-free relaxed exploration
    # cannot omit an operator applicable in any genuinely reachable state.
    _, _, actions, _, axioms, _ = instantiate.explore(task)
    if axioms:
        raise ValueError("FD grounding introduced unsupported axioms")

    def fact(atom):
        if atom.negated:
            raise ValueError("Negative literals must be compiled before grounding")
        return "(" + " ".join((atom.predicate, *atom.args)) + ")"

    operators = []
    for action in sorted(actions, key=lambda action: action.name):
        if any(condition for condition, _ in action.add_effects + action.del_effects):
            raise ValueError("FD grounding introduced conditional effects")
        pre = frozenset(map(fact, action.precondition))
        add = frozenset(fact(atom) for _, atom in action.add_effects)
        delete = frozenset(fact(atom) for _, atom in action.del_effects) - add
        if complements:
            # Resolve parameter aliases on original effects before mirroring.
            # Lifted opposite writes may alias only after grounding.
            def mirror(value):
                predicate, *args = value[1:-1].split()
                return "(" + " ".join((complements[predicate], *args)) + ")"
            mirror_names = set(complements.values())
            add = frozenset(value for value in add if value[1:-1].split()[0] not in mirror_names)
            delete = frozenset(value for value in delete if value[1:-1].split()[0] not in mirror_names)
            delete -= add
            original_add, original_delete = add, delete
            add |= frozenset(mirror(value) for value in original_delete if value[1:-1].split()[0] in complements)
            delete |= frozenset(mirror(value) for value in original_add if value[1:-1].split()[0] in complements)
        # Match the reference STRIPS normalization and zero-argument names.
        operators.append(GroundedOperator(action.name.replace(" )", ")"), pre, add - pre, delete))
    goals = frozenset(map(fact, goals))
    facts = frozenset().union(goals, *(op.preconditions | op.add_effects | op.del_effects
                                    for op in operators))
    initial = frozenset(fact(atom) for atom in task.init if isinstance(atom, pddl.Atom)) & facts
    provenance = dict(translator_provenance())
    if direct:
        provenance["negative_conditions"] = "boand-dual-rail-v1"
    pairs = {}
    for value in facts:
        predicate, *args = value[1:-1].split()
        if predicate in complements:
            other = "(" + " ".join((complements[predicate], *args)) + ")"
            if other in facts:
                pairs[value] = other
    if direct:
        provenance["encoding"] = "boand-paired-boolean-v1"
    return GroundedTask(task.problem_name, facts, initial, goals, tuple(operators), provenance, pairs)


def get_downward_determinization(domain, problem):
    from planner.preprocessing import compile_alloutcome_pddl
    task = ground_compiled_pddl(*compile_alloutcome_pddl(domain, problem))
    # FD's Datalog temporary graphs contain cycles. Reclaim them during
    # preprocessing, before a full-heap collection can interrupt search.
    # Keep normal automatic GC enabled; the elapsed cost belongs to setup.
    gc.collect()
    return task


def get_direct_determinization(domain, problem):
    from planner.fondutils import determinize
    from pddl.formatter import domain_to_string, problem_to_string
    Path("aux_domain.pddl").write_text(domain_to_string(determinize(domain)))
    Path("aux_problem.pddl").write_text(problem_to_string(problem))
    task = ground_compiled_pddl("aux_domain.pddl", "aux_problem.pddl", direct=True)
    gc.collect()
    return task
