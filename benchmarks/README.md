# Benchmark collections

- `icaps2025/`: the 11 domains selected by the published ICAPS campaign.
  Existing PDDL files are preserved byte for byte. Campaign manifests select
  frozen subsets by identity and content hash.
- `legacy_extras/`: the existing `st_blocksworld` and `st_first_responders`
  inputs, which are not selected by the ICAPS campaign.
- `journal_tradeoffs/`: reproducibly generated candidates for the new journal
  benchmark. The FrozenLake pilot collection is exploratory; its final paper
  selection is pending review.

New journal trade-off inputs should form a separate collection. The initial
verified FrozenLake examples currently live in
`campaigns/journal_development/examples/frozenlake/` and are not included in
the frozen ICAPS, smoke or performance selections.

The 2026-10-10 relocation changes paths only. Published archives and historical
run provenance retain their original contents. Campaign manifest migration
ledgers preserve historical result loading without changing scientific
definitions or input hashes.

Relocation validation checked all 293 original files and all 26 profiles across
the four campaigns. Historical BOAND datasets load through exact migration
records, and regenerating the PRP comparison produced identical coverage and
quality CSVs. All 116 tests passed; no planners were rerun. Audit snapshots and
results are retained in ignored `outputs/benchmark-relocation/`.
