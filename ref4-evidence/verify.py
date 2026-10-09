from pathlib import Path
import unittest,json,re,hashlib,subprocess,socket
from html.parser import HTMLParser
from urllib.parse import urlsplit
R=Path(__file__).resolve().parents[1];E=R/'ref4-evidence';BASE='b02e14a73edc7c0061bdeeaab652c66dd7224883'
q=json.loads((E/'qa-report.json').read_text());b=(E/'baseline.html').read_text();s=(R/'index.html').read_text()
class Parser(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.controls=[];self.assets=[]
 def handle_starttag(self,t,attrs):
  a=dict(attrs)
  if a.get('id'):self.ids.append(a['id'])
  if t in ['input','select','textarea','button']:self.controls.append((t,)+tuple(a.get(k,'') for k in ['type','id','name','form','data-dim','data-p','required']))
  if t in ['script','link'] and (a.get('src') or a.get('href')):self.assets.append(a.get('src',a.get('href')))
def parse(t):p=Parser();p.feed(t);return p
class Ref4(unittest.TestCase):
 def test_01_exact_source(self):self.assertEqual(q['candidate_index_sha256'],hashlib.sha256(s.encode()).hexdigest());self.assertEqual(b.encode(),subprocess.check_output(['git','show',BASE+':index.html'],cwd=R))
 def test_02_all_base_files_except_index_unchanged(self):
  inv=json.loads((E/'PRESERVATION-INVENTORY.json').read_text())
  for p,h in inv['files'].items():
   if p=='tests/test_dashboard_visual_contract.py':
    # Exact reviewer-prescribed test-only correction; runtime assets stay locked.
    self.assertEqual(hashlib.sha256((R/p).read_bytes()).hexdigest(),'6a3ed1abc175d387b32b93f25b82480f46983b88086397045e25f92e84b7e2ab',p)
   elif p!='index.html':self.assertEqual(hashlib.sha256((R/p).read_bytes()).hexdigest(),h,p)
 def test_03_controls_ids_assets(self):
  a,c=parse(b),parse(s);self.assertCountEqual(a.controls,c.controls);self.assertEqual(a.assets,c.assets);self.assertEqual(len(c.ids),len(set(c.ids)))
 def test_04_runtime_exact_except_one_guard(self):
  a=re.findall('<script>(.*?)</script>',b,re.S);c=re.findall('<script>(.*?)</script>',s,re.S)
  self.assertEqual(a[0],c[0]);self.assertEqual(a[1].replace('if (done || !st || !st.ready) return;','if (done || !st || !st.ready || !st.user) return;'),c[1]);self.assertEqual(len(c),3)
  for forbidden in ['localStorage','sessionStorage','FB.','STORE.','fetch(','XMLHttpRequest']:
   self.assertNotIn(forbidden,c[2])
 def test_05_signedout_routes_all_widths(self):
  self.assertEqual(len(q['firstscreen']),6)
  for r in q['firstscreen']:
   self.assertTrue(all(r['checks'].values()),str(r));self.assertFalse(r['axe'])
 def test_06_keyboard_and_status_preservation(self):
  for r in q['firstscreen']:
   for k in ['keyboardAccessOpen','keyboardAccessClosed','warningPreserved','pendingPreserved','errorPreserved','explicitDemoLoaded','shellHiddenAfterDemo','noRemoteWriteAfterDemo']:self.assertTrue(r[k],k)
 def test_07_parity_all_values_non_null(self):
  self.assertEqual(set(q['parity']),{'320','390','1280'})
  for width,p in q['parity'].items():self.assertEqual(len(p),27);self.assertTrue(all(p.values()),width)
  for r in q['runs']:
   for k in ['csv','matrixCSV']:self.assertGreater(r['snapshotProof'][k]['characters'],100)
 def test_08_axe_all_loaded_states(self):
  for r in q['runs']:
   self.assertFalse(r['errors'])
   for a in r['axe'].values():self.assertFalse(a)
 def test_09_storage_writes_language(self):
  for r in q['runs']:
   self.assertEqual(json.loads(r['storageBefore']),{});self.assertEqual(json.loads(r['storageAfter']),{'mhpss-np-lang':'en'});self.assertFalse(r['remoteWrites']);self.assertFalse(r['reads']);self.assertEqual(r['lang'],'ne')
 def test_10_responsive_order_labels(self):
  for r in q['runs']:
   for g in r['geometry'].values():self.assertLessEqual(g['scroll'],g['client'])
   if not r['base']:
    self.assertTrue(all(x['hasLabel'] for x in r['inputLabels']));ys=[x['y'] for x in r['primaryOrder']];self.assertEqual(ys,sorted(ys))
 def test_11_root_auth_explicit_preserved(self):
  a,b=q['authJourneys'];self.assertEqual(a['initialReads'],[]);self.assertEqual(a['explicitRead'],['activity']);self.assertEqual(b['initialReads'],['activity'])
  for r in q['authJourneys']:self.assertTrue(r['accessOpen']);self.assertTrue(r['livePanelVisible'])
 def test_12_red_and_mutation(self):
  red=json.loads((E/'red-report.json').read_text());self.assertTrue(any(not all(r['checks'].values()) for r in red['firstscreen']));self.assertTrue(q['mutation']['killed']);self.assertFalse(q['mutation']['checks']['no_sidebar'])
 def test_13_cleanup(self):
  u=urlsplit(q['origin']);sock=socket.socket();sock.settimeout(1);self.assertNotEqual(sock.connect_ex((u.hostname,u.port)),0);sock.close()
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(Ref4);result=unittest.TextTestRunner(verbosity=2).run(suite)
 out={'passed':result.testsRun-len(result.failures)-len(result.errors),'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'firstscreen_cases':len(q['firstscreen']),'firstscreen_assertions':sum(len(r['checks']) for r in q['firstscreen']),'parity_comparisons':sum(len(p) for p in q['parity'].values()),'axe_candidate_states':sum(len(r['axe']) for r in q['runs'] if not r['base'])+len(q['firstscreen']),'index_sha256':q['candidate_index_sha256'],'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R).decode().strip(),'tree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=R).decode().strip(),'screenshots':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in E.glob('*.png')}}
 (E/'verification.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));raise SystemExit(not result.wasSuccessful())
