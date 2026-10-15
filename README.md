# BOAND*

BOAND* computes Pareto-optimal policies for bi-objective fully observable
nondeterministic (FOND) planning. It generalizes AND* to optimize best-case and
worst-case policy costs.

This branch develops BOAND* for a new journal study. It also preserves the
benchmarks, campaign definitions and published results for Aineto and Scala,
**“Cost-Optimal FOND Planning as Bi-Objective Best-First Search,” ICAPS 2025**.
The `icaps2025` tag preserves the original paper implementation; the current
planner includes subsequent correctness fixes and backend improvements.

## Current journal work

Journal development uses direct Fast Downward/hmax for its fixed correctness
and performance profiles. The native hmax/LM-cut migration and full ICAPS/PRP
comparisons are documented in these reports, whose reviewed figures are
included in the repository:

- [Performance improvements and backend migration](docs/performance-report.md).
- [PRP coverage and solution-quality comparison](docs/prp-comparison-report.md).
- [FrozenLake benchmark pilot](docs/frozenlake-pilot-report.md).
- [Three-point FrozenLake recovery-route evaluation](docs/frozenlake-recovery-report.md).
- [Serial Pareto-front scaling: proof and embedding diagnostics](docs/serial-tradeoff-report.md).
- [Physical FrozenLake stages: verified fronts of sizes 2–4](docs/frozenlake-stages-report.md).

New benchmark collections are exploratory and separate from the preserved
ICAPS inputs:

| Campaign | Status | Inputs | Purpose |
| --- | --- | ---: | --- |
| `journal_tradeoffs` | Pilot completed | 19 fixed candidates | FrozenLake quality/difficulty evaluation with both native heuristics. |
| Adaptive pilot follow-up | Completed | 5 additional candidates | Wider layouts and a mixed strong/strong-cyclic example; outside the fixed pilot manifest. |
| `journal_frozenlake_recovery` | Smoke and pilot completed | 10 candidates | Three-point fronts at every tested height, confirmed with both native heuristics. |

See the [trade-off pilot guide](campaigns/journal_tradeoffs/README.md) and
[recovery-route guide](campaigns/journal_frozenlake_recovery/README.md) for
inputs, reference certainty and commands. Recovery base fronts are independently
exact; larger fronts rely on completed BOAND searches and policy replay. Measured
search times range from about 0.0015 to 3.32 seconds. Neither collection is a
finalized paper
benchmark, and neither replaces the journal development smoke/performance
profiles.

## Installation

Use Linux, Python 3.10, Git, Bash, and GNU `timeout` and `time`. Run the following
commands from the repository root:

```bash
git submodule update --init --recursive
python3.10 -m venv .venv
source .venv/bin/activate
.venv/bin/python -m pip install -r requirements-runtime.txt
.venv/bin/python -m pip install ./planner/pddl ./planner/pyperplan
```

The planner's `pddl`, `pyperplan` and `fondutils` dependencies are included as
pinned Git submodules. `fondutils` is loaded directly from its source directory.
Use `requirements-runtime.txt` for installation.

The commands below use `.venv/bin/python` explicitly.

## Analyze the published results

The ICAPS 2025 archive is included in `results/icaps2025/published/`. Generate
its three heuristic comparisons, coverage plot, two quality comparisons and
coverage table without running the planner:

```bash
MPLBACKEND=Agg .venv/bin/python -m analysis.run icaps2025 --dataset published
```

Figures, numerical data and dataset diagnostics are written to
`outputs/icaps2025/published/<analysis-time>/`. Use `--output <directory>` to
choose another destination.

See the [ICAPS 2025 campaign documentation](campaigns/icaps2025/README.md) for
configuration details, analysis conventions and known differences between the
archive and the paper.

## Run an experimental campaign

Journal development uses the direct Fast Downward backend with hmax. Build the
pinned native dependency once before running its profiles:

```bash
git clone --depth 1 --branch release-26.6.0 \
  https://github.com/aibasel/downward.git outputs/fast-downward/source
.venv/bin/python -m planner.backends.native.build --compiler g++-12 --jobs 4
```

