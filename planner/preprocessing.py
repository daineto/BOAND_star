from fondutils import determinize

from unified_planning.shortcuts import *
from unified_planning.io import PDDLReader, PDDLWriter

from pddl.logic.base import Not, And
from pddl.logic.effects import AndEffect
from pddl.logic.predicates import Predicate
from pddl.action import Action
from pddl.core import Domain, Problem
from pddl.formatter import domain_to_string, problem_to_string

from pyperplan.pddl.parser import Parser
from pyperplan import grounding


def get_alloutcome_determinization(domain, problem):
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


    # Pyperplan setup
    parser = Parser("aux_domain.pddl", "aux_problem.pddl")
    aux_domain = parser.parse_domain()
    aux_problem = parser.parse_problem(aux_domain)

    task = grounding.ground(aux_problem, True, False)
    
    return task