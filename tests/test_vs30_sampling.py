import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin

from vs30_sampling import sample_vs30_raster


class Vs30SamplingTests(unittest.TestCase):
    def make_raster(self, directory):
        raster_file = Path(directory) / "test_vs30.tif"
        values = np.full((3, 3), 500.0, dtype="float32")
        values[1, 1] = -9999.0

        with rasterio.open(
            raster_file,
            "w",
            driver="GTiff",
            height=3,
            width=3,
            count=1,
            dtype="float32",
            crs="EPSG:3857",
            transform=from_origin(-150.0, 150.0, 100.0, 100.0),
            nodata=-9999.0,
        ) as raster:
            raster.write(values, 1)

        return raster_file

    def sample(self, locations, raster_file):
        return sample_vs30_raster(
            locations,
            raster_file,
            id_column="location_id",
            longitude_column="longitude",
            latitude_column="latitude",
            input_crs="EPSG:4326",
            minimum_vs30=150.0,
            maximum_vs30=1200.0,
            maximum_fallback_distance_m=200.0,
        )

    def test_direct_and_nearest_values_preserve_location_order(self):
        locations = pd.DataFrame(
            {
                "location_id": ["direct", "fallback"],
                "longitude": [-0.0008983153, 0.0],
                "latitude": [0.0008983153, 0.0],
            }
        )

        with tempfile.TemporaryDirectory() as directory:
            result = self.sample(locations, self.make_raster(directory))

        self.assertEqual(result["location_id"].tolist(), ["direct", "fallback"])
        self.assertEqual(result["vs30_status"].tolist(), ["direct", "nearest_valid"])
        np.testing.assert_allclose(result["vs30_m_s"], [500.0, 500.0])
        self.assertAlmostEqual(result.loc[1, "fallback_distance_m"], 100.0, places=3)

    def test_duplicate_location_ids_are_rejected(self):
        locations = pd.DataFrame(
            {
                "location_id": [1, 1],
                "longitude": [0.0, 0.0],
                "latitude": [0.0, 0.0],
            }
        )

        with tempfile.TemporaryDirectory() as directory:
            raster_file = self.make_raster(directory)
            with self.assertRaisesRegex(ValueError, "Duplicate location IDs"):
                self.sample(locations, raster_file)

    def test_invalid_coordinates_are_rejected(self):
        locations = pd.DataFrame(
            {
                "location_id": [1],
                "longitude": [np.nan],
                "latitude": [0.0],
            }
        )

        with tempfile.TemporaryDirectory() as directory:
            raster_file = self.make_raster(directory)
            with self.assertRaisesRegex(ValueError, "finite numbers"):
                self.sample(locations, raster_file)

    def test_location_outside_raster_is_reported(self):
        locations = pd.DataFrame(
            {
                "location_id": [1],
                "longitude": [10.0],
                "latitude": [10.0],
            }
        )

        with tempfile.TemporaryDirectory() as directory:
            result = self.sample(locations, self.make_raster(directory))

        self.assertEqual(result.loc[0, "vs30_status"], "outside_raster")
        self.assertTrue(pd.isna(result.loc[0, "vs30_m_s"]))


if __name__ == "__main__":
    unittest.main()
