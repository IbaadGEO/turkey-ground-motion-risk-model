import unittest

import pandas as pd

from elazig_sivrice_depth_analysis import (
    COMPARISON_SOURCE,
    DEPTH_SCENARIOS,
    ELAZIG_SIVRICE_EVENT,
    REFERENCE_SOURCE,
    build_map_data,
)


class TestElazigSivricePresentationConfig(unittest.TestCase):
    def test_depths(self):
        depths = {row["depth_source"]: row["depth_km"] for row in DEPTH_SCENARIOS}
        self.assertEqual(depths["wilber3_usgs"], 10.0)
        self.assertEqual(depths["global_cmt"], 12.0)
        self.assertEqual(depths["analysed"], 14.0)

    def test_subtraction_direction(self):
        self.assertEqual(COMPARISON_SOURCE, "global_cmt")
        self.assertEqual(REFERENCE_SOURCE, "analysed")

    def test_map_difference_is_analysed_minus_global_cmt(self):
        rows = pd.DataFrame(
            [
                {
                    "depth_source": REFERENCE_SOURCE,
                    "location_id": 1,
                    "receiver_latitude": 38.0,
                    "receiver_longitude": 39.0,
                    "repi_km": 20.0,
                    "median_pga_g": 0.20,
                    "structural_loss_ratio_mean": 0.10,
                },
                {
                    "depth_source": COMPARISON_SOURCE,
                    "location_id": 1,
                    "receiver_latitude": 38.0,
                    "receiver_longitude": 39.0,
                    "repi_km": 20.0,
                    "median_pga_g": 0.30,
                    "structural_loss_ratio_mean": 0.20,
                },
            ]
        )
        result = build_map_data(rows).iloc[0]
        self.assertAlmostEqual(result["pga_difference_g"], -0.10)
        self.assertAlmostEqual(result["loss_ratio_difference"], -0.10)

    def test_event_metadata(self):
        self.assertEqual(ELAZIG_SIVRICE_EVENT["event_id"], "2020024175513")
        self.assertAlmostEqual(ELAZIG_SIVRICE_EVENT["magnitude"], 6.7)
        self.assertAlmostEqual(ELAZIG_SIVRICE_EVENT["latitude"], 38.3897)
        self.assertAlmostEqual(ELAZIG_SIVRICE_EVENT["longitude"], 39.0883)
        self.assertAlmostEqual(ELAZIG_SIVRICE_EVENT["rake"], -12.0)


if __name__ == "__main__":
    unittest.main()
