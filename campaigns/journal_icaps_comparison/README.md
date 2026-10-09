# Full ICAPS comparison before migration merge

Definition 1 evaluates the corrected journal planner on the exact 196 frozen
ICAPS inputs across its 11 domains. It runs **FD hmax** and **FD lmcut**, both
`bw / MinSum / MaxSum / Delta / largestg / downward-direct`: **392 planner runs**.
It does not alter the published ICAPS campaign, tag, inputs or archive.

The user authorized 600 seconds per instance, 6,000,000 KB virtual memory per
planner/replay process and four workers. This full profile has no one-minute
suite deadline. Run it alone; keep planner source fixed during execution. The
monitored driver interrupts execution if planner source hashes change.

```bash
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_icaps_comparison --profile paper --dry-run
PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_icaps_comparison.run
```

Build the pinned native dependency first as described in the
[backend guide](../../docs/fast-downward-backend.md). The driver samples process
VmHWM every 50 ms and machine resources every second. Controller logs and status
are under `outputs/journal_icaps_comparison/<time>/`; durable execution records,
source/runtime/native/translator provenance, resource samples and the final
comparison are under `runs/journal_icaps_comparison/<run-id>/`.

After execution the driver validates every emitted policy, including incumbents
from timed-out searches, with at most four independent Python replay processes.
Each replay instance has its own 600-second/6,000,000 KB limit. It uses reference
UP/Pyperplan preprocessing and Python selected-action applicability/effects,
then independent graph reachability/shortest/longest costs. Replay does not prove
Pareto completeness or unsolvability. Inapplicable policies, wrong costs,
malformed/missing stats, crashes and unresolved replay are recorded explicitly.

The comparison reports completed searches separately from instances with verified
policies. Native cost sets must agree when both searches complete and validate;
otherwise investigation is required. Historical comparisons join by domain and
instance identity, not discovery order. Historical timing speedups only include
completed pairs with identical cost sets; timeouts/errors are not averaged as
successful measurements. All completed historical cost differences are retained
for review, accounting for corrected cyclic bounds/properness and initial goals.
Historical policies are not automatically certified as correct.

The archive used 8,000,000 KB/two workers and a historical machine/runtime, whereas
this study uses 6,000,000 KB/four workers and corrected semantics. A single run
per configuration is an evaluation, not a controlled migration-only speedup or
variability estimate. Configuration ordering follows the recorded scheduler.
These limitations accompany CSV/JSON/Markdown reports and standalone PDF
completion/solution cactus and search scatter plots. Raw zero times remain in
data; only plot coordinates are floored at one microsecond.

A 28-job smoke profile runs both configurations on the 14 journal correctness
instances, using copied version-9 cost expectations:

```bash
PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_icaps_comparison.run --profile smoke
```

To regenerate comparison/replay/figures after execution:

```bash
MPLBACKEND=Agg .venv/bin/python -m analysis.run journal_icaps_comparison --dataset runs/journal_icaps_comparison/<run-id>
```

Interrupted planner execution can use the shared durable resume command at the
recorded source revision; then regenerate analysis:

```bash
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_icaps_comparison --resume runs/journal_icaps_comparison/<run-id>
```
