# Adding and maintaining paper campaigns

Scientific definitions live in `campaigns/<id>/`; shared mechanics live in
`experiment_support/` and `analysis/`. ICAPS 2025 is the first campaign, not a
shared default for future papers. Compatibility imports preserve old ICAPS
scripts, while new papers pass their own configurations and domain lists.

## Create a campaign

1. Copy `docs/campaign-template/` to `campaigns/new_paper/` (choose a descriptive
   lowercase ID with underscores).
2. Update the ID, analysis module, configurations, per-run resource settings,
   and smoke subset in `campaign.py`. The `paper` profile is the complete
   campaign; smaller profiles may select named domains or exact `(domain, instance)`
   identities. The ICAPS `mini` profile intentionally retains all 31 FrozenLake
   problems; future papers should choose a small representative smoke subset.
3. Explicitly freeze the intended inputs, once:

   ```bash
   python -m experiment_support.freeze_inputs --campaign new_paper \
     --domain frozenlake=benchmarks/frozenlake \
     --output campaigns/new_paper/instances.json
   ```

   Repeat `--domain LABEL=PATH` for multiple domains. At this authoring step,
   the helper uses the runner's PDDL collector and records domain/problem pairs
   and SHA-256 hashes. Review the manifest before publishing. The helper refuses
   to overwrite an existing manifest. Launching never discovers additional files.
4. Dry-run and then execute the smoke subset:

   ```bash
   python -m experiment_support.run new_paper --profile smoke --dry-run
   PYTHONHASHSEED=0 python -m experiment_support.run new_paper --profile smoke --workers 2
   ```

5. Add scientific calculations and plot specifications to the campaign's
   `analysis.py`, using shared loading/plotting helpers. The template exports
   a per-run CSV and dataset identity; extend its validation as you add figures.
   Expose the analysis through the campaign's command-line entry point.
   Keep data loading, selection rules and plotting functions reusable.
6. Validate the complete manifest and execute the full campaign when ready.
   Save publication provenance and reproduction notes in that campaign's README.

## Definition and manifest versions

`Campaign.schema_version` and the instance JSON `schema_version` describe their
formats (currently 1). `Campaign.version` describes the scientific definition,
while `dataset_version` documents the frozen input collection. Run and analysis
manifests also declare their format versions. Unsupported schemas are rejected.

After publication, retain the campaign definition, input manifest, and scientific
analysis rules. A materially revised study should get a new campaign ID, or be
maintained at a separately documented Git revision and definition version.
Do not edit a published manifest to accept changed benchmark hashes. Keep
configuration and domain labels consistent across manifests and results.

A verified metadata-only input-manifest migration may be declared in
`manifest-migrations.json`, next to `instances.json`. The ledger declares
`schema_version`, `campaign_id`, `campaign_version`, and a `migrations` list
with exact `from_sha256`, `to_sha256` and `reason` fields. Verify that selected
input paths, hashes and order are unchanged before recording a migration.
Dataset resolution accepts only the recorded hash pair and reports its use;
new run provenance includes the ledger. Changes to inputs or scientific
settings require a scientific revision rather than a metadata migration.

The external executor has one global timeout per environment; configurations
with mixed timeouts are rejected. Use separate campaign definitions when
per-run limits differ. Worker counts are execution choices, not scientific
configuration names, and may be overridden for a different machine. This
32 GB host defaults to two workers for 8 GB planner jobs.

## What each run records

Runs default to `runs/<campaign-id>/<UTC-time>-<profile>-<unique-id>/`, ignored
by Git. `--output-root` changes the parent, not the unique per-run directory.
Each directory contains:

```text
manifest.json
provenance/
  campaign.json              # Resolved definition, including all profiles
  campaign.py                # Definition source at launch
  instances.json             # Selected frozen input entries
  requirements.freeze.txt    # Actual installed dependencies
  source.patch               # Tracked changes plus non-ignored untracked files
  submodules/<path>/
    state.json               # Actual submodule revision and dirty status
    source.patch             # Submodule tracked/untracked changes
results/EVALUATION/RUN_<executor-time>/...
  <configuration>/<domain>/<instance>/execution.json
attempts/<resume-time>/...   # Preserved retries and resumed runner source
scripts/                    # External runner's scripts
analysis/<analysis-time>/... # Analysis outputs when analyzing this run
```

The manifest records the base Git revision, dirty state, submodule revisions,
source-snapshot hashes, Python environment, CPU/memory information, hash seed,
scientific limits, worker count, verified input hashes, and actual commands.
`result_root` identifies the nested configuration root relative to the run.
`execution_finished` means every job has a finished execution record; inspect
raw statistics to determine which planners completed their search.

## Interrupted executions

`python -m experiment_support.run <campaign-id> --resume <run-directory>` uses
the recorded profile. Add `--dry-run` to inspect which jobs need retrying.
Timeouts, memory failures and other planner exit codes are finished executions;
interrupted, unstarted and infrastructure-failed jobs remain pending.
An atomic `execution.json` distinguishes these outcomes from search completion.
The controller holds a run lock and checks for surviving job processes before
resuming. Graceful interruption stops its active process groups.

Resume verifies input selection and hashes, flags, resource limits, Python,
installed dependencies, hash seed and planner Python source. Worker counts may
change. Planner sources in older runs are reconstructed from their recorded
Git revision, patches and submodule snapshots. Python build/cache directories
are excluded from source fingerprints.

Earlier runs without execution records are imported conservatively: a collected
job and a complete `real`/`user`/`sys` timing footer establish a finished
execution, whose exit code remains unknown. Ambiguous jobs are retried.
Previous artifacts are retained; new attempts go under `attempts/`. The manifest
lists each job's attempt directories and each resumption's environment and
runner source snapshot. Analysis retains the original instance discovery order
and selects the latest finished attempt, or latest attempt when none finished.

Run remote campaigns inside a persistent server session such as `tmux`.

## Source reconstruction

The patch and Git revision describe source at launch. Keep planner source
unchanged during a campaign: the external executor invokes the working-tree
planner, so editing it mid-run could mix implementations. Ignored local files
are not included in Git-based source provenance. Retain the original Git
repository/submodule revisions and benchmark files as well as the run directory;
this provenance is a reconstruction record, not an executable environment image.

## Dataset-specific analysis

Use `python -m analysis.run <campaign-id> --dataset <run-directory>` to dispatch
the campaign's analysis. ICAPS also accepts `--dataset published`, which maps
to `results/icaps2025/published/`. Published archives belong under
`results/<campaign-id>/published/`; new papers declare that location in
`Campaign.archive_root` when an archive exists. Raw legacy configuration roots remain
supported without guessing or merging campaigns.

Analysis manifests record the selected dataset, statistics-file hashes,
source state, and settings. ICAPS exports its six figures, source point CSVs,
Table 1, per-run records, and diagnostics. It refuses a mini dataset for the
six full-paper outputs. A manifested run from another campaign, another definition
version, or another frozen instance manifest is rejected. Unmanifested legacy
roots rely on the explicitly selected campaign and cannot provide that identity
check.

For a new paper, add tests for its scientific selections and manifest contracts.
Keep the common mini smoke test for planner/infrastructure changes, and verify
that unrelated benchmark additions do not expand a frozen campaign. Published
cross-machine runtime or coverage matching is not a refactoring criterion.
