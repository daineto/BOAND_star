"""Validate emitted mini policies by replaying every nondeterministic outcome."""
import argparse
from collections import deque
import json
import os
from pathlib import Path
import re
import tempfile

import networkx as nx
from pddl import parse_domain, parse_problem

from experiment_support.configurations import MINI_CONFIGURATIONS, MINI_DOMAINS, REPOSITORY_ROOT
from planner.policy import CYCLE_COST
from planner.preprocessing import get_alloutcome_determinization
from .results import load_results
from experiment_support.campaigns import load_campaign, resolve_dataset


def parse_policy(file):
    strategy = {}
    lines = [line for line in Path(file).read_text().splitlines() if line.strip()]
    if len(lines) % 2:
        raise ValueError(f"Unpaired state/action lines in {file}")
    for state_line, action_line in zip(lines[::2], lines[1::2]):
        if not state_line.startswith("If holds: ") or not action_line.startswith("Execute: "):
            raise ValueError(f"Invalid policy line in {file}")
        state = frozenset(state_line[len("If holds: "):].split("/"))
        strategy[state] = action_line[len("Execute: "):]
    return strategy


def validate_policy(task, strategy):
    graph = nx.DiGraph()
    graph.add_node(task.initial_state)
    pending = deque([task.initial_state])
    seen = {task.initial_state}
    goals = set()
    while pending:
        state = pending.popleft()
        if task.goal_reached(state):
            goals.add(state)
            continue
        if state not in strategy:
            raise ValueError("Reachable non-goal state has no action")
        successors = [successor for operator, successor in task.get_successor_states(state)
                      if re.sub('_detdup_' + '[0-9]*', '', operator.name) == strategy[state]]
        if not successors:
            raise ValueError(f"Inapplicable policy action: {strategy[state]}")
        for successor in successors:
            graph.add_edge(state, successor)
            if successor not in seen:
                seen.add(successor)
                pending.append(successor)
    can_reach_goal = set(goals)
    for goal in goals:
        can_reach_goal.update(nx.ancestors(graph, goal))
    if can_reach_goal != seen:
        raise ValueError("Policy has a reachable state from which no goal is reachable")
    distances = nx.single_source_shortest_path_length(graph, task.initial_state)
    best = min(distances[goal] for goal in goals)
    if nx.is_directed_acyclic_graph(graph):
        longest = {task.initial_state: 0}
        for state in nx.topological_sort(graph):
            for successor in graph.successors(state):
                longest[successor] = max(longest.get(successor, 0), longest[state] + 1)
        worst = max(longest[goal] for goal in goals)
    else:
        worst = CYCLE_COST
    return {"best": best, "worst": worst, "reachable_states": len(seen)}


def validate_run(root):
    result_root, _ = resolve_dataset(load_campaign("icaps2025"), root)
    runs = load_results(result_root, MINI_CONFIGURATIONS, MINI_DOMAINS)
    report = []
    cwd = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="boand-policy-check-") as temporary:
        try:
            os.chdir(temporary)  # Preprocessing's auxiliary files stay outside the repository.
            domain = parse_domain(str(REPOSITORY_ROOT / "benchmarks" / "frozenlake" / "domain.pddl"))
            for run in runs.values():
                policies = sorted(run.directory.rglob("*.boand.*.out"))
                if not policies:
                    continue
                problem = parse_problem(str(REPOSITORY_ROOT / "benchmarks" / "frozenlake" / f"{run.instance}.pddl"))
                task = get_alloutcome_determinization(domain, problem)
                solutions = [row for row in run.stats if row["best"] != -1]
                if len(policies) != len(solutions):
                    raise ValueError(f"{run.instance}: policy/statistics count mismatch")
                for file, row in zip(policies, solutions):
                    costs = validate_policy(task, parse_policy(file))
                    if (costs["best"], costs["worst"]) != (row["best"], row["worst"]):
                        raise ValueError(f"{file}: replay costs {costs} disagree with statistics {row}")
                    report.append({"instance": run.instance, "policy": file.name, **costs})
        finally:
            os.chdir(cwd)
    return {"validated_policies": len(report), "policies": report}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate_run(args.root.resolve()), indent=2))


if __name__ == "__main__":
    main()
