# Serial composition diagnostics (definition 1)

This study separates a provable abstract FOND family from attempts to embed
gadgets in ordinary rectangular FrozenLake maps. It does not change prior
campaigns, frozen inputs, planning objectives or policy semantics.

The original FrozenLake domain is copied byte for byte into both input folders.
**`serial-topology` is not a geometric lake:** an entry has multiple directional
successors, and alternating horizontal/vertical relations encode private paths.
This is an explicit diagnostic encoding of an abstract graph. Do not pool it
with geometric ICAPS/FrozenLake benchmark results or claim a physical embedding.
`physical-ports` contains ordinary rectangular grids and no assumed front.

## Exact construction

For positive integer gap `d`, each stage chooses between nondeterministic
branches with costs `(3, 3+6d)` and `(3+2d, 3+4d)`. Each outcome follows a forced
private path to one shared exit. One deterministic connector action leads to
the next entry. All branches and actions have unit cost.

For `k` stages and `j` choices of the second mode, the strong-policy cost pair is

```
best  = 4k - 1 + 2dj
worst = (4 + 6d)k - 1 - 2dj       j = 0, ..., k
```

There are exactly `k+1` distinct nondominated pairs. The `k−1` connector actions
are included in both costs. Every pair has the same sum, and increasing `j`
strictly increases best cost while strictly decreasing worst cost.

The FrozenLake encoding admits a real extra action: from a far nondeterministic
outcome, reversing returns nondeterministically to the near outcome or stage
entry. A reachable reversal creates a cycle through the fixed stationary entry
decision, giving infinite worst cost. It cannot improve the best cost, since
the near outcome was already available directly. The all-first-mode strong
policy has globally minimal best cost and finite worst cost, so it dominates
every such cyclic policy. Other directional back edges are absent because
forced edges alternate axes. Stage exits have no bypass and every solution
must visit them in order. This establishes completeness, not just availability
of the proposed points.

Independent grounding from parsed original PDDL confirms **all** available
actions, including reversals. Complete stationary-policy enumeration matches
the formula for `k=1,2,3,4`, `d=1`, and `k=2,d=2`. There are `8^k` full
assignments (including choices at unreachable states). All larger-cardinality
claims beyond enumerated cases rely on the composition proof.

The shared-wall encoding intentionally avoids duplicate grounded operators
at merged exits. A preliminary version used distinct walls with equivalent
effects; its evidence is retained under ignored
`outputs/serial-tradeoffs/prototype-duplicate-walls/`. This was corrected before
freezing the diagnostic manifest and before planner execution.

## Bounded planner checks

The `smoke` profile schedules eight jobs: both native heuristics on three
stage counts (`k=1,2,3`, gap one) and a cost-gap control (`k=2`, gap two).
The `embedding` profile schedules two FD/hmax jobs on one/two-room physical-port
attempts. These profiles run sequentially with original-PDDL policy replay.
The larger `pilot` profile is prepared but is not part of the requested bounded
checks. All profiles use 600 seconds/job, 6,000,000 KB/job, at most four workers
and `PYTHONHASHSEED=0`. Do not overlap other campaigns.

```bash
.venv/bin/python -m unittest tests.test_serial_tradeoffs -v
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_serial_tradeoffs --profile smoke --dry-run
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_serial_tradeoffs --profile smoke
.venv/bin/python -m campaigns.journal_serial_tradeoffs.analysis --dataset runs/journal_serial_tradeoffs/<smoke-run> --output outputs/serial-tradeoffs/smoke-analysis
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_serial_tradeoffs --profile embedding --dry-run
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_serial_tradeoffs --profile embedding
.venv/bin/python -m campaigns.journal_serial_tradeoffs.analysis --dataset runs/journal_serial_tradeoffs/<embedding-run> --output outputs/serial-tradeoffs/embedding-analysis
```

Generate into a fresh destination with
`.venv/bin/python -m experiment_support.benchmark_generators.serial_tradeoffs <directory>`.
`generation.json` preserves all graph actions, static relations, physical grids,
parameters, source/domain/input hashes and reference scope. No reference costs
are assigned to physical joins before evaluation. One measurement per case
characterizes behavior rather than establishing timing speedups.
