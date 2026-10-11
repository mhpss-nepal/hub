"""Owner sidebar delta: loopback, synthetic sample only; no credentials/cloud."""
from pathlib import Path
import sys,json,threading,http.server,subprocess,hashlib
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1]
E=Path(sys.argv[1]);E.mkdir(parents=True,exist_ok=True)
BASE='e74e128'
class H(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(R),**kw)
 def log_message(self,format,*args):pass
 def translate_path(self,path):
  clean=urlsplit(path).path
  if clean.startswith('/form/'):
   return str(R.parent/'form'/clean.removeprefix('/form/'))
  if clean.startswith('/hub/'):
   return str(R/clean.removeprefix('/hub/'))
  return super().translate_path(path)
 def do_GET(self):
  if urlsplit(self.path).path=='/baseline.html':
   raw=subprocess.check_output(['git','show',BASE+':index.html'],cwd=R)
   self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(raw);return
  return super().do_GET()
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),H)
threading.Thread(target=server.serve_forever,daemon=True).start()
origin=f'http://127.0.0.1:{server.server_port}'
MOCK="window.FB={status:()=>({configured:false,ready:false,user:null,pending:0}),onStatus:f=>f(FB.status()),myRole:()=>Promise.resolve(null)};"
APP="export const getApps=()=>[];export const initializeApp=()=>({});export const getApp=()=>({});"
AUTH="""const a={};const u={uid:'sidebar-synthetic',emailVerified:true,getIdToken:async()=> 'synthetic-only'};export const browserLocalPersistence={};export const getAuth=()=>a;export const setPersistence=async()=>{};export const onIdTokenChanged=(a,f)=>{queueMicrotask(()=>f(localStorage.getItem('sidebar-qa-auth')?u:null))};export const isSignInWithEmailLink=()=>false;export const sendSignInLinkToEmail=async()=>{};export const signInWithEmailAndPassword=async()=>({user:u});export const signInWithEmailLink=async()=>({user:u});export const signOut=async()=>{};"""
report={'base':BASE,'checks':[],'geometry':[],'external_blocked':[],'production_data':False}
def check(v,n):
 report['checks'].append({'name':n,'pass':bool(v)})
 assert v,n
