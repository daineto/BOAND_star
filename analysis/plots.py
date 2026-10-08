"""Six explicit paper plots; no manual cell edits or repeated execution needed."""
from dataclasses import dataclass
from pathlib import Path

import matplotlib
from matplotlib import pyplot as plt
import numpy as np

from planner.policy import CYCLE_COST



@dataclass(frozen=True)
class HeuristicPlot:
    left: str
    right: str
    title: str
    filename: str
    xlabel: str = "SumMin elapsed time (s)"
    ylabel: str = "MinSum elapsed time (s)"


@dataclass(frozen=True)
class QualityPlot:
    bi_objective: str
    single_objective: str
    criterion: str
    xlabel: str
    filename: str


def plot_heuristic(points, specification):
    fig, ax = plt.subplots(figsize=(4, 4))
    for _, group in points.groupby("domain", sort=False):
        ax.scatter(group.x, group.y, marker="d", edgecolor="red", facecolor="none")
    ax.plot([0.001, 600], [0.001, 600], c="black", linestyle="--", lw=0.5, alpha=1)
    ax.set(xlabel=specification.xlabel, ylabel=specification.ylabel,
           xscale="log", yscale="log", title=specification.title)
    ticks = [0.001, 0.01, 0.1, 1, 10, 100, 600]
    labels = [r"$10^{-3}$", r"$10^{-2}$", r"$10^{-1}$", r"$10^{0}$",
              r"$10^{1}$", r"$10^{2}$", "t/o"]
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_ticks(ticks, labels=labels)
    # Identical limits and equal aspect give both axes the same logarithmic scale.
    limits = (min(ax.get_xlim()[0], ax.get_ylim()[0]),
              max(ax.get_xlim()[1], ax.get_ylim()[1]))
    ax.set(xlim=limits, ylim=limits)
    ax.set_aspect("equal", adjustable="box")
    ax.grid()
    fig.tight_layout()
    return fig


def plot_coverage(runs, configurations, coverage_configurations, labels):
    fig, ax = plt.subplots(figsize=(6, 4))
    for label in coverage_configurations:
        times = sorted(run.stats[-1]["time"] for run in runs.values()
                       if run.configuration == label and run.complete)
        ax.plot(times + [configurations[label].timeout],
                list(range(1, len(times) + 1)) + [len(times)], label=labels[label])
    ax.set(xlabel="elapsed search time (s)", ylabel="coverage", xscale="log")
    ax.legend()
    ax.grid()
    fig.tight_layout()
    return fig


def plot_quality(points, specification):
    fig, ax = plt.subplots(figsize=(4, 3))
    # Keep the original cycle-cost display mapping and histogram density coloring.
    x = points.x.replace(CYCLE_COST, 1200).to_numpy()
    y = points.y.replace(CYCLE_COST, 1200).to_numpy()
    if len(x):
        histogram, edges_x, edges_y = np.histogram2d(x, y, bins=[250, 250])
        density = np.array([histogram[np.argmax(a <= edges_x[1:]), np.argmax(b <= edges_y[1:])]
                            for a, b in zip(x, y)])
        order = density.argsort()
        ax.scatter(x[order], y[order], c=density[order], cmap=plt.cm.copper, marker="^")
    ax.plot([1, 1000], [1, 1000], c="black", linestyle="--", lw=0.5, alpha=1)
    ax.set(xlabel=specification.xlabel, ylabel="BOAND*", xscale="log", yscale="log")
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_ticks([1, 10, 100, 1000])
    ax.grid()
    fig.tight_layout()
    return fig


def generate_paper_outputs(*args, **kwargs):
    """Compatibility entry point; scientific output definitions belong to ICAPS."""
    from campaigns.icaps2025.analysis import generate_paper_outputs as generate
    return generate(*args, **kwargs)


def __getattr__(name):
    if name in {"HEURISTIC_PLOTS", "QUALITY_PLOTS", "PLANNER_LABELS"}:
        from campaigns.icaps2025 import analysis
        return getattr(analysis, name)
    raise AttributeError(name)
