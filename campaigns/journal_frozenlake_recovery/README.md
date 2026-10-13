# FrozenLake recovery-route follow-up (definition 1)

This is a separate follow-up to the 19-instance journal trade-off pilot.
No previous manifest, input, profile, numerical reference or scientific rule
is changed. The original FrozenLake domain is copied byte for byte.

**Execution is deferred:** the user reported other experiments running and
requested no campaign launches. No BOAND jobs, smoke executions or full runs
have been launched for this collection. The definitions and input hashes have
only been checked statically; campaign dry-run commands are also deferred.

## Independently verified base construction

The 3×5 map starts at `(0, 2)` and aims at `(0, 1)`. Its lower ice tile permits
a one-step shortcut that can overshoot and return to the start. The upper/right
region gives two competing finite recovery routes. Exhaustive stationary-policy
enumeration confirms the complete front:

| Lower tile | Complete front (best, worst) | Assignments enumerated |
| --- | --- | ---: |
| Ice (`cyclic`) | (1, ∞), (3, 9), (5, 7) | 4,608 |
| Pit (`pit`) | (2, ∞), (3, 9), (5, 7) | 3,072 |

The finite pair `(5, 7)` sacrifices two best-case actions to save two worst-case
actions compared with `(3, 9)`. The third pair captures a shorter cyclic policy.
These are three-point fronts, but not three entirely finite points.

Replacing the lower ice with a pit does **not** eliminate cyclic solutions.
The direct downward action becomes improper, but an upward/downward cycle still
has best cost two. An initial hypothesis that the pit variant would have only
the two finite points was rejected by the independent oracle; no planner was
run, and no existing planner reference was changed.

Discovery used an independent exploratory C++ enumerator (seed 131). Its first
three-point candidate was attempt 12 after eight eligible layouts, in a 3×6
map. Cropping its unreachable top row gives this smaller 3×5 map; the Python
oracle independently confirmed the canonical map's front. A separate bounded
search found no all-finite three-point front in 26,890 eligible layouts. This
does not prove impossibility. That auxiliary search had finished by the
subsequent status check; no further layout searches were launched after the
user's resource constraint.

Both base maps' movements were checked against the original PDDL action
preconditions and all outcomes. The oracle tests and generation/manifest tests
passed (six targeted tests, under a second). This establishes the independent base
references; it is **not** BOAND validation.

## Parameterized inputs

`experiment_support/benchmark_generators/frozenlake_recovery.py` deterministically
generates width-three maps at heights 5, 6, 7, 8 and 10, with both lower-tile
types. Increasing height extends the shared upper recovery region. It is a
scaling hypothesis: front cardinality, quality gaps and difficulty have not
been established for larger maps. Their references remain explicitly pending.

`benchmarks/journal_tradeoffs/frozenlake_recovery/generation.json` records full
layouts, start/goal coordinates, parameters, generator/renderer/domain hashes,
PDDL hashes and reference certainty. This collection remains exploratory,
not a finalized paper benchmark. The fixed manifest contains ten instances.

## Commands for when resources are available

The following commands have not been run. Use the pinned native backend and
the project virtual environment. Both profiles use seed 0, 600 seconds/job,
6,000,000 KB virtual memory/job and four workers, with no suite deadline.

```bash
.venv/bin/python -m experiment_support.benchmark_generators.frozenlake_recovery \
  outputs/frozenlake-recovery-regenerated

PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_frozenlake_recovery \
  --profile smoke --dry-run
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_frozenlake_recovery \
  --profile smoke
.venv/bin/python -m campaigns.journal_frozenlake_recovery.analysis \
  --dataset runs/journal_frozenlake_recovery/<smoke-run> \
  --output outputs/frozenlake-recovery-smoke

PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_frozenlake_recovery \
  --profile pilot --dry-run
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_frozenlake_recovery \
  --profile pilot
.venv/bin/python -m campaigns.journal_frozenlake_recovery.analysis \
  --dataset runs/journal_frozenlake_recovery/<pilot-run> \
  --output outputs/frozenlake-recovery-pilot
```

Run the smoke validation first: four jobs, with both heuristics on the two exact
base maps. Only after that gate passes, evaluate the full 20-job collection.
Analysis replays emitted policies, requires exact base costs for completed
searches, compares completed heuristic fronts and labels partial larger fronts
as best known. The analysis execution path remains untested until campaign
execution is permitted. It refuses replay while campaign jobs are running.

Do not launch alongside other campaigns. The user's current no-campaign
instruction remains in force until lifted. Independent discovery source/logs,
the original candidate and the lightweight Python verification are retained in
ignored `outputs/frozenlake-rich-fronts/`.
