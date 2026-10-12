"""Declared approved-root gate, additive to unchanged per-layer language checks."""
import subprocess, unittest
from pathlib import Path
R=Path(__file__).resolve().parent
class ApprovedRootCorrection(unittest.TestCase):
 def test_strict_contract_and_continuation(self):
  subprocess.run(['node','tests/landing-correction.cjs'],cwd=R,check=True)
 def test_preserved_auth_queue_and_language_engine(self):
  subprocess.run(['node','tests/landing-contract.cjs'],cwd=R,check=True)
  for p in ['assets/i18n.js','assets/i18n-strings.js','review-current-v51/current-auth.js','review-current-v51/field-queue.js']:
   self.assertEqual((R/p).read_bytes(),subprocess.check_output(['git','show','649dac352772863ccc86ed5f65b1b3763f6a8315:'+p],cwd=R))
 def test_root_loads_one_existing_language_engine(self):
  html=(R/'index.html').read_text()
  self.assertEqual(html.count('src="assets/i18n.js"'),1)
  self.assertIn('data-i18n-toggle',html)
  self.assertIn('src="assets/landing-strings.js"',html)
  self.assertIn('id="base" maxlength="160"',html)
  self.assertNotIn('id="base" required',html)
