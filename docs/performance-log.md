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


### Attempt 9: remove discarded selector heap — REVERT

- Parent: `c984acc`; candidate: `af0bf69`; revert: `336638e`.
- Hypothesis: the largest-g selector builds a heap but returns the last iterated
  pending state. Remove unused heap construction and ancestor-cost calls while
  preserving that historical choice exactly; this does not fix the selector.
- Five runs: search speedup **1.018×**, bootstrap 95% interval
  **0.946–1.035×**. Suite median **21.957 s**. Inconclusive; reverted.
- All five runs complete 14 searches, solve 12 instances and replay 14 policies;
  non-time final statistics match original. Selector preservation tests pass.
  Artifacts: `outputs/performance/round2/attempt9/`. The revert also removed the
  previously committed attempt8 documentation; that entry is restored here.


### Attempt 10: linear Delta bound without sorting — REVERT

- Effective parent: `336638e` (attempt9 reverted, planner equivalent to
  `c984acc`); candidate: `6ab1ad1`; revert: `9265b4f`.
- Hypothesis: sorted nondecreasing h[i] + i reaches its maximum at the last
  index. Replace sorting with max(h) + n - 1 in both Delta implementations,
  preserving zero for empty frontiers. Independent seeded-vector checks compare
  with the historical sorted formula, including ties and infinity.
- Five runs: search speedup **1.007×**, bootstrap interval **0.959–1.035×**.
  Median suite **22.595 s**, range **21.156–31.102 s**. No measurements excluded.
  Correctness checks pass, but speed remains inconclusive; reverted.
- Artifacts: `outputs/performance/round2/attempt10/`. The mathematical simplification
  may help larger frontiers; the agreed smoke gate does not justify retaining it.

### Round 2 outcome

| Attempt | Change | Search speedup over parent | Decision |
| --- | --- | ---: | --- |
| 6 | Reuse action outcomes in ancestor traversal | 1.109× | Keep |
| 7 | Immutable trajectory tuples | 1.027× | Revert |
| 8 | Policy slots | 1.010× | Keep for memory |
| 9 | Remove discarded selector heap | 1.018× | Revert |
| 10 | Delta bound without sorting | 1.007× | Revert |

All candidates have five measurements; the fresh round-start reference has
three. Attempt6's extended five-run interval is **1.065–1.173×**; its initial
three-run keep evidence is retained above. Attempt7 revert commit: `747b8a3`.
The final planner source matches measured attempt8 byte for byte.

- Retained code: **1.120×** geometric-mean search speedup over the fresh round2
  start and **8.174×** over fixed original baseline `0d570b3`. Summed per-instance
  median search time **4.449 s**. Largest-case median peak RSS **162,256 KB**.
- Final measured suite median **22.922 s**, versus original **33.920 s**. Whole
  wall time is noisy; this round does not establish an additional wall-time win.
  All observed suites finish within 60 s. Small search samples and this compact
  suite limit claims about larger problems or other configurations.
- **28 controlled runs** (three round-start plus five per candidate) all complete
  14 searches, solve the same 12 instances, and validate 14 policies. Every raw
  intermediate and final non-time statistics row matches original. Separate
  supplementary attempt6 raw records are preserved without double-counting.
- All manifests retain frozen inputs, seed 0, 4 workers, 6,000,000 KB and 30 s/job.
  Final **46 tests pass**. Logs: `outputs/performance/round2/tests-final.log`,
  `statistics-equivalence.txt`, `resource-and-source-validation.txt`.
- Plot-ready aggregate/per-instance CSV and JSON: `outputs/performance/round2/`
  `round-summary.*` and `per-instance-summary.*`; rejected candidates are included.
  Raw reports preserve work counts, costs, timings and sampled process memory.
- Final diagnostic profiles in `outputs/performance/round2/profiles-final/` are
  excluded from timing comparisons. FrozenLake ancestor recomputation remains
  the main search target; Tireworld-truck spends time on policy bounds. Imports,
  preprocessing and serial policy replay limit whole-suite gains. The historical
  largest-g selector behavior remains unchanged and could be studied separately
  as an intentional search-order change.

Stopped after the requested five attempts; no further round launched.


## Round 3: ancestor tracking and cycle detection

Original baseline remains `0d570b3`; round-start revision is `97404f2`.
Fresh reference: three smoke runs, same fixed 14 instances/11 domains,
seed 0, four workers, 6,000,000 KB and 30 s per planner job, 60 s suite limit.
Artifacts and measurement scripts: `outputs/performance/round3/`; raw planner
runs: `runs/journal_development/`. Whole-run bootstrap uses 4,000 samples,
seed 0. Exact ancestor-map checks compare against original implementation.

### Attempt 11: cache ancestor-chain prefixes — REVERT

- Parent: `97404f2`; candidate: `cd8b609`; revert: `2fd9f16`.
- Hypothesis: cache every intermediate ancestor cost rather than just the queried
  state within recomputation, clearing on any corresponding parent-map mutation.
- Three runs: search speedup **0.946×**, bootstrap interval **0.926–0.961×**.
  Doors and FrozenLake p07 slow substantially (speedups 0.585× and 0.606×),
  despite Beam-walk improving 1.601×. Cache rebuilding overhead dominates.
- Costs agree on 1,000 random parent maps; exact ancestor maps/cycle flags agree
  on 500 cyclic/convergent graphs. Targeted tests pass. All smoke runs pass
  completion, expected Pareto costs and policy replay, with unchanged final
  non-time work statistics. Decision: revert a clear loss after three runs.
- Raw measurements: `outputs/performance/round3/attempt11/`; diagnostic scripts
  `check-cost-helper.py`, `apply11.py` preserve the rejected candidate approach.


### Attempt 12: skip unchanged-parent comparisons — KEEP

- Effective parent: `2fd9f16` (planner equivalent to `97404f2`);
  candidate: `78de6ee`. Compared with fresh round-start measurements.
- Hypothesis: when the candidate ancestor already equals the recorded parent,
  both compared costs are equal; avoid both ancestor walks and cache lookups.
  Other comparisons and parent assignments retain their order.
- Three runs: search speedup **1.079×**, bootstrap interval **1.053–1.106×**.
  Every instance median improves or stays effectively equal; improvements include
  Elevators 1.204×, Chain-of-rooms 1.196× and FrozenLake motivating 1.276×.
- Exact ancestor maps/cycle flags match original on 500 seeded graphs; targeted
  tests pass. All runs meet completion, expected cost and policy replay gates;
  non-time final statistics match original. Decision: retain the clear gain.
- Artifacts: `outputs/performance/round3/attempt12/` and
  `ancestor-equivalence-attempt12.txt`.


### Attempt 13: share trajectory prefixes across siblings — REVERT

- Parent: `78de6ee`; candidate: `ef9bf22`; revert: `06ef31c`.
- Hypothesis: build one read-only extended ancestor list per expanded trajectory
  rather than separately copying it for every noncyclic successor.
- Five runs per revision: speedup **1.014×**, bootstrap interval
  **0.965–1.046×**. Median suite **22.669 s** versus parent **21.447 s**;
  candidate wall range **21.265–31.783 s**. No observations excluded.
- Exact ancestor maps/cycle flags agree on 500 graphs; targeted tests and all
  completion/cost/replay gates pass, with unchanged final work statistics.
  Decision: revert unresolved timing; peak memory does not establish a clear
  compensating improvement.
- Artifacts: `outputs/performance/round3/attempt13/`, `attempt12-extra/`,
  `ancestor-equivalence-attempt13.txt`. Supplementary parent runs restored
  `planner/search.py` exactly from `78de6ee` under HEAD `ef9bf22`, recording the
  inverse patch and source variant. Combined attempt12 now has five records:
  speedup **1.088×**, interval **1.054–1.107×** over the three round-start runs.
  Attempt12's initial three-run keep evidence above is preserved.


### Attempt 14: streamline cycle-aware cost walks — REVERT

- Effective parent: `06ef31c` (planner equivalent to `78de6ee`);
  candidate: `b427134`; revert: `b079381`.
- Hypothesis: bind the parent dictionary once and detect repeated current states
  before stepping, avoiding terminal-sentinel insertion in the visited set.
- Five runs: speedup **0.996×**, bootstrap interval **0.983–1.022×**.
  Median suite **22.516 s**. No repeatable gain; reverted.
- 1,000 random cyclic/acyclic/missing parent maps agree with original worst-cost
  walks; 500 graph recomputations preserve exact ancestors and cycle flags.
  Targeted tests and all smoke correctness/coverage gates pass; final work
  statistics remain unchanged.
- Artifacts: `outputs/performance/round3/attempt14/`,
  `worst-walk-equivalence-attempt14.txt`, `ancestor-equivalence-attempt14.txt`.


### Attempt 15: reuse outcomes during cycle propagation — REVERT

- Effective parent: `b079381` (planner equivalent to `78de6ee`);
  candidate: `3a7e86f`; revert: `4393130`.
- Hypothesis: propagation from loopy states reapplies actions already visited
  during trajectory enumeration. Reuse cached outcomes, taking a separate
  difference set to keep the cached set read-only.
- Five runs: speedup **0.994×**, bootstrap interval **0.925–1.024×**.
  Median suite **21.281 s**. Unresolved timing; reverted under the agreed rule.
- Exact ancestor maps/cycle flags match original on 500 integer-state and 500
  frozenset-state graphs. A targeted cycle-to-goal test confirms outcome reuse
  and unchanged finite best/infinite-cycle worst costs. All smoke correctness
  gates pass; non-time final statistics remain identical.
- Artifacts: `outputs/performance/round3/attempt15/`,
  `ancestor-equivalence-attempt15.txt`, `frozenset-equivalence-attempt15.txt`.
  Small cyclic cases limit how clearly this suite measures propagation savings;
  no larger-campaign benefit is claimed.


### Round 3 outcome

| Attempt | Change | Search speedup over parent | Decision |
| --- | --- | ---: | --- |
| 11 | Cache ancestor-chain prefixes | 0.946× | Revert, regression |
| 12 | Skip comparisons for unchanged parents | 1.088× | Keep |
| 13 | Share trajectory prefixes across siblings | 1.014× | Revert, inconclusive |
| 14 | Streamline cycle-aware cost walks | 0.996× | Revert, inconclusive |
| 15 | Reuse action outcomes during cycle propagation | 0.994× | Revert, inconclusive |

The retained planner source equals the measured attempt12 source byte for byte.

- **1.088×** aggregate search speedup over the fresh round start, **8.743×** over
  original `0d570b3`. The extended five-run keep interval is **1.054–1.107×**
  against three round-start runs. Summed median search time **4.130 s**.
- Median suite **21.447 s** (range **20.477–22.358 s**), versus fresh parent
  **23.185 s** and original **33.920 s**. These are observed wall medians;
  scheduling/import/preprocessing/replay variability limits timing attribution.
  Every controlled suite finishes within 60 s (maximum **31.783 s**).
- Final per-instance medians improve in 13 of 14 cases. The exception is
  st_tires p08: **0.170285 s** versus **0.164210 s**, about 3.7% or 6 ms slower.
  This small regression is accepted alongside gains of 20–27% on several cases.
  No search-order or solution semantics changed. Largest median sampled peak
  RSS **162,676 KB**; no additional memory improvement is claimed this round.
- **26 controlled runs**: 3 reference, 3 attempt11 and 5 each attempt12–15.
  All complete 14 searches, solve the expected 12 cases and replay 14 policies.
  Every intermediate and final non-time statistics row matches original.
  Inputs, configuration, four workers, 6,000,000 KB, 30 s/job and seed 0 remain
  fixed. Supplementary parent records are counted once.
- Final **46 tests pass**. The retained code also matches exact ancestor maps
  and cycle flags on 500 frozenset-state graphs. Evidence:
  `outputs/performance/round3/tests-final.log`, `statistics-equivalence.txt`,
  `resource-and-source-validation.txt`, `frozenset-equivalence-final.txt`.
- Plot-ready aggregate/per-instance CSV and JSON include all five candidates in
  `outputs/performance/round3/round-summary.*` and `per-instance-summary.*`.
  `retained-summary.json` records the final comparison; raw reports retain work
  counts, expected costs, replay outcomes, timings and sampled process memory.
- Diagnostic final profiles use two workers, the same 6,000,000 KB/job and 30 s
  timeout, and are excluded from timing comparisons. FrozenLake best/worst-cost
  walk calls fall from **116,710/158,474** in round2 to **89,249/120,700**;
  Tireworld-truck from **45,997/49,321** to **31,822/35,146**.
  See `profiles-final/` and `ancestor-walk-profile-counts.json`.
- Ancestor recomputation still dominates FrozenLake search. A larger future
  target is replacing trajectory enumeration with graph-based ancestor bounds
  and cycle analysis, with explicit checks for changes to ancestor tie choices,
  cycle-cost propagation, search order and proper-policy decisions. The current
  round preserves all of those behaviors; failed local optimizations are logged.

Stopped after five attempts. No further round or full campaign launched.


## Round 4: graph-based ancestor bounds and cycles

Round-start `0e992c5`; original baseline `0d570b3`. Three fresh reference runs,
fixed smoke instances/configuration, seed 0, four workers, 6,000,000 KB, 30 s/job
and 60 s suite budget. Artifacts: `outputs/performance/round4/` and raw runs in
`runs/journal_development/`. Same median/geometric-mean and 4,000-sample whole-run
bootstrap methods as earlier rounds.

The full breadth-first best-bound prototype disagreed with original on 40 of
1,000 random cyclic graphs: original best-parent relaxation can overestimate
shortest paths. Worst bounds and cycle flags agree throughout. The prototype is
not retained; this performance round preserves historical cyclic best costs.
Evidence: `full-graph-prototype.py`, `prototype-cost-differential.json` and
`prototype-cost-discrepancy.log`. Correcting those bounds requires a separate,
explicit correctness/scientific decision; expected costs were not edited.

### Attempt 16: topological worst bounds and cycle analysis — KEEP

- Parent `0e992c5`; candidate `1a1661e`.
- Build the reachable policy graph once. Kahn's traversal computes longest
  finite bounds; its residue contains cycles and their descendants. Give every
  residual node a residual predecessor, retaining the CYCLE_COST representation.
  Historical best-parent relaxation uses the same traversal order on cached
  graph outcomes, without worst-ancestor walks or cycle-path enumeration.
- Three runs: aggregate search speedup **1.104×**, bootstrap interval
  **1.094–1.128×**. Beam-walk improves 1.762×, Chain-of-rooms 1.406×,
  Doors 1.372×, FrozenLake p07 1.208×. Mod-first-responders slows 14%; smaller
  regressions on other cases are under 2%. The graph-construction overhead is
  accepted for the repeatable aggregate gain and larger-instance improvements.
- All smoke correctness gates pass; final non-time statistics match original.
  Costs/cycle flags agree on 1,000 random frozenset-state policy graphs. Parent
  tie choices may change, so equivalence checks compare numerical bounds rather
  than require identical predecessor identities. An independent path-enumeration
  oracle checks worst bounds on 100 small graphs, including cycle descendants
  and finite branches. A new fixture initially used a nonexistent parent edge;
  corrected in `cfcdf6d` without a planner fix.
- Artifacts: `outputs/performance/round4/attempt16/`,
  `cost-equivalence-attempt16.txt`; tests in `tests/test_policy_graph.py`.


### Attempt 17: breadth-first best bounds for DAGs — KEEP

- Parent `1a1661e`; candidate `cfcdf6d`.
- Use already-computed BFS predecessors on acyclic policy graphs; keep the
  historical best-parent relaxation only when the graph has cycles.
- Three runs: speedup **1.088×**, bootstrap interval **1.064–1.097×**.
  Doors improves **2.555×**, FrozenLake p07 **1.136×**. Elevators slows about 15%
  (0.2715 vs 0.2312 s) relative to attempt16, but is close to round start
  (0.2684 s). This small absolute timing regression is accepted alongside the
  clear aggregate gain; search work counts are unchanged. Other regressions
  stay below 4%.
- 1,000 graph-cost comparisons, independent worst-bound oracle and targeted
  DAG/cycle tests pass. All smoke correctness gates pass; final non-time
  statistics match original. Artifacts: `outputs/performance/round4/attempt17/`
  and `cost-equivalence-attempt17.txt`.

### Attempt 18: numeric worst costs — KEEP

- Parent `cfcdf6d`; candidate `04d079b`.
- Replace `Policy.worst_ancestors` with `worst_costs`; Kahn's distances and cycle
  residue directly supply the numeric bounds. Tree-only extensions add one to
  the parent's finite worst cost and preserve CYCLE_COST for cycle descendants.
  Update constructors, copying, empty-policy initialization and all callers.
- Three runs: speedup **1.064×**, bootstrap interval **1.057–1.087×**. Thirteen
  medians improve; st_tires p09 changes by under 0.4% in the other direction.
- Costs/cycle flags agree on 1,000 graphs. Independent oracle, graph fixtures,
  heuristic-bound/copy tests and all smoke correctness gates pass; final non-time
  work counts are unchanged. This is an internal representation change, with
  no objective or cost-semantics revision. Baseline differential checks now
  instantiate the original Policy separately, avoiding representation coupling.
- Artifacts: `outputs/performance/round4/attempt18/` and
  `cost-equivalence-attempt18.txt`.


### Attempt 19: materialize numeric best costs — REVERT

- Parent `04d079b`; candidate `7c41bc7`; revert `e052031`.
- Hypothesis: after parent choices are fixed, memoize best costs across shared
  prefixes and store them per policy, avoiding later ancestor walks. Invalidate
  before recomputation, update tree extensions and copy values independently.
- Three runs: speedup **0.948×**, bootstrap interval **0.934–0.965×**: clear loss.
  Largest-case median sampled peak RSS **170,160 KB** versus parent **162,388 KB**.
  Map creation/copying outweighs cheap bound walks in this suite. Reverted after
  the loss was established; no five-run extension was needed.
- Costs/cycle flags agree on 1,000 graphs. **1,188 incremental extensions** across
  200 graphs match original costs for every state, flags and pending/goal sets.
  Targeted graph, numeric-bound/copy-isolation tests and all smoke correctness
  gates pass; final non-time statistics are unchanged.
- Artifacts: `outputs/performance/round4/attempt19/`,
  `cost-equivalence-attempt19.txt`, `incremental-equivalence-attempt19.txt`.


### Attempt 20: task-local action-outcome cache — KEEP

- Effective parent `e052031` (planner equivalent to `04d079b`);
  candidate `17b03ca`. Compared with the three attempt18 measurements.
- Reuse deterministic action outcome sets across policy-graph recomputations,
  using a task-local LRU bounded at 65,536 state/action pairs. Build each cached
  set using the same deterministic-operator iteration order as the graph pass;
  cached outcomes remain read-only. Tasks without the callback use direct action
  application, preserving the standalone graph API.
- Three runs: speedup **1.113×**, bootstrap interval **1.084–1.123×**. Doors
  improves 2.071×, Chain-of-rooms 1.300×, FrozenLake p07 1.286×. FrozenLake
  motivating and Tireworld-truck slow about 5%; other regressions are under 3%.
  These small-case/cache overhead tradeoffs are accepted for the clear gain.
- All smoke correctness gates pass; final non-time statistics match original.
  1,000 graph comparisons and 1,188 incremental extensions agree with original.
  Targeted cache tests verify reuse, bounded storage and unchanged cached sets;
  extension tests verify copied policies preserve cycle costs and isolate fields.
- Artifacts: `outputs/performance/round4/attempt20/`,
  `cost-equivalence-attempt20.txt`, `incremental-equivalence-attempt20.txt`.

### Round 4 outcome

| Attempt | Change | Search speedup over parent | Decision |
| --- | --- | ---: | --- |
| 16 | Topological worst bounds and cycle analysis | 1.104× | Keep |
| 17 | BFS best bounds on acyclic policies | 1.088× | Keep |
| 18 | Numeric worst costs | 1.064× | Keep |
| 19 | Numeric best-cost materialization | 0.948× | Revert |
| 20 | Task-local graph action outcomes | 1.113× | Keep |

Each candidate and the fresh reference has three unprofiled measurements. Gains
or loss are clear at that point; no five-run extensions were needed. The final
planner source matches measured attempt20 byte for byte.

- Final aggregate search speedup **1.422×** over fresh round start, whole-run
  bootstrap interval **1.395–1.445×**; **12.410×** over original `0d570b3`.
  Summed median search time **2.664 s**, versus round start **4.111 s**.
- Round-wide per-instance gains include Doors **7.550×**, Beam-walk **2.309×**,
  Chain-of-rooms **2.101×**, FrozenLake p07 **1.983×**, Responders **1.297×**
  and Elevators **1.231×**. Four small regressions (Blocksworld p02/p06,
  st_tires p09, Tireworld-truck) stay below 2.4% relative to round start.
- Final median suite **22.555 s** (range **22.529–30.415 s**), versus fresh start
  **21.903 s** and original **33.920 s**. This round establishes a search gain,
  not a suite-wall gain. Import/preprocessing/replay costs and scheduling noise
  remain significant. All controlled runs stay within 60 s (maximum 30.415 s).
  Largest median sampled peak RSS **163,408 KB**; no memory gain is claimed.
