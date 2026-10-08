# BOAND* development instructions

## Environment and organization

Use `.venv/bin/python`; do not install packages globally.

Keep shared planner, execution and analysis code in `planner/`,
`experiment_support/` and `analysis/`. Keep paper-specific definitions,
analysis rules in `campaigns/<campaign-id>/`.

Published archives belong in `results/<campaign-id>/published/`.
Generated runs and analysis belong in ignored `runs/` and `outputs/`.

Use campaign-aware commands. Consult `docs/campaigns.md` when adding or
revising a campaign; use the README for setup and researcher commands.

## Validation

Validate the behavior affected by the change.

- **Planner or execution changes:** run the affected campaign's smoke
  profile before and after relevant changes. Inspect raw output, errors,
  completion states and solution costs; replay policies when appropriate.
- **Campaign definition changes:** compare dry-run manifests for input
  selection, configurations, commands and resource limits. Run the smoke
  profile if execution behavior is affected.
- **Analysis changes:** regenerate affected figures and tables, compare
  numerical data and selection rules, and check the affected analysis commands.
- **Archive relocation:** verify file inventories and content hashes,
  update references, and confirm analysis equivalence. Do not rerun planners.
- **Documentation-only changes:** check referenced paths and commands.
  Do not rerun experiments.

For the ICAPS 2025 smoke profile:

    PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run icaps2025 --profile mini --workers 2

It runs one configuration across 31 FrozenLake instances and takes several
minutes. Use identical seeds and settings for controlled comparisons.

Run relevant tests. A dry run validates scheduling, not planner success.
Launch a full experimental campaign only when requested.

## Resources and reproducibility

This machine has 32 GB of RAM. ICAPS runs allow 8,000,000 KB of virtual
memory each. Keep at most two planner jobs running concurrently across
all campaigns unless explicitly instructed otherwise.

Never silently change experimental or analysis semantics. Distinguish
structural refactoring from infrastructure fixes and planner changes.

Do not alter benchmarks, published results or frozen input hashes merely
to obtain agreement. Published archives may move with verified identical
contents. Preserve published definitions; explicitly version scientific
changes.

Report discrepancies and validation limitations. Exact cross-machine
timing or completion agreement is not required for a structural refactor.

## Git

Do not rewrite history or amend existing commits.
Commit or tag only when explicitly requested.
Keep generated outputs, caches and temporary files out of version control.
