# BOAND* development instructions

## Journal development scope

The `codex/journal-development` branch prepares the planner for a new
journal study. The `codex/fast-downward-backend` branch explores a native
Fast Downward backend from that validated journal implementation. The
`icaps2025` tag preserves the published implementation.
Refactoring and interface changes do not need to maintain compatibility with
that implementation. Update affected callers, tests and documentation together.

Use `journal_development` as the default campaign for planner improvements.
Keep the ICAPS campaign definitions and published archive intact. Changes to
planning objectives, solution semantics or scientific evaluation rules must be
explicitly documented and versioned in the new campaign.

## Environment and organization

On `codex/fast-downward-backend`, retain the current backend for controlled
comparisons until the native backend passes correctness validation and review.
Pin the upstream Fast Downward dependency to a specific release and revision.
Evaluate backend migration with hmax separately from switching to LM-cut.
Check translated tasks for unsupported conditional effects and axioms, and
audit pruning assumptions before enabling the inconsistent LM-cut heuristic.
Compare transitions and goal tests across backends and use independent small
task oracles for heuristic admissibility. Record preprocessing, heuristic and
search timings separately where available. Do not merge the migration branch
without an explicit request.

Use `.venv/bin/python`; do not install packages globally.

Keep shared planner, execution and analysis code in `planner/`,
`experiment_support/` and `analysis/`. Keep paper-specific definitions,
analysis rules in `campaigns/<campaign-id>/`.

Keep the preserved 11-domain ICAPS input collection in
`benchmarks/icaps2025/`. The existing unselected `st_blocksworld` and
`st_first_responders` inputs belong in `benchmarks/legacy_extras/`.
New benchmark collections must be separate from the frozen ICAPS inputs.
`journal_tradeoffs` definition 1 is the exploratory FrozenLake benchmark pilot:
19 fixed candidates and two native heuristics, 600 seconds/job, 6,000,000 KB/job
and four workers. Its `smoke` profile checks the three exact examples; its
`pilot` profile evaluates all candidates. The adaptive supplementary collection
is outside that manifest. Neither collection is a finalized paper selection,
and neither replaces the fixed journal development profiles.
Keep historical run paths intact as provenance; verified manifest migration
records support result analysis, not resuming executions under changed paths.

Published archives belong in `results/<campaign-id>/published/`.
Generated runs and analysis belong in ignored `runs/` and `outputs/`.
Reviewed PNG figures referenced by committed reports are an explicit exception:
commit them in report-specific folders under `docs/figures/`, use relative
Markdown links, and record their generated sources and hashes in the figure
manifest. Keep raw measurements, intermediate figures and other generated
formats in ignored artifact directories. After regenerating figures, review
and synchronize the report copies and manifest before committing.

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
optimization per attempt. Use the journal smoke suite as the correctness gate
and the fixed `performance` profile for profiling and timing evaluation. Run the performance
profile with:

    PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_development.smoke --profile performance

It covers 11 instances/11 domains, with 10 solvable instances and 11 emitted
policies; its dedicated command also enforces the 60-second suite deadline.
Keep both selections fixed. Establish a separate repeated baseline for the
performance profile; earlier smoke timing baselines do not apply to new inputs.
Add targeted instances only when the suite cannot clearly
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
after five runs per revision, revert and record the uncertainty, except for the
explicit code-cleanup exception below.

Require 14/14 completed searches and 12/12 solvable instances solved. The two
unsolvable instances must complete with no policies. Require unchanged expected
Pareto cost sets, valid policy replay and relevant tests. Timeouts, crashes,
incomplete searches and incorrect outputs are failures, not unsolvability.
For the performance profile, require 11/11 completed searches, 10/10 solvable
instances solved and all 11 expected policies replayed. Record intentional
changes in search order or work counts.

Record per-instance search times, total profile wall time, expansions,
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

An explicitly justified code cleanup may remain without a demonstrated timing
win after validation and repeated measurements show no substantial aggregate
or per-instance regression. Record the maintainability benefit, timing
uncertainty and reason for retention; do not label it a performance improvement.
This exception does not justify retaining complex algorithmic experiments or
changes with unresolved correctness or substantial regression risk. Evaluate
a requested batch as a whole against its parent, without claiming individual
component gains from the combined result.

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
labels, a per-instance speedup heatmap, and total profile wall time.
Preserve comparable measurements for every attempt so these plots can include
rejected candidates. Coverage is a correctness gate for this suite and a main
performance metric on any later, harder evaluation set.

