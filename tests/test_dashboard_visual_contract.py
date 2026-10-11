"""Exact-baseline presentation contract; no third party dependency."""
import unittest,re,json,hashlib,subprocess
from pathlib import Path
from html.parser import HTMLParser
from test_source_navigation import DEMO
ROOT=Path(__file__).resolve().parents[1]
BASE='e74e128'
class Parser(HTMLParser):
 def __init__(self):super().__init__();self.controls=[];self.ids=[];self.assets=[]
 def handle_starttag(self,t,attrs):
  a=dict(attrs)
  if a.get('id'):self.ids.append(a['id'])
  if t in ['input','select','textarea','button']:self.controls.append((t,)+tuple(a.get(k,'') for k in ['type','id','name','form','data-dim','data-p','required']))
  if t in ['script','link'] and (a.get('src') or a.get('href')):self.assets.append(a.get('src',a.get('href')))
def parse(s):p=Parser();p.feed(s);return p
class Contract(unittest.TestCase):
 def setUp(self):
  self.old=subprocess.check_output(['git','show',BASE+':index.html'],cwd=ROOT).decode();self.new=(ROOT/'index.html').read_text()
 def test_controls_and_assets_exact(self):
  a,b=parse(self.old),parse(self.new)
  # Only anonymous navigation controls may be removed; every data control remains exact.
  self.assertCountEqual([c for c in a.controls if c[2]],[c for c in b.controls if c[2]])
  self.assertEqual(b.assets,a.assets+['assets/layer2-nav.js'])
  self.assertEqual(len(b.ids),len(set(b.ids)))
 def assert_scripts_contract(self,new):
  a=re.findall(r'<script>(.*?)</script>',self.old,re.S);b=re.findall(r'<script>(.*?)</script>',new,re.S)
  self.assertEqual(len(a),3);self.assertEqual(len(b),2)
  self.assertEqual(a[1:],b) # only obsolete rail controller removed
 def test_changed_menu_or_route_rejected(self):
  nav=(ROOT/'assets/layer2-nav.js').read_text()
  for word in ['localStorage','sessionStorage','fetch(', 'indexedDB','BaselineAuth','FIELD_QUEUE']:
   self.assertNotIn(word,nav)
  self.assertIn("window.addEventListener('hashchange', mark)",nav)
  self.assertIn("e.key === 'Escape'",nav)
 def test_scripts_byte_exact(self):self.assert_scripts_contract(self.new)
 def test_restored_unsigned_autoconnect_rejected(self):
  with self.assertRaises(AssertionError):self.assert_scripts_contract(self.new.replace('if (done || !st || !st.ready || !st.user) return;','if (done || !st || !st.ready) return;'))
 def test_changed_observer_rejected(self):
  with self.assertRaises(AssertionError):self.assert_scripts_contract(self.new.replace('shell.hidden=!app.hidden;','shell.hidden=false;'))
 def test_widened_kind_rejected(self):
  with self.assertRaises(AssertionError):self.assert_scripts_contract(self.new.replace('Q_KINDS = ["activity"];','Q_KINDS = ["phq9"];',1))
 def test_all_existing_runtime_assets_exact(self):
  inv=json.loads((ROOT/'design-preview/PRESERVATION-INVENTORY.json').read_text())
  for f,d in inv['assets'].items():
   if f=='assets/hub-shell.css':
    self.assertTrue((ROOT/f).read_bytes().startswith(subprocess.check_output(['git','show',BASE+':'+f],cwd=ROOT)))
   else:self.assertEqual(hashlib.sha256((ROOT/f).read_bytes()).hexdigest(),d['sha256'],f)
 def test_selected_reference_structure(self):
  self.assertIn('dashboard-selected',self.new)
  self.assertIn('id="dashboard-main"',self.new)
  self.assertIn('id="analysis-primary"',self.new)
  self.assertIn('aria-label="Find reports"',self.new)
 def test_control_loss_is_detectable(self):self.assertNotEqual(parse(self.new).controls,parse(self.new.replace('id="fOrg"','id="lostOrg"')).controls)
if __name__=='__main__':unittest.main(verbosity=2)
