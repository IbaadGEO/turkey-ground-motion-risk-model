import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from akkar_turkey_portfolio_gwfm import create_source_receiver_pairs
from prepare_gwfm_catalogue import (
    build_event_depth_table,
    load_gwfm_catalogue,
)


GWFM_HEADER = (
    "id yyyymmdd hhmm wlon wlat wzc mth ilon ilat izc ieb mth ndp "
    "clon clat czc mth st dp rk mth st dp rk %dc mag mty reference"
)


class CatalogueDepthTests(unittest.TestCase):
    def test_raw_catalogue_keeps_three_depth_sources(self):
        catalogue_text = "\n".join(
            [
                "gWFM test catalogue",
                GWFM_HEADER,
                (
                    "1 20200101 1234 30.0 40.0 10 DP "
                    "30.1 40.1 12 10 DEQd 5 "
                    "30.2 40.2 15 FREE 100 45 -10 CMT "
                    "100 45 -10 90 6.5 Mw Test"
                ),
                (
                    "2 20200102 0030 31.0 41.0 20 DP "
                    "- - - - - - - - - - 110 50 20 CMT "
                    "110 50 20 80 6.0 Mw Test"
                ),
            ]
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            source_file = Path(temporary_directory) / "gwfm.txt"
            source_file.write_text(catalogue_text, encoding="utf-8")
            catalogue = load_gwfm_catalogue(source_file)

        self.assertEqual(len(catalogue), 2)
        self.assertEqual(catalogue.loc[0, "waveform_depth_km"], 10)
        self.assertEqual(catalogue.loc[0, "isc_ehb_depth_km"], 12)
        self.assertEqual(catalogue.loc[0, "global_cmt_depth_km"], 15)
        self.assertTrue(pd.isna(catalogue.loc[1, "isc_ehb_depth_km"]))
        self.assertTrue(pd.isna(catalogue.loc[1, "global_cmt_depth_km"]))

    def make_selected_earthquakes(self):
        return pd.DataFrame(
            {
                "event_id": ["1", "2", "3"],
                "waveform_depth_km": [10.0, 20.0, 30.0],
                "isc_ehb_depth_km": [12.0, 0.0, np.nan],
                "global_cmt_depth_km": [15.0, np.nan, np.nan],
                "cmt_depth_km": [15.0, -10.0, 25.0],
            }
        )

    def test_depth_table_records_valid_and_unavailable_sources(self):
        depth_table = build_event_depth_table(
            self.make_selected_earthquakes()
        )

        self.assertEqual(len(depth_table), 9)
        self.assertEqual(
            int((depth_table["depth_status"] == "valid").sum()),
            6,
        )

        statuses = depth_table.set_index(["event_id", "depth_source"])[
            "depth_status"
        ]
        self.assertEqual(statuses.loc[("2", "isc_ehb")], "invalid_nonpositive")
        self.assertEqual(
            statuses.loc[("2", "global_cmt")],
            "missing_sentinel",
        )
        self.assertEqual(statuses.loc[("3", "isc_ehb")], "missing")

        cmt_depths = depth_table[
            depth_table["depth_source"] == "global_cmt"
        ].set_index("event_id")["depth_km"]
        self.assertEqual(cmt_depths.loc["3"], 25.0)

    def test_conflicting_cmt_depths_are_rejected(self):
        earthquakes = self.make_selected_earthquakes()
        earthquakes.loc[0, "cmt_depth_km"] = 16.0

        with self.assertRaisesRegex(ValueError, "CMT depths disagree"):
            build_event_depth_table(earthquakes)


class SourceReceiverDepthTests(unittest.TestCase):
    def test_each_valid_depth_is_calculated_at_each_location(self):
        earthquakes = pd.DataFrame(
            {
                "event_id": ["event-1"],
                "origin_time": [pd.Timestamp("2020-01-01")],
                "magnitude": [6.0],
                "magnitude_type": ["Mw"],
                "rake": [0.0],
                "latitude": [40.0],
                "longitude": [30.0],
            }
        )
        event_depths = pd.DataFrame(
            {
                "event_id": ["event-1", "event-1", "event-1"],
                "depth_source": ["waveform", "isc_ehb", "global_cmt"],
                "depth_km": [10.0, 20.0, np.nan],
                "depth_status": ["valid", "valid", "missing"],
            }
        )
        exposure = pd.DataFrame(
            {
                "location_id": ["site-1", "site-2"],
                "latitude": [40.0, 41.0],
                "longitude": [30.0, 31.0],
                "vs30": [760.0, 760.0],
            }
        )

        scenarios = create_source_receiver_pairs(
            earthquakes,
            event_depths,
            exposure,
        )

        self.assertEqual(len(scenarios), 4)
        self.assertEqual(
            set(scenarios["depth_source"]),
            {"waveform", "isc_ehb"},
        )
        self.assertEqual(
            scenarios.groupby("depth_source").size().to_dict(),
            {"isc_ehb": 2, "waveform": 2},
        )
        self.assertTrue((scenarios["rhypo_km"] >= scenarios["repi_km"]).all())


if __name__ == "__main__":
    unittest.main()
