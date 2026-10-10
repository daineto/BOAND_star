# Journal trade-off benchmark pilot (definition 1)

This campaign evaluates exploratory inputs for a future journal benchmark. It
does not replace ICAPS 2025 or change the journal development smoke/performance
selections. The pilot candidate manifest is fixed for reproducibility; the final
paper benchmark selection is pending review.

The FrozenLake pilot contains 19 predeclared candidates: three independently
verified examples, five increasing-height corner layouts, three staggered-wall
layouts, six random wall/pit layouts with fixed seeds, and open/unsolvable
controls. Family names describe layouts; multiple Pareto points are an observed
property, not an assumption. Singleton fronts and failures are retained.

The original ICAPS FrozenLake domain is copied byte for byte. Coordinates
increase right/up; all grids have exterior walls. A move can travel one or two
tiles; a wall beyond the adjacent ice tile makes the move deterministic. Pits
remain dead ends. All actions retain unit cost and unchanged policy semantics.

`benchmarks/journal_tradeoffs/frozenlake/generation.json` records generator
version and source hash, original-domain and example-definition hashes, every
layout, dimensions, family, seed, start/goal and generated PDDL hash. The seed
is a map-generation seed; planner runs use `PYTHONHASHSEED=0`.

## Reproduction

Build the pinned native backend as documented in the main README. Use the
project virtual environment. Generate to a fresh directory; overwrites are
rejected:

```bash
.venv/bin/python -m experiment_support.benchmark_generators.frozenlake \
  outputs/frozenlake-regenerated

PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_tradeoffs \
  --profile smoke --dry-run
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_tradeoffs \
  --profile smoke

PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_tradeoffs \
  --profile pilot --dry-run
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_tradeoffs \
  --profile pilot

.venv/bin/python -m campaigns.journal_tradeoffs.analysis \
  --dataset runs/journal_tradeoffs/<run-id> --output outputs/frozenlake-pilot
```

`smoke` runs both FD/hmax and FD/LM-cut on the three exact examples (six jobs).
`pilot` runs both on all 19 candidates (38 jobs). Both profiles use 600
seconds/job, 6,000,000 KB virtual memory/job and four workers. Unlike the
development smoke command, this campaign has no 60-second suite deadline.
The pilot campaign is explicitly authorized by the user's request to proceed
with the FrozenLake pilot. Do not launch other campaigns concurrently.

Analysis replays every emitted policy against original PDDL, including
incumbents from incomplete searches. It checks both numerical costs, compares
completed fronts across heuristics, and exhaustively enumerates small grids
when the policy-assignment count is at most 200,000. Larger completed fronts
rely on BOAND optimality; partial fronts are labeled best known. Timeouts and
memory failures are not proofs of unsolvability. Finite trade-off magnitudes
exclude infinity. A single run characterizes difficulty, not timing variability
or repeatable heuristic speedups.

Outputs include per-instance references and their certainty, per-configuration
completion/search work/timing records, replay evidence, figures and a report.
Retain all candidates when reporting the pilot; selecting the final collection
is a later scientific decision.
