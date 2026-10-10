# Adaptive FrozenLake follow-up

These five inputs were selected after inspecting the fixed 19-instance pilot.
They are not part of its frozen manifest. Four widen the corner layout; the
fifth was found by the eligible-small-map exhaustive search (seed 23, attempt
5) and has a mixed strong/strong-cyclic front.

The unchanged original domain, full grids, discovery/generation parameters,
renderer revision/hash, PDDL hashes, and observed fronts are recorded in
`generation.json`. `reference_certainty` distinguishes independently exhaustive
references from completed BOAND results. Generate each PDDL from its record
using `experiment_support.benchmark_generators.frozenlake.render(record)`.

Both direct FD heuristics completed all five searches and all 12 emitted
policies passed original-PDDL replay under the same 600-second, 6,000,000 KB
and four-worker limits as the pilot. Wider corners have the singleton front
`(1, ∞)`; the mixed example has `(2, ∞), (3, 3)`.

Independent enumeration confirmed the 4×3 corner (13,824 assignments), 4×4
corner (1,990,656 assignments), and mixed example (144 assignments). The
larger oracle budget was explicitly raised to 2,000,000 for this follow-up;
the fixed pilot's default remains 200,000. Raw execution/replay records are in
ignored `runs/frozenlake-pilot-supplemental/`; analysis and discovery scripts
are retained in ignored `outputs/frozenlake-tradeoffs/`.
