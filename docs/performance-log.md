# BOAND* performance experiments

## Round 1: journal smoke suite

The fixed suite contains 14 instances in the 11 ICAPS domains. Comparisons use
`PYTHONHASHSEED=0`, four workers, 6,000,000 KB of virtual memory per planner,
and the campaign's unchanged BOAND bw configuration. Each unprofiled revision
is measured three times, extended to five if needed. Successful runs require
14 completed searches, 12 solved instances, matching Pareto costs and policy
replay. Profiled runs are excluded from timing comparisons.

Raw measurements and profiling scripts are retained in
`outputs/performance/round1/`; planner provenance remains in
`runs/journal_development/`. Per-instance search times are summarized by their
median; aggregate speedups use the geometric mean of baseline/candidate ratios.
Peak planner RSS is sampled from Linux `/proc` high-water marks and is a lower
bound when a process exits between samples. Virtual memory remains capped by
the campaign. Total suite times include execution and validation; external
elapsed times additionally include interpreter startup and measurement overhead.

### Original baseline: `0d570b3`

Three unprofiled runs: suite median **33.920 s**, range **33.750–34.086 s**;
sum of per-instance median search times **39.229 s** (jobs run concurrently).
Each run completed 14 searches, solved 12 instances and replayed 14 policies.
Artifacts: `outputs/performance/round1/baseline/`.

Baseline cProfile runs on FrozenLake `p07` and Tireworld-truck `p6` identified
repeated hmax evaluations as the principal bottleneck; FrozenLake additionally
spent substantial time recomputing ancestor costs. Artifacts:
`outputs/performance/round1/profiles-baseline/`.

### Attempt 1: cache classical heuristic values — KEEP

- Parent: `0d570b3`; candidate: `a5a7b36`.
- Hypothesis: policies repeatedly evaluate hmax/lmcut for the same immutable
  state, although these supported heuristics depend only on state and task.
- Change: task-local LRU cache, bounded to 65,536 states. No dependency submodule
  changes. Zero and infinite estimates are cached normally.
- Three candidate runs: suite median **23.226 s**, range **23.222–23.937 s**;
  aggregate search speedup **5.001×** over both parent and original baseline;
  summed median search time **10.107 s**; suite speedup **1.460×**.
- All 14 instances improved in median search time. All three runs completed
  14 searches, solved 12 instances and replayed 14 policies. Non-time search
  statistics match the original baseline. Cache isolation, bounded eviction,
  zero and infinite estimates pass targeted tests.
- Decision: retain; large repeatable improvements with bounded cache storage.
  Sampled memory data and all per-instance timings are in
  `outputs/performance/round1/attempt1/`; post-change profiles are in
  `outputs/performance/round1/profiles-attempt1/`.

### Attempt 2: cache ancestor walks during recomputation — KEEP

- Parent: `a5a7b36`; candidate: `3cc1ec7`.
- Hypothesis: convergent/cyclic policy traversal repeatedly walks unchanged
  ancestor chains. Cache best/worst costs only within one recomputation, clearing
  the corresponding cache whenever any ancestor changes.
- Three candidate runs: suite median **21.233 s**, range **20.902–21.537 s**;
  aggregate search speedup **1.321×** over parent, **6.606×** over original;
  summed median search time **6.074 s**.
- Every run completed 14 searches, solved 12 instances and replayed 14 policies;
  all non-time statistics match baseline. Targeted convergence/self-loop tests
  and 500 seeded cyclic/convergent differential comparisons against original
  `update_g_brute` passed with identical ancestor maps and cycle flags.
- Four-worker regressions: Elevators +0.039 s (12%), Islands +0.113 s (15%).
  Three alternating isolated runs per revision on these same smoke instances
  reduced the differences to +0.011 s (3.4%) and +0.005 s (0.6%). Profiles show
  cache construction overhead; scheduling/contention likely amplifies the
  parallel-run differences. These small absolute costs are accepted in return
  for 2.0–2.5× gains on Beam-walk, Chain-of-rooms, Doors and FrozenLake cases.
