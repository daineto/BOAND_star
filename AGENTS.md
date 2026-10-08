# BOAND* development instructions

## Journal development scope

This branch, `codex/journal-development`, prepares the planner for a new
journal study. The `icaps2025` tag preserves the published implementation.
Refactoring and interface changes do not need to maintain compatibility with
that implementation. Update affected callers, tests and documentation together.

Use `journal_development` as the default campaign for planner improvements.
Keep the ICAPS campaign definitions and published archive intact. Changes to
planning objectives, solution semantics or scientific evaluation rules must be
explicitly documented and versioned in the new campaign.

## Environment and organization

Use `.venv/bin/python`; do not install packages globally.

Keep shared planner, execution and analysis code in `planner/`,
`experiment_support/` and `analysis/`. Keep paper-specific definitions,
analysis rules in `campaigns/<campaign-id>/`.

Published archives belong in `results/<campaign-id>/published/`.
Generated runs and analysis belong in ignored `runs/` and `outputs/`.

Use campaign-aware commands. Consult `docs/campaigns.md` when adding or
revising a campaign; use the README for setup and researcher commands.

## Validation

Validate the behavior affected by the change.

- **Planner or execution changes:** run the affected campaign's smoke
  profile before and after relevant changes. Inspect raw output, errors,
  completion states and solution costs; replay policies when appropriate.
- **Campaign definition changes:** compare dry-run manifests for input
  selection, configurations, commands and resource limits. Run the smoke
  profile if execution behavior is affected.
- **Analysis changes:** regenerate affected figures and tables, compare
  numerical data and selection rules, and check the affected analysis commands.
- **Archive relocation:** verify file inventories and content hashes,
  update references, and confirm analysis equivalence. Do not rerun planners.
- **Documentation-only changes:** check referenced paths and commands.
  Do not rerun experiments.

For current journal planner development, run before and after relevant changes:

    PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_development.smoke

It covers 14 instances from the 11 ICAPS domains, including unsolvable,
multi-solution and cyclic-policy cases. It uses four workers and 6,000,000 KB
of virtual memory per job, and enforces a 60-second suite deadline including
cost checks and policy replay. See `campaigns/journal_development/README.md`.

For checks specifically concerning the historical ICAPS 2025 smoke profile:

    PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run icaps2025 --profile mini --workers 2

It runs one configuration across 31 FrozenLake instances and takes several
minutes. Use identical seeds and settings for controlled comparisons.

Run relevant tests. A dry run validates scheduling, not planner success.
Launch a full experimental campaign only when requested.

For performance comparisons, use identical inputs, configurations and seeds,
repeat measurements, and report search time separately from total suite time.
Compare search work counts alongside timing. Keep the smoke selection fixed as
optimizations make it faster. Do not change expected costs to hide a regression;
investigate mismatches and document any intentional semantic revision.

## Performance improvement loop

Use profiling to identify bottlenecks, including search code, data structures
and preprocessing. State a concrete hypothesis and implement one focused
optimization per attempt. Use the existing journal smoke suite for profiling
and evaluation. Add targeted instances only when the suite cannot clearly
measure a particular effect; do not launch a full campaign without a request.

Establish and retain a fixed original baseline revision and repeated
measurements before the first attempt. Compare each candidate with both that
baseline (cumulative progress) and its immediate parent (individual effect).
Use identical inputs, configurations, resource limits, worker counts and
`PYTHONHASHSEED=0`. Measure unprofiled runs for performance comparisons;
profiling runs diagnose bottlenecks and are not timing baselines.

Start with three runs per compared revision; extend to five if results are
noisy. Reuse recorded baseline measurements only while comparison conditions
remain equivalent. Stop a candidate evaluation when correctness fails or
measurements establish a clear benefit or loss. If results remain inconclusive
after five runs per revision, revert and record the uncertainty.

Require 14/14 completed searches and 12/12 solvable instances solved. The two
unsolvable instances must complete with no policies. Require unchanged expected
Pareto cost sets, valid policy replay and relevant tests. Timeouts, crashes,
incomplete searches and incorrect outputs are failures, not unsolvability.
Record intentional changes in search order or work counts.

Record per-instance search times, total smoke-suite wall time, expansions,
generations, peak memory per planner process, completed searches, solved
instances and correctness outcomes. Use median search times across repetitions.
The primary aggregate is the geometric mean of per-instance speedups, defined
as original-baseline time divided by candidate time. Report variability and
individual regressions; do not include failed or timed-out cases in a speedup
average as if they were successful measurements. Mark coverage failures
explicitly. Report measurement limitations when a metric is unavailable.

Keep clear, repeatable improvements with acceptable complexity and no
substantial unexplained regressions. Simpler changes may justify smaller gains;
more complex changes need stronger evidence. Revert losses, correctness
failures and unresolved results. Use separate candidate commits and revert
commits for rejected committed changes; never rewrite history.

Maintain `docs/performance-log.md` with an entry for every attempt: hypothesis,
implementation, original baseline and parent/candidate revisions, measurement
settings, raw-artifact locations, results, correctness checks, limitations and
the keep/revert decision. Keep raw profiles and measurements in ignored
`outputs/` and planner runs in ignored `runs/`, preserving rejected attempts'
evidence as well as successful attempts'.

Work in rounds of at most five optimization attempts, then review cumulative
gains, regressions and remaining bottlenecks with the user before starting
another round. Stop early if three consecutive well-motivated attempts fail to
show repeatable improvement and profiling offers no promising next target.

After a significant number of attempts, prepare comparison plots when
requested: aggregate speedup across attempts with variability and keep/revert
labels, a per-instance speedup heatmap, and total smoke-suite wall time.
Preserve comparable measurements for every attempt so these plots can include
rejected candidates. Coverage is a correctness gate for this suite and a main
performance metric on any later, harder evaluation set.

## Resources and reproducibility

This machine has 32 GB of RAM. Journal development runs use 6,000,000 KB of
virtual memory per job and at most four concurrent planner jobs. ICAPS runs
use 8,000,000 KB per job and at most two concurrent planner jobs. Do not run
the two campaigns concurrently. Other resource limits or higher concurrency
require explicit user instructions.

Never silently change experimental or analysis semantics. Distinguish
structural refactoring from infrastructure fixes and planner changes.

Do not alter benchmarks, published results or frozen input hashes merely
to obtain agreement. Published archives may move with verified identical
contents. Preserve published definitions; explicitly version scientific
changes.

Report discrepancies and validation limitations. Exact cross-machine
timing or completion agreement is not required for a structural refactor.

## Git

Do not rewrite history or amend existing commits.
On `codex/journal-development`, intermediate commits are authorized without
asking each time. Make coherent commits after relevant validation, describe
what changed, and report validation limitations. Do not include unrelated user
changes. On other branches, commit only when explicitly requested.
Tag, push, merge or publish only when explicitly requested.
Keep generated outputs, caches and temporary files out of version control.