This requires CMake, Python development headers and a C++20 compiler. See the
[backend guide](docs/fast-downward-backend.md) for build verification, supported
PDDL and alternative backends. A missing or stale native build fails explicitly.

For current journal development, run the 14-instance smoke suite across the
11 ICAPS domains:

```bash
PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_development.smoke --dry-run
PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_development.smoke
```

It uses four workers and 6,000,000 KB of virtual memory per job, with a
60-second deadline including policy and cost validation. See the
[journal development campaign](campaigns/journal_development/README.md)
for the selected instances, validation rules and performance measurements.

For optimization timing, use the separate fixed 11-instance performance profile:

```bash
PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_development.smoke --profile performance
```

It retains the same resource limits and one-minute deadline. Keep the original
smoke profile as the correctness gate and establish separate timing baselines.
Use `--profile smoke-pyperplan-hmax` or `--profile performance-pyperplan-hmax`
for explicit Pyperplan comparisons, and `smoke-direct-lmcut` or
`performance-direct-lmcut` for native LM-cut. Standalone planner calls and ICAPS
campaign configurations retain Pyperplan defaults.


Campaigns define their planner configurations, benchmark inputs and resource
limits. The ICAPS 2025 campaign provides four profiles:

| Profile | Configurations | Domains | Instances | Planner runs |
| --- | ---: | ---: | ---: | ---: |
| `mini` | 1 | 1 (FrozenLake) | 31 | 31 |
| `BOAND_bw` | 1 | 11 | 196 | 196 |
| `BOAND_bw_tireworld` | 1 | 1 (Tireworld) | 16 | 16 |
| `paper` | 8 | 11 | 196 | 1,568 |

For a historical-campaign check, use the mini profile:

```bash
.venv/bin/python -m experiment_support.run icaps2025 --profile mini --dry-run
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run icaps2025 --profile mini --workers 2
```

Then run the complete paper campaign:

```bash
.venv/bin/python -m experiment_support.run icaps2025 --profile paper --dry-run
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run icaps2025 --profile paper --workers 2
```

A dry run verifies the selected input hashes and prints the scheduled commands
without executing the planner. ICAPS profiles use a 600-second limit and
8,000,000 KB of virtual memory per planner run. The default is two workers;
the journal campaigns use four workers and 6,000,000 KB/job. Do not run
campaigns concurrently on this machine. The full ICAPS paper campaign can take
several days.

Inputs are fixed by `campaigns/icaps2025/instances.json`. Use the committed
benchmarks to reproduce this campaign. `PYTHONHASHSEED=0` controls Python hash
ordering for comparisons; timing and completion can still vary across machines.

Each ICAPS run creates `runs/icaps2025/<run-id>/` and prints its location.
The directory contains planner output, a run manifest, and source and environment
provenance. Use `--output-root <directory>` to choose another parent directory.
Keep planner code unchanged while a campaign is running.

### Resume an interrupted run

Resume uses the recorded profile, inputs, configuration and resource limits:

```bash
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run icaps2025 \
  --resume "runs/icaps2025/<run-id>" --workers 2 --dry-run
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run icaps2025 \
  --resume "runs/icaps2025/<run-id>" --workers 2
```

Finished executions are skipped, including timeouts and planner failures.
Interrupted or unstarted jobs get new attempt directories; previous output is
preserved. Resume checks benchmark hashes, planner source, installed dependencies,
configuration flags, resource limits and `PYTHONHASHSEED`. Worker counts may change.
Inspection and analysis select the latest finished attempt, or the latest attempt
if none has finished. Older runs without execution records are recovered only
where collected metadata and a complete timing footer establish completion.

The benchmark relocation to `benchmarks/icaps2025/` is recorded in exact
manifest-migration ledgers, allowing historical result analysis. Historical
execution records retain their original paths; those migrations do not allow
resuming runs with changed paths. Start a new run from the current definitions
or use the recorded source revision for an older execution.

For remote campaigns, run inside `tmux` on the server so the VPN or SSH
connection can be disconnected:

```bash
tmux new -s boand-campaign
# Inside tmux, from the repository directory:
PYTHONHASHSEED=0 .venv/bin/python -m experiment_support.run icaps2025 \
  --profile BOAND_bw --workers 2
```

