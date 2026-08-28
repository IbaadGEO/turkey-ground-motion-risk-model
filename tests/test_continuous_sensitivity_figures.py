import unittest

import numpy as np
import pandas as pd

from depth_sensitivity_analysis import (
    build_continuous_sensitivity_summary,
    summarise_sign_balance,
)


class ContinuousSensitivityFigureTests(unittest.TestCase):
    @staticmethod
    def comparison_rows():
        rows = []
        for source in ("global_cmt", "isc_ehb"):
            for location_id, (distance, pga_change, loss_change) in enumerate(
                (
                    (5.0, -20.0, -0.02),
                    (10.0, 0.0, 0.0),
                    (20.0, 10.0, 0.01),
                    (100.0, -2.0, 0.0),
                ),
                start=1,
            ):
                rows.append(
                    {
                        "comparison_source": source,
                        "event_id": "test-event",
                        "location_id": location_id,
                        "repi_km": distance,
                        "pga_percent_change": pga_change,
                        "loss_ratio_difference": loss_change,
                    }
                )
        return pd.DataFrame(rows)

    def test_sign_balance_preserves_negative_zero_and_positive_counts(self):
        summary = summarise_sign_balance(self.comparison_rows())
        near_field = summary[
            (summary["distance_range_km"] == "0-25")
            & (summary["comparison_source"] == "global_cmt")
            & (summary["metric"] == "pga_percent")
        ].iloc[0]

        self.assertEqual(near_field["pair_count"], 3)
        self.assertEqual(near_field["negative_count"], 1)
        self.assertEqual(near_field["unchanged_count"], 1)
        self.assertEqual(near_field["positive_count"], 1)

    def test_continuous_summary_keeps_signed_systematic_tendency(self):
        summary = build_continuous_sensitivity_summary(
            self.comparison_rows()
        )
        origin = summary[
            (summary["comparison_source"] == "global_cmt")
            & (summary["metric"] == "pga_percent")
            & (summary["epicentral_distance_km"] == 0.0)
        ].iloc[0]

        self.assertLess(origin["systematic_mean_signed_change"], 0.0)
        self.assertGreater(origin["empirical_standard_deviation"], 0.0)
        sign_total = (
            origin["weighted_negative_percent"]
            + origin["weighted_unchanged_percent"]
            + origin["weighted_positive_percent"]
        )
        self.assertTrue(np.isclose(sign_total, 100.0))


if __name__ == "__main__":
    unittest.main()
