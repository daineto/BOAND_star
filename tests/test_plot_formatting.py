"""Check the rendered scales and timeout labels of heuristic comparisons."""
import unittest

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
import pandas as pd

from analysis.plots import plot_heuristic
from campaigns.icaps2025.analysis import HEURISTIC_PLOTS


class HeuristicFormattingTests(unittest.TestCase):
    def test_equal_logarithmic_scales_and_timeout_ticks(self):
        points = pd.DataFrame({"domain": ["example", "example"],
                               "x": [0.01, 600], "y": [100, 0.1]})
        for specification in HEURISTIC_PLOTS:
            with self.subTest(plot=specification.filename):
                figure = plot_heuristic(points, specification)
                try:
                    figure.canvas.draw()
                    axes = figure.axes[0]
                    self.assertEqual(axes.get_xscale(), "log")
                    self.assertEqual(axes.get_yscale(), "log")
                    self.assertEqual(axes.get_xlim(), axes.get_ylim())
                    # A tenfold increase must occupy the same pixel distance on both axes.
                    transform = axes.transData.transform
                    dx = transform((0.1, 1))[0] - transform((0.01, 1))[0]
                    dy = transform((1, 0.1))[1] - transform((1, 0.01))[1]
                    self.assertAlmostEqual(dx, dy)
                    for axis in (axes.xaxis, axes.yaxis):
                        ticks = dict(zip(axis.get_majorticklocs(),
                                         (label.get_text() for label in axis.get_ticklabels())))
                        self.assertEqual(ticks[600], "t/o")
                finally:
                    plt.close(figure)


if __name__ == "__main__":
    unittest.main()
