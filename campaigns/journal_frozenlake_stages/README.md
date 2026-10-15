# Physical FrozenLake stages (definition 1)

This bounded follow-up tests actual rectangular maps, separately from the
non-geometric `journal_serial_tradeoffs` diagnostic. The original FrozenLake
domain is byte-identical. Ice tiles and walls are ordinary grid neighbors;
there are no extra predicates, goals, actions or costs.

One stage offers a twelve-step deterministic staircase and a twenty-edge
straight-corridor detour (best ten actions). Four-run corridors join copies.
Slipping across a room entrance/exit remains legal. Reference fronts come from
complete independent reachable strong-policy enumeration plus a strong-cyclic
winning-region/shortest-path bound; no additivity assumption supplies references.
Original-PDDL grounding is compared to every geometric action and outcome.

The three fixed profiles run sequentially, with both direct FD heuristics:
`smoke` checks one stage, `connected` checks two, and `extension` checks three.
Each has two jobs, 600 seconds/job, 6,000,000 KB/job, at most four workers and
seed zero. Stop before the next profile if a reference is not established.
These are bounded validation examples, not a finalized paper benchmark suite.
The fixed journal development smoke/performance selections remain unchanged.

```bash
.venv/bin/python -m unittest tests.test_frozenlake_stages -v
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_frozenlake_stages --profile smoke --dry-run
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run journal_frozenlake_stages --profile smoke
.venv/bin/python -m campaigns.journal_frozenlake_stages.analysis --dataset runs/journal_frozenlake_stages/<run> --output outputs/frozenlake-connected/smoke-analysis
```

Repeat the execution and analysis with `connected`, then `extension` only after
validation of the preceding profile. Regenerate inputs into a fresh folder:

```bash
.venv/bin/python -m experiment_support.benchmark_generators.frozenlake_stages <fresh-directory>
```

The generator records source, oracle, renderer, domain and input hashes.
`analysis.reachable_policy_oracle` rejects cyclic partial assignments when
enumerating finite policies. All cyclic proper policies have infinite worst
cost, so only their minimum achievable best cost can contribute another front
point. The nested winning-region calculation obtains this bound independently
of BOAND*. Its result and the finite enumerator are checked against exhaustive
stationary-policy enumeration on small random graphs and targeted edge cases.
Enumeration limits raise an error, never a partial front disguised as complete.

For one through three stages, respectively, exact fronts contain two, three
and four finite pairs. They fit `(17k−7+2j, 34k−14−8j)` for `j=0,...,k`.
This is an observed formula for the checked cases; a general proof for all
physical stage counts is not claimed.
