import unittest

import matplotlib

matplotlib.use("Agg")

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from map_plotting import (
    POSITIVE_PGA_COLOR_MAP,
    ZERO_PGA_COLOR,
    plot_pga_receiver_points,
)


class PlotPgaReceiverPointsTests(unittest.TestCase):
    def tearDown(self):
        plt.close("all")

    def make_map_results(self, pga_values):
        number_of_values = len(pga_values)
        return pd.DataFrame(
            {
                "receiver_longitude": np.arange(number_of_values, dtype=float),
                "receiver_latitude": np.arange(number_of_values, dtype=float),
                "median_pga_g": pga_values,
            }
        )

    def test_zero_points_are_grey_and_positive_points_are_coloured(self):
        fig, ax = plt.subplots()
        map_results = self.make_map_results([0.0, 0.01, 0.1])

        positive_points = plot_pga_receiver_points(ax, map_results)

        self.assertEqual(len(ax.collections), 2)
        zero_points = ax.collections[0]
        np.testing.assert_allclose(zero_points.get_offsets(), [[0.0, 0.0]])
        np.testing.assert_allclose(
            zero_points.get_facecolors()[0],
            mcolors.to_rgba(ZERO_PGA_COLOR),
        )
        self.assertEqual(zero_points.get_label(), "PGA = 0 g")
        np.testing.assert_allclose(positive_points.get_array(), [0.01, 0.1])
        self.assertIsInstance(positive_points.norm, mcolors.LogNorm)
        self.assertEqual(positive_points.cmap.name, POSITIVE_PGA_COLOR_MAP)

    def test_all_zero_points_are_grey_without_a_colour_bar_mappable(self):
        fig, ax = plt.subplots()
        map_results = self.make_map_results([0.0, 0.0])

        positive_points = plot_pga_receiver_points(ax, map_results)

        self.assertIsNone(positive_points)
        self.assertEqual(len(ax.collections), 1)
        np.testing.assert_allclose(
            ax.collections[0].get_facecolors()[0],
            mcolors.to_rgba(ZERO_PGA_COLOR),
        )

    def test_equal_positive_values_use_a_valid_linear_scale(self):
        fig, ax = plt.subplots()
        map_results = self.make_map_results([0.05, 0.05])

        positive_points = plot_pga_receiver_points(ax, map_results)

        self.assertIsInstance(positive_points.norm, mcolors.Normalize)
        self.assertNotIsInstance(positive_points.norm, mcolors.LogNorm)

    def test_invalid_pga_values_are_rejected(self):
        for value, message in (
            (-0.1, "cannot be negative"),
            (np.nan, "must be finite"),
            (np.inf, "must be finite"),
        ):
            with self.subTest(value=value):
                fig, ax = plt.subplots()
                map_results = self.make_map_results([value])

                with self.assertRaisesRegex(ValueError, message):
                    plot_pga_receiver_points(ax, map_results)


if __name__ == "__main__":
    unittest.main()