- Decision: retain. Artifacts: `outputs/performance/round1/attempt2/`,
  `profiles-attempt2-small/`, `ancestor-probe/`, and `ancestor-equivalence.txt`.

### Attempt 3: cache grouped state successors — KEEP

- Parent: `3cc1ec7`; candidate: `45225ff`.
- Hypothesis: expansions revisit the same states, repeatedly checking applicable
  operators, applying effects, grouping outcomes and allocating operator sets.
- Change: task-local LRU cache of grouped successors/operator sets, bounded to
  65,536 states. Shared sets are read-only after construction; action order and
  original construction sequence are preserved.
- Three candidate runs: suite median **21.068 s**, range **20.769–21.317 s**;
  aggregate search speedup **1.068×** over parent, **7.053×** over original;
  summed median search time **5.667 s**. Tireworld-truck and Modified First
  Responders improve by approximately 30%; the slowest median regression is
  under 2% and affects sub-0.1-second cases.
- All three runs completed 14 searches, solved 12 instances and replayed 14
  policies. All non-time statistics match baseline. Tests preserve no-op
  outcomes, distinguish nondeterministic actions, retain operator order and
  reject inapplicable actions.
- Sampled median peak RSS on Tireworld-truck falls by **21,532 KB** versus
  parent, consistent with sharing operator sets across policies. Some domains
  add roughly 0.4–1.2 MB of cache storage; other domains use less memory.
- Decision: retain. Per-instance ranges, memory and raw data:
  `outputs/performance/round1/attempt3/`. Total suite ranges overlap parent:
  claim the clearer per-instance search improvements, not a precise wall-time
  improvement from this attempt alone.

### Attempt 4: eliminate discarded policy-copy allocations — REVERT

- Parent: `45225ff`; candidate: `5e7497b`; reverted in `b06dd70`.
- Hypothesis: each policy copy constructs five empty containers and default
  fields that are immediately replaced. Allocate the object without calling
  its initializer, then copy every field exactly as before.
- Initial three-run aggregate gain was 1.018×, so both parent and candidate
  were extended to five runs. Final aggregate search speedup was **1.003×**
  over parent, summed median search time **5.607 s** versus **5.627 s**;
  suite medians **21.047 s** versus **21.208 s**, with overlapping ranges.
- All five candidate runs passed completion, cost and policy checks, and all
  non-time statistics match baseline. A copy-isolation test passed. An isolated
  100,000-copy microbenchmark repeated five times showed roughly **1.50×**
  primitive speedup, but no clear benefit on the agreed smoke evaluation.
- Decision: revert under the five-run inconclusive-result rule. Artifacts:
  `outputs/performance/round1/attempt4/` and supplementary parent measurements
  in `attempt3-extra/`. For the supplementary parent runs, HEAD remained
  `5e7497b` and `planner/policy.py` was restored byte-for-byte from `45225ff`;
  run provenance records the inverse patch. Other differences were docstrings
  and documentation. Original three-run records and both extra runs remain
  available; the combined attempt3 summary now uses five runs.

### Attempt 5: share frontier evaluation across bounds — KEEP

- Effective parent: `b06dd70` (attempt4 reverted, numerically equivalent to
  `45225ff`); candidate: `067b28d`. Compared with the five attempt3 measurements.
- Hypothesis: MinSum, MaxSum and Delta each construct the same frontier and
  evaluate classical heuristic values separately, even with state caching.
- Change: reuse the existing joint `compute_f_value` calculation for this exact
  heuristic combination. Other combinations retain their separate evaluators.
- Five candidate runs: suite median **21.067 s**, range **20.832–21.402 s**;
  aggregate search speedup **1.047×** over effective parent, **7.422×** over
  original; summed median search time **5.432 s**. Largest search regressions
  versus parent are approximately 1.5% on Beam-walk and 0.3% on Doors, while
  Elevators, First Responders and Tireworld-truck improve by 8–14%.
