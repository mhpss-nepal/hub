"""All-homes source/safety boundary pinned to fresh b330e73."""
import subprocess, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='b330e73018908b8330d4b287265f3b6cc6fb5929'
class Scope(unittest.TestCase):
 def test_integrated_registry(self):
  self.assertTrue((ROOT/'assets/instrument-homes.js').exists(), 'unified instrument homes missing')
  text=(ROOT/'assets/instrument-homes.js').read_text()
  for key in ['5ws','contacts','referrals','phq9','selfreport','training','providers','servicepoints','gbv','baseline','sample']:
   self.assertIn("key:'"+key+"'",text)
  self.assertIn('ALL_HOMES', (ROOT/'assets/landing.js').read_text())
 def test_locked_sources_unchanged(self):
  for name in ['assets/store.js','assets/codes.js','assets/i18n-strings.js','assets/training-form.js','staff-5ws-shell.html']:
   self.assertEqual((ROOT/name).read_bytes(), subprocess.check_output(['git','show',BASE+':'+name],cwd=ROOT),name)
 def test_reviewed_protocol_only_deltas(self):
  staff=(ROOT/'assets/staff-api.js').read_text()
  self.assertEqual(staff.replace("SECTIONS=['5ws','contacts','referrals','phq9','selfreport','training','providers','servicepoints','gbv','baseline','sample']","SECTIONS=['5ws','contacts','referrals','phq9','gbv','baseline','sample']"),subprocess.check_output(['git','show',BASE+':assets/staff-api.js'],cwd=ROOT).decode())
 def test_training_transport_only_admin_reader_delta(self):
  text=(ROOT/'assets/training-api.js').read_text()
  for old,new in [("async function pages(own,admin=false){","async function pages(own){"),("own?'/training/entries':admin?'/dashboard/training':'/training/current'","own?'/training/entries':'/training/current'"),("current:(admin=false)=>pages(false,admin===true)","current:()=>pages(false)")]:text=text.replace(old,new)
  self.assertEqual(text,subprocess.check_output(['git','show',BASE+':assets/training-api.js'],cwd=ROOT).decode())
 def test_no_deleted_clinical_input_routes(self):
  js=(ROOT/'assets/landing.js').read_text()
  self.assertNotIn("'contact.html'",js)
  self.assertNotIn("'referral.html'",js)
if __name__=='__main__':unittest.main()
