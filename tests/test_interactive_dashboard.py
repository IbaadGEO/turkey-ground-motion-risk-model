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
        html = (DOCS / "index.html").read_text(encoding="utf-8-sig")
        for expected in [
            "300&ndash;500",
            "500&ndash;700",
            "700&ndash;900",
        ]:
            self.assertIn(expected, html)

    def test_nonselected_earthquakes_are_visually_deemphasised(self):
        javascript = (DOCS / "dashboard.js").read_text(encoding="utf-8-sig")
        self.assertIn("magnitudeRadius * 0.68", javascript)
        self.assertIn("fillOpacity: selected ? 0.98 : 0.38", javascript)
        self.assertIn("weight: selected ? 3 : 0.8", javascript)
        self.assertIn("eventMarkerRadius(event, selected)", javascript)

    def test_dashboard_has_no_mojibake_sequences(self):
        combined = "\n".join(
            (DOCS / name).read_text(encoding="utf-8-sig")
            for name in ["index.html", "dashboard.js"]
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


if __name__ == "__main__":
    unittest.main()