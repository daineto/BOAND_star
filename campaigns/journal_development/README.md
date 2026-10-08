# Journal development campaign

This campaign supports planner improvements for the forthcoming journal study.
It defines a development smoke suite, not the full paper experiment. The working
branch is `codex/journal-development`; `icaps2025` remains the publication tag.

The input manifest reuses the 196 verified ICAPS 2025 domain/problem entries
without changing their paths, ordering or hashes. Only the 14 explicitly named
smoke instances execute. The suite covers exactly the 11 ICAPS domains; it
excludes `st_blocksworld` and `st_first_responders`.

## Definition versions

Version 2 corrects best-cost bounds on cyclic policy graphs: breadth-first
predecessors now give shortest paths for all policies. Version 1 retained the
historical trajectory relaxation, which could skip a shorter edge when the
current trajectory classified it as cyclic. This can change search priorities,
pruning and work counts. Inputs, configurations, resource limits and expected
Pareto solution costs are unchanged. Earlier version-1 runs remain available
at their recorded Git revision; validation uses the matching campaign version.
The ICAPS 2025 definition, tag and published archives remain unchanged.

## Run and validate

From the repository root:

```bash
PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_development.smoke --dry-run
PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_development.smoke
```

The smoke command uses the campaign runner with **four workers**, a
**6,000,000 KB virtual-memory limit per job**, and a 30-second per-job timeout.
It enforces a **60-second deadline for launch, execution and validation**.
On expiry, active jobs are stopped through the runner's normal cleanup, which
can take additional time. Run this suite before and after planner changes,
using identical seeds and settings and leaving planner source unchanged during
execution. Avoid running another campaign concurrently on this 32 GB machine.

Validation requires successful execution and search completion for every
instance, compares the entire emitted Pareto cost set with `expected.json`,
and replays every emitted policy through every nondeterministic outcome. Cost
expectations come from completed published BOAND bw searches. Emission order,
policy structure and search counts may change during optimization. The two
unsolvable cases require completed searches with no policies; timeouts and
missing statistics fail validation. Replay shares the planner's preprocessing
but independently checks the reachable policy graph and costs. It does not
independently prove unsolvability or Pareto completeness.

Runs and provenance are saved under `runs/journal_development/`. Successful
checks add `smoke-validation.json` to the run directory. It records costs,
search statistics, execution timestamps, replay count and overall wall time.
To validate an existing run without running planners again:

```bash
.venv/bin/python -m campaigns.journal_development.smoke \
  --dataset runs/journal_development/<run-id>
```

For scheduling inspection or resume, the ordinary campaign commands also work:

```bash
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_development --profile smoke --dry-run
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_development --resume runs/journal_development/<run-id>
```

The ordinary runner applies the per-job limit; only the dedicated smoke command
enforces the whole-suite deadline. Resumed runs can be checked with `--dataset`;
that command measures validation time only.

## Selected instances and calibration

All runs use `bw / hmax / MinSum / MaxSum / Delta / largestg`. The first verified
run on this host on 2026-10-08 took **33.75 seconds**, including validation of
14 policies; a repeat took **34.01 seconds**. Every search completed and all
costs matched the archive in both runs.

| Domain | Instance | Behavior | Search time (s) |
| --- | --- | --- | ---: |
| Beam-walk | `p6` | Cyclic policy | 3.17 |
| Blocksworld-ex | `p02` | One solution | 0.02 |
| Blocksworld-ex | `p06` | No solution | 0.38 |
| Chain-of-rooms | `p16` | One solution | 2.15 |
| Doors | `p6` | One solution | 3.77 |
| Elevators | `p05` | One solution | 1.80 |
| FrozenLake | `motivating` | Two Pareto solutions | 0.72 |
| FrozenLake | `p07` | Cyclic policy | 7.01 |
| Islands | `p10` | One solution | 5.66 |
| Modified First Responders | `p_2_2` | Two Pareto solutions | 2.44 |
| ST Tires | `p08` | One solution | 3.75 |
| ST Tires | `p09` | No solution | 0.11 |
| Tireworld | `p03` | Cyclic policy | 0.16 |
| Tireworld-truck | `p6` | One solution | 7.87 |

Fast cases provide complementary correctness coverage. The longer searches
provide room to measure improvements. Search time excludes preprocessing;
overall wall time includes imports, preprocessing, provenance, scheduling and
validation. Repeat runs when assessing performance and compare search time and
work counts as well as total time. Keep the subset fixed as it becomes faster.

During calibration, Blocksworld-ex `p04` timed out at 30 seconds despite a
completed approximately 10-second search in the published archive. It was
excluded in favor of the verified unsolvable `p06`; the archive and benchmarks
were preserved. Archived times are selection hints, not runtime guarantees on
this host. A full journal campaign and its scientific analysis remain to be
defined separately.
