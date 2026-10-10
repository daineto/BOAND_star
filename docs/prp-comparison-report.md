# PRP versus BOAND*: first proper policy and solution quality

The October 10 PRP run covers the same 196 frozen ICAPS instances as the native
BOAND comparison: **600 seconds per invocation, 6,000,000 KB virtual memory per
job, four workers and seed 0**. PRP finds **161 independently verified proper
policies**, compared with **145 for BOAND*/FD LM-cut** and **137 for BOAND*/FD
hmax**. Its 17 weak or incomplete exports are excluded.

PRP has a net coverage advantage of 16 cases over LM-cut. On completed, paired
BOAND searches, PRP often finds a Pareto-optimal cost pair, but misses meaningful
worst-case guarantees in some cases. This comparison does not isolate the cost
of optimality alone: the planners also differ in heuristics, search and policy
representation.

## First proper-policy coverage

![First proper-policy coverage](../runs/journal_prp_comparison/2026-10-10T06-32-18Z-paper/comparison/first-solution-coverage.png)

| Planner | Within 0.1 s | Within 1 s | Within 10 s | Within 60 s | By the 600 s limit |
| --- | ---: | ---: | ---: | ---: | ---: |
| Earlier local BOAND*/Pyperplan hmax, reported | 45 | 73 | 90 | 102 | 114 |
| BOAND*/FD hmax | 103 | 123 | 131 | 136 | 137 |
| BOAND*/FD LM-cut | 108 | 128 | 136 | 143 | 145 |
| PRP | 125 | 138 | 152 | 158 | 161 |

These are first **proper** policies, not completed searches. Verified incumbents
count even when subsequent BOAND optimization runs out of time or memory. Weak
policies contribute zero. All 196 attempted inputs remain in the accounting;
failure to produce a proper policy does not establish unsolvability.

PRP solves 23 instances for which LM-cut produces no proper policy; LM-cut solves
seven for which PRP produces none. The latter are Doors p1–p3, Islands p19 and
Tireworld-truck p6, p7 and p11. PRP's additional coverage is concentrated in
Elevators, First Responders and several larger instances in other domains.
Per-domain counts and exact identities are in the generated CSV/JSON files.

BOAND leads at very short times: by 0.01 search seconds, hmax and LM-cut have
80 and 81 policies, versus PRP's 36. PRP overtakes both by 0.1 seconds and retains
the higher final coverage. The geometric mean across common successful first
policies favors BOAND by 3.92x with hmax and 2.82x with LM-cut, but many of these
cases take milliseconds. On the subsets where BOAND's first search takes at
least 0.1 seconds, PRP is faster by 6.33x over 30 hmax pairs and 11.36x over 33
LM-cut pairs. The subset rule and all per-instance times are recorded; these are
single-run comparisons, not variability estimates or full-front completion
speedups.

The timer distinction matters on tiny instances. BOAND records its internal
elapsed search time after heuristic setup. PRP records wall time from search
process launch through final policy construction, before the disabled final
simulator. This includes startup and is a conservative upper bound on discovery
of its first final proper policy. Neither search-axis timer includes translation;
PRP's full invocation/export wall time is also retained in the data.

The Pyperplan curve is the earlier **local** October 7 run, not the published
archive. It used 8,000,000 KB/two workers and older planner semantics, and its
historically accepted proper policies have not undergone the new independent
replay. It is explicitly labelled reported.

## Solution quality

![PRP cost pairs versus completed BOAND fronts](../runs/journal_prp_comparison/2026-10-10T06-32-18Z-paper/comparison/frontier-quality.png)

| BOAND reference | Paired proper first policies | Paired completed fronts | PRP cost pair on the front | PRP dominated by BOAND |
| --- | ---: | ---: | ---: | ---: |
| FD hmax | 130 | 128 | 113 | 15 |
| FD LM-cut | 138 | 134 | 116 | 18 |

Against LM-cut, **116/134 (86.6%)** PRP cost pairs match a point on a completed
BOAND Pareto front; **18/134 (13.4%)** are dominated. Matching a cost pair does
not mean identical policies. None of the verified PRP cost pairs is incomparable
with or improves a completed front, and none contradicts a completed BOAND
unsolvability result. Partial BOAND fronts carry no completeness claim.

![Best-cost comparison](../runs/journal_prp_comparison/2026-10-10T06-32-18Z-paper/comparison/best-cost-comparison.png)

Points above the diagonal have a higher PRP best cost. Across the 137 positive
best-cost pairs with LM-cut, PRP's geometric-mean best cost is **1.9% higher**
than BOAND's first policy. Its finite worst cost is also **1.9% higher** over
82 positive, jointly finite pairs. These small averages exclude an important
qualitative difference: in **13 of the 138 first-policy pairs**, PRP is cyclic
while BOAND's first policy has a finite worst cost. The reverse occurs in zero
cases. Infinite costs are never treated as the finite display sentinel 999999
in ratios.

