# Fast Downward migration prototype

Work on `codex/fast-downward-backend` starts from journal planner `c937f43`.
The first stage retains the existing PDDL compilation and Pyperplan grounding,
and sends that grounded STRIPS task to native Fast Downward execution. The
backend is experimental and opt-in: the default remains Pyperplan with hmax.

## Dependency and build

The dependency is upstream Fast Downward **26.6.0**, commit
`7ea2755269ff9398279b30f5c848e32ba6047c9c`, recorded in
`planner/backends/native/upstream.json`. Upstream and build products remain
ignored under `outputs/fast-downward/`. No global Python packages are required.
The native module uses the CPython C API and the upstream CMake dependency
selection to compile only core code and the hmax/LM-cut dependencies. It needs
CMake, Python development headers and a C++20 compiler; this host uses GCC 12.

```bash
git clone --depth 1 --branch release-26.6.0 \
  https://github.com/aibasel/downward.git outputs/fast-downward/source
.venv/bin/python -m planner.backends.native.build --compiler g++-12 --jobs 4
```

The build verifies the exact revision and a clean upstream checkout, then builds
from a generated source overlay without modifying upstream. Build provenance
records the upstream pin, compiler, Python ABI, binding source hashes and module
hash. Native loading rejects a stale binding or incompatible binary. Campaign
manifests and snapshots record the build; resume requires identical native
build provenance as well as the existing source/runtime checks.
Fast Downward is GPL-3.0-or-later; see the upstream LICENSE.md and README.

## Interface and preservation rules

`DownwardTask` exposes task-local integer state IDs, goal tests, applicability,
successor generation, fact decoding and hmax/LM-cut evaluation. All native calls
hold the GIL, and each capsule owns its task, registry and heuristic. Operators
have unit costs. The first-stage encoding uses one Boolean variable per existing
compiled fact rather than running the Fast Downward translator.

Every original operator is preserved in the grounded order, including no-ops
and dead-end outcomes. Pyperplan's add-over-delete precedence is preserved.
Fast Downward's SAS reader rejects empty effect lists and empty goals, so an
immutable true auxiliary variable represents an identity effect for a no-op
and the goal of a trivially solved task. It is omitted from decoded states.
Neither operation changes original transitions or classical relaxed costs.

Production integration uses `FactStateTask`: native IDs stay internal, while
Python search sees the existing fact sets and operator hashes. An initial
integer-state smoke candidate timed out on unsolvable ST Tires `p09` after
changing the legacy selector's set iteration order. The fact-state interface
passed the same case and preserves hmax search work. This stage therefore does
not claim the memory advantages of a fully native state representation.

## Heuristic and pruning audit

The 23 distinct inputs in the two fixed profiles compile to unconditional
STRIPS with no axioms: 0 conditional effects and 66 grounded no-op operators.
This check applies to the selected tasks, not every benchmark instance.
Fast Downward LM-cut rejects conditional effects and axioms; the adapter guards
unsupported SAS tasks before constructing the heuristic.

BOAND* does not maintain a state closed list or discard alternate paths based
on a first evaluation. Pareto pruning uses the best/worst lower bounds. The
third priority component is a tie-breaker; infinite heuristic values reject
certified dead ends. These operations do not require heuristic consistency.
Both state heuristics remain classical lower bounds on the all-outcome task.
The independent tiny-policy oracle checks the resulting FOND Pareto cost sets.
LM-cut uses the release's explicit goal-zone and border detection options,
both enabled. Its values need not match Pyperplan's implementation because
supporter choices can differ; equal values are not the correctness gate.

## Validation and evaluation

Journal definition **5** adds explicit experimental configurations and profiles.
The default configuration, fixed input selections, resource limits, expected
numerical costs and planner objectives remain unchanged from version 4. The
expected-cost files only change their campaign-version metadata. Policy replay
continues to use the existing backend, independently of native execution.

```bash
PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_development.smoke
PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_development.smoke --profile smoke-downward-hmax
PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_development.smoke --profile smoke-downward-lmcut
PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_development.smoke --profile smoke-pyperplan-lmcut
```

Replace `smoke` with `performance` in the profile names for timing comparisons.
Every command retains four workers, 6,000,000 KB/job, 30 seconds/job and the
60-second suite deadline including replay. Dry-run manifests include the native
build hash and backend command flag. Tests requiring the native module are
explicitly skipped when it has not been built; a native campaign requires it.

```bash
.venv/bin/python -m unittest tests.test_downward_backend tests.test_downward_search
```

The oracle checks transition equivalence and classical admissibility on 120
small generated tasks, plus edge cases. It exhaustively enumerates policies on
60 tiny FOND tasks and checks both backends with both heuristics. Selected-domain
sampling compares transitions, goal tests and hmax values on 1,378 states and
9,218 transitions across all 23 inputs; only three sampled task graphs are
exhaustive. This sampling is not a completeness proof for the remaining graphs.

Per-instance `.backend.json` sidecars separate parsing/compilation/grounding
from backend/heuristic construction. Existing `.stats` search times exclude
both setup phases. Heuristic evaluation time is obtained from diagnostic
profiles, not added to unprofiled timing baselines. Integral floating costs
returned by Pyperplan LM-cut are serialized as integers, fixing the existing
statistics reader incompatibility without rounding fractional values.

The next migration stage must evaluate Fast Downward grounding/translation
separately. Its default goal-relevance pruning, no-op removal and replacement
of unsolvable tasks cannot be assumed to preserve a FOND transition graph.
Do not enable it until preservation options and outcome reconstruction have
passed independent checks. The PR2 rewrite is reference material; upstream
is the dependency for this prototype.

## First-stage outcome

Prototype commit `37368cb` passes all 85 tests and both native smoke gates.
Three repeated performance runs give geometric-mean search speedups of **2.26×**
for native hmax and **2.17×** for native LM-cut against the exact parent planner.
Summed median search times are 12.10 s for the parent, 9.71 s for native hmax
and 8.46 s for native LM-cut. Suite time improves much less because existing
compilation/grounding and replay remain outside the search timer.

Native hmax preserves every recorded non-time statistics row. LM-cut reduces
Elevators expansions from 46,819 to 461 but adds overhead on Beam-walk, where
both heuristics already give initial h=256. Native LM-cut completes all cases;
Pyperplan LM-cut times out on Beam-walk in the performance profile. The default
remains unchanged while both native options are available for review. Detailed
intervals, per-case regressions, coverage and resource measurements are in
[the performance log](performance-log.md), with raw evidence under
`outputs/fast-downward/`.

A separate three-repetition BOAND* bw Pyperplan LM-cut baseline is recorded in
[the performance log](performance-log.md#additional-baseline-boand-bw-with-pyperplan-lm-cut).
It passes all 14 smoke cases but completes only 10/11 performance searches:
Beam-walk p7 times out in every repetition at the unchanged 30-second job limit.
The log includes a four-configuration per-instance timing table; raw baseline
data are under `outputs/baselines/pyperplan-lmcut-bw/`. Incomplete coverage
precludes a full-profile aggregate speedup for this configuration.
