# PRP versus BOAND* campaign 1

This explicitly requested campaign runs installed PRP on the exact 196 frozen
ICAPS inputs, with 600 seconds per complete invocation (translation included),
6,000,000 KB virtual memory per job, four workers and seed 0. Published campaigns,
benchmarks and archives remain unchanged. The `smoke` selection is the existing
14 journal instances, with these same PRP limits and no 60-second suite deadline.
PRP is satisficing; incomplete, timed-out or unsupported cases are not unsolvable.

Commands (use this external runner, not the BOAND-specific shared runner):

```bash
PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_prp_comparison.run --profile paper --dry-run
PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_prp_comparison.run --profile smoke
PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_prp_comparison.run --profile paper
PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_prp_comparison.run --profile paper --resume runs/journal_prp_comparison/RUN_ID
MPLCONFIGDIR=/tmp/boand-prp-mpl .venv/bin/python -m campaigns.journal_prp_comparison.analysis runs/journal_prp_comparison/RUN_ID
```

PRP source stays in `/media/datos/aineto/planners/`; all run files stay in ignored
`runs/`. Manifests record the installed revision, local changes and hashes of
wrappers, binaries and translator Python files. Hashes are checked before/after
execution. Resume reuses completed job records and validates configuration,
resources, inputs and dependency hashes. Do not launch other campaigns concurrently.

PRP uses its FF/lazy-greedy policy-repair configuration, overridden random seed 0,
`--jic-limit 600`, `--dump-policy 2`, and `--trials 0`. The last option disables
only the post-planning simulator; internal repair/quality evaluation remains
unchanged (1,000 evaluation trials). Exit 8/9 is PRP strong cyclic/strong success.
Policy existence or PRP's own strong-cyclic flag alone is not validation.

Independent replay interprets original PDDL directly, grounding only the selected
action. Static facts are shared rather than copied across states. Exported rules
are sorted SC-first, then distance and creation order; forbidden-action rules and
PRP's final return-if-possible fallback are respected. The variable labels are
read from preprocessed `output`, not preprocessor input `output.sas`. Replay
checks applicability and all original outcomes, reverse goal reachability,
shortest best cost and finite longest/cyclic worst costs; each replay has its own
600-second/6 GB limit and at most four workers. Unsupported formulas fail explicitly.

The first-policy coverage plot includes native BOAND hmax/LM-cut and the local
October 7 Pyperplan hmax reference. It uses first-solution times (valid incumbents
also count after later timeout), not search completion. PRP's recorded search
interval starts at wrapper search launch and ends after construction before the
(disabled) final simulator; this is a conservative bound for the first final
closed policy, excluding translation. BOAND times are its internal search wall
timer. No fabricated sub-millisecond CPU zeros are used. PRP invocation wall time
including translation is exported separately. Legacy reference policies are
labelled reported/unverified, and it used 8 GB/two workers rather than 6 GB/four.

Quality compares PRP costs to BOAND's first policy and, only when BOAND completes,
its reported Pareto frontier. Classify equal frontier point, dominated by BOAND,
dominating a BOAND point (investigate), and incomparable. A cyclic worst cost is
infinite, displayed with the existing 999999 sentinel; never divide or average
that sentinel as a finite cost. Partial fronts carry no optimality claim.
Best/worst component minima may belong to different policies; report tradeoffs.
