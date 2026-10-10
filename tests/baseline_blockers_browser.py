"""Independent exact-head browser probes. Local synthetic SDK/transport only."""
from pathlib import Path
import json, threading, http.server, sys, copy, subprocess
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1];W=R.parent;E=Path(sys.argv[1]);E.mkdir(parents=True,exist_ok=True)
sys.path[:0]=[str(W/'backend/tests'),str(W/'backend/functions'),str(W/'backend/tools')]
from test_baseline import Backend,call
summary=json.loads(call(Backend(),headers={'Origin':'https://mhpss-nepal.github.io'}).data)
class H(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**k):super().__init__(*a,directory=str(R),**k)
 def log_message(self,*a):pass
s=http.server.ThreadingHTTPServer(('127.0.0.1',0),H);threading.Thread(target=s.serve_forever,daemon=True).start();origin=f'http://127.0.0.1:{s.server_port}'
APP="export const getApps=()=>[];export const initializeApp=()=>({});export const getApp=()=>({});"
AUTH="""let cb;const u={uid:'fixture',getIdToken:async()=>{REVIEW.events.push('token');if(REVIEW.holdToken)await new Promise(r=>REVIEW.releaseToken=r);return 'ONLY_SYNTHETIC_REVIEW_TOKEN'}};const a={currentUser:null};export const browserLocalPersistence={};export const getAuth=()=>a;export const setPersistence=async()=>REVIEW.events.push('localPersistence');export const onIdTokenChanged=(a,f)=>{cb=f;REVIEW.auth=yes=>{a.currentUser=yes?u:null;f(a.currentUser)};queueMicrotask(()=>REVIEW.auth(REVIEW.initialUser));};export const onAuthStateChanged=onIdTokenChanged;export const signInWithEmailAndPassword=async()=>{REVIEW.events.push('signin');REVIEW.auth(true)};export const signOut=async()=>{REVIEW.events.push('signout');if(REVIEW.holdSignout)await new Promise(r=>REVIEW.releaseSignout=r);if(REVIEW.rejectSignout)throw Error('fixture signout refused');REVIEW.auth(false)};export const isSignInWithEmailLink=()=>REVIEW.link;export const signInWithEmailLink=async()=>{REVIEW.events.push('finishLink');if(REVIEW.rejectLink)throw Error('fixture link failure');};export const sendSignInLinkToEmail=async(a,e,x)=>{REVIEW.events.push('sendLink');REVIEW.linkSettings=x;};"""
FS="""export const getFirestore=()=>({});export const doc=(...x)=>x;export const collection=(...x)=>x;export const query=(...x)=>x;export const where=(...x)=>x;export const orderBy=(...x)=>x;export const limit=(...x)=>x;export const serverTimestamp=()=>({});export const setDoc=async()=>REVIEW.events.push('setDoc');export const getDoc=async()=>({exists:()=>false});export const getDocs=async()=>({docs:[]});export const onSnapshot=(q,ok)=>{REVIEW.events.push('watch');queueMicrotask(()=>ok({docs:[]}));return ()=>{}};export const deleteDoc=async()=>REVIEW.events.push('deleteDoc');"""
report={'candidate':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'synthetic_only':True,'checks':[],'observations':[],'screens':[]}
def check(value,name,blocking=True):report['checks'].append({'name':name,'pass':bool(value),'blocking':blocking})
poison='[{"_rid":"independent-review-poison","kind":"activity","total":19}]'
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=str(next(Path('/root/.cache/ms-playwright').glob('**/chrome'))),args=['--no-sandbox'])
  for width in [320,390,1280,1748]:
   ctx=browser.new_context(viewport={'width':width,'height':1022},accept_downloads=True,service_workers='block')
   ctx.add_init_script("window.REVIEW={events:[],imports:[],requests:[],initialUser:false,link:false};localStorage.setItem('mhpss-np-queue-v1',"+json.dumps(poison)+");const old=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){REVIEW.events.push('storageWrite:'+k);return old.call(this,k,v)};")
   state={'status':200,'body':copy.deepcopy(summary),'hold':False,'pending':[]};errors=[]
   def route(rt):
    u=urlsplit(rt.request.url)
    if u.netloc=='www.gstatic.com':
     name=u.path.rsplit('/',1)[-1]
     rt.fulfill(body={'firebase-app.js':APP,'firebase-auth.js':AUTH,'firebase-firestore.js':FS}.get(name,''),content_type='text/javascript')
    elif u.netloc=='mhpss5ws-tdp3xtfnsq-as.a.run.app':
     report.setdefault('request_shapes',[]).append({'method':rt.request.method,'path':u.path,'keys':sorted(rt.request.headers)})
     if state['hold']:state['pending'].append(rt)
     else:rt.fulfill(status=state['status'],body=json.dumps(state['body']),content_type='application/json')
    elif u.netloc==urlsplit(origin).netloc:rt.continue_()
    else:rt.abort()
   ctx.route('**/*',route);page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
   def populated():page.wait_for_function("document.querySelectorAll('#historical-stats .v').length===5")
   def empty():return page.locator('#historical-stats').text_content()=='' and page.locator('#historical-provenance').text_content()=='' and page.locator('#historical-summary').text_content()==''
   page.goto(origin+'/index.html',wait_until='networkidle')
   check(page.locator('#historical-login').is_visible() and empty(),f'{width} default first-screen genuinely signed out')
   check(page.locator('#historical-file').count()==0,f'{width} no historical file input')
   page.screenshot(path=str(E/f'first-screen-signedout-{width}.png'))
   report['screens'].append({'width':width,'state':'first-screen-signedout','stats_y':None})
   page.evaluate('REVIEW.auth(true)');populated()
   geometry=page.locator('#historical-stats').bounding_box();report['screens'].append({'width':width,'state':'populated','stats_y':geometry['y'],'stats_bottom':geometry['y']+geometry['height']})
   page.screenshot(path=str(E/f'first-screen-populated-{width}.png'))
   for status in [201,202,206]:
    state['status']=status;page.locator('#historical-refresh').click();page.wait_for_timeout(100)
    check(empty(),f'{width} reject non-200 success status {status}')
    report['observations'].append({'width':width,'http_status':status,'rendered_values':page.locator('#historical-stats .v').all_text_contents()})
   state['status']=200
   malformed=[{'extra':'refused'}, {'version':'historical-master-v0'}, {'version':'historical-master-v01'}, {'version':'historical-master-v1000000'}, {'version':['historical-master-v1']},{'historical_entries':-1},{'known_service_contacts':9007199254740992},{'unknown_count_entries':3},{'combine_classes':True}]
   for patch in malformed:
    state['body']={**summary,**patch};page.locator('#historical-refresh').click();page.wait_for_timeout(70);check(empty(),f'{width} invalid summary rejected {next(iter(patch))}:{str(next(iter(patch.values())))}')
   state['body']=copy.deepcopy(summary);page.locator('#historical-refresh').click();populated()
   page.evaluate('REVIEW.holdToken=true');page.locator('#historical-refresh').click();page.wait_for_timeout(30);page.evaluate('REVIEW.auth(false);REVIEW.releaseToken();REVIEW.holdToken=false');page.wait_for_timeout(80);check(empty(),f'{width} token-wait signout fence')
   page.evaluate('REVIEW.auth(true)');populated()
   state['hold']=True;page.locator('#historical-refresh').click();page.wait_for_timeout(80);page.locator('#source-tools').evaluate('(e)=>e.open=true');page.locator('#useDemo').click()
   for rt in state['pending']:
    try:rt.fulfill(status=200,body=json.dumps(summary),content_type='application/json')
    except Exception:pass
   state['pending']=[];state['hold']=False;page.wait_for_timeout(80)
   check(empty() and page.locator('#app').is_visible(),f'{width} late fetch cannot repopulate after demo switch')
   page.locator('.tab[data-p=raw]').click();page.locator('#reload').click();page.locator('#useHistorical').click();populated()
   page.evaluate('REVIEW.holdSignout=true');page.locator('#historical-account').evaluate('(e)=>e.open=true');page.locator('#historical-signout').click();check(empty(),f'{width} signout immediately erases')
   page.locator('#historical-refresh').evaluate('(e)=>e.click()');page.wait_for_timeout(100);check(empty(),f'{width} pending signout prevents private rehydrate')
   before_requests=len(report.get('request_shapes',[]));downloads=[];page.on('download',lambda d:downloads.append(d))
   page.evaluate("REVIEW.auth(true);dispatchEvent(new Event('online'));document.querySelector('#historical-export').click()");page.wait_for_timeout(100)
   check(empty() and not downloads and len(report.get('request_shapes',[]))==before_requests,f'{width} pending intent blocks callback online export and reads')
   if not empty():
    with page.expect_download() as dl:page.locator('#historical-export').click()
    downloaded=Path(dl.value.path()).read_text(encoding='utf-8-sig')
    report['observations'].append({'width':width,'signout_pending_values':page.locator('#historical-stats .v').all_text_contents(),'signout_pending_csv_contains_private_summary':'historical-master-v1,2,7,1,1,' in downloaded})
    page.screenshot(path=str(E/f'BUG-signout-pending-repopulated-{width}.png'))
   page.evaluate('REVIEW.releaseSignout();REVIEW.holdSignout=false');page.wait_for_timeout(80);check(empty(),f'{width} completed signout erases')
   page.evaluate("BaselineAuth.signIn('fixture@example.invalid','synthetic-only')");populated();before_requests=len(report.get('request_shapes',[]));page.evaluate('REVIEW.rejectSignout=true');page.locator('#historical-account').evaluate('(e)=>e.open=true');page.locator('#historical-signout').click();page.wait_for_timeout(60);check(empty(),f'{width} failed signout immediately empty')
   page.evaluate("dispatchEvent(new Event('online'))");page.wait_for_timeout(100);check(empty(),f'{width} failed signout cannot reconnect rehydrate')
   page.evaluate("REVIEW.auth(true);document.querySelector('#historical-refresh').click();document.querySelector('#historical-export').click()");page.wait_for_timeout(100)
   check(empty() and not downloads and len(report.get('request_shapes',[]))==before_requests,f'{width} rejected intent blocks old callback Refresh export and reads')
   page.evaluate('REVIEW.rejectSignout=false;REVIEW.auth(false)')
   check(page.evaluate("localStorage.getItem('mhpss-np-queue-v1')")==poison,f'{width} historical legacy queue exact bytes unchanged')
   check(page.evaluate("!REVIEW.events.some(x=>['setDoc','watch','deleteDoc'].includes(x))"),f'{width} historical zero datastore effects')
   check(page.evaluate("!Object.values(localStorage).some(x=>x.includes('ONLY_SYNTHETIC_REVIEW_TOKEN')) && !document.documentElement.innerHTML.includes('ONLY_SYNTHETIC_REVIEW_TOKEN')"),f'{width} token absent DOM/storage')
   check(not errors,f'{width} no browser exceptions')
   # Source choose and explicit live use the untouched actual legacy bridge.
   page.goto(origin+'/index.html?source=choose',wait_until='networkidle')
   check(page.locator('#historical-baseline').is_hidden() and page.locator('#entry-shell').is_visible(),f'{width} choose first screen legacy placeholder')
   check(page.evaluate("REVIEW.events.includes('setDoc')"),f'{width} deliberate choose retains legacy flush behavior')
   page.locator('#useHistorical').click();page.wait_for_url('**/*source=historical');page.wait_for_load_state('networkidle')
   check(urlsplit(page.url).query=='source=historical' and page.locator('#historical-login').is_visible(),f'{width} choose to historical full navigation Auth-only signedout')
   page.locator('#source-tools > summary').click();page.locator('#access-options > summary').click();page.locator('#useLive').click();page.wait_for_url('**/*source=live');page.wait_for_load_state('networkidle')
   page.evaluate('REVIEW.auth(true)');page.wait_for_timeout(150)
   check(page.evaluate("REVIEW.events.includes('watch')"),f'{width} explicit historical to live restores real kind-scoped listener')
   page.screenshot(path=str(E/f'explicit-live-{width}.png'))
   page.locator('#useHistorical').click();page.wait_for_load_state('networkidle')
   check('source=historical' in page.url and page.locator('#historical-baseline').is_visible(),f'{width} live to historical reload route')
   check(page.evaluate("!REVIEW.events.includes('watch') && !REVIEW.events.includes('setDoc')"),f'{width} return historical no inherited legacy writes')
   ctx.close()
  # Email-link recovery and successful URL credential stripping.
  for mode in ['missing-email','valid-email']:
   ctx=browser.new_context(service_workers='block');ctx.add_init_script("window.REVIEW={events:[],initialUser:false,link:true};"+("localStorage.setItem('mhpss-np-linkmail','fixture@example.invalid');" if mode=='valid-email' else ''))
   def linkroute(rt):
    u=urlsplit(rt.request.url)
    if u.netloc=='www.gstatic.com':rt.fulfill(body=APP if u.path.endswith('firebase-app.js') else AUTH,content_type='text/javascript')
    elif u.netloc==urlsplit(origin).netloc:rt.continue_()
    else:rt.abort()
   ctx.route('**/*',linkroute);page=ctx.new_page();page.goto(origin+'/index.html?source=historical&mode=signIn&oobCode=synthetic-link-code',wait_until='networkidle')
   if mode=='missing-email':
    page.locator('#historical-email').fill('fixture@example.invalid');page.locator('#historical-password-options > summary').click();page.locator('#historical-link').click();page.wait_for_timeout(70)
    check(page.evaluate("REVIEW.events.includes('sendLink')"),'email link without stored address can recover/request replacement')
    report['observations'].append({'email_link_missing_email_status':page.locator('#historical-status').text_content()})
    check('oobCode' in page.url,'missing hint keeps uncompleted link credential in URL only')
    check(page.locator('#historical-signin').text_content()=='Complete email sign-in','address reentry action available')
    page.locator('#historical-signin').click();page.wait_for_timeout(70)
    check(page.evaluate("REVIEW.events.includes('finishLink')") and 'oobCode' not in page.url,'address reentry finishes link and strips successful credential')
   else:check('oobCode' not in page.url,'successful email link strips URL credential')
   ctx.close()
  browser.close()
finally:
 s.shutdown();s.server_close();report['passes']=sum(c['pass'] for c in report['checks']);report['count']=len(report['checks']);report['failures']=[c for c in report['checks'] if not c['pass']];(E/'adversarial-result.json').write_text(json.dumps(report,indent=2));print(json.dumps({'passes':report['passes'],'count':report['count'],'failures':report['failures']}))
if report['failures']:sys.exit(1)
