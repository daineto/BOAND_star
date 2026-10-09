# Journal development campaign

This campaign supports planner improvements for the forthcoming journal study.
It defines fixed correctness and timing profiles, not the full paper experiment. The working
branch is `codex/journal-development`; `icaps2025` remains the publication tag.

The input manifest reuses the 196 verified ICAPS 2025 domain/problem entries
without changing their paths, ordering or hashes. Only the explicitly named profile instances execute (14 for smoke, 11 for
performance). The suite covers exactly the 11 ICAPS domains; it
excludes `st_blocksworld` and `st_first_responders`.

## Definition versions

Version 4 adds a fixed `performance` profile for timing the faster planner.
It retains version-3 planner semantics and the exact original smoke selection
and numerical cost expectations. The input manifest, configuration and limits
are unchanged. Expected-outcome metadata now identifies version 4. Earlier runs
remain usable with their recorded campaign revision; timings on the two
profiles require separate baselines and must not be mixed.

Version 3 corrects closed-policy properness using reverse reachability from
goals. The historical trajectory checker could reject valid cyclic policies
(for example, `0 -> {1, goal}`, `1 -> 0`). This may change accepted policies,
coverage and Pareto costs on other inputs. Smoke inputs and numerical expected
costs remain unchanged; validation must confirm them rather than adjust them
to force agreement.

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

## Performance profile

Keep the smoke profile as the correctness gate. Use this separate selection
for profiling and timing before and after each optimization:

```bash
PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_development.smoke --profile performance --dry-run
PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_development.smoke --profile performance
```

The profile uses the same configuration, seed, four workers, 6,000,000 KB/job,
30-second job timeout and 60-second deadline including replay. The ordinary
runner also accepts `--profile performance`, but does not enforce the whole-suite
deadline. To replay an existing performance run, pass both `--profile performance`
and `--dataset <run-directory>` to the dedicated validator.

Require 11 completed searches, 10 solvable instances solved, the one unsolvable
instance completed without policies, and all 11 emitted policies replayed.
`performance-expected.json` freezes the complete cost sets from the corrected
current-parent planner. Where archived completed searches exist their costs
agree. Doors `p8` and Elevators `p04` have no completed archived result; their
expectations come from current completed searches and independent policy replay.
Replay verifies policy validity and costs, not Pareto completeness or
unsolvability. Validation writes `performance-validation.json`.

| Domain | Instance | Median search time (s) |
| --- | --- | ---: |
| Beam-walk | `p7` | 0.44 |
| Blocksworld-ex | `p13` (unsolvable) | 0.40 |
| Chain-of-rooms | `p24` | 0.55 |
| Doors | `p8` | 1.34 |
| Elevators | `p04` | 2.83 |
| FrozenLake | `p19` | 0.86 |
| Islands | `p16` | 2.79 |
| Modified First Responders | `p_2_2` (two Pareto solutions) | 0.12 |
| ST Tires | `p08` | 0.14 |
| Tireworld | `p06` | 6.84 |
| Tireworld-truck | `p7` | 1.36 |

The first whole-profile run took **31.78 seconds**, including all replay. The
0.5–3 second search target is approximate: Beam-walk and Blocksworld are close,
Modified First Responders and ST Tires remain faster because larger shortlisted
cases timed out, and Tireworld is deliberately longer to obtain measurable work.
Cyclic solutions occur in Beam-walk, FrozenLake and Tireworld. Keep every case
in the aggregate, including fast cases; report per-case medians and variability.
Repeat unprofiled runs for comparisons and retain all samples. The original
smoke baseline remains applicable only to the original smoke selection.

Calibration tested a bounded shortlist of 31 inputs from the frozen collection,
using four workers and 12-second pilot limits; it was not a full campaign.
Timed-out/partial candidates were excluded from the selection and preserved
as failed pilots, never classified as unsolvable or averaged as successful
searches. Raw pilot logs, manifests and validated profile runs are recorded
under `outputs/performance/profile-calibration/`. Freeze this selection before
optimization; future deliberate selection changes need a new definition version.

The frozen-profile baseline is commit `c7cd597`, with three repetitions on this
host: median **32.43 s**, range **32.14–32.47 s**, including launch and replay.
The table above uses per-instance medians from those repetitions; their summed
search time is **17.66 s**. Every repetition has identical cost sets and work
counts. The largest median sampled peak planner RSS is **489,868 KB**.
Baseline measurements, source provenance and per-instance CSV are under
`outputs/performance/profile-calibration/performance-baseline/`. Use this
profile's own baseline when evaluating future changes.

## Native backend prototype (definition 5)

Definition 5 adds opt-in Fast Downward and Pyperplan LM-cut comparison profiles.
The original `smoke` and `performance` profiles retain their input selection,
configuration and resource limits. Expected numerical costs are unchanged.

Use `smoke-downward-hmax`, `smoke-downward-lmcut` or `smoke-pyperplan-lmcut`
with the dedicated smoke command; their corresponding timing profiles start
with `performance-`. Each contains one configuration and enforces the same
suite deadline. Native profiles require the pinned module to be built first.
See [the backend migration guide](../../docs/fast-downward-backend.md) for build,
validation, provenance and the distinction between native execution and the
future grounding/translation migration.
