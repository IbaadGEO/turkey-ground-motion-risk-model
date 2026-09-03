import json
import math
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from build_dashboard_data import (
    CURRENT_VULNERABILITY_FUNCTION,
    SCENARIO_FIELDS,
    VALID_DEPTH_SOURCES,
    export_dashboard_data,
    prepare_tables,
)


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MANIFEST_PATH = DOCS / "data" / "dashboard_manifest.json"
SUMMARY_PATH = (
    ROOT
    / "outputs_gwfm"
    / "complete_output"
    / "earthquake_depth_pga_loss_summary.csv"
)
VULNERABILITY_PATH = DOCS / "data" / "vulnerability_functions.json"
VULNERABILITY_MODEL_PATH = (
    ROOT / "data" / "gem_vulnerability_v2026" / "vulnerability_structural.xml"
)
TEST_SOURCE_COUNTS = {"waveform": 1, "isc_ehb": 0, "global_cmt": 0}


def make_test_tables():
    detail = pd.DataFrame(
        [
            {
                "event_id": "1",
                "depth_source": "waveform",
                "location_id": 10,
                "receiver_latitude": 39.0,
                "receiver_longitude": 35.0,
                "vs30_m_s": 400.0,
                "median_pga_g": 0.1,
                "structural_loss_ratio_mean": 0.01,
                "rhypo_km": 20.0,
            },
            {
                "event_id": "1",
                "depth_source": "waveform",
                "location_id": 11,
                "receiver_latitude": 40.0,
                "receiver_longitude": 36.0,
                "vs30_m_s": 500.0,
                "median_pga_g": 0.3,
                "structural_loss_ratio_mean": 0.05,
                "rhypo_km": 30.0,
            },
        ]
    )
    summary = pd.DataFrame(
        [
            {
                "event_id": "1",
                "depth_source": "waveform",
                "receiver_count": 2,
                "mean_pga_g": 0.2,
                "maximum_pga_g": 0.3,
                "mean_structural_loss_ratio": 0.03,
                "maximum_structural_loss_ratio": 0.05,
            }
        ]
    )
    return detail, summary


class DashboardDataExporterUnitTests(unittest.TestCase):
    def test_valid_tables_are_accepted(self):
        detail, summary = make_test_tables()
        checked_detail, checked_summary = prepare_tables(
            detail,
            summary,
            expected_scenarios=1,
            expected_receivers=2,
            expected_events=1,
            expected_source_counts=TEST_SOURCE_COUNTS,
        )
        self.assertEqual(len(checked_detail), 2)
        self.assertEqual(len(checked_summary), 1)

    def test_duplicate_receiver_is_rejected(self):
        detail, summary = make_test_tables()
        detail.loc[1, "location_id"] = detail.loc[0, "location_id"]
        with self.assertRaisesRegex(ValueError, "duplicate locations"):
            prepare_tables(
                detail,
                summary,
                expected_scenarios=1,
                expected_receivers=2,
                expected_events=1,
                expected_source_counts=TEST_SOURCE_COUNTS,
            )

    def test_nonpositive_pga_is_rejected(self):
        detail, summary = make_test_tables()
        detail.loc[0, "median_pga_g"] = 0.0
        with self.assertRaisesRegex(ValueError, "PGA values must be positive"):
            prepare_tables(
                detail,
                summary,
                expected_scenarios=1,
                expected_receivers=2,
                expected_events=1,
                expected_source_counts=TEST_SOURCE_COUNTS,
            )

    def test_summary_mismatch_is_rejected(self):
        detail, summary = make_test_tables()
        summary.loc[0, "mean_pga_g"] = 0.25
        with self.assertRaisesRegex(ValueError, "do not reproduce mean_pga_g"):
            prepare_tables(
                detail,
                summary,
                expected_scenarios=1,
                expected_receivers=2,
                expected_events=1,
                expected_source_counts=TEST_SOURCE_COUNTS,
            )

    def test_nonfinite_summary_value_is_rejected(self):
        detail, summary = make_test_tables()
        summary.loc[0, "maximum_pga_g"] = float("inf")
        with self.assertRaisesRegex(ValueError, "non-finite numerical values"):
            prepare_tables(
                detail,
                summary,
                expected_scenarios=1,
                expected_receivers=2,
                expected_events=1,
                expected_source_counts=TEST_SOURCE_COUNTS,
            )

    def test_incorrect_summary_receiver_count_is_rejected(self):
        detail, summary = make_test_tables()
        summary.loc[0, "receiver_count"] = 1
        with self.assertRaisesRegex(ValueError, "receiver_count must equal 2"):
            prepare_tables(
                detail,
                summary,
                expected_scenarios=1,
                expected_receivers=2,
                expected_events=1,
                expected_source_counts=TEST_SOURCE_COUNTS,
            )

    def test_custom_output_directory_contains_complete_export_tree(self):
        detail, summary = make_test_tables()
        checked_detail, checked_summary = prepare_tables(
            detail,
            summary,
            expected_scenarios=1,
            expected_receivers=2,
            expected_events=1,
            expected_source_counts=TEST_SOURCE_COUNTS,
        )

        with tempfile.TemporaryDirectory(dir=ROOT) as temporary_directory:
            output_directory = Path(temporary_directory) / "custom-output"
            manifest = export_dashboard_data(
                checked_detail,
                checked_summary,
                output_directory,
                VULNERABILITY_MODEL_PATH,
                expected_receivers=2,
                source_table_path=Path("source.csv"),
                summary_table_path=Path("summary.csv"),
            )

            self.assertTrue((output_directory / "dashboard_manifest.json").is_file())
            self.assertTrue((output_directory / "vulnerability_functions.json").is_file())
            self.assertTrue(
                (output_directory / "events" / "1" / "waveform.json").is_file()
            )
            self.assertFalse(
                (output_directory.parent / "data" / "events" / "1" / "waveform.json").exists()
            )
            self.assertEqual(
                manifest["scenarios"][0]["path"],
                "data/events/1/waveform.json",
            )


class ProductionDashboardDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.summary = pd.read_csv(SUMMARY_PATH, dtype={"event_id": "string"})
        cls.summary["event_id"] = cls.summary["event_id"].astype(str)

    def test_manifest_represents_all_valid_scenarios(self):
        scenarios = self.manifest["scenarios"]
        self.assertEqual(self.manifest["scenario_count"], 321)
        self.assertEqual(self.manifest["receivers_per_scenario"], 311)
        self.assertEqual(len(scenarios), 321)
        self.assertEqual(len({row["event_id"] for row in scenarios}), 117)
        self.assertEqual(sum(row["receiver_count"] for row in scenarios), 99_831)

        manifest_keys = {
            (str(row["event_id"]), row["depth_source"]) for row in scenarios
        }
        summary_keys = set(
            self.summary[["event_id", "depth_source"]].itertuples(
                index=False,
                name=None,
            )
        )
        self.assertEqual(manifest_keys, summary_keys)
        self.assertEqual(
            {source: sum(row["depth_source"] == source for row in scenarios)
             for source in VALID_DEPTH_SOURCES},
            {"waveform": 117, "isc_ehb": 110, "global_cmt": 94},
        )
        sources_by_event = self.summary.groupby("event_id")["depth_source"].nunique()
        self.assertEqual(int((sources_by_event == 3).sum()), 90)

    def test_manifest_paths_match_exported_files(self):
        listed = {
            (DOCS / row["path"]).resolve()
            for row in self.manifest["scenarios"]
        }
        exported = {
            path.resolve()
            for path in (DOCS / "data" / "events").rglob("*.json")
        }
        self.assertEqual(listed, exported)

    def test_receiver_files_are_valid_and_reproduce_summary(self):
        summary_lookup = {
            (str(row.event_id), row.depth_source): row
            for row in self.summary.itertuples(index=False)
        }
        field_index = {field: index for index, field in enumerate(SCENARIO_FIELDS)}

        for scenario in self.manifest["scenarios"]:
            key = (str(scenario["event_id"]), scenario["depth_source"])
            with self.subTest(event_id=key[0], depth_source=key[1]):
                payload = json.loads((DOCS / scenario["path"]).read_text("utf-8"))
                self.assertEqual(payload["event_id"], key[0])
                self.assertEqual(payload["depth_source"], key[1])
                self.assertEqual(payload["fields"], list(SCENARIO_FIELDS))
                self.assertEqual(payload["receiver_count"], 311)
                self.assertEqual(len(payload["receivers"]), 311)

                locations = [
                    row[field_index["location_id"]] for row in payload["receivers"]
                ]
                self.assertEqual(len(set(locations)), 311)

                for receiver in payload["receivers"]:
                    self.assertEqual(len(receiver), len(SCENARIO_FIELDS))
                    latitude = receiver[field_index["latitude"]]
                    longitude = receiver[field_index["longitude"]]
                    vs30 = receiver[field_index["vs30_m_s"]]
                    pga = receiver[field_index["median_pga_g"]]
                    loss = receiver[field_index["structural_loss_ratio_mean"]]
                    self.assertTrue(all(math.isfinite(value) for value in receiver[1:]))
                    self.assertGreaterEqual(latitude, -90)
                    self.assertLessEqual(latitude, 90)
                    self.assertGreaterEqual(longitude, -180)
                    self.assertLessEqual(longitude, 180)
                    self.assertGreater(vs30, 0)
                    self.assertGreater(pga, 0)
                    self.assertGreaterEqual(loss, 0)
                    self.assertLessEqual(loss, 1)

                pga_values = [
                    row[field_index["median_pga_g"]]
                    for row in payload["receivers"]
                ]
                loss_values = [
                    row[field_index["structural_loss_ratio_mean"]]
                    for row in payload["receivers"]
                ]
                summary_row = summary_lookup[key]
                comparisons = [
                    (math.fsum(pga_values) / len(pga_values), summary_row.mean_pga_g),
                    (max(pga_values), summary_row.maximum_pga_g),
                    (
                        math.fsum(loss_values) / len(loss_values),
                        summary_row.mean_structural_loss_ratio,
                    ),
                    (max(loss_values), summary_row.maximum_structural_loss_ratio),
                ]
                for actual, expected in comparisons:
                    self.assertTrue(
                        math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12),
                        (actual, expected),
                    )

    def test_vulnerability_metadata_is_source_limited(self):
        metadata = json.loads(VULNERABILITY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(metadata["function_count"], 521)
        self.assertEqual(metadata["asset_category"], "buildings")
        self.assertEqual(metadata["loss_category"], "structural")
        self.assertFalse(metadata["taxonomy_descriptions_available"])
        selected = [
            function
            for function in metadata["functions"]
            if function["current_production_function"]
        ]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["function_id"], CURRENT_VULNERABILITY_FUNCTION)


if __name__ == "__main__":
    unittest.main()
