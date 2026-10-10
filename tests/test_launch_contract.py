"""Approved launch UI delta against the independently reviewed Auth candidate."""
from pathlib import Path
from html.parser import HTMLParser
import subprocess, unittest, re
R=Path(__file__).resolve().parents[1]
BASE='e2160ff4d7a2cf334a78055af9eb88ebeeafa5ad'
def old(path):return subprocess.check_output(['git','show',BASE+':'+path],cwd=R).decode()
class DOM(HTMLParser):
 def __init__(self,text):super().__init__();self.ids=[];self.controls=[];self.form='';self.feed(text)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
  if tag=='form':self.form=a.get('id','')
  if tag in ['input','select','textarea','button']:self.controls.append((tag,)+tuple(a.get(k,'') for k in ['type','id','name','required'])+(a.get('form',self.form),))
 def handle_endtag(self,tag):
  if tag=='form':self.form=''
class LaunchContract(unittest.TestCase):
 def test_only_declared_controls_and_wrappers_added(self):
  a,b=DOM(old('index.html')),DOM((R/'index.html').read_text())
  approved_additions={'launch-entry-layout','source-tools','historical-account','historical-password-options','historical-password-signin'}
  self.assertEqual(set(b.ids)-set(a.ids),approved_additions);self.assertFalse(set(a.ids)-set(b.ids));self.assertEqual(len(b.ids),len(set(b.ids)))
  additions=[c for c in b.controls if c not in a.controls]
  self.assertEqual(additions,[('button','submit','historical-password-signin','','','historical-login-form')])
  self.assertCountEqual(a.controls,[c for c in b.controls if c not in additions])
 def test_reviewed_auth_startup_legacy_and_shared_assets_byte_locked(self):
  for f in ['assets/baseline-auth.js','assets/baseline-startup.js','assets/fb.js','assets/store.js','assets/fb-config.js','assets/codes.js','assets/i18n.js','assets/i18n-strings.js','assets/hub-shell.css','assets/design.css']:
   self.assertEqual((R/f).read_text(),old(f),f)
 def test_reader_validation_fetch_and_csv_unchanged(self):
  a=old('assets/historical-baseline.js');b=(R/'assets/historical-baseline.js').read_text()
  for start,end in [('  var ENDPOINT','  function setStatus'),('  async function refresh()', '  function csv()'),('  function csv()', "  $('historical-refresh')")]:
   # New presentation state lives immediately before setStatus, outside validation.
   aa=a[a.index(start):a.index(end,a.index(start))];bb=b[b.index(start):b.index(end,b.index(start))]
   if end=='  function setStatus':bb=bb.removesuffix('  var linkPending = false;\n')
   self.assertEqual(aa,bb)
 def test_existing_inline_controller_and_category_palette_exact(self):
  a=old('index.html');b=(R/'index.html').read_text()
  self.assertEqual(re.findall(r'<script>(.*?)</script>',a,re.S),re.findall(r'<script>(.*?)</script>',b,re.S))
  self.assertEqual(re.search(r'<style id="dashboard-category-palette">(.*?)</style>',a,re.S).group(1),re.search(r'<style id="dashboard-category-palette">(.*?)</style>',b,re.S).group(1))
if __name__=='__main__':unittest.main(verbosity=2)
