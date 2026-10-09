"""Compile conjunctive negative literals to explicit, maintained complements."""
from itertools import product


def compile_negative_conditions(task, pddl, instantiate):
    def literals(condition):
        if isinstance(condition, pddl.Literal):
            return [condition]
        if isinstance(condition, (pddl.Conjunction, pddl.Truth)):
            return [literal for part in condition.parts for literal in literals(part)]
        raise ValueError("Direct FD translation requires conjunctive literal conditions")

    if task.axioms or task.use_min_cost_metric:
        raise ValueError("Direct FD translation does not support axioms/action costs")
    conditions = [task.goal, *(action.precondition for action in task.actions)]
    negative = {literal.predicate for condition in conditions for literal in literals(condition)
                if literal.negated}
    predicates = {predicate.name: predicate for predicate in task.predicates}
    names = set(predicates) | {action.name for action in task.actions} | {obj.name for obj in task.objects}
    mapping = {}
    for name in sorted(negative):
        if name == "=":
            raise ValueError("Direct FD negative equality compilation is not yet supported")
        complement = "not_" + name
        if complement in names:
            raise ValueError(f"Complement name collision: {complement}")
        mapping[name] = complement
    types = instantiate.get_objects_by_type(task.objects, task.types)
    initial = set(task.init)
    for name, complement in mapping.items():
        predicate = predicates[name]
        task.predicates.append(pddl.Predicate(complement, predicate.arguments))
        for args in product(*(types[arg.type_name] for arg in predicate.arguments)):
            if pddl.Atom(name, args) not in initial:
                task.init.append(pddl.Atom(complement, args))

    def positive(condition):
        return pddl.Conjunction([pddl.Atom(mapping[literal.predicate], literal.args)
                                 if literal.negated else literal for literal in literals(condition)])

    task.goal = positive(task.goal)
    for action in task.actions:
        action.precondition = positive(action.precondition)
        effects = list(action.effects)
        if action.cost or any(effect.parameters or not isinstance(effect.condition, pddl.Truth)
                              for effect in effects):
            raise ValueError("Direct FD translation does not support conditional/quantified effects or costs")
        for effect in effects:
            literal = effect.literal
            if literal.predicate in mapping:
                atom = pddl.Atom(mapping[literal.predicate], literal.args)
                action.effects.append(pddl.Effect([], pddl.Truth(), atom if literal.negated else atom.negate()))
    return mapping