- **18 controlled runs** all complete 14 searches, solve the expected 12 cases
  and replay 14 policies. Every raw intermediate and final non-time statistics
  row matches original. Frozen inputs, campaign configuration, seed 0, four
  workers, 6,000,000 KB and 30 s/job remain unchanged.
- Final **53 tests pass**, including an independent path-enumeration worst-bound
  oracle. Final costs/cycle flags match original on 1,000 random graphs and
  every state across 1,188 incremental extensions. Evidence:
  `outputs/performance/round4/tests-final.log`, `statistics-equivalence.txt`,
  `resource-and-source-validation.txt` and the attempt20 differential logs.
- Plot-ready summaries include retained and rejected candidates:
  `outputs/performance/round4/round-summary.*`, `per-instance-summary.*`,
  `retained-summary.json`, `retained-per-instance-speedups.json`. The cumulative
  interval is saved separately in `retained-bootstrap-output.json`; attempt20's
  `bootstrap.json` retains its immediate-parent comparison.
- Final profiles in `profiles-final/` use two workers, the same 6,000,000 KB and
  30 s job timeout, and are excluded from timing comparisons. FrozenLake's
  recomputation still spends time on historical cyclic best-parent relaxation;
  Tireworld-truck spends more on bound evaluation. Acyclic recomputation and
  cycle/worst-bound classification now use graph passes rather than paths.
- Remaining correctness issue: the rejected full BFS prototype exposes cyclic
  best-cost overestimates in the original implementation. Those are intentionally
  preserved here, along with proper-policy checks and search order. A subsequent
  correctness change should explicitly document/version changed bounds and
  measure their effect separately from these semantics-preserving optimizations.
  This round makes no claim about unmeasured larger campaigns/configurations.

Stopped after the requested five attempts. No further round or full campaign
launched; published definitions, archives and frozen hashes remain untouched.


## Correctness fix: shortest best bounds on cyclic graphs

This is a separately authorized bug fix, not optimization attempt 21 and not
subject to reverting a confirmed correction merely for a lack of speedup.
Parent `5a9907e`; fix `e0583bd`; matching expectation metadata `2b74452`.
Journal campaign definition advances **1 -> 2**. ICAPS definitions, publication
tag, archives, input paths/hashes, configurations, resource limits and every
expected numerical solution cost remain unchanged.

### Cause and correction

Historical relaxation skips an edge when its destination is already in the
current trajectory, suppressing an otherwise valid shortest-path improvement.
The regression graph has 0 -> 1 -> 3 -> 5 (three steps), but the prior code reports
four. Both the specific regression and independent simple-path oracle fail
before the fix; the failure log is retained.

Use the existing breadth-first predecessor map for every reachable policy
state, including cyclic graphs. Remove the historical cyclic best-parent path
traversal. Kahn's worst-cost/cycle analysis and proper-policy decisions are
unchanged. Ancestor recomputation now consists of graph passes for all policies.

Version 2 makes the changed bound semantics explicit. Old version-1 runs use
their recorded code/definition revision for validation. `AGENTS.md` records that
future correctness comparisons must not preserve the old cyclic overestimate.

### Validation and measurements

Artifacts: `outputs/performance/best-bound-fix/`; raw planner runs remain in
`runs/journal_development/`. Fixed 14 cases/11 domains, seed 0, four workers,
6,000,000 KB, 30 s/job and 60 s suite budget; three fresh runs before and after.

- **55 tests pass**, including the counterexample and 200 independent simple-path
  shortest-bound cases. Before-fix tests fail with 4 != 3 and another random
  cyclic graph mismatch. Logs: `tests-before-fix.log`, `tests-after-fix.log`,
  `tests-final.log`.
- **1,000 random graphs** agree with independent shortest-path edge relaxation.
  The original implementation's 40 cyclic best-bound discrepancies are corrected;
  all worst costs and cycle flags agree with original. **1,188 incremental
  extensions** on 200 graphs retain correct shortest bounds, original worst
  costs/cycle flags and the same pending/goal sets. `graph-correctness.txt`,
  `incremental-correctness.txt`, `graph-cost-differential.json` record evidence.
- All **six valid timed runs** complete 14 searches, solve the same 12 cases,
  and replay 14 policies with unchanged expected Pareto costs. All intermediate
  and final non-time statistics rows match before-fix results. No observed
  search-work/solution change on this smoke selection; other graphs deliberately
  have changed best bounds. `statistics-comparison.txt`,
  `work-count-differences.json` record this separately from mathematical tests.
- Dry-run selections, commands, configurations, frozen hashes and resource limits
  are identical; only definition/source provenance changes. Expected-outcome
  numerical cost sets are verified identical to `5a9907e`.
  `dry-before.json`, `dry-after.json`, `campaign-comparison.txt`.
- Search speedup **1.245×** versus fresh parent, whole-run bootstrap interval
  **1.216–1.255×**; **15.091×** versus original on the same smoke cases. Summed
  median search time **2.258 s**. Chain-of-rooms improves 2.256× and FrozenLake
  p07 1.914×; three slight regressions remain below 0.8%.
- Suite median **23.472 s** versus **23.564 s** before; candidate range
  **23.213–25.725 s**. No robust suite-wall improvement is claimed. Median largest
  sampled peak RSS **163,472 KB** versus **163,516 KB** before; no memory claim.
  All timed runs remain under one minute. This suite does not establish impact
  on published results, other configurations, or Pareto completeness beyond its
  fixed expectations; no full campaign was launched.

The first post-fix execution completed all planners but validation rejected the
expected-outcome file's stale campaign-version metadata (1 versus 2). Preserve
that failed invocation in `after-metadata-mismatch/`; correct only metadata,
add a consistency assertion, and independently replay that completed run:
14 instances/14 policies pass (`revalidated-first-run.log`). Its incomplete
validation timing is excluded from the six controlled measurements for the
explicit metadata failure. The three valid post-fix runs are retained in full.

Decision: retain the independently verified correction. Resume optimization
from the corrected version-2 implementation, with this bug-fix boundary explicit.


## Round 5: strategy sharing and incremental graph bounds

Corrected reference `d9fef7d`, journal definition version 2. Five fresh baseline
runs (initial three, extended for uncertainty); fixed 14 cases/11 domains, seed 0, four workers, 6,000,000 KB, 30 s/job and
60 s suite budget. Artifacts: `outputs/performance/round5/`, raw runs under
`runs/journal_development/`. Retain original timing baseline for cumulative
comparison; correctness uses independent oracles and corrected graph passes.

### Attempt 21: immutable parent-linked strategy — REVERT

- Parent `d9fef7d`; candidate `cdf9aef`; revert `6aecd03`.
- Store one assignment and a parent strategy pointer per extension, sharing
  immutable prefixes. Copy returns the same mapping; pending/goal/bound maps
  remain independently copied. Preserve insertion order and add sibling equality
  shortcut. Test lookup, policy-copy isolation and mapping behavior.
- Three runs: aggregate speedup **0.722×**, bootstrap interval **0.711–0.742×**.
  Largest median RSS **161,524 KB** versus **163,420 KB** baseline. The small
  memory saving does not justify the substantial lookup/equality overhead.
- All smoke correctness gates pass; targeted strategy tests and 1,188 incremental
  oracle checks pass. Decision: revert a clear timing loss. Artifacts:
  `outputs/performance/round5/attempt21/`, `incremental-attempt21.txt`.

### Attempt 22: bounded strategy parent chains — REVERT

- Effective parent `6aecd03` (planner equivalent to `d9fef7d`);
  candidate `5ed4ccf`; revert `cd773d0`.
- Flatten into a native-dictionary base every third assignment, bounding lookup
  depth at two. Preserve shared-prefix immutability, insertion order and sibling
  isolation. Root equality uses native dict comparison.
- Three runs: speedup **0.839×**, bootstrap interval **0.822–0.876×**.
  Largest median RSS **161,396 KB**. Bounded lookups are less costly overall than
  unbounded chains but remain slower than native dictionaries; Tireworld-truck
  is particularly sensitive to mapping/equality overhead. Revert a clear loss.
- All smoke correctness gates, bounded-depth/isolation tests and incremental
  oracle checks pass. Artifacts: `outputs/performance/round5/attempt22/`,
  `incremental-attempt22.txt`. No shared-strategy implementation is retained.


### Attempt 23: reuse bounds for dominated edges — REVERT

- Effective parent `cd773d0` (planner equivalent to `d9fef7d`);
  candidate `68c1360`; final revert `99435f7`.
- Generalize the all-new-state shortcut: compare new edges with the parent's
  shortest and cycle-aware longest bounds. When existing children already have
  no greater best cost and no smaller worst cost than the inserted path, no
  bounds change. Strict finite longest-path levels certify no new cycle; an
  already cycle-cost source may connect to already cycle-cost descendants.
  Reuse parent bounds instead of rebuilding the entire graph. Mixed extensions
  still initialize previously unseen leaf states correctly.
- Three runs: speedup **1.066×**, bootstrap interval **1.040–1.095×**. Doors
  improves **2.015×**, Responders **1.198×**. Small regressions elsewhere stay
  below 3.3%; accepted alongside the clear aggregate gain.
- Targeted finite/cyclic dominated-merge tests ensure no rebuild, sibling
  isolation and unchanged numeric bounds. Random incremental extensions agree
  with full corrected graph recomputation; 1,188 extensions across 200 graphs
  agree with independent shortest-path relaxation and original worst costs.
  All smoke correctness gates pass; final work statistics match original.
- Artifacts: `outputs/performance/round5/attempt23/`,
  `incremental-attempt23.txt`; candidate tests were in
  `tests/test_incremental_bounds.py` (removed with its revert).

- The initial three-run result justified provisional retention. After extending
  both candidate and reference to five runs, speedup is **1.049×**, interval
  **0.999–1.112×**. This remains inconclusive under the agreed rule, so revert.
  Extra runs are preserved in `attempt23-extra/` and `round5-start-extra/`;
  restored planner sources match `68c1360` and `d9fef7d`, respectively, with
  explicit source-variant provenance. Original three-run evidence remains above.

### Attempt 24: incremental shortest-bound propagation — REVERT

- Parent `68c1360`; candidate `ec336fc`; revert `4a39b13`.
- Extend the unchanged-worst-bound certificate with shortest-path relaxation.
  Propagate decreases through existing best-parent links as well as alternate
  edges, including descendants whose getters already reflect an ancestor's
  decrease. Other extensions still require full graph analysis.
- Five runs against five parent runs: speedup **1.002×**, bootstrap interval
  **0.949–1.053×**. Suite median **21.754 s**. Revert an inconclusive result.
- Four targeted tests and 1,188 independent incremental graph checks pass;
  smoke completion, solution costs, replay and work counts remain unchanged.
  Artifacts: `outputs/performance/round5/attempt24/`,
  `incremental-attempt24.txt`. After reverting 24, also revert provisional 23.

### Attempt 25: incremental acyclic best/worst bounds — REVERT

- Corrected baseline parent `99435f7` (planner equivalent to `d9fef7d`);
  candidate `4b0f685`; revert `496f2dd`.
- Combine unchanged-bound certificates, shortest-path decreases and longest-path
  increases. For an acyclic parent, test whether a new edge's target reaches its
  source; if it does not, propagate changes through affected descendants.
  Cycle-creating edges and unsupported cyclic extensions use full graph analysis.
  This complete algorithm includes the previous candidates as dependencies and
  is evaluated as a whole against the corrected baseline, without crediting
  their inconclusive gains independently.
- Five candidate runs against five reference runs: speedup
  **1.041×**, bootstrap interval **0.986–1.089×**.
  Suite median **21.796 s**, range
  **20.890–27.209 s**.
  Largest median sampled RSS **164,056 KB**.
  Revert the inconclusive aggregate gain. Doors and Responders improve, while
  several other cases regress; reachability and propagation overhead can offset
  the avoided full traversal.
- Six targeted tests cover sibling isolation, finite/cyclic dominated merges,
  shortest-tree propagation, simultaneous best/worst changes and cycle fallback.
  All pass, as do 1,188 independent incremental checks across 200 graphs.
  Smoke correctness and work counts match throughout. Artifacts:
  `outputs/performance/round5/attempt25/`, `incremental-attempt25.txt`;
  prototype and test templates remain in the ignored round artifact directory.

### Round 5 result

No planner changes are retained. The original native strategy dictionaries and
corrected full graph algorithm remain the measured reference. The initial
three-run retention of attempt 23 was reconsidered after additional evidence;
all decisions below use the final five-run reference (attempt 24 uses its own
five-run immediate parent). Attempts 21 and 22 were stopped after three clear
losses. Intervals are whole-run bootstrap percentile 95% intervals of the
geometric mean of per-instance median search speedups.

| Attempt | Final speedup vs parent | Interval | Decision |
| --- | ---: | --- | --- |
| 21 | 0.722× | 0.706–0.764× | Revert |
| 22 | 0.840× | 0.815–0.889× | Revert |
| 23 | 1.049× | 0.999–1.112× | Revert |
| 24 | 1.002× | 0.949–1.053× | Revert |
| 25 | 1.041× | 0.986–1.089× | Revert |

All **26 timed runs** complete 14 cases, solve the same 12, replay 14 policies
and preserve expected Pareto costs. Every intermediate and final non-time
statistics row matches the original smoke output. Frozen input hashes,
configuration, seed, workers, memory and timeout remain identical. Final planner
source hashes match the measured corrected reference. The restored planner
passes **55 tests**, and 1,000 independent graph checks retain the verified
best-bound correction. No full campaign was launched.

Artifacts include `round-summary.csv/json`, `per-instance-summary.csv/json`,
`retained-summary.json`, `statistics-comparison.txt`, `reproducibility.txt`,
`graph-correctness.txt` and `tests-final.log` under
`outputs/performance/round5/`. Raw measurements and manifests preserve revision
and source-variant provenance, including extended parent runs. These results
establish no repeatable gain on this smoke selection; they do not exclude gains
on larger policies. Correct incremental analysis is feasible, but its overhead
and the current workload did not yield convincing aggregate performance gains.


## Properness correction before round 6

Reading the AND* paper (printed pp. 281–282) exposed a second independent
correctness discrepancy. The closed policy `0 -> {1, goal}`, `1 -> 0` is
strong-cyclic: all reachable states can reach the goal. The historical checker
rejects it because a goal trajectory records ancestors without its current
source, so a cycle root can be absent from the recorded goal paths. Its
state-keyed traversal also conflates paths. On 2,000 seeded random reachable
graphs with nonempty action outcomes, the old checker has **306 false
rejections** and no observed false acceptances. This is a correctness finding,
not an optimization to revert if timing is unchanged.

Correction `7bd2051`: build the reachable policy graph and traverse predecessor
edges backward from goals. Properness requires every reachable state to be
reached in this reverse traversal. Goal checks are explicit, unmapped non-goal
states fail, and task-local outcome caching is reused. Independent forward
reachability from each reachable state and a separate escape fixed point agree
with the replacement; five tests include the minimal regression, trapped
cycles, missing assignments, empty outcomes and cached/uncached behavior.

Journal campaign definition and expected-outcome metadata advance from version
2 to **3**. Inputs, limits and numerical expected cost sets are unchanged.
The ICAPS tag, archive and campaign remain intact. Three pre-fix smoke runs at
`411d4fc` and three initial post-fix runs complete 14 cases, solve 12 and replay
14 policies, with unchanged expected costs and final work counts. Initial
search speedup is **1.014×**, interval **0.981–1.049×**; no performance gain is
claimed for the correction. It remains independently justified on graphs that
the smoke selection does not expose.

Artifacts: `outputs/performance/round6/round6-start/`, `properness-fix/`,
`properness-differences-before.json`, `check-properness.py`,
`properness-after.txt` and `properness-tests.log`. The random oracle records no
post-fix discrepancies. Performance attempts 26–30 use the corrected reference.


## Round 6: AND* properness, deadlock pruning and policy representation

Corrected journal definition version 3; reference planner `7bd2051`. Fixed
14 instances/11 domains, seed 0, four workers, 6,000,000 KB virtual memory,
30 s/job and 60 s suite deadline including replay. Original baseline remains
`0d570b3` for timing context; correctness uses independent graph oracles and
the corrected planner. Raw artifacts: `outputs/performance/round6/`.

### Attempt 26: closed acyclic properness shortcut — REVERT

- Parent `7bd2051`; candidate `f41c507`; revert `da0a301`.
- A reachable closed DAG with nonempty action outcomes must end at goals, so
  avoid the generic properness traversal when maintained graph bounds certify
  acyclicity and goals exist. Cycle cases keep reverse reachability.
- Five runs per revision: search speedup **1.003×**, interval **0.961–1.064×**.
  Revert an inconclusive gain. Five properness contract tests and an independent
  1,000-DAG check pass; expected costs, policy replay and work counts match.
- Extra reference runs in `properness-fix-extra/` restore `planner/search.py`
  byte-for-byte from `7bd2051`; `source_variant` records this provenance.
  Artifacts: `attempt26/`, `tests-attempt26.log`, `acyclic-oracle.txt`.

### Attempt 27: early deadlock rejection before copying — KEEP

- Effective parent `da0a301` (planner equivalent to `7bd2051`);
  candidate `c3d4fd7`.
- Implement AND* Algorithm 2 before creating a child policy: traverse from
  new outcomes, treating the newly mapped source as mapped, and find an escape
  to any unmapped state (goal or pending). If none exists, the closed region
  cannot be repaired by assigning other pending states, so discard immediately.
  The empty policy starts the invariant, and only passing children enter Open.
- Initial three runs against five reference runs: speedup **1.085×**, interval
  **1.052–1.150×**. Chain-of-rooms improves **1.866×**, Responders **1.373×**.
  FrozenLake motivating has a small absolute-time regression from the new
  checking overhead; inspect final per-instance medians and extended evidence.
- Seven tests include an independent partial-policy escape fixed point, and
  3,313 growing-policy extensions agree with the same independent criterion.
  All costs and replay checks pass. Work counts match the corrected parent:
  the old heuristic already rejected these children later, after copying and
  graph-bound computation. Generation counts still include attempted children.
- Artifacts: `attempt27/`, `escape-growth-attempt27.txt`,
  `tests-attempt27.log`, and `work-comparison.json` in the attempt directory.

- Extended five-run evidence: speedup **1.107×**, interval **1.056–1.170×**;
  retain. Extra candidate runs in `attempt27-extra/` restore planner source from
  `c3d4fd7` with explicit provenance. These five runs are the reference for 28–30
  unless a later candidate is retained.

### Attempt 28: finite longest-path escape certificate — REVERT

- Parent `c3d4fd7`; candidate `c5e7539`; revert `992240f`.
- For an acyclic parent, an outcome with finite longest-path level at least
  that of the source cannot return to the source. The parent's existing escape
  from that outcome therefore survives; use the numeric levels before graph
  traversal. Cyclic parents and uncertified outcomes retain the graph test.
- Five runs per revision: speedup **0.965×**, interval **0.929–1.010×**.
  Revert the inconclusive result. Numeric checks add overhead and avoid too
  little traversal on these cases. Costs, replay and work counts match.
- Seven targeted tests and 3,313 growing extensions agree with the independent
  escape fixed point. Artifacts: `attempt28/`, `escape-growth-attempt28.txt`,
  `tests-attempt28.log`; extra parent runs described above.


### Attempt 29: compact child strategies with active materialization — REVERT

- Effective parent `992240f` (planner equivalent to `c3d4fd7`);
  candidate `85404df`; revert `de92fdb`.
- Evaluate policy sharing together with retained early deadlock pruning. Store
  a child as a read-only parent mapping plus one assignment; materialize its
  native dictionary after Open/Pareto selection. Full graph analysis uses a
  temporary native map instead of repeated pointer-chain lookups. Other policy
  maps and sets remain independently copied. This avoids long lookup chains in
  actual search, though standalone helper calls support nested overlays.
- Three runs: speedup **0.839×**, interval **0.784–0.878×**; clear loss, revert.
  Largest median sampled RSS **161,160 KB** vs **163,344 KB** parent: the small
  saving does not compensate. Overlay equality/materialization and extra Python
  mapping operations remain costly; costs, replay and work counts match.
- Two targeted sibling-isolation/materialization tests, 1,188 incremental cost
  checks and 3,313 escape checks pass. Artifacts: `attempt29/`,
  `tests-attempt29.log`, `incremental-attempt29.txt`,
  `escape-growth-attempt29.txt`. Ignored candidate/test-generation scripts retain
  the prototype after its tracked implementation is reverted.


### Attempt 30: larger-policy and serial queue tie-breaking — REVERT

- Effective parent `de92fdb` (planner equivalent to `c3d4fd7`);
  candidate `283ac62`; revert `5429ae1`.
- Preserve all existing objective/heuristic priority fields, then prefer larger
  policies as in AND*. A task-local serial resolves remaining ties, avoiding
  whole-policy equality and the historical unconditional `Policy.__lt__`.
  This deliberately changes equal-priority search order, not objective semantics.
- Five candidate runs against five parent runs: speedup
  **0.978×**, interval **0.929–1.033×**.
  Revert an inconclusive result. Extra queue keys/counters have overhead and
  the new order helps some cases while hurting others.
