"""Pre-launch QC of 20 Nov 2026 (hub side): ministry abbreviation and CSV formula guard."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class HubPrelaunch(unittest.TestCase):
    def test_ministry_abbreviation_is_mohfs(self):
        self.assertIn('credit("MoHFS &middot; EDCD"', (ROOT / "assets/brand.js").read_text(encoding="utf-8"))
        self.assertIn('"attrib.mohp":        "MoHFS · EDCD"', (ROOT / "assets/i18n-strings.js").read_text(encoding="utf-8"))

    def test_csv_exports_neutralise_formulas(self):
        self.assertIn("/^[=+@\\-\\t\\r]/.test(s)", (ROOT / "assets/store.js").read_text(encoding="utf-8"))
        self.assertIn("""replace(/^([=+\\-@\\t\\r])/,"'$1")""", (ROOT / "directory.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
