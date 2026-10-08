# BOAND*

BOAND* computes Pareto-optimal policies for bi-objective fully observable
nondeterministic (FOND) planning. It generalizes AND* to optimize best-case and
worst-case policy costs.

This repository provides the planner, benchmarks, experimental campaigns and
published results for Aineto and Scala, **“Cost-Optimal FOND Planning as
Bi-Objective Best-First Search,” ICAPS 2025**.

## Installation

Use Linux, Python 3.10, Git, Bash, and GNU `timeout` and `time`. Run the following
commands from the repository root:

```bash
git submodule update --init --recursive
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-runtime.txt
python -m pip install ./planner/pddl ./planner/pyperplan
```

The planner's `pddl`, `pyperplan` and `fondutils` dependencies are included as
pinned Git submodules. `fondutils` is loaded directly from its source directory.
Use `requirements-runtime.txt` for installation.

Keep the virtual environment activated for the commands below.

## Analyze the published results

The ICAPS 2025 archive is included in `results/icaps2025/published/`. Generate
its three heuristic comparisons, coverage plot, two quality comparisons and
coverage table without running the planner:

```bash
MPLBACKEND=Agg python -m analysis.run icaps2025 --dataset published
```

Figures, numerical data and dataset diagnostics are written to
`outputs/icaps2025/published/<analysis-time>/`. Use `--output <directory>` to
choose another destination.

See the [ICAPS 2025 campaign documentation](campaigns/icaps2025/README.md) for
configuration details, analysis conventions and known differences between the
archive and the paper.

## Run an experimental campaign

For current journal development, run the 14-instance smoke suite across the
11 ICAPS domains:

```bash
PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_development.smoke --dry-run
PYTHONHASHSEED=0 .venv/bin/python -m campaigns.journal_development.smoke
```

It uses four workers and 6,000,000 KB of virtual memory per job, with a
60-second deadline including policy and cost validation. Calibration on this
host took about 34 seconds. See the [journal development campaign](campaigns/journal_development/README.md)
for the selected instances, validation rules and performance measurements.

Campaigns define their planner configurations, benchmark inputs and resource
limits. The ICAPS 2025 campaign provides four profiles:

| Profile | Configurations | Domains | Instances | Planner runs |
| --- | ---: | ---: | ---: | ---: |
| `mini` | 1 | 1 (FrozenLake) | 31 | 31 |
| `BOAND_bw` | 1 | 11 | 196 | 196 |
| `BOAND_bw_tireworld` | 1 | 1 (Tireworld) | 16 | 16 |
| `paper` | 8 | 11 | 196 | 1,568 |

Start with the mini profile to check your installation:

```bash
python -m experiment_support.run icaps2025 --profile mini --dry-run
PYTHONHASHSEED=0 python -m experiment_support.run icaps2025 --profile mini --workers 2
```

Then run the complete paper campaign:

```bash
python -m experiment_support.run icaps2025 --profile paper --dry-run
PYTHONHASHSEED=0 python -m experiment_support.run icaps2025 --profile paper --workers 2
```

A dry run verifies the selected input hashes and prints the scheduled commands
without executing the planner. All profiles use a 600-second limit and
8,000,000 KB of virtual memory per planner run. The default is two workers;
choose concurrency according to available memory, including any other running
campaigns. The full campaign can take several days.

Inputs are fixed by `campaigns/icaps2025/instances.json`. Use the committed
benchmarks to reproduce this campaign. `PYTHONHASHSEED=0` controls Python hash
ordering for comparisons; timing and completion can still vary across machines.

Each new campaign creates `runs/icaps2025/<run-id>/` and prints its location.
The directory contains planner output, a run manifest, and source and environment
provenance. Use `--output-root <directory>` to choose another parent directory.
Keep planner code unchanged while a campaign is running.

### Resume an interrupted run

Resume uses the recorded profile, inputs, configuration and resource limits:

```bash
PYTHONHASHSEED=0 python -m experiment_support.run icaps2025 \
  --resume "runs/icaps2025/<run-id>" --workers 2 --dry-run
PYTHONHASHSEED=0 python -m experiment_support.run icaps2025 \
  --resume "runs/icaps2025/<run-id>" --workers 2
```

Finished executions are skipped, including timeouts and planner failures.
Interrupted or unstarted jobs get new attempt directories; previous output is
preserved. Resume checks benchmark hashes, planner source, installed dependencies,
configuration flags, resource limits and `PYTHONHASHSEED`. Worker counts may change.
Inspection and analysis select the latest finished attempt, or the latest attempt
if none has finished. Older runs without execution records are recovered only
where collected metadata and a complete timing footer establish completion.

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
python -m analysis.inspect_run "runs/icaps2025/<run-id>" \
  --reference results/icaps2025/published > outputs/mini-comparison.json
python -m analysis.validate_policies "runs/icaps2025/<run-id>"
```

The inspector compares completion states, costs and non-time statistics. The
policy validator independently replays the FrozenLake policies and checks
their costs.

Generate the paper figures from a completed `paper` run:

```bash
MPLBACKEND=Agg python -m analysis.run icaps2025 \
  --dataset "runs/icaps2025/<paper-run-id>"
```

Analysis outputs are saved under the run's `analysis/<analysis-time>/`
directory. Published archives are kept separate from newly generated results.

## Run the planner on one problem

```bash
python planner/planner.py benchmarks/frozenlake/domain.pddl \
  benchmarks/frozenlake/motivating.pddl outputs/example \
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
- `benchmarks/`: PDDL domains and problem instances.
- `campaigns/<campaign-id>/`: paper-specific configurations, input manifests,
  analysis commands.
- `experiment_support/` and `analysis/`: shared execution and analysis tools.
- `results/<campaign-id>/published/`: published result archives.
- `runs/` and `outputs/`: generated experiments and analysis, excluded from Git.
- `generators/`: benchmark-generation notebooks.
- `tests/`: scheduling and analysis checks.

To add an experimental campaign for another paper, follow
[the campaign guide](docs/campaigns.md). New campaigns provide their own
configurations, input selection, smoke profile and analysis rules.

Run the lightweight tests with:

```bash
python -m unittest discover -s tests -v
```
