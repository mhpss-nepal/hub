"""Real Chromium, actual index/script order, Auth-only SDK instrumentation.
All users/transport/data synthetic. Actual Python adapter supplies API responses.
"""
from pathlib import Path
import sys,json,threading,http.server,hashlib,copy,time
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1];W=R.parent
sys.path[:0]=[str(W/'backend/tests'),str(W/'backend/functions'),str(W/'backend/tools')]
from test_baseline import Backend,call
E=Path(sys.argv[1]);E.mkdir(parents=True,exist_ok=True)
class H(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**k):super().__init__(*a,directory=str(R),**k)
 def log_message(self,*a):pass
s=http.server.ThreadingHTTPServer(('127.0.0.1',0),H);threading.Thread(target=s.serve_forever,daemon=True).start();origin=f'http://127.0.0.1:{s.server_port}'
APP="export const getApps=()=>[]; export const initializeApp=c=>{window.QA.sdk.push('app');return {}};export const getApp=()=>({});"
AUTH="""const u={uid:'fixture_primary',getIdToken:async()=>{window.QA.sdk.push('token');return 'fixture'}};const a={currentUser:u};let cb;
export const browserLocalPersistence={};export const getAuth=()=>a;
export const setPersistence=async()=>{window.QA.sdk.push('persistence-local')};
export const onIdTokenChanged=(x,f)=>{cb=f;window.QA.auth=(yes)=>{a.currentUser=yes?u:null;f(a.currentUser)};queueMicrotask(()=>f(a.currentUser));return ()=>{}};
export const onAuthStateChanged=onIdTokenChanged;
export const signInWithEmailAndPassword=async()=>{window.QA.auth(true)};export const signOut=async()=>{window.QA.auth(false)};
export const isSignInWithEmailLink=()=>false;export const signInWithEmailLink=async()=>{};export const sendSignInLinkToEmail=async()=>{};
"""
POISON='[{"_rid":"fixture_legacy_poison","kind":"activity","reachedTotal":123}]'
report={'checks':[],'production':False,'screenshots':[]}
def check(x,name):report['checks'].append({'name':name,'pass':bool(x)});assert x,name
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=str(next(Path('/root/.cache/ms-playwright').glob('**/chrome'))),args=['--no-sandbox'])
  for width in [320,390,1280]:
   context=browser.new_context(viewport={'width':width,'height':1022},service_workers='block',reduced_motion='reduce',accept_downloads=True)
   context.add_init_script("window.QA={sdk:[],forbidden:[],requests:[]};localStorage.setItem('mhpss-np-queue-v1',"+json.dumps(POISON)+");localStorage.setItem('fixture-records','UNCHANGED');")
   backend=Backend();state={'status':None,'hold':False,'pending':[],'summary':None}
   def route(rt):
    url=urlsplit(rt.request.url)
    if url.netloc=='www.gstatic.com':
     if url.path.endswith('/firebase-app.js'):rt.fulfill(body=APP,content_type='text/javascript')
     elif url.path.endswith('/firebase-auth.js'):rt.fulfill(body=AUTH,content_type='text/javascript')
     else:
      report.setdefault('forbidden_network',[]).append(url.path);rt.abort()
    elif url.netloc=='mhpss5ws-tdp3xtfnsq-as.a.run.app' and url.path=='/admin/baseline':
     check(rt.request.method=='GET',f'{width} GET only');check(rt.request.headers.get('authorization')=='Bearer fixture',f'{width} auth header')
     response=call(backend,headers={'Origin':'https://mhpss-nepal.github.io'});state['summary']=json.loads(response.data)
     if state['hold']:state['pending'].append(rt);return
     rt.fulfill(status=state['status'] or response.status_code,body=response.data if not state['status'] else '{"error":"fixture refusal"}',headers={'Content-Type':'application/json','Access-Control-Allow-Origin':origin,'Cache-Control':'no-store','X-Baseline-Version':backend.plan['version']['version'],'X-Baseline-Digest':backend.plan['version']['digest']})
    elif url.netloc==urlsplit(origin).netloc:rt.continue_()
    else:report.setdefault('blocked_other',[]).append(url.netloc);rt.abort()
   context.route('**/*',route);page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(origin+'/index.html',wait_until='networkidle');page.wait_for_function("document.querySelectorAll('#historical-stats .v').length===5",timeout=6000)
   check(page.locator('#historical-stats .v').all_text_contents()==['2','7','1','—','—'],f'{width} real API cards')
   check(page.locator('#historical-file').count()==0,f'{width} no file-primary path')
   check('1 later form entries' in page.locator('#historical-summary').text_content(),f'{width} class exclusion')
   with page.expect_download() as d:page.locator('#historical-export').click()
   text=Path(d.value.path()).read_text(encoding='utf-8-sig');check('historical-master-v1,2,7,1,1,' in text,f'{width} API cards CSV parity')
   for event in ['online','offline','online']:page.evaluate('(e)=>window.dispatchEvent(new Event(e))',event)
   page.locator('#historical-refresh').click();page.wait_for_function("document.querySelectorAll('#historical-stats .v').length===5")
   check(page.evaluate("localStorage.getItem('mhpss-np-queue-v1')")==POISON,f'{width} poisoned queue bytes unchanged')
   check(page.evaluate("localStorage.getItem('fixture-records')")== 'UNCHANGED',f'{width} local records unchanged')
   check(page.evaluate("QA.sdk.every(x=>['app','persistence-local','token'].includes(x))"),f'{width} auth-only imports')
   check(page.locator('#fbbar').count()==0,f'{width} no legacy bridge initialization')
   check(page.evaluate('document.documentElement.scrollWidth===document.documentElement.clientWidth'),f'{width} root no overflow')
   for id in ['historical-refresh','historical-clear','historical-export','historical-signout']:
    page.locator('#historical-account').evaluate('(e)=>e.open=true');box=page.locator('#'+id).bounding_box();check(box['height']>=44 and box['width']>=44,f'{width} {id} 44px')
   page.add_script_tag(path=str(R/'design-preview/source/axe.min.js'))
   axe=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}});return {violations:r.violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)})),incomplete:r.incomplete.map(v=>v.id)}}")
   report.setdefault('axe',[]).append({'width':width,**axe});check(not axe['violations'],f'{width} axe')
   page.screenshot(path=str(E/f'populated-{width}.png'));report['screenshots'].append(str(E/f'populated-{width}.png'))
   # In-flight clear/auth/permission refusal must remove all private DOM and export state.
   state['hold']=True;page.locator('#historical-refresh').click();page.wait_for_timeout(100);page.locator('#historical-account').evaluate('(e)=>e.open=true');page.locator('#historical-clear').click()
   for rt in state['pending']:rt.fulfill(status=200,body=json.dumps(state['summary']),content_type='application/json')
   state['pending']=[];state['hold']=False;page.wait_for_timeout(100)
   check(page.locator('#historical-stats').text_content()=='',f'{width} delayed clear fenced')
   check(page.locator('#historical-provenance').text_content()=='',f'{width} hidden provenance cleared')
   page.evaluate('QA.auth(true)');page.wait_for_function("document.querySelectorAll('#historical-stats .v').length===5")
   page.evaluate('QA.auth(false)');check(page.locator('#historical-stats').text_content()=='',f'{width} signout cleared')
   state['status']=403;page.evaluate('QA.auth(true)');page.wait_for_function("document.querySelector('#historical-status').textContent.includes('refused')")
   check(page.locator('#historical-stats').text_content()=='',f'{width} refused empty not zero')
   check(not errors,f'{width} no page errors')
   check(not report.get('forbidden_network'),f'{width} zero Firestore SDK import/read/write')
   # Default and explicit historical reload repopulate without a chooser.
   state['status']=None
   page.goto(origin+'/index.html?source=historical',wait_until='networkidle')
   page.wait_for_function("document.querySelectorAll('#historical-stats .v').length===5")
   check(page.evaluate("QA.sdk.includes('persistence-local')"),f'{width} explicit local persistence')
   page.reload(wait_until='networkidle');page.wait_for_function("document.querySelectorAll('#historical-stats .v').length===5")
   check(page.locator('#historical-stats .v').all_text_contents()==['2','7','1','—','—'],f'{width} automatic historical reload')
   # Real backend maintained version appears on Refresh.
   from test_baseline_maintenance import next_plan
   updated=next_plan(backend.plan);backend.docs.update(copy.deepcopy(updated['docs']));backend.docs['mhpssHistoricalBaselineControlV1/current']=updated['pointer']
   page.locator('#historical-refresh').click();page.wait_for_function("document.querySelector('#historical-provenance').textContent.includes('historical-master-v2')")
   check(page.locator('#historical-stats .v').all_text_contents()[1]=='8',f'{width} maintained v2 automatic refresh')
   page.evaluate("window.dispatchEvent(new Event('offline'))")
   check(page.locator('#historical-stats').text_content()=='',f'{width} offline clears stale private values')
   page.evaluate("window.dispatchEvent(new Event('online'))");page.wait_for_function("document.querySelectorAll('#historical-stats .v').length===5")
   # Invalid backend pointer/provider failure is unavailable, never synthetic/zero.
   backend.docs['mhpssHistoricalBaselineControlV1/current']['digest']='0'*64
   page.locator('#historical-refresh').click();page.wait_for_function("document.querySelector('#historical-status').textContent.includes('unavailable')")
   check(page.locator('#historical-stats').text_content()=='',f'{width} corrupt pointer no fallback')
   backend.docs['mhpssHistoricalBaselineControlV1/current']=updated['pointer']
   # Auth change while network response is delayed fences all old bytes.
   state['hold']=True;page.locator('#historical-refresh').click();page.wait_for_timeout(100);page.evaluate('QA.auth(false)')
   for rt in state['pending']:rt.fulfill(status=200,body=json.dumps(state['summary']),content_type='application/json')
   state['pending']=[];state['hold']=False;page.wait_for_timeout(100)
   check(page.locator('#historical-stats').text_content()=='',f'{width} delayed signout fenced')
   check(page.locator('#historical-login').is_visible(),f'{width} signed-out login available')
   page.add_script_tag(path=str(R/'design-preview/source/axe.min.js'))
   login_violations=page.evaluate("async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})).violations.map(v=>v.id)")
   check(not login_violations,f'{width} login axe')
   page.screenshot(path=str(E/f'signed-out-{width}.png'))
   check(page.evaluate("localStorage.getItem('mhpss-np-queue-v1')")==POISON,f'{width} queue preserved after all faults')
   # In-page demo remains synthetic and cannot inherit private aggregate data.
   page.locator('#source-tools').evaluate('(e)=>e.open=true');page.locator('#useDemo').click();check(page.locator('#app').is_visible() and page.locator('#historical-baseline').is_hidden(),f'{width} explicit synthetic source switch')
   page.locator('.tab[data-p=raw]').click();page.locator('#reload').click();page.locator('#useHistorical').click();check(page.locator('#historical-baseline').is_visible() and page.locator('#app').is_hidden(),f'{width} return to historical hides legacy DOM')
   context.close()
  browser.close()
finally:
 s.shutdown();s.server_close();report['passes']=sum(x['pass'] for x in report['checks']);report['count']=len(report['checks']);(E/'RESULT.json').write_text(json.dumps(report,indent=2));print(json.dumps({'passes':report['passes'],'count':report['count'],'evidence':str(E)},indent=2))
