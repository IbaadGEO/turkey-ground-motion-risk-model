import unittest

import pandas as pd

from vs30_raster_comparison import (
    build_fallback_diagnostic,
    build_fallback_summary,
)


class Vs30FallbackDiagnosticTests(unittest.TestCase):
    @staticmethod
    def model_receivers():
        return pd.DataFrame(
            {
                "location_id": [1, 2, 3],
                "longitude": [30.0, 31.0, 32.0],
                "latitude": [38.0, 39.0, 40.0],
                "vs30_m_s": [400.0, 500.0, 600.0],
                "vs30_status": ["direct", "nearest_valid", "direct"],
            }
        )

    @staticmethod
    def sampled(label, statuses, values):
        prefix = f"vs30_{label}"
        return pd.DataFrame(
            {
                "location_id": [1, 2, 3],
                f"{prefix}_m_s": values,
                f"{prefix}_status": statuses,
                f"{prefix}_direct_status": [
                    "valid" if status == "direct" else "nodata"
                    for status in statuses
                ],
                f"{prefix}_fallback_distance_m": [
                    None if status == "direct" else 100.0
                    for status in statuses
                ],
            }
        )

    def test_diagnostic_compares_fallback_sets_and_summarises_counts(self):
        model = self.model_receivers()
        sampled_three = self.sampled(
            "3arcsec",
            ["nearest_valid", "nearest_valid", "direct"],
            [410.0, 505.0, 610.0],
        )
        sampled_nine = self.sampled(
            "9arcsec",
            model["vs30_status"].tolist(),
            model["vs30_m_s"].tolist(),
        )

        diagnostic = build_fallback_diagnostic(
            model,
            sampled_three,
            sampled_nine,
        )
        summary = build_fallback_summary(diagnostic).iloc[0]

        self.assertEqual(
            diagnostic["fallback_category"].tolist(),
            ["3arcsec_only", "both", "neither"],
        )
        self.assertEqual(summary["direct_3arcsec_count"], 1)
        self.assertEqual(summary["fallback_3arcsec_count"], 2)
        self.assertEqual(summary["direct_9arcsec_count"], 2)
        self.assertEqual(summary["fallback_9arcsec_count"], 1)
        self.assertEqual(summary["fallback_in_both_count"], 1)
        self.assertEqual(summary["fallback_only_3arcsec_count"], 1)
        self.assertEqual(summary["fallback_only_9arcsec_count"], 0)

    def test_diagnostic_rejects_production_status_mismatch(self):
        model = self.model_receivers()
        sampled_three = self.sampled(
            "3arcsec",
            ["direct", "nearest_valid", "direct"],
            [400.0, 500.0, 600.0],
        )
        sampled_nine = self.sampled(
            "9arcsec",
            ["direct", "direct", "direct"],
            [400.0, 500.0, 600.0],
        )

        with self.assertRaisesRegex(ValueError, "statuses do not match"):
            build_fallback_diagnostic(model, sampled_three, sampled_nine)


if __name__ == "__main__":
    unittest.main()
