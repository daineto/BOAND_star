"""Independent exact cost oracle for small single-position FOND tasks.

Enumerates reachable stationary strong policies, pruning a partial policy only
when it already has a directed cycle. Cyclic proper policies can contribute at
most one additional nondominated pair: their minimum possible best cost with
infinite worst cost. A nested reachability fixed point computes that bound.
This is a diagnostic enumerator, not the BOAND search algorithm.
"""
import time
from collections import deque


def minimum_proper_best(actions, initial, goal):
    """Strong-cyclic winning region, then shortest path within that region."""
    outer = set(actions) | {goal}
    while True:
        inner = {goal}
        while True:
            additions = {s for s in outer - inner if any(
                outcomes and set(outcomes) <= outer and set(outcomes) & inner
                for outcomes in actions.get(s, ())) }
            if not additions:
                break
            inner |= additions
        if inner == outer:
            break
        outer = inner
    if initial not in outer:
        return None
    distance, queue = {initial: 0}, deque([initial])
    while queue:
        source = queue.popleft()
        if source == goal:
            return distance[source]
        for outcomes in actions.get(source, ()):
            if set(outcomes) <= outer:
                for target in outcomes:
                    if target not in distance:
                        distance[target] = distance[source] + 1
                        queue.append(target)
    raise AssertionError('Winning initial state must have a goal path')


def exact_front(actions, initial, goal, *, max_nodes=1000000, seconds=30):
    """Return a complete front or raise on the enumeration resource limit.

    Input maps states to lists of nonempty outcome tuples. Terminal goal actions
    are ignored. A partial assignment is extended at a reachable undecided state;
    unreachable states never need an assignment. DFS detects all partial cycles.
    """
    if any(not outcomes for values in actions.values() for outcomes in values):
        raise ValueError('Actions must have nonempty outcomes')
    started = time.monotonic()
    graph, costs = {}, set()
    visited_nodes = completed_policies = 0

    # Use explicit stacks for both policy backtracking and graph traversal.
    # Python recursion depth must not determine which inputs can be certified.
    assignments = []
    while True:
        visited_nodes += 1
        if visited_nodes > max_nodes or time.monotonic() - started > seconds:
            raise RuntimeError('Independent policy enumeration limit exceeded; front is unknown')
        colors, pending, pending_set, order = {}, [], set(), []
        traversal = [(initial, False)]
        cyclic = False
        while traversal:
            source, exiting = traversal.pop()
            if source == goal:
                continue
            if exiting:
                colors[source] = 2
                order.append(source)
                continue
            color = colors.get(source, 0)
            if color == 1:
                cyclic = True
                break
            if color == 2:
                continue
            if source not in graph:
                if source not in pending_set:
                    pending.append(source)
                    pending_set.add(source)
                continue
            colors[source] = 1
            traversal.append((source, True))
            traversal.extend((target, False) for target in reversed(graph[source]))

        if not cyclic:
            if pending:
                source = pending[0]
                assignments.append((source, iter(actions.get(source, ()))))
            else:
                # DFS postorder supports exact shortest/longest path programs.
                best, worst = {goal: 0}, {goal: 0}
                for source in order:
                    best[source] = 1 + min(best[t] for t in graph[source])
                    worst[source] = 1 + max(worst[t] for t in graph[source])
                costs.add((best[initial], worst[initial]))
                completed_policies += 1

        # Extend the newest undecided state, or backtrack to its next action.
        while assignments:
            source, choices = assignments[-1]
            try:
                graph[source] = next(choices)
                break
            except StopIteration:
                graph.pop(source, None)
                assignments.pop()
        if not assignments:
            break
    best_proper = minimum_proper_best(actions, initial, goal)
    if best_proper is not None:
        costs.add((best_proper, float('inf')))
    front = sorted(p for p in costs if not any(
        q != p and q[0] <= p[0] and q[1] <= p[1] for q in costs))
    return {'front': front, 'partial_assignments': visited_nodes,
            'strong_policies': completed_policies, 'minimum_proper_best': best_proper,
            'seconds': time.monotonic() - started}