- Costs and replay remain unchanged. Summed final work counts change:
  iterations **71,135 -> 70,815**, expansions **13,113 -> 13,043**, generations
  **86,949 -> 86,543**, sum of per-instance max-Open counts **51,794 -> 51,592**.
  The last metric is a sum of individual maxima, not concurrent queue occupancy.
- Two tests verify original priority precedence, larger-policy/FIFO ties and
  absence of policy comparisons for all four sorter configurations. Smoke
  execution covers the fixed bw configuration. Artifacts: `attempt30/`,
  `tests-attempt30.log`, `work-comparison.json` and
  `work-count-differences.json`. Ignored scripts preserve the reverted prototype.

### Round 6 result

Keep early deadlock rejection, attempt 27. Independently retain the confirmed
properness correction `7bd2051` and journal definition version 3. Restore native
strategy dictionaries and historical queue ordering. Do not credit inconclusive
changes. Final planner source hashes match the five measured attempt-27 runs.

| Attempt | Speedup vs parent | Bootstrap interval | Decision |
| --- | ---: | --- | --- |
| 26 | 1.003× | 0.961–1.064× | Revert |
| 27 | 1.107× | 1.056–1.170× | Keep |
| 28 | 0.965× | 0.929–1.010× | Revert |
| 29 | 0.839× | 0.784–0.878× | Revert |
| 30 | 0.978× | 0.929–1.033× | Revert |

Retained search gain **1.107×** versus the fresh corrected
reference, interval **1.056–1.170×**; **16.467×** versus
the original fixed timing baseline on this smoke selection. Per-instance
regressions in the retained optimization are below 5% in the extended data;
no substantial absolute-time regression is observed. Summed per-instance median
search time **2.159 s**. Suite median
**23.673 s**, range
**23.040–24.632 s**, versus
**24.936 s** reference median; overlapping ranges
and launch/preprocessing overhead prevent a robust suite-wall improvement claim.
Largest median sampled RSS **163,344 KB**.

All **31 timed runs** complete 14 instances, solve the same 12 and replay
14 policies with unchanged expected Pareto cost sets. Inputs, configuration,
commands (apart from output locations), seed and resource limits are identical;
properness version 2->3 is explicitly recorded. Every intermediate and final
non-time statistics row matches the corrected reference except deliberate
attempt-30 tie-order changes, preserved separately. The fixed smoke suite does
not expose the old properness false rejections; independent graph oracles do.
Final planner passes **62 tests**. No full campaign or published-impact study
was launched. Original-baseline timing comparisons cross explicit correctness
boundaries and do not assert numerical equivalence on arbitrary tasks.

Diagnostic runs, excluded from controlled timing measurements, confirm the
mechanism: chain-of-rooms p16 rejects **689 of 1,304** attempted extensions before
copying/bounds, and Responders p_2_2 rejects **2,151 of 11,602**. Counts and logs
are in `diagnostics-final/` and `diagnostic-*.log`. Generation statistics still
include these attempted extensions, explaining unchanged work counts despite
less internal computation.

Artifacts under `outputs/performance/round6/` include `round-summary.csv/json`,
`per-instance-summary.csv/json`, `retained-summary.json`,
`statistics-comparison.txt`, `work-count-differences.json`, `reproducibility.txt`,
`tests-final.log`, raw measurement logs and per-run manifests. Restored parent
measurements preserve explicit source variants rather than claim their actual
HEAD was the parent revision. The next promising separate investigation is the
interaction of compact strategy storage with queue comparisons removed; it was
not evaluated in this five-attempt round. Most-recently-generated pending-state
selection also remains untested and would deliberately change search order.


## Round 7: implementation hypotheses from archived AND* code

Reference `e1a21ff`, journal definition version 3. Use fresh reference runs;
fixed 14 instances/11 domains, seed 0, four workers, 6,000,000 KB virtual memory,
30 s/job and 60 s suite budget. Original timing baseline remains `0d570b3`.
Artifacts: `outputs/performance/round7/`. Archived source inspection and checksum
provenance remain in `outputs/and-star-inspection/`.

### Attempt 31: cached infinite-heuristic action rejection — KEEP

- Parent `e1a21ff`; candidate `3c9616a`.
- Before escape checking/copying/bounds, discard an action with any successor
  whose admissible classical heuristic is infinite. All outcomes must be
  handled by a strong-cyclic solution. Cache the boolean certificate per
  state/action (65,536 entries, task-local), using the existing state heuristic
  and grouped-outcome caches. Generation counts still include attempts.
- Initial three runs: speedup **1.046×**, interval **1.023–1.079×**; retain.
  Expected costs, replay and work counts match. Small overhead regressions
  occur where there are fewer dead ends; per-instance data is preserved.
- Two tests use actual mixed nondeterministic outcomes and hmax, verify that
  one dead outcome suffices, finite goal outcomes remain valid, and caches
  are task-local and bounded. Artifacts: `attempt31/`, `tests-attempt31.log`.
- One run has **36.78 s** suite wall time versus approximately 24 s for the
  others. Preserve it in the measurements; no causal attribution or exclusion
  is justified. Suite wall time is reported separately from search time.

- Five candidate runs (extended in `attempt31-extra/`, source restored from
  `3c9616a`) against three fresh reference runs: **1.052×**, interval
  **1.023–1.079×**. The gain remains clear. Source-variant metadata records the
  actual HEAD and restored files. These five runs become the next parent.

### Attempt 32: non-structural Open entries with unchanged tie rule — REVERT

- Parent `3c9616a`; candidate `fc20a3f`; revert `8bb1800`.
- Replace nested tuple entries with slotted priority/policy entries whose
  comparison avoids `Policy.__eq__`. BOAND* generates each strategy only once;
  distinct queued policies are unequal. Preserve the existing priority tuple
  and policy less-than rule on ties, including identical-object handling.
  This explicitly differs from attempt 30's changed FIFO/size tie policy.
- Five runs per revision: **0.977×**, interval **0.953–1.006×**. Revert the
  inconclusive result; Python entry comparisons offset dictionary-equality
  savings on this selection. Costs, replay and work counts match.
- Three tests forbid structural equality during queue operations and verify
  identical removal order for 100 interleaved insertion/pop trials of 200
  unique strategies each. Artifacts: `attempt32/`, `tests-attempt32.log`.
- The fifth suite run takes **41.28 s**; retain it without attribution or
  exclusion. Parent extensions also have slower suite wall times. All remain
  within the fixed deadline. Do not infer a system bottleneck from wall alone.


### Attempt 33: compact strategies with non-structural queue comparisons — REVERT

- Effective parent `8bb1800` (planner equivalent to `3c9616a`);
  candidate `7e8acd2`; revert `e5ccac5`.
- Test the interaction left open by round 6: compact child mappings with native
  materialization for active/full-graph traversal, plus Open entries that avoid
  structural equality. Reintroduce 32 as a required dependency and evaluate the
  complete combination against retained 31; do not credit 32 independently.
- Five candidate and five parent runs: **0.965×**, interval **0.934–0.995×**.
  Revert the measured loss. Removing queue dictionary equality substantially
  narrows the loss seen in 29, but sharing/materialization still fails to pay
  off on this selection. No isolated speedup for either component is claimed.
- Costs, replay and work counts match; largest median sampled RSS is retained
  in the per-attempt summary. Queue/order tests, sibling/materialization tests,
  1,188 incremental bound checks and 3,313 independent escape checks pass.
  Artifacts: `attempt33/`, `tests-queue-attempt33.log`,
  `tests-strategy-attempt33.log`, `incremental-attempt33.txt`,
  `escape-growth-attempt33.txt`. Prototype scripts preserve the reverted code.


### Attempt 34: most-recent-outcome pending-state selection — REVERT

- Effective parent `e5ccac5` (planner equivalent to `3c9616a`);
  candidate `ba5e37e`; revert `46cda89`.
- Following archived AND*, inspect assigned states in reverse insertion order
  and pick a pending outcome from the newest assignment with one available.
  Use task-local outcome caching. This intentionally replaces arbitrary pending
  set ordering in this candidate while retaining the fixed campaign's historical
  `largestg` argument label; it is an explicitly recorded algorithm/order
  experiment, not a structural equivalence claim. Goal/cost semantics are unchanged.
- Stop after the first smoke **fails coverage**: `st_tires/p09` reaches the
  **30-second job timeout**, return code **124**, whereas the retained selector
  proves unsolvability in milliseconds. Suite wall **49.06 s**; sampled peak
  planner RSS **1,169,672 KB** for that case. The execution wrapper finishes,
  but this is not a completed search or a proof of unsolvability.
- Revert immediately; no aggregate speedup is calculated from only the
  successful subset. Other cases finish, but the suite has no complete
  validation report. Two selector contract tests pass; tests do not excuse
  the failed performance/coverage gate. Artifacts: `attempt34/run-1.log/json`,
  `tests-attempt34.log`, raw manifest and execution/error/output files under
  `runs/journal_development/2026-10-08T12-06-47Z-smoke-ee812bda/`.
- Selection order is highly consequential on this unsolvable case; this
  observation alone does not establish a logical bug in the recent selector.

- Post-run inspection independently replays all **14 policies** from the **13
  completed cases**, and all their expected costs match; **12 solved instances**.
  Only `st_tires/p09` is incomplete, with timeout status and no planner exception
  in stderr. This does not promote the failed suite to a successful run.
  `failed-run-inspection.json/txt` records completion, costs, replay, raw work
  rows and the failed execution. The failure remains explicit in exported data.

### Attempt 35: dense policy-local indices for graph bounds — REVERT

- Effective parent `46cda89` (planner equivalent to `3c9616a`);
  candidate `3dd120f`; revert `abd290c`.
- Index reachable states locally during BFS. Use integer adjacency, indegree,
  distance and predecessor arrays for Kahn traversal, reconstructing public
  state-keyed bounds afterward. Preserve BFS discovery and shortest-parent tie
  order. This tests integer graph bookkeeping without changing benchmark/state
  representations globally or interfaces elsewhere in the planner.
- Five runs per revision: **0.997×**, interval
  **0.964–1.033×**. Revert an inconclusive result; indexing/conversion work
  offsets cheaper array operations on these policies.
- Nine graph tests, 1,000 independent shortest-path graphs and 1,188 incremental
  extension checks pass. All expected costs, policy replay and intermediate/
  final work rows match. Artifacts: `attempt35/`, `tests-attempt35.log`,
  `graph-attempt35.txt`, `incremental-attempt35.txt`.

### Round 7 result

Keep attempt 31, the task-local early infinite-heuristic action certificate.
Native strategy dictionaries, historical Open representation/order, previous
pending-state selection and state-keyed graph computation remain. Final planner
source hashes equal the measured attempt-31 revision. All intermediate/revert
commits and rejected prototypes are preserved; no source equivalence is claimed
for the intentional selection experiment.

| Attempt | Speedup vs parent | Bootstrap interval | Coverage | Decision |
| --- | ---: | --- | --- | --- |
| 31 | 1.052× | 1.023–1.079× | 14/14 completed | Keep |
| 32 | 0.977× | 0.953–1.006× | 14/14 completed | Revert |
| 33 | 0.965× | 0.934–0.995× | 14/14 completed | Revert |
| 34 | Not calculated | Not calculated | Timeout; 13/14 completed | Revert |
| 35 | 0.997× | 0.964–1.033× | 14/14 completed | Revert |

Retained search gain **1.052×** versus three fresh
round-reference runs, bootstrap interval **1.023–1.079×** after five candidate
runs; **17.242×** versus the fixed original baseline on
this smoke selection. Summed per-instance median search time
**2.081 s**. Largest median sampled peak planner RSS
**163,324 KB**. Small regressions in individual
cases and full ranges are retained in per-instance data.

The retained suite median is **26.840 s**, range
**23.704–36.775 s**, versus
reference median **24.083 s**. This is a search-time
improvement, not evidence of end-to-end improvement: the observed suite median
is worse and launch/preprocessing/validation variability remains material.
Preserve all outliers; resource snapshots did not establish their cause. No
system-load correction, exclusion, or causal attribution is applied.

Across **24 timed invocations**, **23 successful runs** each complete 14 cases,
solve 12 and replay 14 policies with unchanged expected Pareto costs. Every
intermediate and final non-time statistics row matches the round reference for
these successful runs. The remaining invocation is attempt 34's explicitly
failed timeout, separately inspected as above and excluded from speedup
aggregation. All 24 manifests retain the same frozen inputs, numerical expected
costs, campaign version 3, commands/configuration, seed 0, four workers,
6,000,000 KB and 30 s/job; only intended planner-source revisions differ.
Final planner passes **64 tests**. No full campaign was launched. Original timing
comparisons cross the previously documented correctness boundaries and do not
claim arbitrary-task or published-result equivalence.

Raw measurements, logs and source variants remain under
`outputs/performance/round7/`, including `round-summary.csv/json`,
`per-instance-summary.csv/json`, `retained-summary.json`,
`statistics-comparison.txt`, `work-count-differences.json`, `reproducibility.txt`,
`tests-final.log` and `failed-run-inspection.json/txt`. Failed candidate speedups
are null, not averages over its surviving subset. Parent extension artifacts
record actual HEAD plus restored-file provenance. Stop after the requested five
attempts; compact storage/cheap queue comparisons are now tested jointly, and
state-selection sensitivity on unsolvable inputs is an important limitation.

## Round 8 — repeated bound evaluation and policy copying (attempts 36–40)

The user authorized another five-attempt round. Start from `bc14a81`, retain
journal definition version 3 and the corrected graph semantics. Use the fixed
14-instance/11-domain smoke, seed 0, four workers, 6,000,000 KB/job, 30 s/job
and 60 s suite deadline, including independent policy replay. Three fresh
reference runs are under `outputs/performance/round8/round8-start/`; original
baseline `0d570b3` measurements remain separate. Bootstrap whole-run repeats
(4,000 samples, seed 0); extend inconclusive comparisons to five per revision.
Parent extension measurements record the actual HEAD and byte-for-byte restored
source provenance. No failed or slow run is silently dropped.

Profile two representative cases separately from timed comparisons, with the
same planner limits. At the round reference, Tireworld-truck's 25,303 joint
bound calls consume 0.221 s under cProfile, versus 0.054 s in policy copying;
FrozenLake's 5,588 bound calls consume 0.089 s. Final properness checks are
comparatively small. These are instrumented profile costs, not timing evidence
for candidate speedups. Raw profiles and summaries: `profiles-before/`.

### Attempt 36 — direct cached state-heuristic access — keep

- Candidate `a2829d2`. Access the task-local state cache directly in joint and
  individual policy bounds, avoiding temporary `SearchNode` construction on
  cache hits. Keep node-based fallback support for uncached heuristics.
- Three runs per revision: **1.036×** search speedup, bootstrap interval
  **1.004–1.048×**. Keep. Preserve these decision measurements in
  `attempt36/decision-summary.json` and `decision-bootstrap.json`; additional
  parent repetitions later support the next comparison, not this decision.
- Tests verify cache-hit allocation avoidance and uncached/infinite-value
  behavior. Every smoke run completes 14 cases, solves 12 and replays 14
  policies with unchanged expected costs and non-time statistics.
- Artifacts: `attempt36/`, `tests-attempt36.log`,
  `joint-tests-attempt36.log`.

### Attempt 37 — fuse outgoing-state evaluation scans — revert

- Candidate `5377719`, revert `f509654`. Evaluate state heuristics, best and
  worst bounds in one pass; avoid constructing the outgoing union and numeric
  best/worst lists. Deduplicate overlapping pending/goal inputs and preserve
  empty/infinite/cyclic results.
- Five runs per revision: **1.003×**, interval **0.957–1.046×**. Revert an
  inconclusive change; Python loop/deduplication costs offset the saved scans.
- Thirteen relevant tests pass; 2,000 randomized cases match the round-start
  bound function exactly. All completed/solved/replay counts and cost sets
  match. Preserve the 37.34 s external-wall outlier; no timing exclusion or
  system-load attribution. Candidate tests are preserved in its Git commit.
- Artifacts: `attempt37/`, `attempt36-extra/` and its restored-source provenance.

### Attempt 38 — exact closed form for the current size bound

- Candidate `8e09390`. The existing ascending sort makes `h[i] + i` monotone,
  so the bound is exactly `max(h) + len(pending) - 1` for nonempty pending,
  zero otherwise. Remove sorting and index-list construction in joint and
  separate size evaluators. This preserves the current bound; it does not
  introduce the paper's alternative ordering or a scientific definition change.
- No incremental histogram is needed for this algebraic simplification. Check
  1,005 empty/duplicate/infinite/random size cases and 2,000 independent bound
  cases, including overlapping outgoing inputs and cyclic flags.
- Artifacts: `attempt38/`, `bounds-attempt38.txt`, `tests-attempt38.log`.
- Three candidate runs versus five parent repetitions: **0.969×**, interval
  **0.943–0.997×**. Revert a measured regression (`585d569`). The generator-based
  maximum did not repay its overhead on the small pending sets in this profile;
  algebraic equivalence alone is not evidence of faster Python execution.

### Attempt 39 — reuse the early escape invariant at closure

- Candidate `e4054a3`. Every accepted search extension preserves an escape to
  an unmapped state. When pending becomes empty those exits are goals, so
  accept the closed policy without rebuilding its reverse graph, and mark it
  proper. Keep the generic `Policy.is_proper` implementation for other callers.
- Independent forward-reachability oracle verifies 2,000 closed policies after
  11,536 accepted incremental extensions, including cycles; the 3,313 growing
  extension checks and 25 relevant tests also pass. This is search-local reuse
  of an invariant, not a reversion of the corrected properness definition.
- Artifacts: `attempt39/`, `closure-invariant.txt`,
  `escape-growth-attempt39.txt`, `tests-attempt39.log`.
- Five runs per revision: **0.999×**, interval **0.953–1.025×**. Revert an
  inconclusive change (`d065919`). Retain the explicit generic properness scan;
  its small profile cost does not justify an unmeasurable search-local shortcut.

### Attempt 40 — avoid discarded initialization during policy copying

- Candidate `0c3f6a1`. Allocate the slotted `Policy` directly, then assign all
  eight fields as before. Avoid the five empty containers and initial flag
  assignments that the constructor performs only to have `copy()` overwrite
  them immediately. Keep independent copies of strategy, pending, goals and
  both bound maps; no parent chain or shared mutable state is introduced.
- This targets the profiled sibling-copy cost more directly than immutable
  goal sharing or another strategy representation. Existing copy tests verify
  flags, bounds and independent mutability of all five containers. Twenty-five
  relevant tests and 1,188 randomized extension comparisons pass.
- Artifacts: `attempt40/`, `tests-attempt40.log`, `incremental-attempt40.txt`.
- Revert commit: `abdde96`. Preserve the FrozenLake/motivating timing outlier
  (0.424 s versus about 0.018 s in other candidate repetitions), which widens
  the interval. No observed cause is established and no run is excluded.
- 5 candidate runs: **0.997×**, interval **0.816–1.026×**. Decision: **revert**.

### Round 8 result

| Attempt | Search speedup vs parent | Bootstrap interval | Decision |
| --- | ---: | --- | --- |
| 36 | 1.036× | 1.004–1.048× | Keep |
| 37 | 1.003× | 0.957–1.046× | Revert |
| 38 | 0.969× | 0.943–0.997× | Revert |
| 39 | 0.999× | 0.953–1.025× | Revert |
| 40 | 0.997× | 0.816–1.026× | Revert |

Final measured planner: `attempt36`. Retained search speedup **1.035×**
versus this round's fresh reference (five retained-source repetitions, interval
**1.004–1.057×**) and **17.522×** versus the
fixed original smoke baseline. Summed per-instance median search time:
**2.034 s**. Full suite median **24.357 s**,
range **24.142–26.800 s**, versus
round-start median **24.215 s**. These are search improvements;
launch/preprocessing/replay dominate suite time and no end-to-end improvement
is established. Largest median sampled peak planner RSS:
**163,552 KB**. Resource snapshots show about 22–23 GB
available RAM and no swap use; they do not establish the cause of timing outliers.

All **26 timed smoke invocations** complete 14 instances, solve 12 and replay
14 policies, with unchanged expected Pareto costs and every intermediate/final
non-time work row matching the corrected round reference. Manifests preserve
version 3, frozen inputs, commands/configurations, resource limits and seed.
Final planner hashes match its measured revision. Relevant tests and independent
graph/bound/escape checks pass; final suite passes 66 tests. No full campaign
was launched. Fixed original timing comparisons cross the previously documented
correctness boundaries and do not claim arbitrary-task equivalence.

Raw results, source-variant provenance, resource observations and comparison data
are under `outputs/performance/round8/`: `round-summary.csv/json`,
`per-instance-summary.csv/json`, `retained-summary.json`,
`retained-bootstrap.json`, `statistics-comparison.txt`, `work-count-differences.json`,
`reproducibility.txt`, `tests-final.log`, `graph-final.txt` and
`incremental-attempt40.txt`. Original attempt-36 decision data are preserved
separately from additional repetitions used as the parent for later attempts.
Stop after the requested five attempts; no further optimization was started.