- Bootstrap of whole-run repetitions, preserving correlation across instances
  (4,000 samples, seed 0), gives a percentile 95% aggregate speedup interval
  **1.026–1.126×** versus parent. Attempt4's corresponding interval spans 1
  (**0.987–1.081×**), supporting its inconclusive classification. These intervals
  describe this small measured sample, not performance on unseen problems.
- All five candidate runs completed 14 searches, solved 12 instances and
  replayed 14 policies. All statistics rows, including intermediate solutions,
  match baseline except elapsed time. Joint-bound tests cover ordinary policies,
  cycles, deadlock rejection, infinite heuristic values and empty frontiers.
- Decision: retain. Artifacts: `outputs/performance/round1/attempt5/`.

## Round 1 outcome

Four changes retained; attempt4 reverted. Work stopped after the five agreed
attempts. Source changes and the revert are separate commits; history was not
rewritten. Nothing was pushed or tagged.

| Revision / attempt | Runs | Decision | Search speedup vs parent | Search speedup vs original | Median suite time (s) |
| --- | ---: | --- | ---: | ---: | ---: |
| Original `0d570b3` | 3 | Reference | 1.000× | 1.000× | 33.920 |
| 1: classical heuristic cache | 3 | Keep | 5.001× | 5.001× | 23.226 |
| 2: ancestor walk cache | 3 | Keep | 1.321× | 6.606× | 21.233 |
| 3: grouped successor cache | 5 | Keep | 1.073× | 7.091× | 21.208 |
| 4: cheaper policy copying | 5 | Revert | 1.003× | 7.112× | 21.047 |
| 5: joint bound evaluation | 5 | Keep | 1.047× | 7.422× | 21.067 |

The attempt3 table uses the supplementary five-run comparison; its entry above
retains the original three-run decision evidence. Attempt5 compares with
attempt3 because attempt4 was reverted. Faster search does not guarantee a
measurable suite-wall improvement for every small individual change.

- Final suite time improves **1.610×**, or **37.9% less wall time**, versus
  original. Sum of per-instance median search times falls from **39.229 s** to
  **5.432 s** (these are concurrent jobs, so the sum is not suite wall time).
- All **24 measured smoke runs** have 14 completed searches, 12 solved instances
  and 14 valid policies. Every non-time statistics row matches original,
  including expansions, generations, iterations and maximum open-list size.
- Maximum per-instance median sampled peak planner RSS falls from **185,848 KB**
  to **164,828 KB** (roughly 181 to 161 MiB), on Tireworld-truck. Cache memory is
  bounded by state count, not bytes; larger tasks still need independent memory
  evaluation under the 6,000,000 KB virtual-memory cap.
- Final full test suite: **44 tests passed**. Formatting checks passed. Published
  definitions, benchmark contents, input hashes and published results were not
  changed. All measured manifests use the same worker count, limits and seed.
- Plot-ready data: `outputs/performance/round1/round-summary.csv` and
  `outputs/performance/round1/per-instance.csv`, with the JSON equivalents and
  raw per-run records retained. The reverted candidate remains represented.

Final profiles (`outputs/performance/round1/profiles-final/`) identify ancestor
trajectory traversal as the remaining principal FrozenLake search cost. Policy
extension and joint bound evaluation remain visible in Tireworld-truck. Imports,
preprocessing and sequential policy validation now account for much of total
suite time. Profiling timings are diagnostic and excluded from comparisons.

An existing selector issue was observed: `LargestGStateSelector` builds a heap
but selects the last iterated state. This round preserves that behavior and all
other search ordering; correcting it is a separate, explicitly evaluated
algorithm change. Results here establish improvements on the fixed smoke
suite on this host, not coverage or performance claims for a larger campaign.

## Round 2: attempts 6–10

Starting revision: `e2ad72d`, retaining attempts 1, 2, 3 and 5. The original
baseline remains `0d570b3`; its measurements are copied unchanged into
`outputs/performance/round2/baseline/`. Fresh starting measurements are in
`outputs/performance/round2/round2-start/`: three runs, median suite time
**20.960 s**, range **20.609–23.223 s**.
Inputs, limits, four workers and seed 0 remain fixed. The measurement and
bootstrap scripts use the round1 methods. Comparisons use fresh immediate
parent measurements and the fixed original baseline; artifacts stay under
`outputs/performance/round2/` and `runs/journal_development/`.

