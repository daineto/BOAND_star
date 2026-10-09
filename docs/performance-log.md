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