## Performance-profile calibration — journal definition version 4

The user requested a harder timing profile before another optimization round.
This is a campaign/validation change, not optimization attempt 41. Preserve the
original 14-instance smoke correctness selection and all its numerical expected
costs, and add a separate fixed 11-instance `performance` selection covering
exactly the same 11 ICAPS domains. Planner source is unchanged from `d1a4798`.

A bounded shortlist of 31 frozen inputs was piloted at seed 0 with four workers,
6,000,000 KB of virtual memory and a 12-second process limit. Eighteen searches
complete; thirteen pilots time out or remain incomplete. Keep all raw logs,
including Tireworld `p13`'s partial solution; none of these failures is treated
as unsolvability or included in successful timing aggregates. The pilot
collector initially looked for `.stat` rather than `.stats`; reconstruct its
records from the existing raw `.stats` files without rerunning or excluding
planners. `pilot-summary.json` is the corrected authoritative inventory;
earlier timestamped summaries preserve the original collection output.

Select Beam-walk `p7`, Blocksworld-ex `p13`, Chain-of-rooms `p24`, Doors `p8`,
Elevators `p04`, FrozenLake `p19`, Islands `p16`, Modified First Responders
`p_2_2`, ST Tires `p08`, Tireworld `p06` and Tireworld-truck `p7`. Blocksworld
is unsolvable; Modified First Responders has two Pareto solutions; three domains
supply cyclic policies. Search-time targets are approximate: two cases remain
around 0.12–0.14 s because shortlisted larger alternatives time out, two are
around 0.40–0.44 s, six are around 0.55–2.83 s, and Tireworld is around 6.84 s.
All cases remain in the primary geometric-mean aggregate; no fast-case exclusion
or timing-dependent weighting is introduced.

The definition is versioned as 4 to explicitly record the additional selection;
version-3 planner semantics, smoke numerical costs, full input manifest bytes,
input hashes/order, configuration and limits remain unchanged. Each profile
has its own expected-outcome file and exact-selection validation. Both dedicated
commands enforce a 60-second deadline including replay, four workers,
6,000,000 KB/job and 30 s/job. Updated documentation and AGENTS.md distinguish
the correctness gate from timing evaluation; earlier smoke timing baselines
must not be reused or mixed with new performance timings.

Nine selected cost sets match complete published BOAND bw searches. Doors `p8`
and Elevators `p04` have no complete archived baseline, so freeze their costs
from current-parent completed searches and validate emitted policies independently.
No archive or benchmark was changed. Replay verifies validity and policy costs,
not unsolvability or Pareto completeness. Expected costs must not be revised
merely to accept later optimization output.

The provisional full-profile run passes in 31.78 s. Freeze source at `c7cd597`
and measure three fresh repetitions: all 11 searches complete, 10 instances
are solved and 11 policies are independently replayed in every run. Expected
costs, final work counts and planner source hashes are identical. Median full
suite time **32.43 s**, range **32.14–32.47 s**; summed per-instance median search
time **17.66 s**. Largest median sampled peak planner RSS **489,868 KB**;
a resource snapshot shows about 23 GB available RAM and no swap use. Record
search time separately from suite time; use `c7cd597` and these measurements
as this profile's baseline, without comparing ratios across profile selections.

Dry manifests show identical original smoke selections, commands, input hashes,
configurations and limits before/after; only version metadata and the added
profile differ. The initial pre-change dry run omitted the seed; a comparable
seed-0 manifest is reconstructed from the unchanged version-3 definition in
memory, with provenance noted separately. Actual pre/post smoke runs use seed 0
and pass in **24.44 s** and **23.82 s**, respectively, with all 14 searches
complete, 12 solvable cases solved, 14 policies replayed, and every non-time
statistics row unchanged. New tests cover timing-profile selection, resource
limits, outcomes and rejection of wrong-profile validation. **68 tests pass**.
No full campaign or new optimization round was launched.

Artifacts: `outputs/performance/profile-calibration/`, including raw pilots,
`pilot-summary.json`, `manifest-comparison.txt`, `archive-comparison.txt`,
`validation-summary.txt`, `tests-final.log`, before/after smoke logs, the
provisional performance log, resource snapshot and `performance-baseline/`
(raw repetitions, measurements, source provenance, summary JSON and CSV).
The profile's selections and researcher commands are documented in
`campaigns/journal_development/README.md`.

## Round 9 — cleanup and interacting bound batches (attempts 41–42)

The user accepted two proposed batches and a code-cleanup exception to the
strict timing rule. Record the exception in AGENTS.md: a clear maintainability
improvement may remain without a demonstrated speedup when correctness and
repeated measurements show no substantial regression. Explicitly label such
retention as cleanup, not a timing win. Complex algorithmic experiments still
need stronger evidence. Evaluate a batch as a whole; do not assign its measured
gain to individual components.

Use the fixed version-4 performance profile (11 cases/11 domains, 10 solved,
11 policies replayed), with the unchanged smoke correctness gate (14 complete,
12 solved, 14 policies replayed). Seed 0, four workers, 6,000,000 KB/job,
30 s/job and 60 s suite deadline. Reuse the three calibrated `c7cd597` timings
as this profile's own baseline, then add two fresh reference repetitions to
investigate the per-instance concern. Never mix these inputs with the older
smoke timing baseline. Preserve all raw samples; bootstrap whole-run repeats
(4,000 samples, seed 0). Artifacts: `outputs/performance/round9/`.

### Attempt 41 — unused selector heap + discarded copy initialization

Candidate `1e31fb7` removes the unread heap and worst-cost lookups from the
historical last-iterated selector, and bypasses Policy initialization while
assigning every copied field. These are the combined attempts 9 and 4/40.
The 14-case smoke and copy/bound/properness tests pass.

The added selector test initially cloned the pending set before constructing
its reference. Set copying can change iteration order, so that fixture failed
even though both selectors preserve their own last-iterated element. Correct
it to compare paths on the same set in `abae178`: 500 randomized cases pass.
This test-only correction does not alter the measured planner source. Preserve
the initial failure log and corrected test evidence.

Three candidate runs initially show 1.010× aggregate speedup, interval
1.004–1.032×. Provisional retention is revisited after per-case inspection:
ST Tires p08 has mixed samples around 0.135 and 0.167 s versus reference
around 0.135–0.142 s. Extend both the reference and candidate to five rather
than treating the aggregate result as sufficient. Five-run aggregate is 1.011×,
interval 0.987–1.044×: no proven timing gain, and ST Tires remains slower.

### Attempt 42 — fuse bound scans with the exact size-bound formula

Candidate `ac5a92e` combines attempts 37 and 10/38 with a different implementation:
compute the pending heuristic maximum during the existing outgoing-state scan,
so no heuristic-value dictionary, numeric bound lists, sorted vector or index
list is needed. Retain the outgoing union to deduplicate overlapping goal/pending
inputs and preserve iteration order. The separate Delta bound evaluates only
pending states. The ascending-sort formula remains exactly max(h)+n-1, zero
for empty pending; this is not a new scientific size objective.

Fourteen relevant tests, 500 random comparisons with the separate best/worst
estimators and an independent sorted size formula, and 2,000 comparisons with
the corrected round-eight reference function pass. Empty frontiers, overlap,
cycles, infinity, uncached node heuristics and a small state cache are covered.
The original smoke again completes/replays with unchanged costs and work.

Three runs initially show 1.068× versus the first batch, interval 1.026–1.085×.
Extend to five while investigating the first batch's ST Tires issue. Final
five-run speedup is 1.048×, interval 1.021–1.084×, versus batch 41, and 1.060×
versus the reference. Aggregate improvement is clear, but ST Tires still has
slow samples; do not hide this case or exclude it from the aggregate.

### Diagnosis and conservative refinement

Run 15 separately instrumented ST Tires checks: three each of baseline,
selector-only, copy-only, both initial cleanup components, and fused-only.
AST-extracted original methods are substituted at runtime; no benchmarks or
expected outcomes change. At most four jobs, the same flags/seed/memory, and
30 s/job. All complete with the expected solution costs. GC instrumentation
shows all variants around 0.134–0.142 s, with one generation-2 collection each;
it does not reproduce or explain the full-profile slowdown. These instrumented
samples are diagnostic evidence, not replacement timing baselines or proof that
concurrent-profile regressions cannot occur.

The constructor bypass has a weaker maintainability benefit and introduces
manual initialization responsibility. Drop it instead of using the cleanup
exception to justify that uncertainty. Commit `5dd815a` restores the ordinary
constructor and temporarily restores the old bounds to measure only the
unread-heap removal. The first batch is not retained intact.

Selector-only source has three full-profile repetitions: 1.006×, interval
0.996–1.040×, against the five reference repetitions. This does not establish
a speedup. The ST Tires median is 0.147 s (0.135–0.148 s), versus the reference
median about 0.136 s. Other median ratios range approximately 0.99–1.06×.
The aggregate interval excludes substantial loss; retain the straightforward
unused-work cleanup subject to the final combined validation, explicitly
without claiming an independent timing improvement. Report the small absolute
ST Tires difference and timing limitations instead of claiming every case wins.

Reapply the independently validated fused bounds with ordinary Policy copying;
measure that final combination separately. Its measurements must not be mixed
with `ac5a92e`, which also contained the constructor bypass. These are refinements
of the two requested batches, not additional speculative optimization attempts.

### Final decision and validation

Keep the unread-selector-heap removal as a code cleanup, and retain the fused
bound/size calculation as a measured performance improvement. The constructor
bypass remains reverted; final `planner/policy.py` equals the performance
baseline exactly. Final source revision: `b81e48e`. No separate speedup is
assigned to the removed copy component or to the selector cleanup.

Five final repetitions versus three selector-only repetitions give **1.051×**,
interval **1.005–1.066×**. Versus the five original-profile reference repetitions,
retained aggregate speedup is **1.058×**, interval
**1.013–1.092×**. Summed per-instance median search time is
**16.282 s**; suite median **31.628 s**,
range **31.591–31.758 s**, versus
reference median **32.137 s**. Largest median sampled peak planner
RSS **489,816 KB**.

ST Tires p08 remains a measured exception: reference median **0.136 s**,
final median **0.167 s**, range **0.133–0.215 s**.
This is about **23.1% slower**, or **31.4 ms**.
Dropping constructor bypass did not resolve the full-profile variability;
component-isolated diagnostic runs did not establish its cause. Explicitly
accept this small absolute tradeoff alongside the clear aggregate improvement
and larger gains in the longer cases. Do not claim absence of per-case regression
or exclude the case from the geometric mean. A low aggregate risk and a readable
selector cleanup do not turn inconclusive selector timing into a speedup claim.

All **23 performance invocations** (including reused and refreshed reference
measurements) complete 11 cases, solve 10 and replay 11 policies. All three
smoke checks complete 14 cases, solve 12 and replay 14 policies. Every intermediate
solution and final non-time work row matches the corresponding reference;
cost sets are unchanged. Final planner fingerprints equal its measured source;
frozen inputs, campaign version 4, commands/configurations, seed and limits
remain unchanged. **71 tests pass**. No full campaign or further optimization
attempt was launched.

Raw artifacts remain under `outputs/performance/round9/`: original candidate
records, restored-source parent extensions, `selector-only/`, `refined/`,
`gc-diagnostic/`, original failed/corrected selector test logs, independent
bound checks, final test/validation logs, resource snapshots,
`round-summary.csv/json`, `per-instance-summary.csv/json` and
`retained-bootstrap.json`. Initial candidates are labelled rejected or
superseded; final refinements have their own revisions and measurement groups.

## Round 10 — retest graph and queue candidates on the harder profile (43–45)

The user requested retesting old attempts 23, 25 and 32. Execute these three
retests only; do not start a fourth candidate. Round parent `2b1fc90` retains
fused bounds, the historical last-iterated selection with its unused heap
removed, and ordinary Policy copying. Fixed original performance baseline is
`c7cd597`; old smoke timing baselines are not mixed with these inputs.

Three fresh parent timing runs and a before-change smoke check are recorded
under `outputs/performance/round10/round10-start/` and `smoke-before.log`.
Use the unchanged definition version 4, frozen selections and expected costs,
seed 0, four workers, 6,000,000 KB/job, 30 s/job and 60 s suite deadline.
Primary metric is geometric mean of per-case median search speedups; bootstrap
whole-run repeats (4,000 samples, seed 0). Extend uncertain comparisons to five
per revision. Keep every timing sample, including suite outliers. Inspect
individual results, especially ST Tires; do not claim universal improvements.

### Attempt 43 — dominated-edge graph bound reuse (old 23)

Candidate `98cbec9` adapts the historical `68c1360` update function to the current
planner without replacing its retained bound evaluator or early deadlock/action
pruning. Initialize new children, then skip full graph computation only when
all existing-child edges cannot improve shortest bounds or increase cycle-aware
worst bounds. Strict finite longest-path levels certify no new cycle; cycle-cost
nodes keep their established cycle status. Other extensions retain full BFS/Kahn
analysis. The fixed eight-field Policy representation is unchanged.

Nineteen targeted graph/properness tests pass. Independently compare 5,422
randomized growing extensions with the corrected full-graph parent, including
cycles and graphs up to 34 states, and 1,188 extensions with independent
shortest-path relaxation and historical worst costs. All numeric bounds,
reachability, cycle flags and pending/goal sets agree. Smoke passes with all
14 searches complete, 12 solved and 14 policies replayed.

Three runs per revision: **1.136×**, interval **1.098–1.157×**. **Keep**. Doors
improves **3.524×**; ST Tires is **1.010×**, effectively unchanged. Other
per-case ratios range approximately **0.961–1.096×**, including small losses
reported in the raw table. Preserve the third suite's 35.41 s external-wall
sample; do not exclude it or assign its cause. Costs and work counts agree.
Artifacts: `attempt43/`, `tests-attempt43.log`, `growing-attempt43.txt`,
`incremental-attempt43.txt`, `smoke-attempt43.log`.

### Attempt 44 — full incremental acyclic updates (old 25)

Candidate `8ee5e2e` adapts the complete historical `4b0f685` implementation,
including the unchanged-worst certificate, shortest-path relaxation, DAG
return-path cycle check and finite longest-path propagation. This contains
old attempts 23–25 as dependencies, but is evaluated as a complete candidate
against retained 43; no independent gain is assigned to its subcomponents.
Cyclic/unsupported extensions still use the corrected full graph computation.

Twenty-two targeted tests and the same 5,422 corrected-parent plus 1,188
independent extension checks pass. Smoke completes/replays with unchanged
costs and search work. Artifacts: `attempt44/`, `tests-attempt44.log`,
`growing-attempt44.txt`, `incremental-attempt44.txt`, `smoke-attempt44.log`.

Five runs per revision: **1.027×**, interval **0.983–1.083×**. **Revert** in
`c9d948b`: additional propagation logic has no demonstrated benefit over the
simpler retained shortcut. Do not use the cleanup exception for this algorithm.
Parent extension runs restore `planner/search.py` byte-for-byte from `98cbec9`
under actual HEAD `8ee5e2e`, with source-variant provenance recorded. The
extended attempt-43 interval versus the fresh reference is **1.065–1.157×**;
its clear gain remains supported. All rows and policies still match.

### Attempt 45 — non-structural heap entries (old 32)

Candidate `2f436a3` reintroduces `fc20a3f`'s slotted priority/policy entries,
avoiding `Policy.__eq__` for distinct queued strategies. Preserve priority
vectors, the historical policy less-than tie rule and identical-object
handling. This is not the earlier changed FIFO/size tie policy. All four sorters,
initial push and main pop use the same representation. No parent-linked strategy
representation or scientific queue-order revision is introduced.

Fifteen relevant queue/copy/incremental tests pass. Queue tests prohibit
strategy equality and check identical removal order on 100 interleaved trials
of 200 unique strategies. The four sorters and identical-object comparisons
are covered. Smoke again passes (14 complete, 12 solved, 14 policies replayed),
with unchanged numerical expected costs. Artifacts: `attempt45/`,
`tests-attempt45.log`, `smoke-attempt45.log`.

Five candidate runs versus five parent runs: **1.007×**, interval
**0.979–1.062×**. **Revert** in `85efc80`. Larger open lists still do not establish
a gain for the Python comparator; do not claim dictionary equality is free or
infer that the idea could never help another implementation. Historical queue
representation and tie behavior remain. All observed costs/work still agree.

### Round 10 result

Keep only attempt 43. Full incremental propagation and custom heap entries are
reverted with separate history-preserving commits. Final planner fingerprints
match the measured `98cbec9` source. Stop after the three requested retests.

| Retest | Previous attempt | Speedup vs parent | Bootstrap interval | Decision |
| --- | --- | ---: | --- | --- |
| 43: dominated-edge reuse | 23 | 1.125× | 1.065–1.157× | Keep |
| 44: full incremental updates | 25 | 1.027× | 0.983–1.083× | Revert |
| 45: non-structural heap entries | 32 | 1.007× | 0.979–1.062× | Revert |

The retained revision has five repetitions compared with three fresh round
reference repetitions: **1.125×** search speedup, interval
**1.065–1.157×**. Its initial three-run keep result is preserved above;
additional parent runs strengthen the following comparisons and update this
final summary. Per-case details retain every regression and range. ST Tires
median **0.175 s** versus **0.176 s**,
effectively unchanged. Doors remains the major beneficiary.

Summed per-instance median search time **15.491 s**.
Suite median **32.808 s**, range
**31.767–35.107 s**, versus starting
median **31.855 s**. This is a search improvement;
whole-suite variability does not establish an end-to-end gain. Largest median
sampled peak planner RSS **489,936 KB**. System
snapshots show about 22 GB available RAM and no swap use, without causal
attribution of timing fluctuations.

Across **18 performance runs**, each completes 11 searches, solves 10 cases,
and replays 11 policies. All four smoke checks complete 14 searches, solve 12
and replay 14 policies. Every intermediate solution/final non-time row matches
the fresh reference. Independent growing-graph and numeric-bound checks pass;
final planner passes **74 tests**. Inputs, expected Pareto costs, commands,
version 4, seed 0 and resource limits remain fixed. No full campaign launched.

Artifacts: `outputs/performance/round10/`, including parent-source provenance,
raw candidate/revert measurements, `round-summary.csv/json`,
`per-instance-summary.csv/json`, `retained-summary.json`,
`validation-performance.txt`, `validation-smoke.txt`, `source-verification.txt`,
corrected-parent/independent graph checks, final test log and resource snapshots.
Original-profile cumulative comparisons refer only to the fixed `c7cd597`
performance measurements, not the old 14-case smoke selection.

## Round 11 — numeric best bounds and cheaper extensions (attempts 46–50)

The user authorized up to five focused attempts after reviewing the proposed
round. Start at `9f37332`, with version-4 definitions, fixed smoke/performance
selections, seed 0, four workers, 6,000,000 KB/job, 30 seconds/job and a
60-second suite deadline. Original performance baseline remains `c7cd597`;
old 14-case smoke measurements are not used for performance speedups.

Initial correctness smoke passes in 22.29 seconds. The first performance run
(`round11-start/run-1.*`) fails the suite deadline: 64.34 seconds external wall,
only four completed searches reported before the deadline. It has no validation
report and is a **coverage failure**, not unsolvability or a speedup sample.
Preserve all logs and partial execution artifacts. No planner changes were made
before this failure. No memory-pressure evidence: about 29 GB available and zero
swap use. A fresh unchanged-parent retry completes three suites in approximately
31 seconds each; `round11-retry/` is the round reference. The initial failure
limits claims about reliably meeting the deadline under all execution conditions.
Do not hide it in successful-run averages or infer its cause from these samples.

Diagnostic cProfile runs on Tireworld p06, Elevators p04, Islands p16 and Doors
p8 run separately from timing (at most two diagnostic jobs). All complete.
Tireworld makes 1,711,880 best-bound calls, 3.238 seconds cumulative under
instrumentation; graph rebuilding takes 3.045 seconds. Elevators and Islands
show substantial copying/extension costs. Profiles are diagnostic, not speedup
baselines. Raw evidence: `outputs/performance/round11/profiles-before/`.

### Attempt 46 — numeric shortest distances

Hypothesis: predecessor walking dominates repeated best-bound access. Candidate
`f72333f` replaces predecessor-valued `best_ancestors` with numeric `best_costs`
without adding a container. BFS records a distance at first discovery;
incremental new-node initialization uses the parent's numeric distance. Full
BFS/Kahn semantics, dominated-edge certificate and queue order remain fixed.
Update all affected test fixtures and callers. This changes representation,
not planning objectives or numerical bounds; campaign version remains 4.

All 74 tests pass, including independent shortest-path/worst-path contracts;
5,528 randomized growing graph extensions agree with full recomputation.
Correctness smoke completes all 14 searches and replays all 14 policies.
Three candidate versus three fresh parent runs give **1.113×** geometric-mean
search speedup, 95% bootstrap interval **1.107–1.140×**. **Keep**. Doors 1.895×,
Tireworld 1.186×; Mod First Responders 0.980×, Blocksworld 0.999× and ST Tires
1.002×. All costs and non-time work match. Original-profile baseline ratio is
1.382×, with cross-round timing-condition limitations. Summed median search
13.678 seconds, maximum median sampled peak planner RSS 489,496 KB.
Artifacts: `attempt46/`, `tests-attempt46.log`, `graph-attempt46.txt`,
`smoke-attempt46.log`; sampled process RSS at 0.05-second intervals.