try:
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path=str(next(Path('/root/.cache/ms-playwright').glob('**/chrome'))),args=['--no-sandbox'])
  for width in [320,390,1280]:
   c=b.new_context(viewport={'width':width,'height':900},service_workers='block',reduced_motion='reduce');pg=c.new_page()
   def route(rt):
    u=urlsplit(rt.request.url)
    if u.netloc==urlsplit(origin).netloc:
     if u.path=='/assets/fb.js':rt.fulfill(body=MOCK,content_type='text/javascript')
     else:rt.continue_()
    else:report['external_blocked'].append(rt.request.url);rt.abort()
   c.route('**/*',route)
   if sys.argv[-1]!='before':
    c.route('https://www.gstatic.com/**/firebase-app.js',lambda rt:rt.fulfill(body=APP,content_type='text/javascript'))
    c.route('https://www.gstatic.com/**/firebase-auth.js',lambda rt:rt.fulfill(body=AUTH,content_type='text/javascript'))
   api_state={'deny':False,'calls':[]}
   def api(rt):
    path=urlsplit(rt.request.url).path;api_state['calls'].append({'path':path,'method':rt.request.method})
    if path=='/profile':data={'protocol':'own-reporter-profile/1','access':'no_access','reason':'enabled_reporter_grant_required'} if api_state['deny'] else {'protocol':'own-reporter-profile/1','access':'reporter','org':'TPO'}
    elif path=='/current':data={'protocol':'own-current-pages/1','scope':'reporter-own-org-current','rows':[],'nextCursor':None,'pageComplete':True,'snapshotComplete':True,'readTime':'2026-10-11T04:00:00Z','pageCount':0}
    elif path=='/admin/baseline/analytics' and api_state.get('baseline'):
     data={'schema':'mhpss-private-historical-analytics-v2','version':'historical-master-v2','source_sha256':'a'*64,'mapping_sha256':'b'*64,'membership_sha256':'c'*64,'summary':{'schema':'mhpss-private-historical-summary-v1','version':'historical-master-v2','classification':'private-owner-reading','unit':'service contacts, not unique people','combine_classes':False,'historical_date_status':'unresolved-bs-dates','historical_entries':2,'known_service_contacts':7,'unknown_count_entries':1,'unverified_form_entries':1,'original_export_date':'2026-09-01','backup_capture_utc':'2026-10-01T00:00:00.000000+00:00'},'cells':[{'activity':'synthetic','district':'Synthetic district','entries':2,'known_count_entries':1,'unknown_count_entries':1,'known_service_contacts':7,'membership_sha256':'d'*64}],'activity_labels':{'synthetic':'Synthetic QA bucket'},'district_labels':['Synthetic district'],'limitations':['Synthetic browser fixture only; not retained operational data']}
    else:rt.fulfill(status=403,body='{}',headers={'Access-Control-Allow-Origin':origin,'Content-Type':'application/json'});return
    rt.fulfill(body=json.dumps(data),headers={'Access-Control-Allow-Origin':origin,'Content-Type':'application/json'})
   if sys.argv[-1]!='before':c.route('https://mhpss5ws-tdp3xtfnsq-as.a.run.app/**',api)
   for label,path in [('root','/?source=choose'),('sample','/?source=demo'),('current','/review-current-v51/'),('historical','/review-analytics-v48/?source=historical')]:
    pg.goto(origin+path,wait_until='load');pg.wait_for_timeout(250)
    pg.screenshot(path=str(E/f'{label}-{width}.png'))
    geom=pg.evaluate("""()=>{let r=(document.querySelector('.rail')||document.querySelector('header')).getBoundingClientRect(),m=document.querySelector('main').getBoundingClientRect();return {rail:{x:r.x,y:r.y,w:r.width,h:r.height},main:{x:m.x,y:m.y,w:m.width},overflow:document.documentElement.scrollWidth>innerWidth}}""")
    report['geometry'].append({'width':width,'route':label,**geom})
    if sys.argv[-1]=='before':continue
    check(not geom['overflow'],f'{width} {label} no document overflow')
    check(pg.locator('.rail [data-destination]').count()==3,f'{width} {label} exactly three usable sources')
    if width==1280:check(geom['rail']['x']==0 and geom['rail']['w']>=220 and geom['main']['x']>=geom['rail']['w'],f'{width} {label} persistent left sidebar')
    else:
     check(not pg.locator('.rail').is_visible(),f'{width} {label} closed phone menu')
     pg.locator('.l2-menu').click();check(pg.locator('.rail').is_visible(),f'{width} {label} open phone menu')
     pg.screenshot(path=str(E/f'{label}-menu-{width}.png'))
     check(pg.locator('.l2-close').evaluate('(e)=>e===document.activeElement'),f'{width} {label} drawer entry focus')
     pg.keyboard.press('Shift+Tab');check(pg.locator('.rail').evaluate('(e)=>e.contains(document.activeElement)'),f'{width} {label} focus trap')
     pg.keyboard.press('Escape');check(not pg.locator('.rail').is_visible() and pg.locator('.l2-menu').evaluate('(e)=>e===document.activeElement'),f'{width} {label} Escape returns focus')
    check(pg.locator('.rail [aria-disabled=true]').count()==4,f'{width} {label} held sections not linked')
    if label in ['sample','current','historical']:
     check(pg.locator(f'.rail [data-destination={label}]').get_attribute('aria-current')=='page',f'{width} {label} active route')
    if label=='current':check('held' in pg.locator('.l2-activation').inner_text().lower(),f'{width} activation hold visible')
    if label=='sample':
     check(pg.locator('#app').is_visible(),f'{width} sample actually populated')
     first=pg.locator('#stats').inner_text();pg.reload(wait_until='load');check(first==pg.locator('#stats').inner_text(),f'{width} fixed sample reload')
   if sys.argv[-1]!='before':
    for dest in ['current','historical','sample']:
     if width<900:pg.locator('.l2-menu').click()
     pg.locator(f'.rail [data-destination={dest}]').click();pg.wait_for_load_state('load')
     check(pg.locator(f'.rail [data-destination={dest}]').get_attribute('aria-current')=='page',f'{width} clicked {dest} correct route')
     pg.reload(wait_until='load');check(pg.locator(f'.rail [data-destination={dest}]').get_attribute('aria-current')=='page',f'{width} reload {dest} correct route')
   if sys.argv[-1]!='before':
    snapshots=[]
    for path in ['/baseline.html?source=demo','/?source=demo']:
     pg.goto(origin+path,wait_until='networkidle')
     snapshots.append(pg.locator('#stats').inner_text()+pg.locator('#rawBody').inner_text())
    check(snapshots[0]==snapshots[1],f'{width} baseline sample cards and rows unchanged')
    pg.goto(origin+'/hub/?source=demo',wait_until='networkidle')
    if width<900:pg.locator('.l2-menu').click()
    pg.locator('.l2-form-link').click();pg.wait_for_load_state('load')
    check('/form/' in pg.url,f'{width} actual canonical forms click')
    pg.locator('a[href="../hub/"]').first.click();pg.wait_for_load_state('networkidle')
    check('/hub/review-current-v51/' in pg.url,f'{width} canonical forms returns current dashboard')
    # Returning synthetic verified identity: automatic own-profile/current read,
    # empty operational snapshot, then explicit no-grant and baseline refusal.
    pg.evaluate("localStorage.setItem('sidebar-qa-auth','yes')")
    pg.goto(origin+'/review-current-v51/',wait_until='networkidle')
    pg.wait_for_function("document.querySelector('#status').textContent.includes('Own reports loaded')")
    check(pg.locator('#result').is_visible() and pg.locator('#rows tr').count()==0,f'{width} automatic empty current authorised fixture')
    check(not pg.locator('#export').is_disabled(),f'{width} complete empty snapshot CSV enabled')
    pg.screenshot(path=str(E/f'current-authorised-empty-{width}.png'))
    pg.reload(wait_until='networkidle');check('Own reports loaded' in pg.locator('#status').inner_text(),f'{width} returning automatic read')
    api_state['deny']=True;pg.reload(wait_until='networkidle')
    check(pg.locator('#result').is_hidden() and 'no enabled reporter assignment' in pg.locator('#status').inner_text(),f'{width} no grant honest refusal')
    pg.screenshot(path=str(E/f'current-no-grant-{width}.png'))
    pg.goto(origin+'/review-analytics-v48/?source=historical',wait_until='networkidle')
    check(pg.locator('#historical-results').is_hidden() and 'refused' in pg.locator('#historical-status').inner_text(),f'{width} baseline access refused without data')
    pg.screenshot(path=str(E/f'historical-refused-{width}.png'))
    api_state['baseline']=True;pg.reload(wait_until='networkidle')
    check(pg.locator('#historical-stats .v').all_text_contents()[:3]==['2','7','1'],f'{width} automatic synthetic baseline fixture')
    pg.screenshot(path=str(E/f'historical-synthetic-populated-{width}.png'))
    with pg.expect_download() as download:pg.locator('#historical-export').click()
    csvtext=Path(download.value.path()).read_text();check('historical-master-v2' in csvtext and 'Synthetic QA bucket' in csvtext,f'{width} real baseline CSV download fixture')
    report.setdefault('csv_sha256',[]).append({'width':width,'hash':hashlib.sha256(csvtext.encode()).hexdigest()})
    check(all(x['method']=='GET' for x in api_state['calls']),f'{width} navigation zero writes')
    pg.goto(origin+'/?mode=signIn&oobCode=synthetic-invalid-qa&continueUrl=%2Fhub%2F#reports',wait_until='networkidle')
    check('/review-current-v51/' in pg.url and 'oobCode=synthetic-invalid-qa' in pg.url and pg.url.endswith('#reports'),f'{width} root alias preserves auth parameters')
    # Audit rendered sample and both signed-out readers; axe's unresolved checks retained.
    pg.evaluate("localStorage.removeItem('sidebar-qa-auth')")
    for label,path in [('sample','/?source=demo'),('current','/review-current-v51/'),('historical','/review-analytics-v48/?source=historical')]:
     pg.goto(origin+path,wait_until='networkidle')
     pg.evaluate((R/'design-preview/source/axe.min.js').read_text())
     axe=pg.evaluate("async()=>{let r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}});return {violations:r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)})),incomplete:r.incomplete.map(v=>v.id)}}")
     report.setdefault('axe',[]).append({'width':width,'state':label,**axe})
     check(not axe['violations'],f'{width} {label} axe violations')
     if width<900:
      pg.locator('.l2-menu').click()
      targets=pg.locator('.rail a,.rail button').evaluate_all('(es)=>es.filter(e=>e.getClientRects().length).map(e=>({text:e.textContent.trim(),w:e.getBoundingClientRect().width,h:e.getBoundingClientRect().height}))')
      check(all(t['w']>=44 and t['h']>=44 for t in targets),f'{width} {label} drawer 44px targets')
      check(pg.locator('.rail').evaluate('(e)=>e.getBoundingClientRect().right<=innerWidth'),f'{width} {label} drawer no clip')
      pg.keyboard.press('Escape')
   c.close()
  b.close()
finally:
 server.shutdown();server.server_close()
 (E/'browser-results.json').write_text(json.dumps(report,indent=2))
 print(json.dumps({'checks':len(report['checks']),'passed':sum(c['pass'] for c in report['checks']),'evidence':str(E)}))
