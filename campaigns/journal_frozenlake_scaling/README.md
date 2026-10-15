# Physical FrozenLake scaling probes (definition 1)

Four fixed geometric inputs vary stage count and room size separately. The
[composition proof](../../docs/frozenlake-stage-composition.md) predicts `k+1`
finite Pareto pairs, and complete independent enumeration also verifies every
frozen reference. Cases are `(k,n)=(4,6),(6,6),(8,6),(4,10)`.
Existing campaigns, profile selections and input hashes remain unchanged.

Run sequentially: `smoke` (4 stages), `six`, `larger` (4 larger rooms), `eight`.
Each has both direct FD/hmax and FD/LM-cut: eight jobs in total, 600 seconds/job,
6,000,000 KB virtual memory/job, seed zero and at most four workers. Stop before
the next profile if search/replay does not establish its references. These are
bounded scaling probes, not a request to run a full suite.

```bash
.venv/bin/python -m unittest tests.test_frozenlake_scaling tests.test_frozenlake_stages -v
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_frozenlake_scaling --profile smoke --dry-run
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_frozenlake_scaling --profile smoke
.venv/bin/python -m campaigns.journal_frozenlake_scaling.analysis --dataset runs/journal_frozenlake_scaling/<run> --output outputs/frozenlake-scaling/smoke-analysis
```

Repeat execution/analysis with subsequent profiles after each validation.
Regenerate into a fresh destination with
`.venv/bin/python -m experiment_support.benchmark_generators.frozenlake_stage_scaling <directory>`.

Replay uses `analysis.frozenlake_policy_replay`, restricted by domain hash to
the unchanged FrozenLake domain. It checks every selected action against typed,
parsed original-PDDL preconditions and effects, then checks all reachable
outcomes, properness and costs. It avoids the legacy replay's expensive full
Pyperplan grounding on wall-heavy maps. Its costs and reachable-state counts
were cross-checked with all 18 earlier independently replayed policies.
The generic replay default and all previous analyses remain unchanged.