### Attempt 47 — defer bound copies until the graph decision

Parent `f72333f`, candidate `e3c7763`. Determine whether the extension violates
the dominated-edge certificate before copying; omit the two bound dictionary
copies when full graph recomputation replaces them. Keep ordinary copies for
incremental extensions, preserve sibling independence and all numerical rules.
Twenty-two targeted tests, including a dictionary that forbids discarded copies,
and 5,528 growing-graph comparisons pass. Smoke completes/replays unchanged.
Three runs give **0.956×**, interval **0.951–0.985×**, versus 46; original baseline
ratio 1.321×. **Revert** in `d57f40d`: saved copies do not repay the decision
work on this selection. This is a measured loss, so no extension to five runs.
Artifacts: `attempt47/`, `tests-attempt47.log`, `graph-attempt47.txt`,
`smoke-attempt47.log`. Costs and non-time work match the fresh reference.

### Attempt 48 — classify successors once

Effective measured parent `f72333f` (actual parent `d57f40d` after the revert),
candidate `02b3800`. Replace separate pending/goal comprehensions with one pass,
evaluate each successor's goal predicate once, then use the same list-based set
updates in the same order. Preserve pending selection, goals and search order.
Twenty-one graph/copy/incremental tests and 5,528 growing extensions pass;
smoke completes/replays unchanged. Three runs versus 46 give **1.016×**, interval
**1.004–1.026×**. Every per-instance median ratio exceeds one (1.004–1.030×).
**Keep**: small repeatable benefit with simpler classification; no substantial
regression. Original fixed performance baseline ratio 1.404×. Artifacts:
`attempt48/`, `tests-attempt48.log`, `graph-attempt48.txt`, `smoke-attempt48.log`.
Costs and non-time work match the fresh reference.

Additional parent repetitions were needed for attempt 49. Extend 48 and 46 to
five runs each, recording actual HEAD `ed3808b` and byte-for-byte restored
`planner/search.py` provenance in `attempt48-extra/` and `attempt46-extra/`.
All other planner files are unchanged. Updated 46 versus the three fresh start
runs is **1.113×**, interval **1.077–1.141×**; its keep decision remains clear.
Updated 48 versus five parent runs is **1.014×**, interval
**1.0004–1.0495×**. Blocksworld 0.996× and ST Tires 0.994× are the small median
regressions; preserve all per-case results. Conservatively retain 48 as an
**explicit code cleanup**, removing duplicate goal checks and consolidating
classification, rather than claiming a strong performance win from marginal
timing evidence. The validated five-run comparison shows no substantial
aggregate or per-instance regression. The initial three-run result above is
preserved as the provisional decision, superseded by this final interpretation.
Static migrated fixtures are subsequently expressed directly as numeric costs,
removing redundant conversion helpers where unnecessary (`f450f85`, 22 relevant
tests). This affects tests only and is not another performance attempt.

### Attempt 49 — mark escape states on discovery

Parent `02b3800`, candidate `ed3808b`. Mark mapped states when adding them to the
frontier, preventing duplicate queued states; return as soon as an unmapped
escape is discovered. Preserve the deadlock-free parent premise, outcome cache
and boolean criterion. Nineteen relevant tests and 3,313 growing extensions
against an independent escape fixed point pass. Smoke completes/replays with
unchanged costs/work.

Initial three-run result 0.999× spans gains and losses. Five candidate and five
parent runs give **1.002×**, interval **0.972–1.017×**. **Revert** in `af89cb5`:
no established benefit for the extra traversal logic. Original fixed baseline
ratio 1.405× refers to this rejected candidate. Later suites for both candidate
and parent run more slowly; keep every sample without attributing fluctuations
to CPU contention, memory, GC or the optimization. Artifacts: `attempt49/`,
`tests-attempt49.log`, `escape-attempt49.txt`, `smoke-attempt49.log`.

### Attempt 50 — one hmax operator cost for all add effects

Effective planner parent `02b3800` (actual parent `f450f85` after rejection and
test cleanup), candidate `cec9895`. Profiling shows 1,753,142 stock relaxation
cost calls on Tireworld. Stock hmax recomputes the same operator's maximum
precondition distance for each add effect. A task-local hmax subclass computes
it once when that operator's preconditions are settled, preserving effect
iteration, heap tie counter, goal termination, fact expansion and counter rules.
This is restricted to hmax; lmcut and vendored upstream code are unchanged.
The unit-cost relaxed operator cannot improve its own preconditions while
processing its effects, so its computed cost is constant across those effects.
Campaign version and admissibility/numerical semantics remain unchanged.

Twelve relevant tests pass. The new test compares 2,000 repeated-state evaluations
across 200 generated tasks against both stock hmax and an independent fixed-point
relaxation oracle, including empty goals/preconditions/effects, unreachable goals
and overlapping preconditions/effects. Smoke completes 14 searches and replays
14 policies in 18.27 seconds. Timing artifacts: `attempt50/`; correctness:
`tests-attempt50.log`, `smoke-attempt50.log`.

Three candidate repetitions versus five parent repetitions give **1.045×**,
interval **1.036–1.061×**. **Keep**. Blocksworld
1.412× and Beam Walk 1.111× benefit most; Mod First Responders 0.971×,
Elevators 0.994× and FrozenLake 0.998× are the observed median regressions.
Their absolute differences and ranges are preserved in per-instance artifacts;
no substantial unexplained regression is observed. All costs/work agree.

### Round 11 result

Retain numeric best distances and one operator-cost calculation per hmax
activation. Retain the simpler successor classification as a code cleanup with
weak timing evidence. Revert deferred bound copying and escape-frontier
changes with separate commits; stop after the five authorized attempts.

| Attempt | Parent search speedup | 95% bootstrap interval | Decision |
| --- | ---: | --- | --- |
| 46: numeric best distances | 1.113× | 1.0769–1.1408× | keep |
| 47: deferred bound copying | 0.956× | 0.9505–0.9907× | revert |
| 48: one-pass classification | 1.014× | 1.0004–1.0495× | cleanup |
| 49: escape frontier deduplication | 1.002× | 0.9722–1.0166× | revert |
| 50: one hmax cost per operator | 1.045× | 1.0355–1.0609× | keep |

Final measured planner `cec9895`: **1.179×** search speedup
versus the fresh unchanged-parent reference, interval
**1.176–1.208×**. Against the original fixed
performance baseline `c7cd597`, the observed cumulative ratio is
**1.464×**, interval
**1.451–1.469×**; this is a cross-round
measurement comparison with the timing-condition limitations noted above.
No ratio is derived from the earlier, different smoke inputs.

Across the retained round, Mod First Responders is the sole median slowdown:
0.100620 s to 0.106218 s (about 5.6%, 5.6 ms).
ST Tires is effectively unchanged; other per-instance median ratios improve.

Final summed per-instance median search time **13.233 s**.
Successful-run suite median **25.406 s**, range
**25.398–29.834 s**,
versus fresh reference median **30.546 s**.
The initial baseline deadline failure remains a coverage limitation, not a
successful timing sample. Largest median sampled peak planner RSS
**489,916 KB**; snapshots show roughly 28–29 GB
available RAM and zero swap use. CPU utilization was not continuously measured;
load snapshots do not establish causes of timing fluctuations.

**24 successful performance runs** each complete all 11 searches, solve all
10 solvable cases and replay all 11 policies. The additional initial reference
run is a recorded coverage failure: four finished, four interrupted, three
pending on deadline, without a validation report. All **six smoke checks**
complete 14 searches, solve 12 instances and replay 14 policies. Every raw
intermediate/final non-time statistics row agrees with the fresh reference.
Final **75 tests pass**. Source fingerprints match the measured final revision.
No benchmarks, expected Pareto sets, campaign definitions, objectives or
resource limits change. No full campaign is launched.

Final diagnostic profiles complete on the same four cases, separately from
unprofiled measurements. Full BFS/Kahn recomputation remains substantial in
Tireworld (52,482 calls), while policy copying/extension and native heap work
remain visible in Elevators/Islands. These profiles suggest future targets;
they do not establish another candidate's benefit or authorize another round.

Artifacts: `outputs/performance/round11/`, including all successful/rejected
runs and the failed reference, source-restoration provenance, per-case times,
work counts/RSS, `round-summary.csv/json`, `per-instance-summary.csv/json`,
`retained-summary.json`, `coverage-failures.json`, bootstrap intervals for
parent/original/round references, six smoke logs, graph/escape/heuristic checks,
`validation-performance.txt`, `validation-smoke.txt`, `source-verification.txt`,
`tests-final.log`, `profiles-before/`, `profiles-final/` and resource snapshots.

## Round 12 — hmax propagation and numeric bound hot paths (attempts 51–55)

The user authorized the next round, capped at five attempts. Start at `f5de121`,
with version-4 definitions, fixed smoke/performance inputs, seed 0, four workers,
6,000,000 KB/job, 30 seconds/job and the 60-second suite deadline. Keep original
performance baseline `c7cd597` separate from historical smoke selections.
Fresh three-run baseline: `outputs/performance/round12/round12-start/`;
initial correctness smoke passes in 22.87 seconds. No initial coverage failure.

Separate diagnostic profiles on Tireworld p06, Elevators p04, Islands p16 and
Doors p8 run with at most two jobs and the same planner resource limits.
All complete. Tireworld has 1,761,502 operator-cost calls (0.896 seconds under
instrumentation), 52,482 full graph passes (3.096 seconds), and 94,579 joint
bound evaluations (1.387 seconds). These are bottleneck diagnostics, not
unprofiled speedup estimates. Raw profiles: `profiles-before/`.

### Attempt 51 — use the last settled precondition for hmax

Parent `f5de121`, candidate `c911be9`. In hmax's Dijkstra traversal, the last
precondition settled has the maximum distance because settlement order is
nondecreasing. Use its popped heap distance plus the relaxed operator's unit
cost instead of scanning all precondition facts. The synthetic start entry
has popped distance zero, handling empty-precondition operators even though
the synthetic fact's own distance may be infinite. Preserve queue ordering,
counters, effect iteration, goal termination and repeated-state resets.
No changes to lmcut, upstream vendored code, task costs or admissibility rules.

Thirteen relevant tests pass, including 2,000 evaluations against stock hmax
and an independent fixed-point relaxation oracle. Add explicit repeated-state
contracts with differing precondition distances and empty preconditions.
Smoke completes all 14 searches, solves 12 and replays 14 policies in
22.51 seconds. Raw artifacts: `attempt51/`, `tests-attempt51.log`,
`smoke-attempt51.log`. Campaign semantics/version and expected costs stay fixed.

Three candidate and three parent runs: **1.119×**, interval
**1.101–1.142×**. **Keep**. Every per-instance median improves; Beam Walk
1.561×, Blocksworld 1.586× and Tireworld 1.123× are the main gains.
Original fixed performance baseline ratio 1.657×. Every raw intermediate and
final non-time row, expected cost set and replay outcome matches the reference.

### Attempt 52 — fuse the dominated-edge test and initialization

Parent `c911be9`, candidate `3bbe895`. Use numeric bound dictionaries directly,
compute child costs once, initialize previously unseen outcomes and check known
outcomes in one pass. Remove the temporary known-node list, generator and
repeated worst-cost lookups. On the first violated certificate, recompute the
full graph immediately: the strategy already contains every outcome, so the
remaining outcomes do not need temporary initialization before replacement.
The certificate and BFS/Kahn numerical rules remain unchanged.

Twenty-three graph/copy/bound tests and 5,528 growing-graph extensions against
full recomputation pass; smoke completes/replays unchanged in 22.89 seconds.
Artifacts: `attempt52/`, `tests-attempt52.log`, `graph-attempt52.txt`,
`smoke-attempt52.log`.

Three-run result 1.010× spans gains/losses. Extend both revisions to five;
parent extras restore `planner/search.py` byte-for-byte from `c911be9` under
actual HEAD `3bbe895`, recorded in `attempt51-extra/`.
Final **1.012×**, interval **0.975–1.057×**: timing remains inconclusive.
**Retain as an explicit code cleanup**, not a performance win. A single pass
removes the temporary list/generator and duplicate worst-cost lookups without
introducing incremental propagation or a new mathematical certificate.
Validation and all five repeated measurements show no substantial aggregate
or per-instance regression; Mod First Responders 0.977× is the small observed
median slowdown and remains in the comparison. Updated 51 versus fresh start
is 1.120×, interval 1.070–1.146×; its keep decision remains supported.

### Attempt 53 — start Kahn's traversal from the root only

Parent `3bbe895`, candidate `b7cef3c`. All vertices discovered by the BFS are
reachable from root; every non-root vertex therefore has a positive indegree
before Kahn's traversal starts. Root is the only possible initial zero-indegree
vertex. Replace the full indegree-table scan with a root check, including the
empty-ready case when a cycle reaches root. Subsequent longest-path and cyclic
residue calculations are unchanged. Correct the BFS comment to describe numeric
distances rather than the removed predecessor representation.

Twenty-one relevant tests, including root cycles and independent shortest/worst
path oracles, plus 5,528 growing extensions agree with full recomputation.
Smoke completes/replays unchanged in 25.28 seconds. Artifacts: `attempt53/`,
`tests-attempt53.log`, `graph-attempt53.txt`, `smoke-attempt53.log`.

Three-run result 1.003× is inconclusive. Five candidate runs versus five parent
runs give **1.007×**, interval **0.982–1.045×**. **Revert** in `20429af`:
no established benefit for the graph specialization. Original fixed performance
baseline ratio 1.690× describes the rejected revision. Preserve all per-case
regressions/ranges and the two additional samples. No numerical discrepancy.

### Attempt 54 — direct numeric accesses in joint bound evaluation

Effective parent `3bbe895` (actual `20429af` after the revert), candidate
`9424638`. Bind the existing best/worst dictionaries locally and read them in
the joint bound loop without per-state helper calls. Preserve numeric formulas,
outgoing union/iteration, heuristic caching, cyclic correction, worst-cost
default and legacy dummy-sentinel handling. This is a representation access
optimization, not a heuristic or queue-order change.

Twenty-three bound/state-cache/graph/copy tests pass, including 500 randomized
comparisons with separate estimators and a new sentinel equivalence contract.
Smoke completes/replays unchanged in 18.41 seconds. Artifacts: `attempt54/`,
`tests-attempt54.log`, `smoke-attempt54.log`.

Three-run result 1.018× is inconclusive. Five candidate versus five parent runs
give **1.014×**, interval **0.999–1.057×**. **Revert** in `1d51bc3`:
no established aggregate gain after the allowed repetitions. Doors shows
1.185× and Tireworld 1.031×, but preserve the aggregate uncertainty and the
individual median regressions rather than selecting only favorable cases.
This duplicates helper semantics in a hot loop, so it has no compelling
maintainability justification under the cleanup exception. Original fixed
performance baseline ratio 1.701× describes this rejected candidate.

### Attempt 55 — compile relaxed effect references once

Effective parent `3bbe895` (actual `1d51bc3` after rejection of 54), candidate
`d1ceb75`. A fresh retained-parent Tireworld profile (`profiles-before55/`)
shows hmax propagation still takes 0.587 seconds cumulative under instrumentation,
including 0.529 seconds in its traversal body. Three preceding attempts have
not established repeatable timing benefits, but this remaining concrete hmax
hot path is a promising low-complexity target, so proceed with the fifth
already-authorized attempt rather than start another round.

Compile an ordered tuple of effect-fact objects on each task-local relaxed
operator. Its objects belong to the heuristic instance; no task operators,
benchmarks or upstream code are mutated. Iterate these references rather than
look up each effect name in the fact dictionary on every activation. Keep
activation counters, relaxation costs, goal termination, effect order and heap
tie order unchanged. Extra initialization/allocation is included in full suite
wall time and sampled process RSS; do not infer a startup gain from search time.

Thirteen heuristic/oracle/graph/bound tests pass, including the stock-hmax and
independent fixed-point comparisons and empty-precondition contracts. Smoke
completes/replays unchanged in 23.55 seconds. Artifacts: `attempt55/`,
`tests-attempt55.log`, `smoke-attempt55.log`, `profile-before55.log`.

Three-run result 0.970× is noisy, with slow Mod First Responders samples.
Extend the candidate to five; parent already has five. Final **0.980×**,
interval **0.801–1.035×**. **Revert** in `f840c32`: no established benefit,
and Mod First Responders' median ratio is 0.682× (roughly 0.097 to 0.142
seconds). ST Tires 0.965× also slows in the measured medians. Preserve all
samples, including slow samples in both parent and candidate. Do not infer
GC, CPU contention or reference-cycle causation from these uninstrumented
measurements. Added cache state/allocation has no cleanup justification.
Original fixed performance baseline ratio 1.644× describes the rejected revision.

### Round 12 result

Keep the last-settled-precondition hmax optimization. Retain the fused numeric
bound update as an explicit code cleanup with unproven timing benefit. Revert
root-only Kahn initialization, direct joint bound accesses and compiled effect
references with separate history-preserving commits. Stop after the five
requested attempts; no further optimization is started.

| Attempt | Parent search speedup | 95% bootstrap interval | Decision |
| --- | ---: | --- | --- |
| 51: last settled precondition for hmax | 1.120× | 1.070–1.146× | keep |
| 52: fused numeric bound update | 1.012× | 0.975–1.057× | cleanup |
| 53: root-only Kahn initialization | 1.007× | 0.982–1.045× | revert |
| 54: direct numeric bound evaluation | 1.014× | 0.999–1.057× | revert |
| 55: compiled relaxed effect references | 0.980× | 0.801–1.035× | revert |

Retained planner source matches measured `3bbe895` byte-for-byte. Five retained
measurements versus three fresh starting measurements give **1.133×**
search speedup, interval **1.092–1.158×**.
This measures the retained combination; it does not establish an independent
performance gain for cleanup 52. Versus fixed original performance baseline
`c7cd597`, observed cumulative speedup is **1.677×**,
interval **1.617–1.705×**, with cross-round
timing-condition limitations. Earlier smoke inputs/baselines are not mixed in.

Summed per-instance median search **12.076 s**;
successful suite median **24.961 s**, range
**24.548–28.204 s**,
versus starting median **29.156 s**.
Largest median sampled peak planner RSS **489,784 KB**.
Resource snapshots show ample available RAM and no swap use. Memory sampling
uses per-process VmHWM at 0.05-second intervals; continuous CPU utilization
was not measured. Do not infer causes of timing fluctuations from load snapshots.

All **28 performance runs** complete 11 searches, solve the 10 solvable cases
and replay all 11 expected policies. All **seven smoke checks**, including
post-revert final smoke, complete 14 searches, solve 12 and replay 14 policies.
Every intermediate/final non-time statistics row agrees with the fresh reference.
Final **76 tests pass**, with independent graph/path and heuristic oracles.
No benchmark hashes, expected Pareto costs, scientific objectives, campaign
version/definitions, seeds, commands, resource limits or published archives
change. No full campaign is launched. Source fingerprints match the retained
measured revision. Generated evidence remains ignored.

Final diagnostic profiles complete separately on the four representative cases.
Tireworld's full graph recomputation remains substantial (52,482 calls,
3.060 seconds cumulative under instrumentation), followed by joint bounds
(1.431 seconds); hmax traversal is reduced to 0.614 seconds. Policy copying
and native heap work remain visible in Elevators/Islands. These are possible
future targets, not timing evidence for another change or authorization to
start another round.

Artifacts: `outputs/performance/round12/`: raw baseline/candidate/rejected
measurements, parent-restoration provenance, all per-instance medians/ranges,
work counts and sampled peak RSS, `round-summary.csv/json`,
`per-instance-summary.csv/json`, `retained-summary.json`, parent/original/round
bootstrap intervals, seven smoke logs, graph/heuristic contracts,
`validation-performance.txt`, `validation-smoke.txt`, `source-verification.txt`,
`tests-final.log`, `profiles-before/`, `profiles-before55/`, `profiles-final/`
and resource snapshots. Keep every noisy sample and every rejected attempt.

Retained per-instance median regressions versus fresh start:
- `mod_first_responders/p_2_2`: 0.095264 to 0.097036 s (1.9%, 1.8 ms).

## Fast Downward migration stage 1 — native execution prototype (attempt 56)

Hypothesis: replacing Python heuristic evaluation, applicability and effect
application with upstream Fast Downward C++ can improve BOAND* without changing
objectives or requiring a complete search rewrite. This is a requested migration
batch, not evidence for individual component gains. Parent: `0cdb224` (planner
identical to `c937f43`); fixed original performance baseline: `c7cd597`.

The opt-in `downward-strips` backend retains existing compilation/grounding and
uses a Boolean SAS encoding, native state registry, successor generator and
hmax/LM-cut. Upstream release 26.6.0 is pinned to
`7ea2755269ff9398279b30f5c848e32ba6047c9c`. The first integer-state candidate
failed the correctness gate: ST Tires `p09` exceeded 30 seconds after changed
set iteration affected the historical selector. Its failed run is preserved
under `runs/journal_development/2026-10-09T07-32-12Z-smoke-downward-hmax-2c886abf/`.
It was not timed as a successful candidate. The revised fact-set boundary keeps
native IDs internal and preserves Python state/operator hashes and ordering.

