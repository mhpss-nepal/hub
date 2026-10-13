"""Real Chromium + actual modules. All API/Auth responses EXPLICIT SYNTHETIC.
No live data or provider authority proof. No outbound writes permitted.
"""
import json, hashlib, copy, csv, io, mimetypes
from pathlib import Path
from threading import Thread
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'all-homes-evidence';EVIDENCE.mkdir(exist_ok=True)
AUTH="""window.BaselineAuth={u:{uid:'fixture-A',emailVerified:true,email:'fixture@example.invalid'},currentUser(){return this.u},async token(){return 'EXPLICIT-SYNTHETIC-'+this.u.uid},callbacks:[],onChange(f){this.callbacks.push(f);f(this.u,{ready:true,restoration:'signed-in'})},async signOut(){this.u=null;this.callbacks.forEach(f=>f(null,{ready:true}))},switch(){this.u={uid:'fixture-B',emailVerified:true};this.callbacks.forEach(f=>f(this.u,{ready:true,restoration:'signed-in'}))}};"""
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  path=urlparse(self.path).path.removeprefix('/hub/')
  if path.endswith('current-auth.js'):data=AUTH.encode();mime='application/javascript'
  else:
   f=ROOT/(path or 'index.html')
   if f.is_dir():f=f/'index.html'
   if not f.is_file():self.send_error(404);return
   data=f.read_bytes();mime=mimetypes.guess_type(f.name)[0] or 'text/plain'
  self.send_response(200);self.send_header('Content-Type',mime);self.end_headers();self.wfile.write(data)
