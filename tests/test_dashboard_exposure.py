import json
import math
import unittest
from pathlib import Path

import prepare_elazig_osm_dashboard as osm_prepare
import prepare_gem_exposure_dashboard as gem_prepare


ROOT = Path(__file__).resolve().parents[1]
EXPOSURE = ROOT / "docs" / "data" / "exposure"


class DashboardExposureDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adm1 = json.loads(
            (EXPOSURE / "gem_turkiye_adm1.json").read_text(encoding="utf-8")
        )
        cls.taxonomy = json.loads(
            (EXPOSURE / "gem_turkiye_taxonomy.json").read_text(encoding="utf-8")
        )
        cls.gem_metadata = json.loads(
            (EXPOSURE / "gem_exposure_metadata.json").read_text(encoding="utf-8")
        )
        cls.boundary = json.loads(
            (EXPOSURE / "turkiye_adm1.geojson").read_text(encoding="utf-8")
        )
        cls.buildings = json.loads(
            (EXPOSURE / "elazig_buildings.geojson").read_text(encoding="utf-8")
        )
        cls.clusters = json.loads(
            (EXPOSURE / "elazig_building_clusters.json").read_text(encoding="utf-8")
        )
        cls.osm_metadata = json.loads(
            (EXPOSURE / "elazig_osm_metadata.json").read_text(encoding="utf-8")
        )

    def test_expected_static_exposure_files_exist(self):
        expected = {
            "gem_turkiye_adm1.json",
            "gem_turkiye_taxonomy.json",
            "gem_exposure_metadata.json",
            "turkiye_adm1.geojson",
            "elazig_buildings.geojson",
            "elazig_building_clusters.json",
            "elazig_osm_metadata.json",
        }
        self.assertTrue(expected.issubset({path.name for path in EXPOSURE.iterdir()}))

    def test_gem_source_version_scope_and_licence_are_pinned(self):
        gem = self.gem_metadata["gem"]
        self.assertEqual(gem["version"], "v2026.0.0")
        self.assertEqual(gem["commit"], gem_prepare.GEM_COMMIT)
        self.assertEqual(gem["licence"], "CC BY-NC-SA 4.0")
        self.assertIn("aggregate summaries only", gem["scope"])
        self.assertTrue(all("/v2026.0.0/" in url for url in gem["source_files"].values()))
        self.assertTrue(any("restricted/full 1 km" in item for item in gem["limitations"]))

    def test_adm1_schema_identifiers_and_occupancies(self):
        provinces = self.adm1["provinces"]
        self.assertEqual(self.adm1["province_count"], 81)
        self.assertEqual(len(provinces), 81)
        self.assertEqual({item["ID_0"] for item in provinces}, {"TUR"})
        self.assertEqual(len({item["ID_1"] for item in provinces}), 81)
        self.assertEqual(len({item["NAME_1"] for item in provinces}), 81)
        self.assertEqual(self.adm1["occupancies"], ["RES", "COM", "IND"])

    def test_adm1_building_counts_are_finite_nonnegative_and_totalled(self):
        for province in self.adm1["provinces"]:
            buildings = province["BUILDINGS"]
            for key in ("TOTAL", "RES", "COM", "IND"):
                self.assertTrue(math.isfinite(buildings[key]))
                self.assertGreaterEqual(buildings[key], 0)
            self.assertAlmostEqual(
                buildings["TOTAL"],
                buildings["RES"] + buildings["COM"] + buildings["IND"],
            )

    def test_elazig_province_context_is_exact(self):
        province = next(item for item in self.adm1["provinces"] if item["ID_1"] == "TR-23")
        self.assertEqual(province["NAME_1"], "Elazığ")
        self.assertEqual(province["BUILDINGS"]["RES"], 61694)
        self.assertEqual(province["BUILDINGS"]["COM"], 5600)
        self.assertEqual(province["BUILDINGS"]["IND"], 1569)

    def test_taxonomy_records_retain_exact_gem_fields(self):
        self.assertEqual(self.taxonomy["source_row_count"], 1727)
        self.assertEqual(self.taxonomy["taxonomy_record_count"], 1095)
        self.assertEqual(len(self.taxonomy["records"]), 1095)
        required = {"MACRO_TAXONOMY", "TAXONOMY", "OCCUPANCY", "BUILDINGS"}
        for record in self.taxonomy["records"]:
            self.assertEqual(set(record), required)
            self.assertIn(record["OCCUPANCY"], {"RES", "COM", "IND"})
            self.assertTrue(math.isfinite(record["BUILDINGS"]))
            self.assertGreaterEqual(record["BUILDINGS"], 0)
        self.assertEqual(
            {item["MACRO_TAXONOMY"] for item in self.taxonomy["macro_groups"]},
            {"ADO|ST|E", "CR+", "CR-", "MUR", "OT", "S", "W"},
        )

    def test_boundary_and_exposure_join_one_to_one(self):
        self.assertEqual(self.boundary["type"], "FeatureCollection")
        self.assertEqual(len(self.boundary["features"]), 81)
        exposure_ids = {item["ID_1"] for item in self.adm1["provinces"]}
        boundary_ids = {
            feature["properties"]["ID_1"] for feature in self.boundary["features"]
        }
        self.assertEqual(boundary_ids, exposure_ids)
        for feature in self.boundary["features"]:
            self.assertIn(feature["geometry"]["type"], {"Polygon", "MultiPolygon"})
            self.assertEqual(feature["properties"]["source"], "geoBoundaries gbOpen")

    def test_boundary_source_metadata_is_explicit(self):
        boundary = self.gem_metadata["boundary"]
        self.assertEqual(boundary["boundary_id"], "TUR-ADM1-25984515")
        self.assertEqual(boundary["province_count"], 81)
        self.assertEqual(boundary["gem_country_readme_licence"], "CC BY 4.0")
        self.assertEqual(
            boundary["source_record_licence"],
            "Creative Commons Attribution-ShareAlike 2.0",
        )

        self.assertEqual(
            self.gem_metadata["gem"]["source_table_building_totals"],
            {"adm0": 10103556, "adm1": 10103560, "taxonomy": 10103501},
        )

    def test_osm_features_have_unique_ids_valid_rings_and_attribution(self):
        features = self.buildings["features"]
        self.assertEqual(self.buildings["type"], "FeatureCollection")
        self.assertEqual(len(features), self.osm_metadata["feature_count"])
        ids = [feature["properties"]["osm_id"] for feature in features]
        self.assertEqual(len(ids), len(set(ids)))
        for feature in features:
            properties = feature["properties"]
            self.assertRegex(properties["osm_id"], r"^way/\d+$")
            self.assertEqual(properties["source"], "OpenStreetMap")
            self.assertEqual(properties["licence"], "ODbL 1.0")
            self.assertEqual(feature["geometry"]["type"], "Polygon")
            ring = feature["geometry"]["coordinates"][0]
            self.assertGreaterEqual(len(ring), 4)
            self.assertEqual(ring[0], ring[-1])
            self.assertGreaterEqual(len({tuple(point) for point in ring[:-1]}), 3)

    def test_osm_geojson_bbox_covers_returned_geometry(self):
        points = [
            point
            for feature in self.buildings["features"]
            for point in feature["geometry"]["coordinates"][0]
        ]
        west, south, east, north = self.buildings["bbox"]
        self.assertLessEqual(west, min(point[0] for point in points))
        self.assertLessEqual(south, min(point[1] for point in points))
        self.assertGreaterEqual(east, max(point[0] for point in points))
        self.assertGreaterEqual(north, max(point[1] for point in points))
        self.assertEqual(
            self.buildings["query_bbox"],
            [39.18, 38.66, 39.23, 38.69],
        )

    def test_osm_vulnerability_is_not_fabricated(self):
        for feature in self.buildings["features"]:
            properties = feature["properties"]
            self.assertIsNone(properties["vulnerability_function_id"])
            self.assertEqual(properties["vulnerability_class"], "Not assigned")
            self.assertNotIn("GEM_TAXONOMY", properties)
            self.assertNotIn("receiver_structural_loss", properties)
            self.assertNotIn("building_pga", properties)

    def test_osm_metadata_defines_nonofficial_fixed_box_and_attribution(self):
        self.assertEqual(self.osm_metadata["source"], "OpenStreetMap")
        self.assertEqual(self.osm_metadata["licence"], "ODbL 1.0")
        self.assertEqual(self.osm_metadata["attribution"], "© OpenStreetMap contributors")
        self.assertEqual(self.osm_metadata["retrieved_on"], "2026-09-03")
        self.assertEqual(self.osm_metadata["study_area"]["type"], "fixed urban bounding box")
        self.assertFalse(self.osm_metadata["study_area"]["is_official_boundary"])
        self.assertEqual(
            [
                self.osm_metadata["study_area"][key]
                for key in ("south", "west", "north", "east")
            ],
            [38.66, 39.18, 38.69, 39.23],
        )

    def test_each_cluster_level_reproduces_building_total(self):
        self.assertEqual(self.clusters["feature_count"], len(self.buildings["features"]))
        for level in self.clusters["levels"].values():
            self.assertEqual(len(level["clusters"]), level["cluster_count"])
            self.assertEqual(
                sum(cluster["count"] for cluster in level["clusters"]),
                self.clusters["feature_count"],
            )

    def test_preprocessors_do_not_map_osm_tags_to_gem_taxonomy(self):
        sample = {
            "type": "way",
            "id": 42,
            "tags": {"building": "apartments", "building:levels": "5"},
            "geometry": [
                {"lon": 39.2, "lat": 38.67},
                {"lon": 39.201, "lat": 38.67},
                {"lon": 39.201, "lat": 38.671},
                {"lon": 39.2, "lat": 38.67},
            ],
        }
        feature, _ = osm_prepare.build_feature(sample, "2026-09-03")
        self.assertEqual(feature["properties"]["building"], "apartments")
        self.assertEqual(feature["properties"]["levels"], "5")
        self.assertIsNone(feature["properties"]["vulnerability_function_id"])
        self.assertEqual(feature["properties"]["vulnerability_class"], "Not assigned")

    def test_preprocessor_rejects_nonclosed_building_way(self):
        sample = {
            "type": "way",
            "id": 43,
            "tags": {"building": "yes"},
            "geometry": [
                {"lon": 39.2, "lat": 38.67},
                {"lon": 39.201, "lat": 38.67},
                {"lon": 39.201, "lat": 38.671},
            ],
        }
        self.assertIsNone(osm_prepare.build_feature(sample, "2026-09-03"))


class DashboardExposureInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        cls.script = (ROOT / "docs" / "dashboard.js").read_text(encoding="utf-8")

    def test_exposure_is_separate_from_primary_map_variable(self):
        self.assertIn('name="map-variable"', self.html)
        self.assertIn('name="exposure"', self.html)
        self.assertIn('value="none" checked', self.html)
        self.assertIn("GEM province exposure", self.html)
        self.assertIn("Elazığ buildings", self.html)

    def test_exposure_url_state_has_safe_default_and_preserves_existing_state(self):
        self.assertIn('url.searchParams.set("event"', self.script)
        self.assertIn('url.searchParams.set("source"', self.script)
        self.assertIn('url.searchParams.set("layer"', self.script)
        self.assertIn('url.searchParams.set("exposure"', self.script)
        self.assertIn('normaliseExposure(params.get("exposure"))', self.script)
        self.assertIn('const DEFAULT_EXPOSURE = "none"', self.script)

    def test_exposure_data_are_lazy_loaded_and_cached(self):
        initial_block = self.script.split("async function initialise()", 1)[1]
        self.assertNotIn("DATA_URLS.gemAdm1", initial_block)
        self.assertNotIn("DATA_URLS.elazigBuildings", initial_block)
        self.assertIn("state.exposureCache", self.script)
        self.assertIn('"elazig-buildings"', self.script)
        self.assertIn("loadExposureData", self.script)

    def test_exposure_errors_do_not_replace_receiver_error_state(self):
        self.assertIn("function handleExposureError", self.script)
        self.assertIn("The receiver hazard/loss layers remain available.", self.script)
        self.assertIn("state.exposureLayer.clearLayers()", self.script)
        handler = self.script.split("function handleExposureError", 1)[1].split(
            "function renderExposure", 1
        )[0]
        self.assertNotIn("failInitial(", handler)

    def test_exposure_transition_clears_previous_overlay(self):
        apply_block = self.script.split("function applyExposure", 1)[1].split(
            "function populateStats", 1
        )[0]
        self.assertIn("clearExposure();", apply_block)
        self.assertIn(
            'state.map.getPane("exposure-symbols").style.zIndex = 390',
            self.script,
        )
        self.assertIn('pane: "exposure-symbols"', self.script)

    def test_gem_attribution_is_visible_in_exposure_legend(self):
        self.assertIn("GEM Global Exposure Model", self.script)
        self.assertIn("CC BY-NC-SA 4.0", self.script)
        self.assertIn("province geometry: geoBoundaries", self.script)

    def test_zoom_dependent_clusters_and_footprints_are_present(self):
        self.assertIn('renderMode = "overview clusters"', self.script)
        self.assertIn('renderMode = "local clusters"', self.script)
        self.assertIn('renderMode = "individual footprints"', self.script)
        self.assertIn('state.map.on("zoomend"', self.script)
        self.assertIn("fitElazigPilot", self.script)
        self.assertIn("Zoom to Elazığ pilot", self.html)

    def test_dashboard_language_keeps_scientific_layers_separate(self):
        for phrase in (
            "GEM exposure, Adm1 aggregate",
            "Vulnerability class",
            "Not assigned",
            "not an official city or administrative boundary",
            "not individual building locations",
            "No structural loss is calculated for these classes.",
        ):
            self.assertIn(phrase, self.script + self.html)
        self.assertNotIn("insured loss", self.script.lower())
        self.assertNotIn("building pga", self.script.lower())


if __name__ == "__main__":
    unittest.main()