### Attempt 6: reuse action outcomes in ancestor traversal — KEEP

- Parent: `e2ad72d`; candidate: `ae8fbbd`.
- Hypothesis: convergent trajectories reapply the same fixed policy action to
  the same state. Cache those successor sets within one ancestor recomputation.
  The cache is discarded afterward. The propagation phase still uses fresh
  sets wherever it mutates the successor set.
- Three runs: aggregate search speedup **1.105×** over parent,
  **8.060×** over original; suite median
  **21.245 s**, summed median search time **4.484 s**.
- Whole-run bootstrap 95% interval: **1.058–1.181×** over parent. Chain-of-rooms,
  Doors and FrozenLake p07 improve by 44–60%. Elevators slows about 6% (under
  0.02 s); local cache allocation/scheduling overhead is accepted for the
  larger gains. Remaining regressions are below 2% on very short cases.
- All three runs completed 14 searches, solved 12 instances and replayed 14
  policies. Non-time final statistics match original. Targeted reuse, convergence
  and cycle tests pass; 500 seeded differential graph checks match original
  ancestor maps and cycle flags. Artifacts: `outputs/performance/round2/attempt6/`
  and `ancestor-equivalence-attempt6.txt`.
- Decision: retain, with bounded lifetime storage proportional to policy size.

### Attempt 7: immutable trajectory tuples — REVERT

- Parent: `ae8fbbd`; candidate: `546d243`; reverted after five-run evaluation.
- Change: concatenate immutable trajectory tuples instead of copying/appending
  lists, retaining exactly the original traversal order and cycle slices.
- Five runs per revision: aggregate search speedup **1.027×** over parent;
  bootstrap 95% interval **0.989–1.059×** includes no improvement. Suite medians
  **22.823 s** versus **21.650 s**, with substantial run variability (parent
  range 21.071–30.038 s, candidate 20.959–25.421 s). No observations excluded.
- All searches, costs and policy replay pass; non-time statistics match original.
  Targeted tests and 500 seeded differential graph checks retain exact ancestor
  maps/cycle flags. Decision: revert as inconclusive under the agreed rule.
- Artifacts: `outputs/performance/round2/attempt7/`, `attempt6-extra/` and
  `ancestor-equivalence-attempt7.txt`. Supplementary parent runs used HEAD
  `546d243` with `planner/search.py` restored exactly from `ae8fbbd`; provenance
  captures the inverse patch. The combined attempt6 summary now uses five runs;
  its entry above preserves the initial three-run keep evidence.

### Attempt 8: fixed policy fields in slots — KEEP (memory benefit)

- Effective parent: `747b8a3` (attempt7 reverted, equivalent to `ae8fbbd`);
  candidate: `c984acc`. Compared with the five attempt6 measurements.
- Change: eight explicit `__slots__` instead of a per-instance attribute dict.
  Fields, copy behavior and flags retain their values. Dynamic extra attributes
  are no longer supported; no repository caller relied on them.
- Five runs: aggregate search speedup **1.010×**, bootstrap interval
  **0.992–1.037×**. No proven search-speed gain. Median suite time **22.922 s**
  versus parent **21.650 s**; substantial wall-time variability remains.
- Policy object plus its attribute dict reduces from **192 to 96 bytes**,
  excluding unchanged referenced containers. Five largest-case peak RSS samples
  are **162,024–162,560 KB**, versus **163,588–164,420 KB** for parent; medians
  **162,256 vs 163,964 KB**, saving **1,708 KB**. The ranges do not overlap.
- All five runs pass completion, cost and replay checks; non-time statistics
  match original. Copy-isolation/flag tests pass. Decision: retain the clear,
  repeatable memory reduction from a small representation change, without
  claiming a timing win. Artifacts: `outputs/performance/round2/attempt8/` and
  `policy-object-size-attempt8.txt`.
