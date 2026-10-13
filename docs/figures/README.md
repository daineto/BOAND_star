# Figures included in repository reports

These reviewed PNGs are committed so Markdown reports render on GitHub and in
a fresh checkout. Subdirectories group images by report or comparison.
`manifest.json` records the referring report, original generated artifact path
and SHA-256 hash. The initial copies are byte-identical to their sources.

Raw measurements, intermediate outputs and generated PDF/SVG versions remain
in ignored `outputs/` or `runs/`. The reports document regeneration commands.
Regeneration writes to those original artifact directories; review the result,
copy the selected PNGs into the corresponding folder here, and update the
manifest hashes. Report links must stay relative to the report's directory.

This is a deliberate exception to excluding generated artifacts from version
control. Do not add unrelated plots, caches or raw experiment data here.
