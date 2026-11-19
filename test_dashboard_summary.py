"""Locks the 19 Nov 2026 summary-first dashboard layout for the Referral Directory and Grief Mapping
pages, and checks the Excel download holds organisation-level data only."""
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
DIR = (ROOT / 'directory.html').read_text(encoding='utf-8')
GRIEF = (ROOT / 'grief.html').read_text(encoding='utf-8')


class DirectorySummaryFirst(unittest.TestCase):
    def test_order_summary_findings_then_closed_database(self):
        i_heat, i_find, i_db = DIR.index('id="heat"'), DIR.index('id="find"'), DIR.index('<details class="panel2 rd-db" id="db">')
        self.assertTrue(i_heat < i_find < i_db)
        self.assertNotIn('id="db" open', DIR)

    def test_heatmap_cells_open_the_organisations(self):
        self.assertIn('id="pick"', DIR)
        self.assertIn('function pickRows()', DIR)

    def test_excel_is_built_in_the_browser_from_the_public_seed(self):
        # the hub repository ignores *.xlsx on purpose; the workbook is made on click from the page data
        self.assertFalse(list((ROOT / 'data').glob('*.xlsx')))
        self.assertIn('id="xlsx"', DIR)
        self.assertIn('X.writeFile(wb,"referral-directory-unconfirmed-"', DIR)
        self.assertNotIn('Staff contacts', DIR)


class GriefSummary(unittest.TestCase):
    def test_small_palikas_hidden_and_labels_follow_the_form(self):
        self.assertIn('const MIN=5', GRIEF)
        self.assertIn('Ceremonies not yet held', GRIEF)
        self.assertIn('What is stopping funeral and mourning ceremonies', GRIEF)
        self.assertLess(GRIEF.index('id="heat"'), GRIEF.index('id="find"'))


if __name__ == '__main__':
    unittest.main()
