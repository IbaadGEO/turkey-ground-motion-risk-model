import unittest

from iris_event_depth_analysis import (
    COMPARISON_SOURCE,
    DEPTH_SCENARIOS,
    IRIS_EVENT,
    REFERENCE_SOURCE,
)


class TestIrisEventPresentationConfig(unittest.TestCase):
    def test_depths(self):
        depths = {row["depth_source"]: row["depth_km"] for row in DEPTH_SCENARIOS}
        self.assertEqual(depths["wilber3_usgs"], 10.0)
        self.assertEqual(depths["global_cmt"], 12.0)
        self.assertEqual(depths["analysed"], 14.0)

    def test_subtraction_direction(self):
        self.assertEqual(COMPARISON_SOURCE, "global_cmt")
        self.assertEqual(REFERENCE_SOURCE, "analysed")

    def test_event_metadata(self):
        self.assertEqual(IRIS_EVENT["event_id"], "2020024175513")
        self.assertAlmostEqual(IRIS_EVENT["magnitude"], 6.7)
        self.assertAlmostEqual(IRIS_EVENT["latitude"], 38.3897)
        self.assertAlmostEqual(IRIS_EVENT["longitude"], 39.0883)
        self.assertAlmostEqual(IRIS_EVENT["rake"], -12.0)


if __name__ == "__main__":
    unittest.main()
