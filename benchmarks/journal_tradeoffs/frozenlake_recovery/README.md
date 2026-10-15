# Recovery-route candidate family

Ten deterministic candidates for a separate FrozenLake follow-up.
The original domain is unchanged. The 3×5 base maps have independently verified
three-point fronts:

- `recovery-3x5-cyclic`: (1, ∞), (3, 9), (5, 7).
- `recovery-3x5-pit`: (2, ∞), (3, 9), (5, 7).

The 2026-10-15 evaluation completed all 20 native-heuristic jobs and replayed
all 60 policies. Every tested map has three Pareto pairs; completed search
times range from about 0.0015 to 3.32 seconds. Larger references rely on BOAND
completion, rather than independent exhaustive enumeration.
Full grids, source/input hashes, parameters and reference certainty are in
`generation.json` (reference labels describe knowledge at construction time).
Reproduce with the version-1 generator in
`experiment_support/benchmark_generators/frozenlake_recovery.py`.

See `campaigns/journal_frozenlake_recovery/README.md` for discovery evidence,
validation limitations and commands, and `docs/frozenlake-recovery-report.md`
for the completed evaluation. The initial no-campaign restriction was lifted
before execution; the original frozen manifest is unchanged.
