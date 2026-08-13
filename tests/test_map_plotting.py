import unittest

import matplotlib

matplotlib.use("Agg")

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from map_plotting import (
    POSITIVE_PGA_COLOR_MAP,
    TURKEY_BORDER_COLOR,
    TURKEY_BOUNDARY_FILE,
    ZERO_PGA_COLOR,
    load_turkey_boundary_rings,
    plot_pga_receiver_points,
    plot_turkey_border,
)


class PlotTurkeyBorderTests(unittest.TestCase):
    def tearDown(self):
        plt.close("all")

    def test_boundary_file_contains_valid_multi_part_turkey_outline(self):
        rings = load_turkey_boundary_rings()
        all_coordinates = np.vstack(rings)

        self.assertEqual(len(rings), 3)
        self.assertTrue(all(np.allclose(ring[0], ring[-1]) for ring in rings))
        self.assertGreater(all_coordinates[:, 0].min(), 25.0)
        self.assertLess(all_coordinates[:, 0].max(), 45.0)
        self.assertGreater(all_coordinates[:, 1].min(), 35.0)
        self.assertLess(all_coordinates[:, 1].max(), 43.0)

    def test_boundary_file_records_natural_earth_provenance(self):
        import json

        with TURKEY_BOUNDARY_FILE.open(encoding="utf-8") as boundary_stream:
            boundary = json.load(boundary_stream)

        properties = boundary["features"][0]["properties"]
        self.assertEqual(properties["source"], "Natural Earth")
        self.assertEqual(properties["source_version"], "5.1.2")
        self.assertEqual(properties["license"], "Public domain")
        self.assertEqual(properties["iso_a3"], "TUR")

    def test_border_is_drawn_as_black_lines(self):
        fig, ax = plt.subplots()

        lines = plot_turkey_border(ax)

        self.assertEqual(len(lines), 3)
        self.assertEqual(tuple(ax.lines), lines)
        self.assertTrue(
            all(line.get_color() == TURKEY_BORDER_COLOR for line in lines)
        )
        self.assertTrue(all(line.get_linewidth() == 1.2 for line in lines))
        self.assertTrue(all(line.get_zorder() == 2 for line in lines))


class PlotPgaReceiverPointsTests(unittest.TestCase):
    def test_positive_pga_colour_map_is_viridis(self):
        self.assertEqual(POSITIVE_PGA_COLOR_MAP, "viridis")

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