Journal definition 5 versions the new comparison profiles; existing default
configuration, selections, numerical cost sets and limits are unchanged. The
statistics writer additionally normalizes integral Pyperplan LM-cut floating
costs to the existing integer text format; an initial Pyperplan LM-cut smoke
run completed all searches but failed result parsing before this fix.

Preliminary validation: both revised native heuristics passed 14/14 searches,
12/12 solvable cases and 14 policy replays against the old backend. Pyperplan
LM-cut passed after its statistics-format fix. Tests check 120 random classical
tasks against transitions and exact shortest distances, and all policies on
60 tiny FOND tasks with both backends and heuristics. Domain sampling compares
1,378 states / 9,218 transitions across all 23 distinct fixed-profile inputs;
only three of those sampled graphs are exhaustive. All compiled selected tasks
have no conditional effects or axioms, including 66 grounded no-ops. The pruning
audit found no consistency assumption; this does not remove the requirement for
admissible bounds and safe dead-end detection.

Raw build, audit, tests, smoke and baseline evidence lives in ignored
`outputs/fast-downward/`. The unchanged-parent smoke initially failed with an
execution-infrastructure error and suite timeout; its retry passed in 22.95 s.
Initial parent performance repetitions 1 and 3 passed; repetition 2 overlaps a
build and is excluded from timing; repetition 4 used transitional default code
and is diagnostic only. Repetition 5 restores the parent's three modified
planner modules exactly for a third parent timing sample, using identical
profile inputs/flags/limits under definition-5 metadata. All parent cost sets
remain unchanged. Repeated candidate evaluation and final keep/revert assessment
will follow this validated prototype commit. No performance win is claimed yet.
See `docs/fast-downward-backend.md` for architecture, build and remaining scope.

### Final evaluation of prototype `37368cb`

Decision: **retain the opt-in native execution backend** on the migration
branch. The default remains Pyperplan+hmax for review and controlled comparisons.
Native hmax has a clear repeatable benefit with identical search work. Keep
native LM-cut as the requested heuristic capability, with its mixed guidance
results documented; do not select it as a universal default on this evidence.
The integer-state search-boundary candidate remains rejected. This stage does
not migrate grounding or claim the advantages of compact native Python-facing
states, and it does not attribute the batch gain to separate components.

All reported candidate measurements use committed revision `37368cb`, seed 0,
the unchanged 11-instance performance selection, four workers, 6,000,000 KB/job,
30 s/job and the 60 s suite deadline. Three exact-parent planner measurements
use `baseline-performance-{1,3,5-parent}.log`; the fifth restores the parent
search/CLI/output modules and leaves the version-5 profile metadata in place.
The commands, costs, input hashes and limits are equivalent to version 4.
A further three current-Pyperplan controls at `37368cb` interleave with three
runs of each native configuration; there are no concurrent builds or campaigns.
These controls check drift and include the measurement sampler used for native
runs. Whole-run bootstrap intervals use 4,000 resamples, seed 0, and per-instance
medians followed by the geometric mean of baseline/candidate ratios.

