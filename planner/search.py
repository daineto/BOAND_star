"""BOAND* policy search with graph-based best and worst bounds."""
import heapq
import json
from functools import lru_cache
import math
import re
import time
from pathlib import Path
from pddl import parse_domain, parse_problem
from .relaxation import OperatorCostHMaxHeuristic as hMaxHeuristic
from pyperplan.heuristics.lm_cut import LmCutHeuristic
from pyperplan.task import Task
from pyperplan.search.searchspace import SearchNode
from .policy import Policy, CYCLE_COST
from .preprocessing import get_alloutcome_determinization
from .backends import get_backend
from .output import write_solution, write_stats
from .heuristics import (CachedStateHeuristic, FondHeuristic, BlindBestCaseHeuristic, MinSumBestCaseHeuristic, SumMinBestCaseHeuristic, BlindWorstCaseHeuristic, MaxSumWorstCaseHeuristic, DeltaSizeHeuristic, ZeroSizeHeuristic)
from .state_selection import (StateSelector, RandomStateSelector, BoundsFirstStateSelector, LargestGStateSelector, BestStateSelector)
from .queue_order import (OpenListSorter, BestWorstOpenListSorter, WorstBestOpenListSorter, BestOpenListSorter, WorstOpenListSorter)


def select_pending_state(policy, task, heuristic):
    # 1: Expanding lower g first
    # prio_list = []
    # for state in policy.pending:
    #     heapq.heappush(prio_list, (policy.get_best_g(state) + heuristic(SearchNode(state, None, None, 0)),state))
    # g,state = heapq.heappop(prio_list)
    # policy.pending.remove(state)


    # 2: Establish bounds
    prio_list = []
    if len(policy.goal_states) == 0:
        for state in policy.pending:
            heapq.heappush(prio_list, (policy.get_best_g(state) + heuristic(SearchNode(state, None, None, 0)),state))
    else:
        for state in policy.pending:
            heapq.heappush(prio_list, (-(policy.get_best_g(state) + heuristic(SearchNode(state, None, None, 0))),state))
    g,state = heapq.heappop(prio_list)
    policy.pending.remove(state)

    return state


def update_g_values(policy, state, reached_states, task):
    best = policy.best_costs
    worst = policy.worst_costs
    child_best = best[state] + 1
    parent_worst = worst.get(state, CYCLE_COST)
    child_worst = CYCLE_COST if parent_worst == CYCLE_COST else parent_worst + 1
    for child in reached_states:
        if child not in best:
            best[child] = child_best
            worst[child] = child_worst
        else:
            previous_worst = worst.get(child, CYCLE_COST)
            # A dominated edge preserves bounds and cannot create a new cycle.
            if best[child] > child_best or (previous_worst != CYCLE_COST and
                    (child_worst == CYCLE_COST or previous_worst < child_worst)):
                # The full graph includes every outcome of the new assignment;
                # no initialization of the remaining outcomes is needed here.
                update_g_brute(policy, task)
                return


def update_g_brute(policy: Policy, task: Task):
    """Compute shortest best bounds and cycle-aware worst bounds in graph passes."""
    root = task.initial_state
    best = {root: 0}
    indegrees = {root: 0}
    successors = {}
    outcomes_for_action = getattr(task, "policy_outcomes", None)
    frontier = [root]
    # Breadth-first discovery chooses a shortest-path predecessor for each state.
    for state in frontier:
        action = policy.strategy.get(state)
        if action is None:
            reached = ()
        elif outcomes_for_action is not None:
            reached = outcomes_for_action(state, action[0])
        else:
            reached = {op.apply(state) for op in action[1]}
        successors[state] = reached
        for child in reached:
            indegrees[child] = indegrees.get(child, 0) + 1
            if child not in best:
                best[child] = best[state] + 1
                frontier.append(child)

    distances = {root: 0}
    ready = [state for state, degree in indegrees.items() if degree == 0]
    # Kahn's traversal computes finite longest paths. The residue consists of
    # cycle states and their descendants, all of which have CYCLE_COST.
    for state in ready:
        distance = distances[state] + 1
        for child in successors[state]:
            if distance > distances.get(child, -1):
                distances[child] = distance
            indegrees[child] -= 1
            if indegrees[child] == 0:
                ready.append(child)
    cyclic_states = {state for state, degree in indegrees.items() if degree}
    distances.update(dict.fromkeys(cyclic_states, CYCLE_COST))
    policy.best_costs = best
    policy.worst_costs = distances
    policy.cyclic = bool(cyclic_states)


