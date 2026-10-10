# FrozenLake examples with non-singleton Pareto fronts

These three exploratory problems use the original
`benchmarks/frozenlake/domain.pddl` without modifications. They are separate
from the frozen ICAPS inputs and journal smoke/performance profiles.
Coordinates increase right/up, and each grid is surrounded by walls.

| Problem | Grid | Pareto front (best, worst) | Policy assignments enumerated |
| --- | --- | --- | --- |
| `tradeoff-01.pddl` | 3 × 3 | (1, 7), (3, 5) | 384 |
| `tradeoff-02.pddl` | 3 × 4 | (2, 6), (3, 5) | 768 |
| `tradeoff-03.pddl` | 3 × 4 | (2, 10), (3, 4) | 13,824 |

All six Pareto points have finite worst-case cost: their policies are strong.
Thus these are trade-offs between two strong policies, rather than between
strong and strong-cyclic policies. Other cyclic policies are included in the
oracle's enumeration and are dominated.

For the first example, the start is immediately to the right of the goal.
Moving left can reach the goal in one action, but can also overshoot it. A
policy choosing this shortcut needs a longer recovery route in the worst case.
The alternative avoids the initial shortcut: its best case takes three actions,
but its worst case takes only five. In the third example, increasing best-case
cost from two to three reduces worst-case cost from ten to four.

## Validation and reproduction

`grids.json` records the full layouts, start/goal coordinates, expected fronts,
and discovery attempts. A deterministic exploratory search used seed 0, sampled
ice/wall/pit with weights 0.8/0.15/0.05, and selected three distinct fronts whose
points all have finite worst cost. The first grid is 3 × 3; subsequent grids
are 3 × 4. The discovery script/evidence is retained in ignored
`outputs/frozenlake-tradeoffs/`.

The independent small-grid oracle enumerates every stationary policy assignment
over safe applicable actions. Actions with a pit outcome cannot be proper and
are excluded. A placeholder self-loop for an actionless state is rejected if
that state is reachable. Goal states are terminal; unreachable assignments do
not affect a policy's costs. Reverse goal reachability checks properness, BFS
computes best cost, and DAG longest paths compute finite worst cost; reachable
cycles have infinite worst cost. Enumeration establishes the complete front,
not just validity of its reported points.

From the repository root:

```bash
.venv/bin/python -m analysis.frozenlake_tradeoffs \
  campaigns/journal_development/examples/frozenlake/grids.json

PYTHONHASHSEED=0 .venv/bin/python planner/planner.py \
  benchmarks/frozenlake/domain.pddl \
  campaigns/journal_development/examples/frozenlake/tradeoff-01.pddl \
  outputs/frozenlake-tradeoffs/example --backend downward-direct -ch lmcut
```

On 2026-10-10, both direct FD/hmax and direct FD/LM-cut completed all three
searches and returned exactly the enumerated fronts. All 12 emitted policies
passed the original-PDDL policy replay, including agreement on both costs.
Runs used `PYTHONHASHSEED=0`, 6,000,000 KB virtual memory/job, at most four
workers, and a 60-second invocation limit. Search completion took approximately
0.0009–0.0013 seconds per instance; these are correctness examples, not useful
performance benchmarks. Raw runs and replay records are in
`runs/frozenlake-tradeoffs/`; the numerical summary is in
`outputs/frozenlake-tradeoffs/verification.json`.