| Configuration | Searches completed | Solvable cases solved | Policies replayed | Geomean speedup vs parent (95% bootstrap interval) | Sum of median search times (s) | Median suite wall time (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Parent Pyperplan+hmax | 11/11 | 10/10 | 11/11 | 1.000 | 12.095 | 28.817 |
| Current Pyperplan+hmax control | 11/11 | 10/10 | 11/11 | reference control | 12.136 | 28.938 |
| Native hmax | 11/11 | 10/10 | 11/11 | 2.256 (2.229–2.310) | 9.711 | 27.595 |
| Native LM-cut | 11/11 | 10/10 | 11/11 | 2.174 (2.042–2.211) | 8.456 | 27.206 |
| Pyperplan LM-cut | 10/11 | 9/10 | 10/11 | **coverage failure; no aggregate** | unavailable for complete suite | 36.067 external, failed |

The parent wall-time median above is the median of its suite validation reports;
see raw artifacts for exact samples. Current-control wall range is 28.798–30.087 s;
native hmax 27.460–27.799 s; native LM-cut 27.205–27.911 s. Suite-wall improvements
are modest because setup and replay still dominate much of the suite; the
geometric mean weights domains equally and does not predict total elapsed time.
Against the interleaved current Pyperplan control, native hmax is 2.208×
(2.142–2.301) and native LM-cut 2.127× (1.962–2.202). Relative to the fixed
original `c7cd597` baseline, cumulative observed speedups are 3.670×
(3.613–3.735) and 3.536× (3.309–3.575), respectively. Those original-baseline
comparisons span rounds and retain the usual environmental-drift limitation.

Native hmax improves every parent per-instance median (1.024× on Elevators
through 15.840× on Blocksworld); all intermediate and final non-time statistics
rows match the parent exactly, including policy sizes and work counts. Native
LM-cut has an individual regression: Beam-walk search is 0.871 s versus the
parent's approximately 0.191 s (0.219×). It reaches 161.077× on Elevators,
reducing expansions from 46,819 to 461. Modified First Responders expansions
fall from 1,959 to 1,784 and Tireworld-truck from 8,369 to 8,249. Other changes
in generations, queue sizes and policy statistics are recorded in the raw runs.
LM-cut versus native hmax has geomean 0.964× (0.893–0.982), while its summed
median search time is lower. The clear gains/losses established after three
runs do not require extending to five. No failed case enters a speedup average.

Pyperplan LM-cut's first performance run timed out on Beam-walk `p7` at its
30-second job limit; further repetitions stopped. The other ten cases completed,
including the unsolvable case, and their ten emitted policies were independently
replayed with matching cost sets. That partial check is not an overall pass.
Both native configurations pass final 14-case smoke checks, with 12/12 solvable
cases and 14/14 policies replayed. **85 tests pass**, including 120 generated
classical tasks and exhaustive policy oracles on 60 tiny FOND tasks with all
four backend/heuristic combinations. No numerical expected cost was changed.

Diagnostic profiles confirm Beam-walk calls both native heuristics 512 times:
hmax evaluation totals 0.00390 s, LM-cut 0.76903 s (profiled values, not timing
baselines). All four implementations give initial h=256 there. On Elevators,
hmax initially gives 5 while LM-cut gives 10, and the native LM-cut search uses
133 heuristic evaluations versus hmax's 248. These two diagnostic tasks also
show equal initial heuristic values across backends. LM-cut values need not
agree on every task because supporter choices can differ. Profiled samples
are excluded from all aggregate timing calculations.

Per-process sampled median peak RSS is at most 480,116 KB for native hmax and
480,356 KB for native LM-cut, versus 490,080 KB for the current Pyperplan control.
The 50 ms sampler observed all 11 planner processes in every repetition; these
are sampled high-water measurements rather than guaranteed exit-time peaks.
System samples every second show at least 27.566 GiB of available RAM, at most
768 KB of swap used, and mean aggregate CPU busy fractions of approximately
12–14% across 24 logical CPUs. The CPU metric includes other machine activity;
it is not per-planner CPU utilization. There is no indication of substantial
memory pressure from this workload.

Raw evidence: `outputs/fast-downward/measurements/` holds each repetition's
full report, log, peak-RSS and system samples; `summary.json` contains medians,
bootstraps and case-level speedups; `per-instance.csv` adds preprocessing and
backend/heuristic setup times. `raw-work-equivalence-all.json` records the complete
hmax statistics comparison across all six repeated control/native-hmax runs. `pyperplan-lmcut-coverage.json` and
`pyperplan-lmcut-partial-validation.json` preserve failure/partial coverage.
`profiles/` holds four diagnostic cProfiles and native-call totals;
`audit/` holds domain equivalence, feature checks and initial-value diagnostics.
Final smoke runs and their resource samples are also in `measurements/`.
All native run manifests include the upstream revision, compiler, Python ABI,
binding hashes and native binary hash; snapshots include `native-backend.json`.

The next useful milestone is replacing grounding/translation while preserving
all outcomes and explicitly handling translator simplification. It should be
assessed separately from this native execution win. No full campaign, push,
tag or merge was performed.

### Additional baseline: BOAND* bw with Pyperplan LM-cut

At the user's request, record a separate three-repetition baseline for
`BOAND pyperplan lmcut`, rather than treating it as an optimization candidate.
This completes the four-way backend/heuristic comparison available in the
prototype. No planner code, expected costs, profile selections or limits changed.
The fixed original baseline remains `c7cd597`; this is an additional reference.

Measurements use journal definition 5, `bw`, LM-cut, MinSum/MaxSum/Delta,
`largestg`, `PYTHONHASHSEED=0`, four workers, 6,000,000 KB virtual memory/job,
30 seconds/job and the unchanged 60-second suite deadline. Performance repetition
1 reuses the previously recorded `37368cb` run; repetitions 2–3 and all three
smoke repetitions use `0432276`. Every manifest's planner-file hashes match:
these revisions differ only in documentation. Additional repetitions characterize
the requested baseline after the earlier candidate evaluation stopped on failure.
Runs were sequential, without concurrent campaigns or builds.

| Profile | Completed searches, each run | Solvable cases solved, each run | Policies replayed, each run | Median wall time (range), seconds |
| --- | ---: | ---: | ---: | ---: |
| Smoke | 14/14 | 12/12 | 14/14 | 24.501 (24.266–25.433), including suite replay |
| Performance | 10/11 | 9/10 | 10/11 | 36.018 (35.911–36.067), external elapsed to failed exit |

Beam-walk `p7` times out with return code 124 in **all three performance runs**.
It is a coverage failure, not unsolvability. The performance command exits before
its normal validation report, so an independent collector checks the unchanged
expected cost sets and replays all ten policies from the ten completed searches
in each repetition. The unsolvable Blocksworld instance completes correctly.
All smoke cases pass their expected costs and policy replay, including both
unsolvable instances. Collector replay after the failed command is additional
validation and is not included in its external wall time.

The following search medians exclude preprocessing and replay. The other three
columns reuse the three current-control/native repetitions at `37368cb` with
equivalent inputs and settings; measurements are sequential, not simultaneous.

| Performance instance | Pyperplan hmax (s) | Pyperplan LM-cut (s) | Native hmax (s) | Native LM-cut (s) |
| --- | ---: | ---: | ---: | ---: |
| Beam-walk p7 | 0.1911 | timeout | 0.0193 | 0.8755 |
| Blocksworld p13, unsolvable | 0.1752 | 2.4658 | 0.0111 | 0.0456 |
| Chain of Rooms p24 | 0.3604 | 1.5138 | 0.2060 | 0.2299 |
| Doors p8 | 0.1722 | 0.2690 | 0.1368 | 0.1378 |
| Elevators p04 | 2.3125 | 0.0566 | 2.2549 | 0.0143 |
| FrozenLake p19 | 0.6940 | 0.7148 | 0.6223 | 0.6267 |
| Islands p16 | 2.2911 | 3.2682 | 2.0210 | 1.9995 |
| Modified First Responders p_2_2 | 0.1076 | 0.0958 | 0.1129 | 0.0721 |
| ST Tires p08 | 0.1216 | 0.5026 | 0.0138 | 0.0237 |
| Tireworld p06 | 4.6023 | 11.6984 | 3.3861 | 3.5061 |
| Tireworld-truck p7 | 1.1076 | 1.7037 | 0.9264 | 0.9247 |

No full-profile geometric mean or total search-time comparison is reported for
Pyperplan LM-cut because coverage is incomplete. Its ten completed performance
cases sum to 22.289 seconds of per-case medians; that is a partial diagnostic,
not a full-suite total. Smoke sums to 10.581 seconds, with Beam-walk p6 alone
taking a median 6.975 seconds. A job timeout includes setup and cannot be
substituted for a measured search time.

Work counts vary on Elevators despite seed 0: performance p04 records 627 or
669 expansions and 3,201 or 3,342 generations; smoke p05 records 29 or 33
expansions. Other completed cases have stable recorded work counts. The source
of this variation is not established here; preserve it as a reproducibility
limitation and do not attribute cross-backend differences solely to evaluation
speed. The native LM-cut Elevators result has 461 expansions. Timing samples
and all observed work counts are retained per instance, rather than suppressing
the variability.

Maximum per-instance median sampled peak RSS is 494,676 KB for performance and
165,028 KB for smoke. The 50 ms process sampler is not a guaranteed exit-time
peak. System samples show at least 27.636 GiB available RAM and at most 768 KB
swap used across these six runs, with no indication of memory pressure.

Raw baseline index, planner hashes, manifests, coverage, independent replay
results, per-instance timing samples, work counts and sampled memory are in
`outputs/baselines/pyperplan-lmcut-bw/baseline.json`; flat data are in
`measurements.csv` and `performance-comparison.csv` beside it. The reproducible
collector is `collect.py` in that directory. Original execution logs and resource
samples remain in `outputs/fast-downward/measurements/{performance,smoke}-pyperplan-lmcut/`;
each record links its run manifest under `runs/journal_development/`.

Reproduce with `PYTHONHASHSEED=0 .venv/bin/python -m
campaigns.journal_development.smoke --profile smoke-pyperplan-lmcut` or
`--profile performance-pyperplan-lmcut`. The latter is expected to fail coverage
under the recorded limits. Decision: **retain the baseline evidence, including
timeouts**; no optimization is adopted or reverted. No full campaign was run.

### Attempt 57 — Fast Downward grounding migration

Hypothesis: replacing Cartesian Pyperplan grounding with Fast Downward's Datalog
relaxed-reachability grounder reduces preprocessing and the native task size,
while preserving every reachable FOND outcome. Parent: `2f2ab06`; fixed original
performance baseline: `c7cd597`. This is the second backend migration stage,
evaluated separately with hmax and LM-cut. The original native profiles remain
controls and the default stays Pyperplan+hmax.

Implementation: opt-in `downward-grounded` runs the pinned upstream parser,
normalizer and `instantiate.explore` after shared negative-condition compilation.
Keep no-ops, original conjunctive goals and determinized action names. Encode
its grounded positive STRIPS task using the existing Boolean SAS adapter. Reject
unsupported effects, conditions, axioms and action costs. Bypass the full
classical SAS pipeline and its unsolvable-task replacement/relevance pruning.
The unchanged reachable graph can have fewer unreachable operators/facts and a
new sorted operator order; do not presume search-work equivalence. Translator
revision/source hashes join native build metadata in manifests, snapshots and
resume checks. Journal definition 6 adds four comparison profiles; costs,
fixed selections, default flags and resource limits remain unchanged.

Initial validation: **90 tests pass**, including independent explicit transition
and shortest-path checks on 80 new random classical tasks, exhaustive policy
oracles on 30 new tiny FOND tasks with both native heuristics, typed/static
conditions, repeated arguments, unreachable static goals and no-op outcomes.
Both new 14-case smoke profiles pass all expected costs and 14 policy replays.
The first prototype run exposed an incorrect FD task-name attribute; subsequent
unit tests exposed the upstream empty-goal axiom transformation. Both adapter
issues were corrected before timing evaluation; failed development artifacts
are retained. No historical baseline bug or numerical-cost revision is involved.

A benchmark audit checks identical initial states, goals and all applicable
operator-labelled transitions on **1,698 sampled states / 11,447 transitions**
across all 23 distinct selected inputs. Three graphs are exhaustive; the rest
are bounded samples, not completeness proofs. ST Tires p08 has 1,954 reference
operators versus 277 FD-grounded operators; p09 has 2,212 versus 288. These are
unreachable-operator reductions, not deleted reachable outcomes. Audit timings
are diagnostic only, excluded from repeated unprofiled comparisons.

Before/after dry-run manifests confirm identical ordered inputs, hashes, limits,
workers and commands except the explicit backend flag. Raw audit, manifests,
failed development logs, unit-test output and resource-monitored smoke runs are
under `outputs/fast-downward-grounding/`. The pre-change default smoke passes
14/14 searches, 12/12 solvable cases and 14 replays in 22.94 s. A post-change
default smoke and repeated performance comparisons follow before the final
keep/revert decision. Candidate revision and measured outcomes are recorded
below after committing the validated implementation. No full campaign is run.

Final decision for attempt 57: **revert as inconclusive**. Candidate `aad5e03`
was reverted in `7fc3af3`, without rewriting history. Five repetitions per native
control and candidate all complete 11/11 searches, solve 10/10 solvable cases and
replay 11/11 policies with unchanged costs. Three runs left uncertainty, so the
comparison was extended to the prescribed five. All settings are as above.

| Configuration at `aad5e03` | Sum of median search times (s) | Median suite wall (s) | Geomean search speedup vs matching native control (95% bootstrap interval) |
| --- | ---: | ---: | ---: |
| Native hmax control | 9.787 | 27.964 | reference |
| FD-grounded hmax | 9.761 | 27.817 | 1.064 (0.987–1.096) |
| Native LM-cut control | 8.494 | 27.451 | reference |
| FD-grounded LM-cut | 8.438 | 27.411 | 1.073 (0.982–1.101) |

Intervals resample whole runs 4,000 times with seed 0, take per-instance medians,
then geometrically average ratios. The original `c7cd597` comparisons are 3.924×
(3.710–3.940) and 3.824× (3.500–3.844), but do not justify keeping an inconclusive
increment over the retained native parent. Summed median preprocessing is
9.031→8.891 s for hmax and 9.478→8.885 s for LM-cut. There is no established
full-suite wall-time improvement. Detailed variability, memory, per-instance
regressions and work counts are retained in `summary.json`, `per-instance.csv`
and `work-equivalence.json` under `outputs/fast-downward-grounding/`.

Search work differs only on Modified First Responders: hmax expansions
1,959→1,934 and generations 11,602→11,446; LM-cut expansions 1,784→1,772 and
generations 10,598→10,533. Doors regresses from 0.136→0.161 s (hmax) and
0.139→0.160 s (LM-cut), despite identical facts/operator fields and final work
counts. ST Tires improves from 0.0139→0.0092 s and 0.0214→0.0113 s, respectively,
but one candidate LM-cut repetition takes 0.0279 s. Maximum median process peak
RSS stays near 480,000 KB for all four configurations. Post-change default smoke
passes in 22.93 s; final new smoke runs pass in 22.93/23.34 s.

Follow-up diagnosis rejects operator ordering as the established cause of the
Doors slowdown: five isolated unprofiled runs with sorted and restored operator
orders have similar medians (approximately 0.124–0.125 s). That diagnostic loads
both grounders in one process and is not a campaign baseline. Fresh-process GC
callbacks instead record a generation-2 collection during FD-grounded search:
6,247 objects reclaimed in 0.0192 s, contributing to 0.1448 s search versus
0.1283 s for the reference. An explicit collection before search brings the
FD-grounded diagnostic to 0.1244 s, with no full collection during search. These
single-task observations identify a promising follow-up; they are not aggregate
performance evidence. Raw diagnostics are `doors-audit.json`, `doors-order/`
and `gc-*.json` beside the rejected measurements. Expected numerical costs and
planner semantics remain unchanged.

### Attempt 58 — Reclaim FD grounding temporaries during preprocessing

Hypothesis: the otherwise validated FD grounder leaves cyclic Datalog temporary
objects for Python's collector; reclaiming them once during preprocessing avoids
an unrelated full-heap collection in short searches and reduces timing variance.
Reintroduce attempt 57 with this one additional cleanup. Keep normal automatic
GC enabled and include the collection cost in measured preprocessing. Search
speedups must therefore be interpreted alongside preprocessing and total time;
this does not make that cleanup time disappear.

Parent `7fc3af3` is planner-equivalent to `2f2ab06`. Candidate revision follows
validation. Compare against attempt 57 to isolate cleanup effects, and the five
recorded matching native controls at `aad5e03` to assess the complete migration.
Those controls do not execute the new grounding/cleanup path and retain identical
inputs, flags, native build, seed and limits. Reuse their five measurements only
under those equivalent conditions. The fixed original baseline remains `c7cd597`.
New raw artifacts and resource-monitored runs are under
`outputs/fast-downward-grounding-gc/`. Repeat both fixed correctness profiles and
relevant tests before three unprofiled timing repetitions per candidate heuristic;
extend to five only if uncertainty remains. The architecture, definition 6 and
unsupported-feature checks otherwise remain exactly as documented for attempt 57.

Final evaluation of candidate **`290b89e`**: **retain the opt-in FD grounding
backend on its repeatable LM-cut search benefit**. Hmax support remains available
for correctness checks and controlled comparisons, with **no demonstrated hmax
performance improvement**. The existing default and both original native
configurations remain unchanged. Retention is justified by the requested LM-cut
migration capability and its measured gain, not by treating the inconclusive
hmax result as an improvement or invoking the code-cleanup exception. The
adapter/cleanup is one shared implementation; no individual component gain is
claimed from this combined follow-up.

All 90 tests pass again. Both new smoke configurations complete 14/14 searches,
solve 12/12 solvable cases and replay 14/14 policies with unchanged costs; suite
walls are 23.121 s (hmax) and 23.377 s (LM-cut). The post-change default also
passes, in 23.291 s. Performance completes 11/11 searches, solves 10/10 solvable
cases and replays 11/11 policies in every measured repetition. The unchanged
unsolvable instance completes with no policy. No failed search enters an average.

Candidate hmax starts with three repetitions and extends to five because of
noise; LM-cut stops after three with a clear search benefit. Each native control
has five repetitions, reused from attempt 57 under the equivalent conditions
specified above. All candidate performance manifests record `290b89e`, definition
6, seed 0, four workers, 6,000,000 KB/job, 30 s/job and the 60 s suite deadline.
Candidate smoke runs precede the commit and include the same source in their
recorded patches. No builds, diagnostics or other campaigns overlap timing runs.

| Configuration | Repetitions | Geomean search speedup vs matching native control (95% bootstrap interval) | Sum of median search times (s) | Median suite wall (range), s |
| --- | ---: | ---: | ---: | ---: |
| Native hmax control | 5 | reference | 9.787 | 27.964 (27.605–29.982) |
| FD-grounded hmax | 5 | **inconclusive:** 1.065 (0.901–1.096) | 9.965 | 27.901 (27.822–34.687) |
| Native LM-cut control | 5 | reference | 8.494 | 27.451 (27.213–30.808) |
| FD-grounded LM-cut | 3 | **1.079 (1.043–1.108)** | 8.478 | 27.700 (27.412–28.272) |

Bootstraps use the same 4,000 whole-run resamples and seed as attempt 57. The
geometric mean weights each domain equally; the LM-cut gain concentrates on
short cases and does not imply an equivalent reduction in summed search time
or end-to-end time. Suite wall time is effectively unchanged. Do not advertise
this as a total-runtime improvement. Hmax's summed median search time is 1.8%
higher than its control; this also cautions against selecting it as a new default.

Summed median parsing/compilation/grounding (including the explicit collection)
is 9.031→9.185 s for hmax and 9.478→9.393 s for LM-cut. Summed native backend/
heuristic construction is 0.345→0.303 s and 0.346→0.301 s. Some search-time
benefit reflects moving cleanup to its appropriate setup phase; it is not all
an improvement in search operations or heuristic evaluation. The cleanup's
increment relative to rejected attempt 57 is itself inconclusive: geomeans
1.001 (0.848–1.058) for hmax and 1.005 (0.974–1.095) for LM-cut. Its specific
engineering benefit is reclaiming known translation temporaries before search,
not a demonstrated aggregate speedup attributable to `gc.collect()` alone.

Doors now has medians 0.1356 s (hmax) and 0.1361 s (LM-cut), versus controls
0.1359/0.1387 s: the previous repeatable regression is removed. ST Tires medians
are 0.00935/0.01173 s versus 0.01392/0.02139 s. Hmax retains a 0.05798 s
ST Tires outlier; its exact cause is not established, and it remains in the
bootstrap. Normal GC remains enabled and this cleanup cannot prevent all later
collections or scheduling delays. LM-cut has small individual regressions:
Islands 0.960×, Tireworld-truck 0.974× and Tireworld 0.993× relative to matching
controls; these are retained and shown in the per-instance data. Expected costs
and independent replay are unchanged. Non-time statistics differ only on
Modified First Responders, with the same work-count reductions documented for
attempt 57; all intermediate/final rows are preserved in `work-equivalence.json`.

Relative to the fixed original `c7cd597`, observed cumulative search geomeans
are 3.927× (3.327–3.948) for grounded hmax and 3.843× (3.703–3.863) for grounded
LM-cut. These span rounds, with environmental-drift limitations; they are not
substitutes for the matching native-control comparison. Hmax versus LM-cut with
FD grounding is inconclusive (LM-cut/hmax geomean 0.979, interval 0.946–1.155).
No universal heuristic preference follows from this small set.

Largest per-instance median sampled peak RSS is 480,536 KB for candidate hmax
and 480,340 KB for candidate LM-cut, approximately 469 MiB. The 50 ms sampler
observes all 11 planner processes per repetition but is not an exact exit-time
peak. Candidate samples show at least 27.515 GiB available RAM and at most 768 KB
swap used. Mean system CPU busy fraction is approximately 12.6–12.7% across 24
logical CPUs, including other machine activity. There is no evidence of memory
pressure or system saturation from these runs.

Raw evidence: `outputs/fast-downward-grounding-gc/measurements/` contains logs,
reports, manifests, resource samples and revision references; `summary.json`
contains medians, variability, speedups, bootstraps and coverage; `per-instance.csv`
adds preprocessing/construction and work counts. `summarize.py` checks all cases
and assembles the comparison, explicitly reusing the five original native
controls under `outputs/fast-downward-grounding/`. `tests.log` and smoke reports
preserve validation. Rejected attempt 57 and its diagnostics are retained in
that earlier directory, including its three- and five-run summary logs. Runs
remain under ignored `runs/journal_development/` and translator/binary provenance
is captured in every new-backend manifest and snapshot.

Remaining scope: the shared Unified Planning negative-condition compiler,
Boolean SAS encoding and fact-set search boundary are still present. This
milestone replaces Pyperplan parsing/grounding, not the complete preprocessing
pipeline or a compact SAS translation. No full campaign, default switch, push,
merge or tag was performed.

### Attempt 59 — Direct compilation of negative conditions

Hypothesis: replacing Unified Planning's negative-condition-removal round trip
with a typed dual-rail transformation in the pinned FD AST reduces preprocessing
and process startup while preserving reachable FOND transitions and policy labels.
Parent: `5b966d2`; fixed original baseline: `c7cd597`. Implementation is opt-in
`downward-direct`, evaluated separately with native hmax and LM-cut against their
corresponding `downward-grounded` controls. Defaults remain unchanged.

Complement predicates retain `not_` labels. Initial complements enumerate typed
instances false in the original initial state. Lifted mirrored effects support
relaxed grounding; grounded complementary effects are reconstructed after
resolving original add/delete overlaps and parameter aliases. No-op outcomes,
original goals and determinized names are retained. Unsupported negative equality,
name collisions, nonconjunctive conditions, conditional/quantified effects, axioms
and costs fail explicitly. FD grounding/Boolean SAS/native execution stay the
same. Unified Planning imports are lazy so the direct path avoids that dependency
at runtime; legacy controls now count cold imports inside preprocessing. This
changes phase accounting and requires fresh controls, not reuse of older setup
medians. Journal definition 7 records this interface/accounting change, preserving
fixed input hashes, costs, defaults, limits and selections.

Validation before candidate commit: **93 tests pass**, including 100 new random
signed-state transition/complement checks with both heuristics, an aliased-effect
case and 30 signed FOND tasks checked against exhaustive policy oracles. Both
14-case direct smoke profiles pass all expected costs and 14 policy replays.
After lazy imports, resource-monitored direct smoke commands take approximately
13 seconds. The default before/after smoke also passes. A 23-input audit agrees
on initial states, goals and all labelled transitions on 1,698 sampled states /
11,447 transitions; three graphs are exhaustive. Others are bounded samples.

The oracle also exposed a pre-existing search limitation: initially satisfied
goals can fail to produce the valid zero-cost empty policy. Both retained
Pyperplan and original native backends reproduce it on a goal-true initial state
with a no-op action, returning no policy; independent replay gives (0,0).
`outputs/fast-downward-direct/initial-goal-audit.py` and `.json` preserve the
reproducer. The signed classical transition tests include initially true goals;
the search-level FOND oracle uses initially unsatisfied goals to evaluate this
migration independently of that historical error. Fixed profile inputs are
unaffected. This confirmed finding needs a separate correctness fix and explicit
semantic documentation; it is not a reason to preserve a bug in a future oracle.
No expected costs were changed to hide it.

Raw audit, test logs, initial/final smoke logs, dry-run manifests and measurement
scripts are in `outputs/fast-downward-direct/`. Candidate revision and repeated
unprofiled results follow. Use three fresh runs per compared configuration with
seed 0, four workers, 6,000,000 KB/job, 30 s/job and the 60 s suite deadline.
Collect per-instance search/setup times, work counts, completed/solved/replayed
coverage, suite wall time, sampled memory and machine resources. No full campaign
is requested or launched.

Final decision: **retain candidate `9540574` as the opt-in direct compiler path**.
Three fresh repetitions per configuration establish a clear setup/end-to-end
benefit; no extension to five is needed. All twelve performance runs complete
11/11 searches, solve 10/10 solvable cases and replay 11/11 policies with unchanged
expected costs. Both direct smoke configurations complete 14/14 searches, solve
12/12 solvable cases and replay all 14 policies. Resource-monitored final smoke
walls are 13.017 s for hmax and 12.886 s for LM-cut (external command time is
slightly higher). Default before/after smoke passes; **93 tests pass**.

All performance manifests use committed `9540574`, definition 7, seed 0,
four workers, 6,000,000 KB/job, 30 seconds/job and the 60-second suite deadline.
Control and candidate runs are interleaved sequentially without diagnostics,
other campaigns or builds. The earlier controls cannot replace these fresh
controls for setup-time comparisons, because lazy imports changed phase
accounting. Before/after dry-run checks confirm identical selected identities,
paths, input hashes and scientific resource settings, with four workers and
only explicitly chosen configuration/backend flags differing. Manifests and
sidecars identify the direct compiler as `boand-dual-rail-v1`.

| Configuration | Sum of median search times (s) | Sum of median preprocessing times (s) | Median suite wall (range), s | Search geomean speedup vs matching control (95% bootstrap interval) |
| --- | ---: | ---: | ---: | ---: |
| UP compiler + FD grounding, hmax | 9.949 | 30.601 | 27.295 (27.132–28.744) | reference |
| Direct compiler + FD grounding, hmax | 9.618 | 1.730 | 17.969 (17.802–18.782) | 1.023 (1.015–1.086) |
| UP compiler + FD grounding, LM-cut | 8.447 | 29.703 | 26.619 (26.595–26.690) | reference |
| Direct compiler + FD grounding, LM-cut | 8.037 | 1.725 | 18.052 (17.910–19.324) | 1.043 (1.034–1.053) |

Preprocessing includes original FOND parsing, determinization, compiler imports,
compilation, grounding and explicit temporary-object collection. Legacy UP cold
imports were outside this timer in definition 6; they are inside it in definition
7. Thus the 30-second sums do not imply the retained compiler became slower than
before. They sum eleven independent cold processes, run four at a time, and are
not suite wall times. The direct path avoids those imports and the UP parse/
compile/write round trip entirely. Native backend/heuristic construction sums
are 0.301→0.307 s for hmax and 0.298→0.304 s for LM-cut. Total suite wall speedups
are 1.52× and 1.47× (approximately 34%/32% shorter), including launch and replay.
These real end-to-end reductions are unaffected by the phase-accounting change.

Whole-run bootstrap intervals use 4,000 resamples and seed 0, followed by
per-instance medians and a geometric mean of ratios. Every intermediate/final
non-time statistics row matches the corresponding control in all 66 paired
case/repetition comparisons: expansions, generations, iterations, queue sizes,
costs and policy sizes agree. The modest search improvement is therefore not
a search-order/guidance gain; avoiding the compiler changes the Python heap and
runtime overhead. Hmax has small per-instance median regressions on Doors
(0.984×), Modified First Responders (0.973×) and ST Tires (0.965×), retained in
raw data; no substantial regression accompanies the strong setup gain. LM-cut
improves every measured per-instance search median (1.008× through 1.134×).

Observed cumulative search speedups versus fixed `c7cd597` are 4.022×
(3.976–4.068) for hmax and 3.983× (3.925–3.997) for LM-cut. These span rounds
and have environmental-drift limitations; the fresh matching controls are the
primary evidence for this milestone. Comparing direct LM-cut with direct hmax
still gives mixed domain guidance (geomean 0.990, interval 0.972–0.997) despite
LM-cut's lower summed search time. No universal heuristic/default choice follows.

Largest per-instance median sampled peak RSS drops from 480,140→383,492 KB
(hmax) and 480,488→383,372 KB (LM-cut), approximately 469→375 MiB or 20% less.
All planner processes are observed by the 50 ms sampler, but sampled high-water
RSS is not a guaranteed exit-time peak. Candidate system samples show at least
27.424 GiB available RAM and no more than 768 KB swap used. Aggregate system CPU
busy fraction is approximately 7.9–8.3%, versus 12.8–13.1% for controls, across
24 logical CPUs and including other machine activity. No memory pressure is
observed; the compiler replacement also reduces machine CPU demand on this set.

Raw evidence: `outputs/fast-downward-direct/measurements/` preserves all reports,
logs, manifests, sampled RSS and system telemetry. `summary.json` holds coverage,
medians, intervals, work counts, resource summaries and per-instance speedups;
`per-instance.csv` includes preprocessing/construction and search variability;
`work-equivalence.json` retains all compared statistics rows. `summarize.py` checks
coverage, costs, execution states, definition/limits and paired raw rows before
computing results. Audit/test logs and dry-run manifests remain beside these
files. Planner runs and their provenance/snapshots are under ignored
`runs/journal_development/`. The initial-goal correctness finding above remains
a separate documented issue; neither compiler expectations nor profile costs
were altered to suppress it.

Remaining migration scope: compact SAS variables/integer states and consolidation
of defaults/interfaces after review. This direct path still uses the shared FOND
parser/determinizer and Boolean SAS/fact-set search boundary. It intentionally
bypasses classical FD graph simplification and does not claim unrestricted PDDL
support. No full campaign, default switch, push, merge or tag was performed.

## Correctness fix: initially satisfied goals (journal definition 8)

Parent: `3b617cc`. The search root unconditionally entered `pending`, even when
its state satisfied the goal. A task with an initially true goal and a no-op
could return no solution; other tasks could return positive costs. Independent
policy replay establishes that an empty strategy is valid with `(0, 0)` costs.
This defect predates the FD migration and is evaluated separately from attempts.

Initialize the root in `goal_states` when it satisfies the goal, otherwise in
`pending`. The existing closed-policy properness, Pareto recording, output and
metadata paths then handle the empty solution normally. It requires no actions,
expansions or generations. No special early return bypasses output/provenance.
Journal definition 8 versions this corrected behavior; fixed smoke/performance
selections, costs, resources and defaults remain unchanged.

Targeted tests cover initially true and empty goals, no actions, no-ops and
an action deleting the goal, all four metrics and both heuristics under
Pyperplan and the native adapter. They compare with independent replay and
check a single empty policy file, zero costs and zero expansions/generations.
The signed random FOND direct-grounding oracle now includes initially satisfied
goals, comparing full Pareto sets against exhaustive strategy enumeration.

Raw evidence: `outputs/initial-goal-fix/` holds the parent smoke, full test log
and after-change default/direct hmax/direct LM-cut smoke/performance logs,
including references to raw planner runs and validation reports under `runs/`.
This fix is retained for correctness; no timing improvement is claimed.

The first targeted run also exposed Pyperplan LM-cut returning infinity for an
empty goal. Closed empty strategies now record zero costs directly, justified
by goal satisfaction and independent replay, rather than consulting that
estimate. The initial failing test log is preserved as `tests-first.log`.

Validation: all 94 tests pass. Parent/default smoke passes 14/14 completed,
12/12 solvable instances and 14 policy replays. After-change default and direct
hmax/LM-cut smoke profiles each pass the same gate; all three performance
profiles pass 11/11 completed, 10/10 solvable and 11 policy replays. Expected
Pareto sets remain unchanged. These are correctness runs, not repeated timing
baselines; some test execution overlapped the early profile checks, so their
wall times must not be interpreted as performance comparisons. No full campaign
or backend-default change was made.

## Migration consolidation: journal default backend (definition 9)

Parent: `046c861`. This is an interface/campaign consolidation, not another
performance attempt. The direct backend was retained and measured in attempt 59;
this milestone makes it the explicit default for journal smoke/performance.
Hmax remains the default heuristic because LM-cut guidance was mixed on the
fixed inputs. No new timing gain is claimed.

A common lightweight backend registry now selects lazy grounding factories and
native/translator/compiler provenance requirements for search and the runner.
The four existing pipelines retain their implementations and flags. Unknown
names fail before parsing; unsupported inputs and missing/stale native builds
fail explicitly without backend fallback. Legacy standalone CLI/API defaults
remain Pyperplan to preserve ICAPS campaign command behavior. Journal default
profiles now select the existing **BOAND direct hmax** configuration; named
`smoke-pyperplan-hmax` and `performance-pyperplan-hmax` profiles retain the old
**BOAND bw** selection. Configuration identifiers remain unique, and all other
comparison profiles remain available.

Journal definition 9 versions the default change. Before/after dry-run manifests
confirm identical selected identities, paths, hashes, run counts, scientific
settings, four workers, 6,000,000 KB/job and 30-second job limits. Each scheduled
command only gains `--backend downward-direct` and its configuration identifier
gains `_downward-direct`. Runtime provenance adds the verified pinned native
build, translator file hashes and `boand-dual-rail-v1` compiler marker. Expected
Pareto costs are unchanged. No ICAPS definitions or published inputs are edited.

Raw evidence: `outputs/backend-consolidation/` retains before/after manifests,
`manifest-comparison.json`, parent smoke, test logs and validated profile logs;
planner runs and snapshots remain under ignored `runs/journal_development/`.
Documentation now gives the native prerequisite build before the default
journal commands and explains explicit comparison profiles. Compact native
state IDs and direct SAS conditions remain an optional future migration stage.

Validation: all 97 tests pass, including lazy backend dispatch, explicit failure
propagation, unknown-name rejection before parsing, standalone CLI selection and
campaign default/comparison contracts. Parent smoke passes. New-default direct
hmax, explicit Pyperplan hmax and direct LM-cut each pass both fixed profiles:
14/14 smoke searches complete, 12/12 solvable cases solved and all 14 policies
replayed; performance has 11/11 complete, 10/10 solved and 11 policies replayed.
All expected Pareto sets match. Raw intermediate and final non-time statistics
are identical to the corrected parent for all 75 paired case runs across these
six profiles (`work-equivalence.json`), including expansions, generations and
policy sizes. Current default suite walls are 15.03 s (smoke) and 18.26 s
(performance); these single correctness runs are not repeated timing baselines.
Keep the consolidation and default change. No full campaign, push, merge or tag.

## Attempt 60 — compact native handles preserving state hashes

Hypothesis: keep native state IDs at the Python search boundary while retaining
legacy fact-set hashes, so state selection remains unchanged and permanent
fact-set copies/two-way ID maps can be removed. Parent: `b7b2633`; fixed original
performance baseline: `c7cd597`. Direct Boolean SAS/negative compilation and
scientific semantics remain unchanged. This is a focused state representation
experiment; direct SAS-condition compilation is not part of this candidate.

Profiles on current direct hmax Tireworld and Doors show decoding is small:
Tireworld `state_facts` takes 0.043 s and successor conversion 0.112 s cumulative
out of 6.337 s profiled execution. A large runtime benefit is unlikely; reduced
retained Python heap may still matter. Candidate `HandleStateTask` interns
compact task-local state objects holding an ID and the original decoded
fact-set hash. Native goal/heuristic calls use IDs directly; decoding occurs
once for hashing and later for output or legacy subset tie comparisons. No
permanent decoded facts or reverse fact-set-to-ID map is retained. Operator
hashes/order remain unchanged. Python-level state hashing is a potential cost.

Raw diagnostics, before/candidate smoke logs, repeated unprofiled parent
measurements (three runs), sampled planner RSS/system resources and tests are
under `outputs/native-state-handles/`; planner runs are under ignored `runs/`.
The candidate passes all 98 tests, including 40 random classical tasks with
both native heuristics, transition/goal/value/hash equivalence, canonical handle
identity and successor set iteration. Existing independent tiny FOND search
oracles and initial-goal tests also pass. Smoke completes 14/14 searches,
solves 12/12 solvable inputs and replays all 14 policies with unchanged costs;
all intermediate/final non-time rows match the parent. Candidate timing and
keep/revert decision are pending repeated unprofiled performance evaluation.

Final evaluation: candidate `c024093` versus immediate parent `b7b2633`, three
unprofiled repetitions per revision, fixed performance inputs/default direct
hmax, seed 0, four workers, 6,000,000 KB/job, 30-second job timeout and the
60-second suite deadline including replay. All runs complete 11/11 searches,
solve 10/10 solvable cases and replay all 11 policies. All 33 paired
intermediate/final non-time statistics comparisons are identical. The candidate
is therefore a pure representation change, not an altered search-work tradeoff.

Search geometric-mean speedup is **0.819×**, 95% whole-run bootstrap interval
**[0.805, 0.822]** (4,000 resamples, seed 0): a clear loss. Median search sums
increase 9.673→11.720 s and suite wall medians 18.095→19.701 s (parent external
walls 18.40–18.59 s, candidate 20.00–22.12 s). Per-instance speedups range
0.601× (Doors) through 0.993× (unsolvable Blocksworld); no instance improves.
FrozenLake is 0.675×, Chain of Rooms 0.714× and Tireworld 0.724×. Largest
per-instance median sampled peak RSS only falls 383,336→378,064 KB, about 1.4%.
RSS is sampled every 50 ms, not a guaranteed exit-time maximum. Cumulative
speedup versus historical `c7cd597` is 3.290× [3.228, 3.296], but this does not
justify regressing the corrected immediate parent; cross-round timing drift
limits that historical comparison.

Post-measurement diagnostic profiles identify 41,665,705 Python state `__hash__`
calls in Tireworld (1.366 s self time under cProfile, not an unprofiled timing
estimate), versus the C implementation of frozenset hashing in the parent.
Fact decoding remains about 0.042 s; avoiding ID-map lookups cannot offset
Python hash/equality overhead. Both parent and candidate diagnostics are retained.
Do not repeat the Python-handle approach as an inconclusive micro-optimization.
A future handle implementation would require C-level hashing and validated
legacy order preservation. Direct SAS condition/variable encoding should remain
separate and can retain the existing fact-set boundary.

**Revert** in `2f36f72`, preserving candidate history and all raw evidence.
`summarize.py`, `summary.json`, `per-instance.csv`, `work-equivalence.json`,
resource samples, tests and diagnostics are under `outputs/native-state-handles/`.
No definition/default/cost change, full campaign, push, merge or tag. This round
contains one evaluated attempt; no optimization is retained.

Revert verification: planner, execution, campaigns and tests exactly match
`b7b2633` (empty scoped Git diff). Restored-default smoke passes all coverage,
cost and replay checks in 13.27 s. No additional timing comparison is inferred.

SAS follow-up inspection: the direct compiler already returns an explicit
predicate-to-complement mapping, but `GroundedTask` currently retains only the
compiler version marker. A safe complementary-value encoding must carry that
mapping to the native adapter, rather than infer pairs from `not_` names (which
can also be ordinary user predicates). Preserve decoded fact labels, grounded
operator order, add-wins alias handling and FOND reachability semantics while
representing actual complement pairs as opposite values of one SAS variable.
Keep this separate from handle representation and classical FD simplification.
No SAS encoding change was implemented in this attempt.

## Attempt 61 — complement pairs as opposite SAS values

Hypothesis: encode explicit compiler-generated complement pairs as opposite
values of one Boolean SAS variable, reducing native variables without changing
the Python fact-set boundary or FOND grounding. Parent: `a51e9a4` (planner
identical to `b7b2633`); fixed original performance baseline: `c7cd597`.

The direct compiler's mapping now reaches `GroundedTask` as explicit grounded
pairs. `paired_sas` merges eligible pairs, maps negative conditions/goals to
value 0, combines mirrored effects after existing add-wins normalization and
reconstructs the same positive/complement fact labels when decoding. No
predicate-name inference, integer search states, classical SAS simplification
or benchmark change is involved. A pair is left as separate Boolean variables
when both values occur in a goal/precondition or its initial values are not
exclusive. Non-direct tasks use the original Boolean encoding. Manifest and
translation provenance identify `boand-paired-boolean-v1` for the direct path.
This is a candidate encoding; default selections/objectives/costs are unchanged.

All 100 tests pass, including 100 random signed classical graphs with native
bounds checked against independent exact distances, hmax compared with the
unmerged encoding, and signed FOND exhaustive-policy oracles. Targeted tests
check declared-pair-only merging, contradictory-condition fallback, transitions,
values, hashes and complement invariants. Hmax and LM-cut smoke both complete
14/14 searches, solve 12/12 solvable instances and replay all 14 policies with
unchanged costs.

An audit of all 23 distinct fixed-profile tasks compares 1,698 sampled states
and 11,447 labeled transitions per heuristic; three graphs are exhaustive,
the others stop at 80 states. Transitions, goals and hmax/LM-cut values agree
with the unmerged parent. Only Beam-walk p6/p7 and Tireworld-truck p6/p7 have
eligible dynamic pairs, one each (variables 130→129, 258→257, 54→53, 64→63,
excluding the identity auxiliary). Other complements are already static/pruned
or absent. Thus a substantial fixed-profile benefit is unlikely; small SAS
sizes alone do not justify this algorithmic complexity.

Raw evidence: `outputs/paired-sas/` retains parent smoke, three repeated
resource-monitored unprofiled parent runs per heuristic, tests, candidate smoke,
`audit.py`, `audit.json` and grounding/audit logs. Runs/manifests/snapshots remain
under ignored `runs/journal_development/`. Candidate timing/decision pending.

Final evaluation: candidate `4cdfe05`, five unprofiled runs per revision **per
heuristic**. Parent runs 1–3 use `a51e9a4`; after the candidate's runs 4–5,
revert `0aa01e7` restores identical planner/execution/campaign/test content for
parent runs 4–5 (`control-equivalence.json` records the empty scoped diff).
This preserves history and provides additional controls around the candidate.
All comparisons use fixed profiles, seed 0, four workers, 6,000,000 KB/job,
30-second jobs and a 60-second suite deadline including cost checks/replay.
All twenty performance runs complete 11/11 searches, solve 10/10 solvable
instances and replay all 11 policies. All 110 paired case/repetition comparisons of intermediate/final
non-time statistics match, including expansions/generations/queue sizes.

| Heuristic | Search geomean speedup vs parent (95% bootstrap interval) | Sum of median search times, parent→candidate | Median suite wall, parent→candidate | Largest median sampled peak RSS, parent→candidate |
| --- | --- | --- | --- | --- |
| hmax | 0.997× [0.967, 1.008] | 9.533→9.592 s | 19.023→18.292 s | 383,420→383,520 KB |
| LM-cut | 1.008× [1.001, 1.014] | 8.065→7.981 s | 18.271→18.637 s | 383,348→383,328 KB |

The hmax result remains inconclusive after five runs. LM-cut has a small
positive search-time bootstrap result (0.84%), strongest on Beam-walk (1.051×),
but the second encoder and complement-consistency/fallback machinery require
stronger evidence than this gain. Tireworld-truck's LM-cut gain is 1.009×;
no native variables change for the other nine performance cases. Hmax on
Beam-walk is 0.983× and Tireworld-truck 0.996×. Other individual ratios are
retained in `per-instance.csv`/`summary.json`; largest LM-cut regression is
Elevators 0.985×. No meaningful memory reduction is measured. Whole-suite wall
ranges overlap substantially: hmax 18.303–20.283 s parent, 18.080–20.499 s
candidate; LM-cut 18.134–21.292 s parent, 17.947–21.074 s candidate. Wall-time
median changes are not evidence of a stable end-to-end improvement.

Intervals use 4,000 whole-run bootstrap resamples with seed 0, per-instance
medians and the geometric mean of ratios. Sampled VmHWM every 50 ms may miss
exit-time peaks. Cumulative speedups versus fixed historical `c7cd597` are
4.030× [3.906, 4.056] for hmax and 4.008× [3.967, 4.015] for LM-cut; they
have cross-round environmental-drift and original-backend limitations and do
not supersede the immediate-parent comparison. Three-run summaries are retained
separately; final five-run summaries/CSV contain all samples.

**Revert / do not reapply** candidate `4cdfe05`; restored parent is `0aa01e7`.
The default remains direct FD/hmax with the established Boolean encoding,
journal definition 9. This is an algorithmic experiment, not a code cleanup
eligible for retention without a performance win. Restored-default smoke passes
14/14 completed, 12/12 solvable and 14 policy replays (14.75 s). No benchmark,
objective, expected-cost, default/profile selection or published archive change
is retained. No full campaign, push, merge or tag.

The migration's functional goals are already achieved. Further complement
encoding work is unlikely to help these domains: FD grounding has already
removed most static complement facts. Return to the measured policy/search
bottlenecks rather than extending native representations without a clear
benefit on the fixed inputs. A broader future study with many dynamic negative
conditions could revisit this independently validated candidate.

## Full ICAPS evaluation before migration merge

The user requested a full pre-merge historical comparison and selected two
configurations: direct FD/hmax and direct FD/LM-cut, both BOAND* best-worst.
`journal_icaps_comparison` definition 1 schedules 392 jobs over the exact
196 ICAPS dataset-version-2 input entries in its eleven domains. The user
approved 600 seconds/job, 6,000,000 KB/job and four workers. The published
ICAPS campaign remains unchanged (600 seconds, 8,000,000 KB/two workers).
No migration-only causal speedup is claimed from historical-machine timings.

The separate campaign driver records sampled planner VmHWM/system resources,
checks planner-source stability, then independently replays all emitted policies
(including partial-search incumbents) under separate per-instance resource/time
limits. It generates per-case/domain CSVs, JSON/Markdown coverage/cost reports,
completion/solution cactus figures and a historical-runtime scatter. Completed
searches, verified solved cases, timeouts, errors and unresolved replay are
separate metrics. Timing pairs require completed searches and identical cost
sets; historical cost differences and native-heuristic cost disagreements are
explicit review items. Replay proves policy validity/costs, not completeness.

Preflight: all 103 tests pass, including fixed-input identity, resource limits,
malformed-stat failure accounting, all-outcome cyclic replay, stale-validation
rejection, cost-disagreement filtering and valid timeout-incumbent accounting.
The unchanged journal smoke passes 14/14 complete, 12/12 solvable and 14 policy
replays in 13.21 s. Dry-run manifests confirm 392 paper jobs and 28 smoke jobs;
exact input entries, hashes, objectives and selectors match the frozen source.
Preflight artifacts are under `outputs/journal-icaps-preflight/`. End-to-end
comparison smoke and full execution are next. No merge or push has occurred.

End-to-end comparison smoke at `5b26c34` passes: both native configurations
complete 14/14, solve/replay all 12 solvable instances and all 14 policies each;
there are no expected-cost, native-cost or historical-cost discrepancies.
Reports, per-case/domain CSVs and all three PDF figures are generated under
`runs/journal_icaps_comparison/2026-10-09T12-40-33Z-smoke-b21d4e06/comparison/`.
The sampler observes all 28 planner processes, at most four concurrently, with
at least 27.980 GiB available RAM. Controller status/logs and preflight evidence
remain in ignored outputs. The full published BOAND bw inventory is 124/196
completed searches and 118/196 cases with incumbents (historical policies
unverified); parse issues: zero. This is the comparison baseline, not a claim
of 118 independently validated solved problems.

Full execution launched at source revision `86515c6` on the migration branch:
`runs/journal_icaps_comparison/2026-10-09T12-43-05Z-paper-05dc1b6e/`.
Controller status, log and live resource samples are under
`outputs/journal_icaps_comparison/2026-10-09T12-43-03Z/`; the driver performs
bounded replay and writes `comparison/report.md` plus raw CSV/JSON/PDF artifacts
automatically after execution. The long campaign is still running, not yet a
completed comparison. No merge is authorized/performed before report review.

Early observations: 39/392 executions finished; Blocksworld p03 hits the
6,000,000 KB limit while copying policy bounds (explicit MemoryError). Its
historical archive also lacks completion and records a 600-second timeout.
This is a resource/coverage failure, not an unsolvable result or a demonstrated
new correctness bug. Available RAM remains at least 11.596 GiB with only 768 KB
swap used during these samples. Keep all failures in the final coverage report.

### Full ICAPS comparison: review of two validation discrepancies

The 392 executions and bounded replay finished. FD hmax completed 145 searches
(144 automatically validated), with 136 verified solved instances; FD LM-cut
completed 151, with 145 verified solved. The automated comparison remains
`needs_investigation` because 89 executions hit their individual memory limits
and hmax Beam-walk p11 reference replay raised MemoryError. These failures remain
in the original report; the following supplemental review does not overwrite
its raw validation outcomes or historical costs.

- **Blocksworld-ex p05:** its original PDDL initial state contains both goal
  facts `(on-table b3)` and `(on b5 b4)`. Both native configurations emit the
  empty policy with `(0,0)`, which independent replay already validates. The
  historical `(1,1)` is the previously fixed initial-goal bug, addressed by
  `046c861`; it is not a migration regression. Keep the published archive intact.
- **Hmax Beam-walk p11:** a separate domain-specific transition oracle reads
  forward/backward edges, ladder locations, initial position and goal from the
  original PDDL and implements all outcomes of the three original action
  schemas with Python operators. It bypasses Unified Planning compilation and
  Cartesian grounding, and uses the independent NetworkX properness and cost
  checker. All 8,192 reachable states and 8,191 policy assignments validate:
  best cost 4,096, worst sentinel 999,999 (cycle). The oracle uses 12,286 grounded
  outcomes and 109,500 KB peak RSS under the same 6,000,000 KB virtual limit.
  Thus this policy is independently verified; the generic replay failure is a
  validation infrastructure limitation, not evidence of an invalid policy.

Evidence and repeatable domain-specific oracle: `outputs/full-review/review.py`
and `outputs/full-review/findings.json`; diagnostic preprocessing logs are in
that directory. This oracle is specific to the checked Beam-walk action schemas,
not a replacement general validator or proof of Pareto completeness. Including
this supplemental validation raises hmax verified solved coverage to 137 and
validated completed searches to 145; the original automated report continues to
show 136 and 144. No planner changes or additional campaign executions were
needed. A general scalable independent replay preprocessing path remains future
infrastructure work.

The diagnostic stack localizes the replay bottleneck to Unified Planning's
`negative_conditions_remover._compile`, which iterates `problem.initial_values`.
That property materializes every grounding of every fluent, including default
false values. Beam-walk p11 has 4,096 locations and two binary edge predicates:
those predicates alone contribute 33,554,432 potential ground fluents, despite
only 8,190 actual edges. The supplemental oracle keeps just actual edges.
Diagnostic retries bounded at 35/60/120 seconds were stopped by their deadlines;
the original full replay's MemoryError remains the recorded failure. The stack
and dependency source establish the eager materialization bottleneck without
requiring another long memory-exhausting run.

### Comparison with the local pre-development full Pyperplan/hmax run

The full local BOAND bw run is
`runs/icaps2025/2026-10-07T14-01-07Z-BOAND_bw-c6171249`, on the preparation
branch before the journal optimization rounds and native migration. It is a
separate reference from the published archive. Its final statistics mark 120
completed searches and 114 instances with incumbent policies. Only 41 completed
searches retain explicit zero exit codes: the legacy runner did not retain exit
codes for the other 79, which resumed execution records label
`legacy_exit_unknown`. Count those 79 by their final search-completion marker,
reporting this provenance limitation rather than treating them as known failures.
Old policies have not been independently revalidated in this comparison.

Against that local reference, direct FD hmax completes 145 (+25) and has 137
independently verified solved instances (+23 over old policy-bearing coverage,
including supplemental Beam-walk validation). Direct FD LM-cut completes 151
(+31) and solves 145 (+31). Neither loses any previously completed or
policy-bearing instance. Among 119 common completed instances with identical
reported Pareto costs and validated current policies, geometric-mean search
speedups are 41.144x for hmax and 35.602x for LM-cut. The only completed-cost
change is the reviewed initial-goal correction for Blocksworld-ex p05.

Raw reproducible comparison script, JSON and per-instance CSV are under
`outputs/prebranch-comparison/`. These are single measurements, not repeated
controlled estimates. Both campaigns use 600 seconds, but the old run uses
8,000,000 KB/two workers and the current run 6,000,000 KB/four workers. Search
semantics and all intervening journal optimizations differ; the gains cannot
be attributed solely to migration. The old run includes resumed attempts and
partial legacy exit provenance. Published-archive counts (124 completed,
118 policy-bearing) remain a different comparison.

The requested three-configuration coverage-over-time plot is generated by
`campaigns.journal_icaps_comparison.coverage` with the two full local run paths
above. Artifacts: `outputs/prebranch-comparison/coverage/coverage-over-time.*`,
`coverage-data.csv`, and `coverage-metadata.json`. The definition follows the
published coverage curve: completed searches, including unsolvable cases, sorted
by final elapsed search time (preprocessing excluded), connected observations
and a plateau to 600 seconds. All 588 per-instance records match the prior raw
comparison; endpoints are 120/145/151. PNG inspected, PDF/SVG export generated.
No planner runs were needed. Resource, source-revision and legacy-exit limitations
remain documented in the metadata; this is not a migration-only speedup plot.

### Retrospective report and figures

At the user's request, `docs/performance-report.md` summarizes the main measured
performance drivers through attempt 61, historical mechanisms later superseded,
correctness fixes, rejected approaches and full-suite outcomes. Reproduction:
`MPLCONFIGDIR=/tmp/boand-report-mpl PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_icaps_comparison.performance_report`.
No planner runs were launched. The portable PDF and four standalone PNG/PDF/SVG
figures are under `outputs/performance-report/`; the PDF also includes the earlier
full-suite coverage figure when available. Inputs are retained raw summary JSONs.

Figures cover wall-time medians/ranges for attempts 1–55 with smoke/performance
panels, parent search-speedup intervals, a selected smoke milestone heatmap,
and paired direct-compiler preprocessing/search/wall times. Attempt 34's failed
coverage is labelled and excluded from speedup averages. Two refinement rows
remain in the exported 58-row CSV. Migration 56–61 is explained separately rather
than splicing one-off smoke checks into repeated timing baselines. Missing or
incompatible range data are omitted; ranges are not confidence intervals.

Validation compares all 56 numeric baseline/attempt records to their source
summaries, all 84 heatmap cells to source per-instance medians, interval ordering,
figure exports, and PDF/PNG rendering. All agree. Cross-session comparisons,
correctness-version changes, different profiles, weaker legacy execution
provenance and full-suite resource differences are explicitly documented.

### Migration merged into journal development

User-authorized merge `38d344a` integrates `codex/fast-downward-backend` at
`a695630` into `codex/journal-development`, preserving all candidate/revert
history. No conflicts; the merged file tree exactly matches the validated
migration tree. Pending report/plotting changes were committed before merging.
No benchmark, published campaign or archive changes are included.

Before merge: 103 tests pass; default smoke completes 14 searches, solves 12
cases and validates 14 policies (21.63 s, with tests running concurrently;
not a performance comparison). After merge: default smoke passes all coverage,
expected costs and 14 policy replays in 13.85 s; fixed performance passes all
11 searches, 10 solvable cases, expected costs and 11 replays in 18.64 s.
These single post-merge timings are integration checks, not new baselines.
Evidence: `outputs/merge-validation/merge.json`, `tests.log`, `smoke.log` and
`performance.log`; raw runs are journal smoke `2026-10-09T14-28-39Z-smoke-58917e92`
and performance `2026-10-09T14-29-00Z-performance-55511a99`. Earlier tests cover
identical merged source; no redundant full test repetition was needed.
No push, tag or branch deletion was requested or performed.

## Authorized PRP satisficing comparison (campaign 1)

The user requests PRP on all 196 frozen ICAPS instances under the native campaign
constraints (600 seconds per instance, 6,000,000 KB virtual memory per process,
four jobs) and a first-policy coverage plot with the earlier local Pyperplan/hmax
and current direct FD/hmax/LM-cut runs, plus solution-quality comparisons.
This is a new evaluation campaign, not an optimization attempt or a change to
BOAND objectives. Definitions and commands: `campaigns/journal_prp_comparison/`.
Published archives, benchmark hashes and earlier comparison definitions remain
unchanged. No new BOAND full runs are requested or launched.

PRP installed source revision `7466c606ab8cb53e772c7798e02fab6bc24aec25`
resides outside the repo at `/media/datos/aineto/planners/`; wrappers, built
binaries and translator hashes plus untracked build products are recorded in
run provenance. Use its FF/lazy-greedy repair configuration with random seed 0,
600-second JIC budget, human-readable policy dump and zero final simulator
trials. Source inspection confirms the trials option controls only post-planning
simulation, not internal 1,000-trial policy scoring or repair. Do not time an
all-outcome classical plan as a valid nondeterministic policy. The PRP wall timer
starts at search-stage launch and ends at the post-construction simulator marker;
this conservatively records the first final closed policy, excluding translation.
Extra wall timings include the complete pipeline. BOAND uses its internal first
incumbent search timer; document the launch/measurement distinction.

Independent replay reads original PDDL and exported PRP rule/forbidden-action
priorities, grounding only the selected action and sharing static facts. It
checks all outcomes, applicability, reverse goal reachability, shortest best
cost and longest acyclic/cyclic worst cost. Policy variables map through the
preprocessed `output`, not `output.sas`. Initial integration caught case-sensitive
constant comparison against PRP's lowercase PDDL labels; normalize case as PDDL
requires and preserve the before/after validator outputs. No planner or benchmark
changes are involved. Partial policies on unsolvable cases correctly fail replay.
Cyclic worst cost is infinity; do not average the numeric display sentinel.

Preflight: 110 tests pass, including new independent cyclic, forbidden-action,
case normalization, inapplicable-action, initial-goal and Pareto/infinity tests.
Dry-run manifests validate 196 full and 14 smoke identities, exact frozen hashes,
seed/configuration and resource limits. Evidence is in
`outputs/prp-comparison-preflight/`. PRP smoke run
`runs/journal_prp_comparison/2026-10-10T06-22-10Z-smoke` has 13 executions finished
and 11 independently valid policies; Tireworld-truck p6 is still running at this
entry. Its two known unsolvable cases export incomplete rules which do not count
as solutions. Do not tune PRP to hide noncompletion or use incomplete BOAND fronts
for optimality claims. Full launch follows completion and analysis of preflight.
