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
