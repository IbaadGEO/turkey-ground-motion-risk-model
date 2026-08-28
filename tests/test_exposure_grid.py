import unittest

import numpy as np
import pandas as pd

from exposure_grid import generate_turkey_land_grid


class ExposureGridTests(unittest.TestCase):
    def test_50_km_generator_recreates_validated_grid(self):
        generated = generate_turkey_land_grid(50)
        expected = pd.read_csv("data/turkey_50km_land_grid.csv")

        self.assertEqual(len(generated), 311)
        self.assertTrue(
            np.allclose(
                generated[expected.columns].to_numpy(float),
                expected.to_numpy(float),
                rtol=0.0,
                atol=1e-7,
            )
        )

    def test_finer_grids_have_expected_spacing_and_more_points(self):
        grid_20_km = generate_turkey_land_grid(20)
        grid_10_km = generate_turkey_land_grid(10)

        self.assertEqual(len(grid_20_km), 1950)
        self.assertEqual(len(grid_10_km), 7798)
        self.assertTrue(
            np.allclose(grid_20_km["easting_m"] % 20000.0, 0.0)
        )
        self.assertTrue(
            np.allclose(grid_10_km["northing_m"] % 10000.0, 0.0)
        )

    def test_non_positive_spacing_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            generate_turkey_land_grid(0)


if __name__ == "__main__":
    unittest.main()
