from .fondutils import determinize
from io import StringIO
from pathlib import Path as FilePath

from unified_planning.shortcuts import *
from unified_planning.io import PDDLReader, PDDLWriter

from pddl.logic.base import Not, And
from pddl.logic.effects import AndEffect
from pddl.logic.predicates import Predicate
from pddl.action import Action
from pddl.core import Domain, Problem
from pddl.formatter import domain_to_string, problem_to_string

from pyperplan.pddl.parser import Parser
from pyperplan.pddl.lisp_parser import parse_nested_list
from pyperplan import grounding


def explicit_empty_effects(domain_text):
    """Keep compiled no-op actions by giving Pyperplan an explicit empty effect.

    Unified Planning can omit :effect for an action with no effects. Existing
    effect clauses and all other PDDL sections retain their meaning.
    """
    domain = parse_nested_list(StringIO(domain_text))
    changed = False
    for section in domain:
        if (isinstance(section, list) and section and section[0] == ":action"
                and ":effect" not in section):
            section.extend((":effect", ["and"]))
            changed = True
    if not changed:
        return domain_text

    def serialize(expression):
        if isinstance(expression, list):
            return "(" + " ".join(serialize(child) for child in expression) + ")"
        return expression

    return "(" + "\n ".join(serialize(section) for section in domain) + ")\n"


def compile_alloutcome_pddl(domain, problem):
    # All-outcome determinization for heuristic
    detdomain = determinize(domain)
    with open("aux_domain.pddl", "w") as f:
        f.write(domain_to_string(detdomain))
    with open("aux_problem.pddl", "w") as f:
        f.write(problem_to_string(problem))

    # Compile away negative preconditions for pyperplan

    reader = PDDLReader()
    pddl_problem = reader.parse_problem("aux_domain.pddl", "aux_problem.pddl")

    with Compiler(
        problem_kind=pddl_problem.kind,
        compilation_kind=CompilationKind.NEGATIVE_CONDITIONS_REMOVING
        ) as negative_conditions_remover:
        ncr_result = negative_conditions_remover.compile(
            pddl_problem,
            CompilationKind.NEGATIVE_CONDITIONS_REMOVING
        )

    writer = PDDLWriter(ncr_result.problem)
    writer.write_domain("aux_domain.pddl")
    writer.write_problem("aux_problem.pddl")

    # Preserve effect-free outcomes when the writer omits their :effect clause.
    auxiliary_domain = FilePath("aux_domain.pddl")
    generated = auxiliary_domain.read_text()
    normalized = explicit_empty_effects(generated)
    if normalized != generated:
        auxiliary_domain.write_text(normalized)

    return "aux_domain.pddl", "aux_problem.pddl"


def get_alloutcome_determinization(domain, problem):
    domain_file, problem_file = compile_alloutcome_pddl(domain, problem)

    # Pyperplan setup
    parser = Parser(domain_file, problem_file)
    aux_domain = parser.parse_domain()
    aux_problem = parser.parse_problem(aux_domain)

    task = grounding.ground(aux_problem, True, False)
    
    return task
