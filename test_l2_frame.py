"""One frame for every Layer 2 page (QC 20 Nov 2026): the stand-alone pages wear the main
dashboard's frame, so moving between sections does not jump."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(p):
    return (ROOT / p).read_text(encoding="utf-8")


class LayerTwoFrame(unittest.TestCase):
    def test_standalone_pages_wear_the_frame(self):
        for page, key in (("grief.html", "grief"), ("directory.html", "directory"), ("team.html", "team")):
            s = read(page)
            self.assertIn('data-l2-page="%s"' % key, s, page)
            self.assertIn('href="assets/l2-frame.css"', s, page)
            self.assertLess(s.index('src="assets/l2-frame.js"'), s.index('src="assets/codes.js"'), page)

    def test_frame_matches_the_main_dashboard(self):
        css, landing = read("assets/l2-frame.css"), read("assets/landing.css")
        self.assertIn("grid-template-columns:248px", css)
        self.assertIn(".dashlayout{display:grid;grid-template-columns:248px", landing)
        self.assertIn("background:#193d5b", css)
        self.assertIn(".sidebar{background:#193d5b", landing)
        self.assertIn("min-height:60px", css)

    def test_menus_list_the_same_sections_in_the_same_order(self):
        homes = read("assets/instrument-homes.js")
        listed = [k for k, hidden in re.findall(r"\{key:'([a-z0-9]+)'(,hidden:true)?", homes) if not hidden]
        frame = re.findall(r'\["([a-z0-9]+)", "', read("assets/l2-frame.js"))
        self.assertEqual(listed, frame)

    def test_older_pages_wear_the_frame_too(self):
        for page, key, css, js in (("review-analytics-v48/index.html", "baseline", "../assets/l2-frame.css", "../assets/l2-frame.js"),
                                   ("legacy-dashboard.html", "sample", "assets/l2-frame.css", "assets/l2-frame.js")):
            s = read(page)
            self.assertIn('data-l2-page="%s"' % key, s, page)
            self.assertIn('href="%s"' % css, s, page)
            self.assertIn('src="%s"' % js, s, page)
        self.assertIn("<h1>Historical Baseline</h1>", read("review-analytics-v48/index.html"))
        self.assertIn("<h1>Sample Data</h1>", read("legacy-dashboard.html"))

    def test_no_flash_of_the_wrong_state_while_signing_in(self):
        g = read("grief.html")
        self.assertIn("gm-wait", g)
        self.assertIn('st.restoration!=="restoring"', g)
        t = read("team.html")
        self.assertIn('<div class="card hidden" id="signedOut">', t)
        self.assertNotIn("notice('Checking your approved account profile…')", read("assets/landing.js"))

    def test_routine_success_notice_is_not_shown(self):
        self.assertNotIn("Account access verified. Registration choices never change permissions.", read("assets/landing.js"))


if __name__ == "__main__":
    unittest.main()
