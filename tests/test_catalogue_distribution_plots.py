import tempfile
import unittest
from pathlib import Path

import pandas as pd

from catalogue_distribution_plots import (
    plot_catalogue_distributions,
    prepare_common_event_values,
    summarise_catalogue_distributions,
)


def make_event_summary():
    rows = []
    sources = ("waveform", "isc_ehb", "global_cmt")
    for event_id, pga_base, loss_base in [
        ("1", 0.10, 0.00),
        ("2", 0.20, 0.02),
    ]:
        for source_index, source in enumerate(sources, start=1):
            rows.append(
                {
                    "event_id": event_id,
                    "depth_source": source,
                    "maximum_pga_g": pga_base * source_index,
                    "maximum_structural_loss_ratio": loss_base * source_index,
                }
            )

    # This event is deliberately incomplete and must not enter a balanced plot.
    rows.append(
        {
            "event_id": "3",
            "depth_source": "waveform",
            "maximum_pga_g": 0.05,
            "maximum_structural_loss_ratio": 0.0,
        }
    )
    return pd.DataFrame(rows)


class CatalogueDistributionPlotTests(unittest.TestCase):
    def test_prepare_common_event_values_keeps_balanced_events(self):
        values = prepare_common_event_values(make_event_summary())

        self.assertEqual(len(values), 6)
        self.assertEqual(values["event_id"].nunique(), 2)
        self.assertEqual(set(values["depth_source"]), {
            "waveform",
            "isc_ehb",
            "global_cmt",
        })
        self.assertAlmostEqual(
            values["maximum_structural_loss_percent"].max(),
            6.0,
        )

    def test_distribution_summary_reports_zero_loss_events(self):
        values = prepare_common_event_values(make_event_summary())
        summary = summarise_catalogue_distributions(values)

        self.assertTrue((summary["event_count"] == 2).all())
        self.assertTrue((summary["zero_loss_event_count"] == 1).all())
        waveform = summary[summary["depth_source"] == "waveform"].iloc[0]
        self.assertAlmostEqual(
            waveform["largest_event_maximum_pga_g"],
            0.20,
        )

    def test_plot_is_written(self):
        values = prepare_common_event_values(make_event_summary())
        with tempfile.TemporaryDirectory() as temp_directory:
            output_file = Path(temp_directory) / "comparison.png"
            plot_catalogue_distributions(values, output_file)
            self.assertTrue(output_file.is_file())
            self.assertGreater(output_file.stat().st_size, 0)

    def test_invalid_loss_ratio_is_rejected(self):
        summary = make_event_summary()
        summary.loc[0, "maximum_structural_loss_ratio"] = 1.1

        with self.assertRaisesRegex(ValueError, "between zero and one"):
            prepare_common_event_values(summary)


if __name__ == "__main__":
    unittest.main()