## Correctness fixes

Evaluate confirmed correctness fixes separately from performance attempts; do
not revert a correct fix merely because timing is unchanged or slower. Use
independent mathematical tests when the historical baseline is buggy. Document
and version changed numerical bounds and record resulting search-work changes.
Journal definition version 2 uses BFS best bounds on cyclic and acyclic graphs;
version 1 and the original baseline can overestimate best costs on cyclic graphs.
Journal definition version 4 adds the fixed performance profile while keeping
version-3 planner semantics and smoke costs unchanged.
Journal definition version 5 adds explicit native-backend and LM-cut comparison
profiles, preserving the version-4 selections, default configuration, expected
numerical costs and resource limits. The native prototype retains Pyperplan
grounding and fact-set states at the search boundary.
Journal definition version 6 adds opt-in `downward-grounded` hmax/LM-cut profiles,
using the pinned Fast Downward parser and relaxed-reachability grounder before
classical SAS simplification. The common Unified Planning negative-condition
compiler and fact-set search boundary remain. Selections, defaults, numerical
costs and limits are unchanged; unreachable grounded operators may be omitted.
Journal definition version 7 adds opt-in `downward-direct` profiles with a
conjunctive dual-rail negative-condition compiler. It preserves `not_` labels
and mirrors grounded effects after resolving aliases. Negative equality and
complement-name collisions fail explicitly. Unified Planning imports are lazy;
legacy preprocessing measurements now include their cold import cost, requiring
fresh controls when comparing preprocessing. Selections and costs are unchanged.
Journal definition version 3 additionally uses reverse goal reachability for
closed-policy properness, correcting false rejections by the trajectory checker.
Future equivalence checks must compare against the corrected parent or an
independent oracle rather than preserve that historical error. Expected solution
costs remain unchanged unless a separately justified correctness finding requires
an explicitly documented revision.

Journal definition version 8 corrects initially satisfied goals: emit the empty
policy with zero best/worst costs without expanding the root. Compare this case
against independent replay, not the buggy historical search. Fixed profile
selections and expected costs remain unchanged.

Journal definition version 9 selects `downward-direct` with hmax for default
smoke/performance profiles. Build the pinned native dependency before running
these commands; do not silently fall back. Use `smoke-pyperplan-hmax` and
`performance-pyperplan-hmax` for legacy comparisons. Standalone CLI defaults and
ICAPS definitions are unchanged. Backend changes need separate timing baselines.

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
On `codex/journal-development` and `codex/fast-downward-backend`, intermediate commits are authorized without
asking each time. Make coherent commits after relevant validation, describe
what changed, and report validation limitations. Do not include unrelated user
changes. On other branches, commit only when explicitly requested.
Tag, push, merge or publish only when explicitly requested.
Keep generated outputs, caches and temporary files out of version control.

## Authorized full ICAPS comparison

`journal_icaps_comparison` definition 1 is the explicitly requested full
pre-merge evaluation: 196 frozen ICAPS inputs, direct FD/hmax and FD/LM-cut,
392 jobs, 600 seconds/job, 6,000,000 KB/job and four workers. Run it alone via
`.venv/bin/python -m campaigns.journal_icaps_comparison.run`; it automatically
replays policies and compares with the published archive. It has no 60-second
suite deadline. Preserve the published campaign and distinguish corrected
semantics/resource limits from historical timing comparisons. Keep planner
source fixed until execution ends; do not merge before reviewing the report.

## Authorized PRP comparison

The requested `journal_prp_comparison` campaign 1 runs the installed PRP on the
196 frozen ICAPS instances with 600 seconds/instance, 6,000,000 KB/job, four
workers and seed 0. Use its dedicated `.run` module, not the BOAND-only executor.
PRP installation lives outside the repository; pin its revision and executable
hashes. Replay exported policies against original PDDL. First-policy coverage
counts only proper strong or strong-cyclic policies; weak/incomplete exports
contribute zero and do not establish unsolvability. It includes valid timeout
incumbents; compare costs to BOAND first policies and to
completed Pareto fronts separately. Treat cyclic worst costs as infinity, never
as a finite ratio. PRP satisficing output carries no BOAND optimality guarantee.
Keep the older run's resource/timing/validation limitations explicit. Do not run
campaigns concurrently; replay uses bounded jobs with the same concurrency cap.