def extension_has_escape(policy, state, successors, task):
    """AND* incremental deadlock test, given a deadlock-free parent.

    Only the newly assigned state can close the last escape from an existing
    region. Find an unmapped outcome reachable from it; goals also count.
    The override at state is already represented by the initial successors.
    """
    seen = {state}
    frontier = list(successors)
    outcomes = getattr(task, "policy_outcomes", None)
    for child in frontier:
        if child in seen:
            continue
        action = policy.strategy.get(child)
        if action is None:
            return True
        seen.add(child)
        reached = outcomes(child, action[0]) if outcomes is not None else {op.apply(child) for op in action[1]}
        frontier.extend(successor for successor in reached if successor not in seen)
    return False


def extend_policy(current_policy, state, nondet_action, det_actions, successors, task):
    new_policy = current_policy.copy()
    new_policy.strategy[state] = (nondet_action, det_actions)

    # TODO: is it better to compute the pending first?
    # if every successor is in new_pending then no need update_g_brute?

    # Update the g-values (ancestors) of the reached states
    update_g_values(new_policy,state,successors, task)

    # Classify each outcome once, retaining the existing container order.
    pending, goals = [], []
    for successor in successors:
        if task.goal_reached(successor):
            goals.append(successor)
        elif new_policy.strategy.get(successor) is None:
            pending.append(successor)

    new_policy.pending.update(pending)
    new_policy.goal_states.update(goals)

    return new_policy


def compute_f_value(policy: Policy, task: Task, heuristic: hMaxHeuristic):
    """Evaluate all three bounds in one scan without intermediate value tables."""
    outgoing = policy.pending.union(policy.goal_states)
    if not outgoing:
        return math.inf, math.inf, 0
    state_h = (heuristic.evaluate if isinstance(heuristic, CachedStateHeuristic)
               else lambda state: heuristic(SearchNode(state, None, None, 0)))
    f_best = math.inf
    f_worst = -math.inf
    pending_max = -math.inf
    for state in outgoing:
        h = state_h(state)
        best = policy.get_best_g(state) + h
        if best < f_best:
            f_best = best
        g_worst = policy.get_worst_g(state)
        worst = max(CYCLE_COST, h) if g_worst == CYCLE_COST else g_worst + h
        if worst > f_worst:
            f_worst = worst
        if state in policy.pending and h > pending_max:
            pending_max = h
    # In the existing ascending sort, h[i] + i is monotone; its last term wins.
    f_size = pending_max + len(policy.pending) - 1 if policy.pending else 0
    if policy.cyclic and f_worst < CYCLE_COST:
        f_worst = math.inf
    return f_best, f_worst, f_size


def cached_dead_end_actions(successors_for_state, heuristic, maxsize=65_536):
    """Cache an admissible infinite-h certificate for any action outcome."""
    return lru_cache(maxsize=maxsize)(
        lambda state, action: any(heuristic.evaluate(child) == math.inf
                                  for child in successors_for_state(state)[0][action])
    )


def grouped_successors(task, state):
    """Group applicable deterministic outcomes in the task's operator order.

    Returned dictionaries and sets are shared by the search cache and read-only
    after construction. Keep the original construction sequence to avoid
    gratuitous changes to set iteration order and policy ties.
    """
    nondet_action_to_successors = {}
    nondet_to_det_action = {}
    for op, succ in task.get_successor_states(state):
        nondet_action = re.sub('_detdup_' + '[0-9]*', '', op.name)
        successors = nondet_action_to_successors.get(nondet_action, set())
        successors.add(succ)
        nondet_action_to_successors[nondet_action] = successors
        det_actions = nondet_to_det_action.get(nondet_action, set())
        det_actions.add(op)
        nondet_to_det_action[nondet_action] = det_actions
    return nondet_action_to_successors, nondet_to_det_action