def run():
 # Reuse explicitly synthetic accepted-schema fixture, not production records.
 corpus=json.loads((ROOT.parent/'non5ws-integration/non5ws_bridge/evidence/browser.json').read_text())
 payload=copy.deepcopy(next(iter(corpus[0]['records'].values()))[0]);payload['title']='SYNTHETIC TRAINING EVENT';payload.pop('_saved',None)
 def row(i):
  p=copy.deepcopy(payload);p['title']+=' '+str(i)
  return dict(reportId='tr_fixture'+str(i),revision=1,request_sha256=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),subject='fixture-A',org=p['org'],createdAt='2026-10-12T00:00:00Z',updatedAt='2026-10-12T00:00:00Z',payload=p)
 fixture=[row(1),row(2)]
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
 results=[]
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  for width in [390,1280]:
   ctx=browser.new_context(viewport={'width':width,'height':900},accept_downloads=True,service_workers='block');state={'deny':False,'requests':[],'sections':['5ws'],'role':'manager'};errors=[]
   def route(r):
    if r.request.url.startswith(base):r.continue_();return
    path=urlparse(r.request.url).path;state['requests'].append({'path':path,'method':r.request.method})
    assert r.request.method=='GET','No reader writes permitted'
    if path=='/account/profile':d=dict(protocol='staff-account/1',status='active',role=state['role'],scope={'org':None,'cluster':None},sections=state['sections'],profile=None,reportingAccess=False)
    elif path=='/dashboard/5ws':d=dict(protocol='staff-dashboard/1',section='5ws',rows=[],complete=True,nextCursor=None,scope={'org':None,'cluster':None})
    elif path in ['/training/current','/training/entries','/dashboard/training']:
     if state['deny'] or r.request.headers.get('authorization','').endswith('fixture-B'):
      r.fulfill(status=403,content_type='application/json',body='{"error":"EXPLICIT SYNTHETIC refusal"}');return
     rows=copy.deepcopy(fixture)
     # Real two-page continuation with actual API validator/hash path.
     page=bool(r.request.headers.get('x-listing-cursor'));rows=rows[1:] if page else rows[:1]
     if path!='/training/entries':
      for rowdata in rows:
       for key in ['focal_name','focal_phone','note','_saved']:rowdata['payload'].pop(key,None)
     d=dict(protocol='training-list/1',rows=rows,complete=page,nextCursor=None if page else 'EXPLICIT-SYNTHETIC-cursor')
    elif path=='/account/entries':d=dict(protocol='staff-entries/1',rows=[],complete=True,nextCursor=None)
    else:r.abort();return
    r.fulfill(status=200,content_type='application/json',body=json.dumps(d))
   ctx.route('**/*',route);p=ctx.new_page();p.on('pageerror',lambda e:errors.append(str(e)))
   p.goto(base+'/hub/index.html?lang=en');p.wait_for_function("document.querySelector('#session').textContent.includes('active')")
   assert p.locator('#main .card').count()==6
   p.locator('#main [data-view=dashboard]').click();p.wait_for_function("document.querySelector('#dashboardStatus').textContent.includes('Complete')")
   keys=p.locator('#dashNav button').evaluate_all('(els)=>els.map(e=>e.dataset.house)');assert len(keys)==11 and len(set(keys))==11
   def choose(key):
    if width<760 and not p.locator('#sidebar').is_visible():p.locator('#menuToggle').click()
    p.locator(f'[data-house="{key}"]').click()
   for key in keys:
    choose(key)
    assert 'house='+key in p.url
    if key=='training':p.wait_for_function("document.querySelector('#houseTrainingReadStatus').textContent.includes('Complete')")
    elif key!='5ws':
     assert p.locator('#dashOther .house-stat .v').all_text_contents()==['—']*3
     assert not p.locator('#dashOther a[href*="drafts"]').count()
    assert p.evaluate('document.documentElement.scrollWidth<=innerWidth'),key
    if key!='5ws':
     targets=p.locator('#dashOther button:visible,#dashOther a:visible,#dashOther input:visible,#dashOther select:visible,#dashOther summary:visible').evaluate_all('(es)=>es.map(e=>({text:e.textContent,r:e.getBoundingClientRect().toJSON()})).filter(x=>x.r.height<44||x.r.width<44)')
     assert not targets,(key,targets)
     p.screenshot(path=str(EVIDENCE/f'{key}-{width}.png'),full_page=True)
   assert not any(x['path'].startswith(('/clinical','/selfreport','/contacts','/referrals','/directory')) for x in state['requests'])
   choose('training');p.wait_for_function("document.querySelector('#houseTrainingReadStatus').textContent.includes('Complete')")
   assert p.locator('#houseTrainingRows tbody tr').count()==2
   total=2*payload['trained_total'];assert p.locator('#houseTrainingTotals .v').all_text_contents()==['2',str(total),'0']
   with p.expect_download() as download:p.locator('#houseTrainingExport').click()
   text=Path(download.value.path()).read_text();export=list(csv.DictReader(io.StringIO(text)))
   assert [x['reportId'] for x in export]==['tr_fixture1','tr_fixture2'];assert json.loads(export[0]['participants'])==payload['participants'];assert 'focal_phone' not in export[0]
   p.locator('#houseTrainingFilterfrom').fill('2026-12-31');p.locator('#houseTrainingFilterfrom').dispatch_event('change');assert p.locator('#houseTrainingTotals .v').first.inner_text()=='0'
   p.locator('#houseTrainingRefresh').click();p.wait_for_function("document.querySelector('#houseTrainingRows tbody')?.children.length===2")
   state['deny']=True;p.locator('#houseTrainingRefresh').click();p.wait_for_function("document.querySelector('#houseTrainingReadStatus').textContent.includes('not commissioned')")
   assert p.locator('#houseTrainingExport').is_disabled();assert p.locator('#houseTrainingRows').inner_text()=='';assert p.locator('#houseTrainingTotals .v').all_text_contents()==['—']*3
   state['deny']=False;p.locator('#houseTrainingRefresh').click();p.wait_for_function("document.querySelector('#houseTrainingRows tbody')?.children.length===2")
   p.evaluate('BaselineAuth.switch()');p.wait_for_function("!document.querySelector('#houseTrainingRows')||document.querySelector('#houseTrainingRows').textContent==='' ")
   assert 'SYNTHETIC TRAINING EVENT' not in p.locator('body').inner_text()
   p.locator('#dashboard [data-view=landing]').click();assert p.locator('#main .card').count()==6
   p.locator('#signOut').click();assert p.locator('#landing').is_visible();assert 'SYNTHETIC TRAINING EVENT' not in p.content()
   p.goto(base+'/hub/training.html?view=own')
   p.wait_for_function("document.querySelector('#trainingReadStatus').textContent.includes('Complete')")
   assert p.locator('#trainingRows tbody tr').count()==2
   p.screenshot(path=str(EVIDENCE/f'personal-training-{width}.png'),full_page=True)
   p.evaluate('BaselineAuth.switch()');p.wait_for_function("document.querySelector('#trainingReadStatus').textContent.includes('not commissioned')")
   assert p.locator('#trainingExport').is_disabled();assert p.locator('#trainingTotals .v').all_text_contents()==['—']*3
   p.goto(base+'/hub/training.html?view=current');p.wait_for_url('**/hub/?view=dashboard&house=training');p.wait_for_function("document.querySelector('#houseTrainingReadStatus').textContent.includes('Complete')")
   p.goto(base+'/hub/index.html?view=dashboard&house=phq9');state['role']='admin';p.locator('#refreshDashboard').click();p.wait_for_function("document.querySelector('#navScope').textContent.includes('admin')")
   assert 'request approval' not in p.locator('#dashOther').inner_text().lower()
   assert 'Not confirmed for this account' not in p.locator('#dashOther').inner_text(),'verified admin must not be denied by omitted section'
   assert 'administrator' in p.locator('#dashOther').inner_text().lower()
   choose('selfreport');assert 'Not configured' in p.locator('#dashOther').inner_text()
   assert 'Not confirmed for this account' not in p.locator('#dashOther').inner_text()
   state['sections']=keys;p.locator('#refreshDashboard').click();p.wait_for_function("document.querySelector('#navScope').textContent.includes('admin')")
   choose('training');p.wait_for_function("document.querySelector('#houseTrainingReadStatus').textContent.includes('Complete')")
   assert any(x['path']=='/dashboard/training' for x in state['requests'])
   assert p.locator('#houseTrainingRows tbody tr').count()==2
   # Existing language switch: new explanatory copy is explicitly English fallback.
   p.locator('#i18nbar button').last.click();p.wait_for_function("I18N.lang()==='ne'")
   choose('phq9');assert p.locator('#dashOther h1').inner_text()=='PHQ-9'
   choose('selfreport');assert p.locator('#dashOther h1').inner_text()=='Anonymous Self-report'
   p.locator('#i18nbar button').first.click();p.wait_for_function("I18N.lang()==='en'")
   choose('training');p.wait_for_function("document.querySelector('#houseTrainingReadStatus').textContent.includes('Complete')")
   geometry=p.locator('#houseTrainingTotals .v').evaluate_all('(es)=>es.map(e=>e.getBoundingClientRect().toJSON())')
   assert geometry[0]['bottom']<900,geometry
   p.add_script_tag(path='/root/node_modules/axe-core/axe.min.js')
   audit=p.evaluate("async()=>{const r=await axe.run(document.querySelector('#dashOther'),{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return {violations:r.violations.map(x=>({id:x.id,nodes:x.nodes.map(n=>n.target)})),incomplete:r.incomplete.map(x=>x.id)}}")
   assert not audit['violations'],audit
   (EVIDENCE/f'accessibility-{width}.json').write_text(json.dumps(audit,indent=2))
   p.screenshot(path=str(EVIDENCE/f'training-initial-viewport-{width}.png'))
   # Direct destination behavior and Back for the existing approved separate readers.
   choose('baseline');p.wait_for_url('**/review-analytics-v48/**');assert 'source=historical' in p.url
   p.go_back();p.wait_for_selector('#dashboard');choose('sample');p.wait_for_url('**/legacy-dashboard.html?**');assert 'source=demo' in p.url
   p.go_back();p.wait_for_selector('#dashboard')
   assert not errors,errors
   results.append({'width':width,'homes':keys,'real_browser':True,'fixture_csv_rows':len(export),'participations':total,'denied_clear':True,'account_switch_clear':True,'home_six_cards':True,'zero_overflow':True,'module_targets_44px':True,'page_errors':errors})
   ctx.close()
  browser.close()
 server.shutdown();report={'proof':'EXPLICIT SYNTHETIC Auth/API fixtures only; NOT production authority or data proof','results':results};(EVIDENCE/'browser.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':run()
