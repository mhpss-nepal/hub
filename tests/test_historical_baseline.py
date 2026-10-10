import unittest,re,subprocess,hashlib
from pathlib import Path
from test_source_navigation import STYLE
R=Path(__file__).resolve().parents[1]
BASE='47f66df13198345907ace5c314f2fbe6f9d1db58'
class HistoricalContract(unittest.TestCase):
 def test_private_source_exists(self):
  h=(R/'index.html').read_text();self.assertIn('id="historical-baseline"',h);self.assertIn('assets/historical-baseline.js',h)
  j=(R/'assets/historical-baseline.js').read_text()
  for x in ['localStorage','sessionStorage','indexedDB','fetch(','XMLHttpRequest','sendBeacon','FB.','S.']:self.assertNotIn(x,j)
  self.assertNotRegex(j,r'(?:backlog|activity)_[0-9a-f]{10,}')
  self.assertNotRegex(j,r'known_service_contacts\s*:\s*[0-9]')
  self.assertNotIn('/root/',j)
  self.assertNotIn('/Users/',j)
 def test_locked_runtime_and_palette(self):
  for f in ['assets/store.js','assets/fb.js','assets/fb-config.js','assets/codes.js','assets/i18n.js','assets/i18n-strings.js','assets/hub-shell.css','assets/design.css']:
   self.assertEqual((R/f).read_bytes(),subprocess.check_output(['git','show',BASE+':'+f],cwd=R),f)
  old=subprocess.check_output(['git','show',BASE+':index.html'],cwd=R).decode();new=(R/'index.html').read_text()
  oldstyles=re.findall(r'<style[^>]*>(.*?)</style>',old,re.S);newstyles=re.findall(r'<style[^>]*>(.*?)</style>',new,re.S)
  self.assertEqual(new.count(STYLE),1)
  self.assertEqual(oldstyles,[s.replace(STYLE,"") for s in newstyles])
  oldids=set(re.findall(r'\bid="([^"]+)"',old));newids=re.findall(r'\bid="([^"]+)"',new)
  self.assertEqual(len(newids),len(set(newids)))
  approved_additions={'useHistorical','historical-baseline','historical-file','historical-status','historical-results','historical-stats','historical-export','historical-clear','historical-provenance','historical-summary'}
  self.assertFalse(oldids-set(newids));self.assertEqual(set(newids)-oldids,approved_additions)
 def test_no_public_data_asset(self):
  j=(R/'assets/historical-baseline.js').read_text()
  self.assertIn('Object.keys',j);self.assertIn('Number.isSafeInteger',j);self.assertIn('textContent',j)
  self.assertNotIn('innerHTML',j);self.assertNotIn('MASTER',j)
if __name__=='__main__':unittest.main(verbosity=2)