Within the 134 completed-front pairs, BOAND offers a finite-worst policy in
**12 cases where PRP's policy is cyclic**. Eight completed fronts contain
multiple cost pairs, giving best/worst tradeoffs that a single PRP output does
not enumerate. Examples of the practical quality difference are:

| Instance | PRP (best, worst) | BOAND completed front |
| --- | --- | --- |
| FrozenLake motivating | (5, ∞) | (5, 12), (7, 11) |
| First Responders p_2_2 | (2, ∞) | (2, 6), (5, 5) |
| Elevators p06 | (20, 28) | (20, 27), (22, 22) |
| Tireworld-truck p3 | (14, ∞) | (7, 8) |

PRP's extra coverage is therefore useful, while BOAND's guarantees provide
better worst-case bounds and the complete set of tradeoffs. The observations
suggest examining compact policy representation as well as optimization
overhead: PRP's Doors p15 policy has 33 rules covering 196,606 reachable states.
That is evidence of representation compactness, not a measured causal share of
the coverage difference.

## Execution and independent validation

Installed PRP revision: `7466c606ab8cb53e772c7798e02fab6bc24aec25`. Its wrapper,
binaries and translator files are hashed in the manifest. We use its FF/lazy
greedy repair configuration with `--random-seed 0 --dump-policy 2 --trials 0
--jic-limit 600`. Zero trials disables only post-planning simulation; internal
policy-quality evaluation and repair remain enabled. The source was not tuned
or changed for this evaluation.

Execution ended with 161 reported strong-cyclic successes, 17 non-strong-cyclic
returns, 11 wall timeouts and seven memory failures. All 178 exported policies
were independently replayed against original PDDL. The 161 proper policies
include **91 strong** and **70 strong cyclic** policies; all 17 other exports
failed properness. A proper policy is applicable and closed under all original
outcomes, with every reachable state able to reach a goal. Best cost is shortest
goal distance; worst cost is longest acyclic distance or infinity when cyclic.

The validator initially spent excessive time scanning large forbidden-action
tables. Indexing rules by a shared required literal and removing duplicates
preserves their forbidden-action union. All **176 completed previous checks**
retain their status and, when valid, exact costs and reachable-state counts.
The two previous replay timeouts, Doors p14/p15, now validate in about 3.1/6.5
seconds. These are validator improvements; PRP search timings and exports are
unchanged. Previous results, source snapshots, new checks and the equivalence
audit are preserved under `revalidation/guard-indexed/` in the run directory.
An additional selection audit bypasses forbidden-action rules, as PRP does for
policies marked complete. All 178 exports retain the same properness result
and, when valid, exact costs and reachable-state counts; the audit is in
`comparison/selection-semantics-audit.json`.

PRP execution took approximately 39.1 minutes and used at most four jobs. During
execution, the minimum available machine memory was 10.7 GiB and swap usage
ranged from 37.5 to 41.25 MiB. Each replay also has a 600-second/6 GB bound.
The one-worker supplemental pass initially overlapped only the three outstanding
checks, keeping the combined count at four. The reusable revalidation command
requires the original pass to finish first. All **113 tests pass**, including
weak-policy exclusion and equivalence of indexed forbidden-action checks.

## Artifacts and reproduction

PRP execution source revision: `2f134bc`. Run and generated report:
`runs/journal_prp_comparison/2026-10-10T06-32-18Z-paper/`.
The `comparison/` directory contains the report, per-instance/quality/domain
CSVs, and all three figures in PNG, PDF and SVG. Its JSON records the analysis
source hash; supplemental replay records its own exact source snapshots/hashes.
Controller logs, manifests and tests are in `outputs/prp-comparison-preflight/`.

BOAND references are the October 9 native run
`runs/journal_icaps_comparison/2026-10-09T12-43-05Z-paper-05dc1b6e` and October 7
local reference `runs/icaps2025/2026-10-07T14-01-07Z-BOAND_bw-c6171249`.
No BOAND searches were rerun for this comparison.

See [the campaign README](../campaigns/journal_prp_comparison/README.md) for
execution commands. Regenerate this run's numerical report and figures with:

```bash
MPLCONFIGDIR=/tmp/boand-prp-mpl .venv/bin/python -m campaigns.journal_prp_comparison.analysis runs/journal_prp_comparison/2026-10-10T06-32-18Z-paper
```

Measurements use one run per instance and come from different sessions. Search
timer boundaries, the legacy resource/semantics difference, and the different
planner architectures limit causal speedup claims. Independent replay checks
policy validity and costs; it does not independently prove Pareto completeness.
