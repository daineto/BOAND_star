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