def boand_star(
        domain_file,
        problem_file,
        solution_folder,
        use_metric = "bw",
        use_cp_heuristic = "hmax",
        use_best_case_heuristic = "MinSum",
        use_worst_case_heuristic = "MaxSum",
        use_size_heuristic = "Delta",
        use_selector = "bounds_first",
        backend = "pyperplan"):

    backend_spec = get_backend(backend)
    pname = problem_file[problem_file.rfind("/")+1:][:-5]
    initialization_started = time.perf_counter()

    # Read FOND task
    domain = parse_domain(domain_file)
    problem = parse_problem(problem_file)

    task = backend_spec.ground(domain, problem, get_alloutcome_determinization)
    translation_provenance = getattr(task, "translation_provenance", None)
    grounding_seconds = time.perf_counter() - initialization_started
    heuristic_started = time.perf_counter()

    # CONFIG

    if backend_spec.native:
        from .backends.downward import HandleStateTask
        task = HandleStateTask(task, use_cp_heuristic)
        cp_heuristic = task
    elif use_cp_heuristic == "hmax":
        cp_heuristic = hMaxHeuristic(task)
    elif use_cp_heuristic == "lmcut":
        cp_heuristic = LmCutHeuristic(task)
    else:
        print("heuristic must be 'hmax' or 'lmcut'")
        exit()

    cp_heuristic = CachedStateHeuristic(cp_heuristic)
    heuristic_setup_seconds = time.perf_counter() - heuristic_started
    successors_for_state = lru_cache(maxsize=65_536)(lambda state: grouped_successors(task, state))
    action_has_dead_end = cached_dead_end_actions(successors_for_state, cp_heuristic)
    # Retain the deterministic-action iteration order used by graph construction.
    # The cache belongs to this task and stores read-only outcome sets.
    task.policy_outcomes = lru_cache(maxsize=65_536)(
        lambda state, action: {op.apply(state) for op in successors_for_state(state)[1][action]}
    )

    if use_best_case_heuristic == "Blind":
        best_heuristic = BlindBestCaseHeuristic(cp_heuristic)
    elif use_best_case_heuristic == "SumMin":
        best_heuristic = SumMinBestCaseHeuristic(cp_heuristic)
    elif use_best_case_heuristic == "MinSum":
        best_heuristic = MinSumBestCaseHeuristic(cp_heuristic)
    else:
        print("Best Case Heuristic must be 'Blind', 'SumMin' or 'MinSum'")
        exit()

    if use_worst_case_heuristic == "Blind":
        worst_heuristic = BlindWorstCaseHeuristic(cp_heuristic)
    elif use_worst_case_heuristic == "MaxSum":
        worst_heuristic = MaxSumWorstCaseHeuristic(cp_heuristic)
    else:
        print("Worst Case Heuristic must be 'Blind' or 'MaxSum'")
        exit()

    if use_size_heuristic == "Zero":
        size_heuristic = ZeroSizeHeuristic(cp_heuristic)
    elif use_size_heuristic == "Delta":
        size_heuristic = DeltaSizeHeuristic(cp_heuristic)
    else:
        print("Worst Case Heuristic must be 'Zero' or 'Delta'")
        exit()

    joint_bounds = (use_best_case_heuristic, use_worst_case_heuristic, use_size_heuristic) == ("MinSum", "MaxSum", "Delta")

    if use_selector == "random":
        selector = RandomStateSelector()
    elif use_selector == "best":
        selector = BestStateSelector()
    elif use_selector == "largestg":
        selector = LargestGStateSelector()
    elif use_selector == "bounds":
        selector = BoundsFirstStateSelector()
    else:
        print("selector must be 'random' or 'bounds'")
        exit()

    if use_metric == "bw":
        openListSorter = BestWorstOpenListSorter()
    elif use_metric == "wb":
        openListSorter = WorstBestOpenListSorter()
    elif use_metric == "b":
        openListSorter = BestOpenListSorter()
    elif use_metric == "w":
        openListSorter = WorstOpenListSorter()
    else:
        print("metric must be 'b' (best), 'w' (worst), 'bw' (best,worst) or 'wb' (worst,best).")
        exit()

    Path(solution_folder).mkdir(parents=True, exist_ok=True)

    # hcache = dict()

    # Initialize open and closed list
    open_list = []
    # closed_list = set()

    # Generate empty policy
    empty_policy = Policy(dict(),set(), set())
    # Goal states terminate a policy, including when the root is already a goal.
    if task.goal_reached(task.initial_state):
        empty_policy.goal_states.add(task.initial_state)
    else:
        empty_policy.pending.add(task.initial_state)
    empty_policy.best_costs = {task.initial_state:0}
    empty_policy.worst_costs = {task.initial_state: 0}
    # Push the empty policy onto the open list
    heapq.heappush(open_list, ((0,0), empty_policy))

    pareto_frontier = []
    pareto_f = (math.inf, math.inf)
    # repeated = 0
    stats = {"best":[], "worst":[], "size":[], "time":[], "iterations":[], "expansions":[], "generations":[], "max_open":[]}

    max_open = 0
    it = 0
    expansions = 0
    generations = 0
    start_time = time.time()
    # Loop until the open list is empty
    while open_list:
        # Get the policy with the lowest f value
        f_value, current_policy = heapq.heappop(open_list)
        it += 1

        # Pruning non-Pareto solutions
        if f_value[0] >= pareto_f[0] and f_value[1] >= pareto_f[1]:
            continue

        # CLOSED LIST SEEMS UNNECESSARY
        # hashable_strategy = frozenset(current_policy.strategy.items())
        # if hashable_strategy in closed_list:
        #     repeated += 1
        #     pass # Add a breakpoint here to see hits
        # closed_list.add(hashable_strategy)


        # Check if the policy is closed
        if current_policy.is_closed():
            # If closed and proper, it is a solution
            if current_policy.is_proper(task):
                pareto_frontier += [current_policy]
                pareto_f = (f_value[0], f_value[1])

                elapsed_time = time.time() - start_time

                if not current_policy.strategy:
                    # The terminal root needs no action. In particular, avoid
                    # Pyperplan LM-cut's infinite estimate for an empty goal.
                    f_best = f_worst = 0
                else:
                    f_best = best_heuristic.get_f_value(current_policy)
                    f_worst = worst_heuristic.get_f_value(current_policy)

                stats["best"] += [f_best]
                stats["worst"] += [f_worst]
                stats["size"] += [len(current_policy.strategy)]
                stats["time"] += [elapsed_time]
                stats["iterations"] += [it]
                stats["expansions"] += [expansions]
                stats["generations"] += [generations]
                stats["max_open"] += [max_open]


                write_solution(current_policy, len(pareto_frontier),pname, solution_folder, task=task)
                write_stats(stats, pname, solution_folder)

            # Closed policies cannot be expanded
            continue

        ### EXPANSION ###
        expansions += 1
        # Select a state from Out~(current_policy)
        state = selector.select_pending_state(current_policy, cp_heuristic)

        nondet_action_to_successors, nondet_to_det_action = successors_for_state(state)

        for (nondet_action,successors) in nondet_action_to_successors.items():
            # All queued parents retain escape routes; reject the extension
            # before copying policy containers or computing graph bounds.
            generations += 1
            # Strong-cyclic solutions must handle every outcome. A successor
            # with infinite admissible classical h cannot reach a goal.
            if action_has_dead_end(state, nondet_action):
                continue
            if not extension_has_escape(current_policy, state, successors, task):
                continue
            # Create new_policy by extending current_policy
            # Extension: map tile to action
            new_policy = extend_policy(current_policy, state, nondet_action, nondet_to_det_action[nondet_action], nondet_action_to_successors[nondet_action], task)

            # Calculate new_policy's f-value
            if joint_bounds:
                f_best, f_worst, f_size = compute_f_value(new_policy, task, cp_heuristic)
            else:
                f_best = best_heuristic.get_f_value(new_policy)
                f_worst = worst_heuristic.get_f_value(new_policy)
                f_size = size_heuristic.get_f_value(new_policy)

            # Uncomment to discard weak policies
            if f_worst == math.inf or f_size == math.inf:
                continue

            # Uncomment to discard cyclic policies
            # if new_policy.cyclic:
            #     continue

            # Add the child to the open list
            openListSorter.push(open_list,f_best,f_worst,f_size,new_policy)
            # heapq.heappush(open_list, ((f_best,f_worst,f_close),new_policy)) # BEST then WORST
            # heapq.heappush(open_list, ((f_worst,f_best,f_close),new_policy)) # WORST then BEST

        max_open = max(max_open, len(open_list))

    elapsed_time = time.time() - start_time

    stats["best"] += [-1]
    stats["worst"] += [-1]
    stats["size"] += [-1]
    stats["time"] += [elapsed_time]
    stats["iterations"] += [it]
    stats["expansions"] += [expansions]
    stats["generations"] += [generations]
    stats["max_open"] += [max_open]

    write_stats(stats, pname, solution_folder)
    metadata = {"backend": backend, "heuristic": use_cp_heuristic,
                "parsing_compilation_grounding_seconds": grounding_seconds,
                "backend_heuristic_setup_seconds": heuristic_setup_seconds}
    if backend_spec.native:
        metadata["native_build"] = task.backend_provenance
    if translation_provenance is not None:
        metadata["translation"] = translation_provenance
    Path(solution_folder, f"{pname}.backend.json").write_text(json.dumps(metadata, indent=2) + "\n")

    # print(len(closed_list))
    return pareto_frontier
