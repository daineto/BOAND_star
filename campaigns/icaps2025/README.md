# ICAPS 2025 experimental campaign

This campaign accompanies Aineto and Scala, **“Cost-Optimal FOND Planning as
Bi-Objective Best-First Search,” ICAPS 2025**. It provides the configurations,
benchmarks and analysis for the paper's three heuristic comparisons, coverage
plot, two quality comparisons and Table 1.

Follow the [installation instructions](../../README.md#installation) first.
Run the commands below from the repository root with the virtual environment
activated.

## Analyze the published results

The published archive is included in `results/icaps2025/published/`.
Generate all six figures and the coverage table with:

```bash
MPLBACKEND=Agg python -m analysis.run icaps2025 --dataset published
```

Outputs are saved in `outputs/icaps2025/published/<analysis-time>/`. They include
PDF figures, plot-data CSVs, the table in CSV and Markdown, per-run diagnostics
and a manifest identifying the source data and analysis settings. Use
`--output <directory>` to choose another location.

To analyze a completed paper campaign:

```bash
MPLBACKEND=Agg python -m analysis.run icaps2025 \
  --dataset "runs/icaps2025/<paper-run-id>"
```

Its analysis is saved under the run's `analysis/<analysis-time>/` directory.

## Run the campaign

The `mini` profile runs one BOAND* best-worst configuration on 31 FrozenLake
instances. Use it to check your installation before starting the full campaign:

```bash
python -m experiment_support.run icaps2025 --profile mini --dry-run
PYTHONHASHSEED=0 python -m experiment_support.run icaps2025 --profile mini --workers 2
```

The `paper` profile runs eight configurations on 196 benchmark instances across
eleven domains, for 1,568 planner runs:

```bash
python -m experiment_support.run icaps2025 --profile paper --dry-run
PYTHONHASHSEED=0 python -m experiment_support.run icaps2025 --profile paper --workers 2
```

The `BOAND_bw` profile evaluates the same configuration as mini on all 196
instances across the 11 domains:

```bash
python -m experiment_support.run icaps2025 --profile BOAND_bw --dry-run
PYTHONHASHSEED=0 python -m experiment_support.run icaps2025 --profile BOAND_bw --workers 2
```

The `BOAND_bw_tireworld` profile evaluates BOAND bw on Tireworld's 16 instances:

```bash
PYTHONHASHSEED=0 python -m experiment_support.run icaps2025 --profile BOAND_bw_tireworld --workers 2
```

All profiles allow 600 seconds and 8,000,000 KB of virtual memory per run.
Two workers are used by default; adjust concurrency to available memory.
A dry run verifies input hashes and displays the scheduled commands without
executing the planner. New results are saved in `runs/icaps2025/<run-id>/`.

To continue an interrupted campaign, use the recorded run directory:

```bash
PYTHONHASHSEED=0 python -m experiment_support.run icaps2025 \
  --resume "runs/icaps2025/<run-id>" --workers 2
```

Resume skips finished executions, preserves previous attempts and checks the
recorded scientific settings and environment. For remote execution, use a
persistent server session such as `tmux`; see the [main README](../../README.md#resume-an-interrupted-run).

### Planner configurations

All configurations use the classical `hmax` heuristic. Their names correspond
to the comparisons in the paper:

| Configuration | Mode | Best-case heuristic | Worst-case heuristic | Size heuristic | Selector |
| --- | --- | --- | --- | --- | --- |
| SumMin | `b` | SumMin | Blind | Zero | random |
| MinSum | `b` | MinSum | Blind | Zero | random |
| BOAND bw2 | `bw` | SumMin | MaxSum | Delta | largestg |
| BOAND bw | `bw` | MinSum | MaxSum | Delta | largestg |
| BOAND wb2 | `wb` | SumMin | MaxSum | Delta | largestg |
| BOAND wb | `wb` | MinSum | MaxSum | Delta | largestg |
| MaxSum | `w` | Blind | MaxSum | Zero | random |
| AND best | `b` | MinSum | Blind | Delta | random |

The mini profile uses **BOAND bw**. The complete definition is in
[campaign.py](campaign.py), and [instances.json](instances.json) lists the
selected benchmarks and their content hashes.

## Analysis conventions

- Coverage and heuristic timings count runs with the final completion marker.
- Quality comparisons use the first solution, including partial computations.
- Heuristic plots use equal logarithmic scales and a `t/o` tick at 600 seconds.
- Cyclic worst-case costs are displayed at 1200.
- Times measure elapsed search time after preprocessing.

Heuristic comparisons pair instances in filesystem discovery order by default.
Use `--pairing instance` to join by domain and instance identity. This can change
plotted pairs; the exported CSVs identify both instances.

## Reproduction notes

The paper used an Intel Xeon E5-2620 at 2.00 GHz on Ubuntu 22.04.1, with
8 GB and ten-minute limits per run. It used Unified Planning 1.1.0; the supplied
runtime requirements pin 1.3.0. Hardware and dependency differences can affect
runtime, timeout coverage and memory failures.

The archive includes additional configurations and benchmark instances beyond
the current paper profile. Nine extra First Responders instances appear in the
worst-only archives. FrozenLake, elevators and tireworld contain 31, 16 and 16
archived instances, compared with 30, 15 and 15 listed in the paper. The generated
table reports the actual union of archived instances.

Coverage totals for BOAND* best-worst, BOAND* worst-best, AND* worst and AND* best
are **124 / 120 / 134 / 122** in the archive, versus **124 / 121 / 134 / 122**
in the paper. The difference is BOAND* worst-best on First Responders: nine
completed archived runs versus ten reported in the paper.

Use the supplied analysis tools or raw `.stats` and policy files to interpret
results. The external runner's generic summaries may miscount solutions because
BOAND* uses `.sol` directories rather than `.sol` files.
