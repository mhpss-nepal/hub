"""Exact-baseline presentation contract; no third party dependency."""
import unittest,re,json,hashlib,subprocess
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1]
BASE='180a64e8ccb077e26d0905adffa320e107ffb45f'
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
  approved_additions={'useHistorical','historical-file','historical-export','historical-clear'}
  added=[c for c in b.controls if c not in a.controls]
  self.assertCountEqual(a.controls,[c for c in b.controls if c not in added])
  self.assertEqual({c[2] for c in added},approved_additions);self.assertEqual(len(added),len(approved_additions))
  self.assertEqual(b.assets,a.assets+['assets/historical-baseline.js'])
  self.assertEqual(len(b.ids),len(set(b.ids)))
 def assert_scripts_contract(self,new):
  a=re.findall(r'<script>(.*?)</script>',self.old,re.S);b=re.findall(r'<script>(.*?)</script>',new,re.S)
  old_guard='if (done || !st || !st.ready) return;'
  new_guard='if (done || !st || !st.ready || !st.user) return;'
  self.assertEqual(len(a),2);self.assertEqual(len(b),3)
  # W40 approved menu-controller interval only; all other rail code stays exact.
  start="  var saved={};";end="  var m=rail.querySelector('.rmenu');"
  x,y=a[0],b[0]
  self.assertEqual(x[:x.index(start)],y[:y.index(start)])
  self.assertEqual(x[x.index(end):],y[y.index(end):])
  self.assertEqual(hashlib.sha256(y[y.index(start):y.index(end)].encode()).hexdigest(),'8bf38aa2765c39a5fd052498e062e0f508f21297bb9b68bd73f4ebf453362878')
  self.assertEqual(a[1].count(old_guard),1)
  legacy_source_guard='if (/[?&]source=choose\\b/.test(location.search) || !window.FB || !window.FB.onStatus) return;'
  explicit_source_guard='if (new URLSearchParams(location.search).get("source") !== "live" || !window.FB || !window.FB.onStatus) return;'
  self.assertEqual(a[1].count(legacy_source_guard),1)
  self.assertEqual(b[1],a[1].replace(old_guard,new_guard).replace(legacy_source_guard,explicit_source_guard))
  self.assertEqual(b[1].count(explicit_source_guard),1)
  self.assertEqual(hashlib.sha256(b[2].encode()).hexdigest(),'85a7cfca5e4d8fb42822015a90fd65b443a816efeec4379fb3de6d67e9910ed0')
 def test_changed_menu_or_route_rejected(self):
  for old,new in [("closeAux(); setOpen(g,on);","setOpen(g,on);"),("hashchange', mark","hashchange', closeAux")]:
   with self.assertRaises(AssertionError):self.assert_scripts_contract(self.new.replace(old,new,1))
 def test_scripts_byte_exact(self):self.assert_scripts_contract(self.new)
 def test_restored_unsigned_autoconnect_rejected(self):
  with self.assertRaises(AssertionError):self.assert_scripts_contract(self.new.replace('if (done || !st || !st.ready || !st.user) return;','if (done || !st || !st.ready) return;'))
 def test_changed_observer_rejected(self):
  with self.assertRaises(AssertionError):self.assert_scripts_contract(self.new.replace('shell.hidden=!app.hidden;','shell.hidden=false;'))
 def test_widened_kind_rejected(self):
  with self.assertRaises(AssertionError):self.assert_scripts_contract(self.new.replace('Q_KINDS = ["activity"];','Q_KINDS = ["phq9"];',1))
 def test_all_existing_runtime_assets_exact(self):
  inv=json.loads((ROOT/'design-preview/PRESERVATION-INVENTORY.json').read_text())
  for f,d in inv['assets'].items():self.assertEqual(hashlib.sha256((ROOT/f).read_bytes()).hexdigest(),d['sha256'],f)
 def test_selected_reference_structure(self):
  self.assertIn('dashboard-selected',self.new)
  self.assertIn('id="dashboard-main"',self.new)
  self.assertIn('id="analysis-primary"',self.new)
  self.assertIn('aria-label="Find reports"',self.new)
 def test_control_loss_is_detectable(self):self.assertNotEqual(parse(self.new).controls,parse(self.new.replace('id="fOrg"','id="lostOrg"')).controls)
if __name__=='__main__':unittest.main(verbosity=2)
