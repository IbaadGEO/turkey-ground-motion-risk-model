import unittest

import pandas as pd

from akkar_turkey_portfolio_gwfm import (
    build_complete_pga_structural_loss_table,
    build_earthquake_depth_pga_loss_summary,
)


def make_structural_loss_rows():
    rows = []
    for depth_source, depth_km in [
        ("waveform", 8.0),
        ("isc_ehb", 12.0),
    ]:
        for location_id, pga, loss in [
            (1, 0.20, 0.10),
            (2, 0.10, 0.00),
        ]:
            rows.append(
                {
                    "event_id": "1",
                    "origin_time": "2020-01-01T00:00:00",
                    "magnitude": 6.0,
                    "magnitude_type": "Mw",
                    "rake": 0.0,
                    "source_latitude": 39.0,
                    "source_longitude": 35.0,
                    "depth_source": depth_source,
                    "source_depth_km": depth_km,
                    "location_id": location_id,
                    "receiver_latitude": 39.5,
                    "receiver_longitude": 35.5 + location_id,
                    "vs30": 300.0,
                    "repi_km": 20.0 * location_id,
                    "rhypo_km": 22.0 * location_id,
                    "source_within_30_km": True,
                    "within_200_km": True,
                    "median_pga_g": pga,
                    "sigma_total_ln": 0.6,
                    "structural_loss_ratio_mean": loss,
                    "structural_loss_ratio_cov": 0.2,
                    "vulnerability_function_id": "test-function",
                    "vulnerability_model_version": "test-version",
                    "vulnerability_distribution": "BT",
                    "asset_category": "buildings",
                    "loss_category": "structural",
                }
            )
    return pd.DataFrame(rows)


class CompleteOutputTests(unittest.TestCase):
    def test_complete_table_has_one_row_per_event_depth_location(self):
        complete = build_complete_pga_structural_loss_table(
            make_structural_loss_rows(),
            expected_valid_depths={"waveform": 1, "isc_ehb": 1},
            expected_exposure_locations=2,
        )

        self.assertEqual(len(complete), 4)
        self.assertIn("vs30_m_s", complete.columns)
        self.assertFalse(
            complete.duplicated(
                ["event_id", "depth_source", "location_id"]
            ).any()
        )

    def test_summary_has_one_row_per_event_depth(self):
        complete = build_complete_pga_structural_loss_table(
            make_structural_loss_rows(),
            expected_valid_depths={"waveform": 1, "isc_ehb": 1},
            expected_exposure_locations=2,
        )
        summary = build_earthquake_depth_pga_loss_summary(
            complete,
            expected_valid_depths={"waveform": 1, "isc_ehb": 1},
            expected_exposure_locations=2,
        )

        self.assertEqual(len(summary), 2)
        self.assertTrue((summary["receiver_count"] == 2).all())
        self.assertTrue((summary["maximum_pga_g"] == 0.20).all())
        self.assertTrue(
            (summary["locations_with_nonzero_structural_loss"] == 1).all()
        )

    def test_wrong_row_count_is_rejected(self):
        rows = make_structural_loss_rows()
        duplicate = pd.concat([rows, rows.iloc[[0]]], ignore_index=True)

        with self.assertRaisesRegex(
            ValueError,
            "Expected 4 complete PGA/loss rows",
        ):
            build_complete_pga_structural_loss_table(
                duplicate,
                expected_valid_depths={"waveform": 1, "isc_ehb": 1},
                expected_exposure_locations=2,
            )


if __name__ == "__main__":
    unittest.main()
