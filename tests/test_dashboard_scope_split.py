import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class DashboardScopeSplitTests(unittest.TestCase):
    def test_research_and_expandable_pages_exist(self):
        for name in ("index.html", "future.html", "future.js", "scope.css"):
            path = DOCS / name
            self.assertTrue(path.is_file(), name)
            self.assertGreater(path.stat().st_size, 0)

    def test_research_dashboard_declares_fixed_scope(self):
        html = (DOCS / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-dashboard-scope="research"', html)
        self.assertIn("fixed placement dataset", html.lower())
        self.assertIn("does not load live earthquake feeds", html)
        self.assertIn('href="./future.html"', html)

    def test_research_visible_controls_do_not_offer_exposure_extensions(self):
        html = (DOCS / "index.html").read_text(encoding="utf-8")
        visible, hidden = html.split(
            '<section class="research-extension-placeholder" hidden aria-hidden="true">',
            1,
        )
        self.assertNotIn('name="exposure"', visible)
        self.assertIn('name="exposure"', hidden)
        self.assertIn("GEM province exposure", hidden)
        self.assertIn("Elazığ buildings", hidden)

    def test_expandable_dashboard_is_catalogue_only(self):
        html = (DOCS / "future.html").read_text(encoding="utf-8")
        script = (DOCS / "future.js").read_text(encoding="utf-8")
        self.assertIn('data-dashboard-scope="expandable"', html)
        self.assertIn("does not calculate placement-model PGA", html)
        self.assertIn("USGS_QUERY_URL", script)
        self.assertIn("fdsnws/event/1/query", script)
        self.assertNotIn("structural_loss_ratio_mean", script)
        self.assertNotIn("AkkarEtAlRhyp2014", script)
        self.assertNotIn("gem_turkiye_adm1", script)
        self.assertNotIn("elazig_buildings", script)

    def test_expandable_query_is_explicitly_bounded_and_updateable(self):
        script = (DOCS / "future.js").read_text(encoding="utf-8")
        for expected in (
            "minlatitude: 35.0",
            "maxlatitude: 43.0",
            "minlongitude: 24.0",
            "maxlongitude: 46.0",
            'format: "geojson"',
            'eventtype: "earthquake"',
            'cache: "no-store"',
            "refreshEvents",
        ):
            self.assertIn(expected, script)


if __name__ == "__main__":
    unittest.main()