Detach with **Ctrl-b**, then **d**. Reconnect with
`tmux attach -t boand-campaign`. Use the resume command inside tmux when
continuing an interrupted run.

### Inspect and analyze a completed run

Inspect a mini run and compare it with the corresponding archived configuration:

```bash
mkdir -p outputs
.venv/bin/python -m analysis.inspect_run "runs/icaps2025/<run-id>" \
  --reference results/icaps2025/published > outputs/mini-comparison.json
.venv/bin/python -m analysis.validate_policies "runs/icaps2025/<run-id>"
```

The inspector compares completion states, costs and non-time statistics. The
policy validator independently replays the FrozenLake policies and checks
their costs.

Generate the paper figures from a completed `paper` run:

```bash
MPLBACKEND=Agg .venv/bin/python -m analysis.run icaps2025 \
  --dataset "runs/icaps2025/<paper-run-id>"
```

Analysis outputs are saved under the run's `analysis/<analysis-time>/`
directory. Published archives are kept separate from newly generated results.

## Run the planner on one problem

```bash
.venv/bin/python planner/planner.py benchmarks/icaps2025/frozenlake/domain.pddl \
  benchmarks/icaps2025/frozenlake/motivating.pddl outputs/example \
  -m bw -ch hmax -bh MinSum -wh MaxSum -sh Delta -s bounds
```

| Option | Purpose | Values |
| --- | --- | --- |
| `-m` | Optimization objectives | `bw`, `wb`, `b`, `w` |
| `-ch` | Classical heuristic | `hmax`, `lmcut` |
| `-bh` | Best-case heuristic | `Blind`, `SumMin`, `MinSum` |
| `-wh` | Worst-case heuristic | `Blind`, `MaxSum` |
| `-sh` | Policy-size heuristic | `Zero`, `Delta` |
| `-s` | State selection | `random`, `best`, `largestg`, `bounds` |
| `--backend` | Grounding and heuristic backend | See the [backend guide](docs/fast-downward-backend.md); use `downward-direct` for the current journal backend. |

The example above uses the standalone Pyperplan default. To use native grounding
and LM-cut, add `--backend downward-direct` and replace `-ch hmax` with
`-ch lmcut` after building the pinned dependency.

The output directory contains policies (`.boand.NNN.out`) and semicolon-separated
statistics (`.stats`):

```text
best;worst;size;time;iterations;expansions;generations;max_open
```

Each solution produces a statistics row. A final row beginning `-1;-1;-1`
indicates search completion; solutions without that marker represent a partial
computation. The time column measures elapsed search time after preprocessing.

Preprocessing creates `aux_domain.pddl` and `aux_problem.pddl` in the current
working directory. Use separate working directories for concurrent direct
planner calls. Campaign execution isolates the working directory for each job.

## Repository organization

- `planner/`: planner implementation and dependency submodules.
- `benchmarks/icaps2025/`: the preserved 11-domain ICAPS input collection.
- `benchmarks/legacy_extras/`: existing domains outside the ICAPS selection.
- `benchmarks/journal_tradeoffs/`: new FrozenLake pilot, supplementary and
  recovery-route candidates, with generation metadata.
- `campaigns/<campaign-id>/`: paper-specific configurations, input manifests,
  analysis commands.
- `experiment_support/` and `analysis/`: shared execution and analysis tools.
- `experiment_support/benchmark_generators/`: reproducible benchmark generators.
- `results/<campaign-id>/published/`: published result archives.
- `runs/` and `outputs/`: generated experiments and analysis, excluded from Git.
- `generators/`: benchmark-generation notebooks.
- `docs/figures/`: reviewed, committed report figures and their source/hash manifest.
- `tests/`: planner correctness, backend, generation, scheduling and analysis checks.

To add an experimental campaign for another paper, follow
[the campaign guide](docs/campaigns.md). New campaigns provide their own
configurations, input selection, smoke profile and analysis rules.

Run the lightweight tests with:

```bash
.venv/bin/python -m unittest discover -s tests -v
```
