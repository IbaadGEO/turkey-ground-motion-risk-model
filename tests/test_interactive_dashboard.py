import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class InteractiveDashboardTests(unittest.TestCase):
    def test_dashboard_assets_exist(self):
        for relative_path in [
            "index.html",
            "dashboard.css",
            "dashboard.js",
            "INTERACTIVE_DASHBOARD.md",
        ]:
            path = DOCS / relative_path
            self.assertTrue(path.is_file(), relative_path)
            self.assertGreater(path.stat().st_size, 0)

    def test_dashboard_references_repository_data(self):
        javascript = (DOCS / "dashboard.js").read_text(encoding="utf-8-sig")
        for expected in [
            "data/turkey_boundary.geojson",
            "data/turkey_50km_land_grid_vs30.csv",
            "outputs_gwfm/complete_output/earthquake_depth_pga_loss_summary.csv",
            "./data/dashboard_manifest.json",
        ]:
            self.assertIn(expected, javascript)

    def test_dashboard_has_expected_interactive_libraries(self):
        html = (DOCS / "index.html").read_text(encoding="utf-8-sig")
        self.assertIn("leaflet", html.lower())
        self.assertIn("papaparse", html.lower())
        self.assertIn("plotly", html.lower())
        self.assertIn('id="map"', html)

    def test_leaflet_css_integrity_hash(self):
        html = (DOCS / "index.html").read_text(encoding="utf-8-sig")
        self.assertIn(
            "sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=",
            html,
        )

    def test_legend_uses_encoding_safe_ranges(self):
        javascript = (DOCS / "dashboard.js").read_text(encoding="utf-8-sig")
        for expected in [
            "300&ndash;500",
            "500&ndash;700",
            "700&ndash;900",
        ]:
            self.assertIn(expected, javascript)

    def test_selected_earthquake_is_always_separate_from_optional_others(self):
        javascript = (DOCS / "dashboard.js").read_text(encoding="utf-8-sig")
        html = (DOCS / "index.html").read_text(encoding="utf-8-sig")
        self.assertIn("magnitudeRadius * 0.68", javascript)
        self.assertIn("fillOpacity: selected ? 0.98 : 0.38", javascript)
        self.assertIn("weight: selected ? 3 : 0.8", javascript)
        self.assertIn("eventMarkerRadius(event, selected)", javascript)
        self.assertIn("selectedEventLayer", javascript)
        self.assertIn("otherEventLayer", javascript)
        self.assertIn("state.selectedEventLayer.addTo(state.map)", javascript)
        self.assertNotIn('id="show-events" type="checkbox" checked', html)
        self.assertIn("Show all earthquake locations", html)

    def test_dashboard_has_no_mojibake_sequences(self):
        combined = "\n".join(
            (DOCS / name).read_text(encoding="utf-8-sig")
            for name in ["index.html", "dashboard.js", "INTERACTIVE_DASHBOARD.md"]
        )
        for suspicious in ["\u00e2", "\u00c2", "\u00c3"]:
            self.assertNotIn(suspicious, combined)

    def test_dashboard_has_no_environment_specific_paths(self):
        combined = "\n".join(
            (DOCS / name).read_text(encoding="utf-8-sig")
            for name in [
                "index.html",
                "dashboard.css",
                "dashboard.js",
                "INTERACTIVE_DASHBOARD.md",
            ]
        )
        patterns = [
            r"[A-Za-z]:\\Users\\",
            r"/(?:home|Users)/[^/\s]+",
            r"file_[0-9A-Za-z]{12,}",
        ]
        for pattern in patterns:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, combined))

    def test_dashboard_v2_controls_and_cache_busting_are_present(self):
        html = (DOCS / "index.html").read_text(encoding="utf-8-sig")
        self.assertIn("Interactive dashboard v2", html)
        self.assertIn('name="map-variable" value="vs30"', html)
        self.assertIn('name="map-variable" value="pga" checked', html)
        self.assertIn('name="map-variable" value="loss"', html)
        self.assertIn("dashboard.css?v=20260902-1", html)
        self.assertIn("dashboard.js?v=20260902-1", html)

    def test_dashboard_uses_validated_headline_metrics(self):
        javascript = (DOCS / "dashboard.js").read_text(encoding="utf-8-sig")
        for field in [
            "maximum_pga_g",
            "mean_pga_g",
            "maximum_structural_loss_ratio",
            "mean_structural_loss_ratio",
        ]:
            self.assertIn(field, javascript)
        html = (DOCS / "index.html").read_text(encoding="utf-8-sig")
        self.assertIn("Highest modelled value among 311 receivers", html)
        self.assertIn("Arithmetic mean across 311 receivers", html)

    def test_mean_comparisons_use_visible_diamond_markers(self):
        javascript = (DOCS / "dashboard.js").read_text(encoding="utf-8-sig")
        self.assertIn('type: "scatter"', javascript)
        self.assertIn('mode: "markers"', javascript)
        self.assertIn('name: "Mean"', javascript)
        self.assertIn('symbol: "diamond"', javascript)
        self.assertIn('color: "#e69f00"', javascript)

    def test_dashboard_has_scenario_cache_and_stale_data_protection(self):
        javascript = (DOCS / "dashboard.js").read_text(encoding="utf-8-sig")
        for expected in [
            "scenarioCache: new Map()",
            "scenarioRequestToken",
            "state.thematicLayer.clearLayers()",
            "No validated receiver data exist",
            "Malformed JSON",
            "must contain ${EXPECTED_RECEIVERS} receivers",
        ]:
            self.assertIn(expected, javascript)

    def test_url_state_includes_layer_with_safe_default(self):
        javascript = (DOCS / "dashboard.js").read_text(encoding="utf-8-sig")
        self.assertIn('const DEFAULT_LAYER = "pga"', javascript)
        self.assertIn('url.searchParams.set("layer", state.selectedLayer)', javascript)
        self.assertIn('normaliseLayer(params.get("layer"))', javascript)

    def test_dynamic_legends_match_map_scales(self):
        javascript = (DOCS / "dashboard.js").read_text(encoding="utf-8-sig")
        for expected in [
            'title: "PGA (g)"',
            'title: "Structural loss ratio (%)"',
            'type: "log"',
            'type: "linear"',
            'const ZERO_COLOUR = "#bdbdbd"',
            "renderVs30Legend",
        ]:
            self.assertIn(expected, javascript)

    def test_vulnerability_and_exposure_limits_are_explicit(self):
        html = (DOCS / "index.html").read_text(encoding="utf-8-sig")
        self.assertIn("MUR+CLBRS/LWAL/CDN+ERN/H:1/RES", html)
        self.assertIn("not monetary or insured-loss estimates", html)
        self.assertIn("Vulnerability class not assigned to buildings", html)
        self.assertIn("No verified building or city-exposure dataset", html)


if __name__ == "__main__":
    unittest.main()
