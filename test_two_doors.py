"""Two-door contract (19 Nov 2026): every dashboard menu lists the same working
sections; parked homes stay defined but are not offered; owner tools stay out of
the partner menu."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAIL_PAGES = ['legacy-dashboard.html', 'directory.html', 'grief.html',
              'review-current-v51/index.html', 'review-analytics-v48/index.html']
MAIN = ['5Ws Reports', 'Referral Directory', 'Grief Mapping',
        'Training &amp; orientation', 'Provider register', 'Service points']


class DashboardDoorTest(unittest.TestCase):
    def test_separate_pages_share_one_menu(self):
        for page in RAIL_PAGES:
            s = (ROOT / page).read_text()
            nav = s[s.index('<nav aria-label="Dashboard sections">'):]
            nav = nav[:nav.index('</nav>')]
            main = nav[:nav.index('<div class="l2-owner" hidden>')]
            self.assertEqual(re.findall(r'<span>([^<]+)</span><small>', main), MAIN, page)
            for phrase in ('Coming next', 'pilot not open', 'Not available yet', 'PHQ-9'):
                self.assertNotIn(phrase, nav, page)
            self.assertIn('../form/', nav)

    def test_main_dashboard_menu_hides_parked_homes(self):
        js = (ROOT / 'assets/instrument-homes.js').read_text()
        for key in ('contacts', 'referrals', 'phq9', 'selfreport', 'gbv'):
            self.assertIn("{key:'%s',hidden:true," % key, js)
        for key in ('baseline', 'sample'):
            self.assertIn("{key:'%s',adminOnly:true," % key, js)
        self.assertIn("if(h.hidden||(h.adminOnly&&account?.role!=='admin'))continue;", js)

    def test_landing_sends_field_entry_to_the_form_door(self):
        s = (ROOT / 'index.html').read_text()
        self.assertIn('href="../form/"', s)
        self.assertNotIn('data-view="forms"><div', s)
        self.assertNotIn('operational activation remains held', s)


if __name__ == '__main__':
    unittest.main()
