# New paper campaign

Replace this title, the `new_paper` ID, and the default example configuration.
Record the paper citation, dataset origin, scientific limits, smoke subset,
expected output figures/tables, and known reproduction discrepancies here.

Freeze the chosen input collection once, then review its hashes and selection:

```bash
python -m experiment_support.freeze_inputs --campaign new_paper \
  --domain frozenlake=benchmarks/frozenlake \
  --output campaigns/new_paper/instances.json
python -m experiment_support.run new_paper --profile smoke --dry-run
PYTHONHASHSEED=0 python -m experiment_support.run new_paper --profile smoke
```

The starter smoke profile contains only FrozenLake's motivating example.
Choose representative instances for this paper's configurations and domains.
For an actual generated run, record validation results and extend the analysis:

```bash
python -m analysis.run new_paper --dataset runs/new_paper/<run-id> \
  --output outputs/new_paper/analysis
```

Before publishing, preserve the campaign definition, input manifest, analysis
rules, source/environment provenance, and final dataset. Document the archive
location as `results/<campaign-id>/published/` in `Campaign.archive_root`
when appropriate. Materially different
follow-up studies should use a new ID or an explicitly maintained revision.
