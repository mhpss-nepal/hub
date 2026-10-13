"""Actual frontend + unchanged adapter + real loopback Auth/Firestore SDK.
Synthetic demo project only. No production data, grants or credential discovery.
Run: uv run --with firebase-admin --with google-cloud-firestore --with flask --with pytest --with playwright python tests/all-homes-provider.py
"""
import os,sys,json,socket,subprocess,signal,time,threading,mimetypes,csv,io,traceback
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]; AREA=ROOT.parents[1]; BACK=AREA.parent/'48-historical-analytics/backend'; EV=AREA/'all-homes/route-correction'; EV.mkdir(parents=True,exist_ok=True)
CACHE=AREA/'non5ws-bridge/training/combined-review'; FORM=AREA/'latest-claude-screen/form'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=BACK,text=True).strip()=='3fd05578f8588786410ca42c6a0275bb0ac2cfe9'
def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
a,f,h,l=[port() for _ in range(4)]; PROJECT='demo-mhpss-training';procs=[];checks=[];calls=[];browser=None;server=None;http=None;db=None
home=EV/'provider-home';home.mkdir(exist_ok=True)
env={k:v for k,v in os.environ.items() if not any(x in k for x in ['GOOGLE','GCLOUD','FIREBASE','CREDENTIAL','TOKEN','PROXY','MHPS5WS'])}
env.update(HOME=str(home),PLAYWRIGHT_BROWSERS_PATH='/root/.cache/ms-playwright',GCLOUD_PROJECT=PROJECT,FIREBASE_AUTH_EMULATOR_HOST=f'127.0.0.1:{a}',FIRESTORE_EMULATOR_HOST=f'127.0.0.1:{f}',NO_PROXY='127.0.0.1',CI='true',PYTHONDONTWRITEBYTECODE='1');os.environ.clear();os.environ.update(env)
cfg=EV/'firebase.json';cfg.write_text(json.dumps({'emulators':{'auth':{'host':'127.0.0.1','port':a},'hub':{'host':'127.0.0.1','port':h},'logging':{'host':'127.0.0.1','port':l},'ui':{'enabled':False}}}))
def check(name,ok,detail=None):
 checks.append(dict(name=name,passed=bool(ok),detail=detail));assert ok,(name,detail)
try:
 cmds=[['firebase','emulators:start','--only','auth','--project',PROJECT,'--config',str(cfg)],['/usr/lib/jvm/java-21-openjdk-amd64/bin/java','-jar','/root/.cache/firebase/emulators/cloud-firestore-emulator-v1.22.0.jar','--host','127.0.0.1','--port',str(f),'--project_id',PROJECT,'--single_project_mode','--single_project_mode_error','--rules',str(BACK/'legacy-tests/active-v3.rules')]]
 for n,(cmd,p) in enumerate(zip(cmds,[a,f])):
  log=open(EV/f'provider-{n}.log','w');proc=subprocess.Popen(cmd,cwd=EV,env=env,stdout=log,stderr=log,start_new_session=True);procs.append(proc);end=time.monotonic()+45
  while True:
   if proc.poll() is not None:raise RuntimeError('Provider startup failed')
   try:
    with socket.create_connection(('127.0.0.1',p),.2):break
   except OSError:
    if time.monotonic()>end:raise RuntimeError('Provider startup timeout')
    time.sleep(.1)
 sys.path[:0]=[str(BACK/'functions'),str(BACK/'tests')]
 import firebase_admin,adapter,identity,training,requests
 from firebase_admin import auth
 from google.cloud import firestore
 from google.auth.credentials import AnonymousCredentials
 from backend import Backend
 from test_staff import control,grant,policy
 from test_training import payload
 from flask import Flask,request
 from werkzeug.serving import make_server
 from playwright.sync_api import sync_playwright
 app=firebase_admin.initialize_app(options={'projectId':PROJECT},name='all-homes-real')
 class Local(Backend):
  project=PROJECT
  def verify(self,token):
   try:return auth.verify_id_token(token,app=app,check_revoked=True,clock_skew_seconds=0)
   except Exception:raise identity.AuthenticationError('refused') from None
  def client(self):return firestore.Client(project=PROJECT,credentials=AnonymousCredentials())
 backend=Local();db=backend.client();web=Flask(__name__);origin=None
 @web.route('/<path:path>',methods=['GET','POST','OPTIONS'])
 def api(path):
  r=adapter.handle(request,backend,origin=origin);body=r.get_json(silent=True);uid=None
  try:uid=auth.verify_id_token(request.headers.get('Authorization','')[7:],app=app)['uid']
  except Exception:pass
  calls.append(dict(path=request.path,status=r.status_code,uid=uid,body=body));return r
 http=make_server('127.0.0.1',0,web,threaded=True);threading.Thread(target=http.serve_forever,daemon=True).start();API=f'http://127.0.0.1:{http.server_port}'
 password='Synthetic-demo-only-123!';tokens={};s=requests.Session();s.trust_env=False
 for uid in ['primary','backup','reporter','other','manager','field','denied']:
  auth.create_user(uid=uid,email=uid+'@example.invalid',password=password,email_verified=True,app=app)
  tokens[uid]=s.post(f'http://127.0.0.1:{a}/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=demo',json=dict(email=uid+'@example.invalid',password=password,returnSecureToken=True),timeout=10).json()['idToken']
 db.document('mhpss5wsAdminControlV1/bootstrap').set(control())
 for uid,org,role in [('reporter','TPO','reporter'),('other','CMC','reporter'),('manager','TPO','manager')]:db.document('mhpssTrainingGrantsV1/'+uid).set(dict(version=1,uid=uid,email=uid+'@example.invalid',org=org,enabled=True,role=role,approvedBy='primary',approvalId='synthetic-only'))
 for uid,role in [('manager','manager'),('field','field')]:db.document('mhpssStaffGrantsV1/'+uid).set({**grant(),'uid':uid,'email':uid+'@example.invalid','role':role,'sections':['5ws'] if role=='manager' else []})
 db.document('mhpssStaffScopePolicyV1/5ws').set(policy())
 for uid,org in [('reporter','TPO'),('other','CMC')]:
  p={**payload(),'org':org,'title':'SYNTHETIC '+org};envelope=dict(protocol='training-submit/1',reportId='synthetic-'+org,revision=1,predecessor=None,payload=p);training.submit(backend,tokens[uid],json.dumps(envelope).encode())
 check('no_admin_training_grants',not any(db.document('mhpssTrainingGrantsV1/'+u).get().exists for u in ['primary','backup']))
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def do_GET(self):
   path=urlparse(self.path).path
   if path.endswith('fb-config.js'):data=('window.__FIREBASE_DEFAULTS__='+json.dumps({'emulatorHosts':{'auth':f'127.0.0.1:{a}'}})+';window.FB_CONFIG='+json.dumps(dict(apiKey='demo-key',authDomain=PROJECT+'.firebaseapp.com',projectId=PROJECT))+';').encode();mime='application/javascript'
   else:
    target=(ROOT/path.removeprefix('/hub/')) if path.startswith('/hub/') else FORM/path.removeprefix('/form/')
    if target.is_dir():target=target/'index.html'
    if not target.is_file():self.send_error(404);return
    data=target.read_bytes();mime=mimetypes.guess_type(target.name)[0] or 'text/plain'
   self.send_response(200);self.send_header('Content-Type',mime);self.end_headers();self.wfile.write(data)
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start();origin=f'http://127.0.0.1:{server.server_port}'
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  for width,uid in [(390,'primary'),(1280,'backup')]:
   ctx=browser.new_context(viewport={'width':width,'height':900},accept_downloads=True,service_workers='block');errors=[];missing=[]
   def route(r):
    url=r.request.url
    if url.startswith('https://www.gstatic.com/firebasejs/10.13.0/'):
     file=CACHE/url.rsplit('/',1)[-1];r.fulfill(body=file.read_bytes(),content_type='application/javascript');return
    if url.startswith((origin,API,f'http://127.0.0.1:{a}')):r.continue_();return
    raise AssertionError('Outbound network blocked: '+url)
   ctx.add_init_script("const originalFetch=window.fetch;window.fetch=(url,opts)=>originalFetch(typeof url==='string'?url.replace('https://mhpss5ws-tdp3xtfnsq-as.a.run.app',"+json.dumps(API)+"):url,opts);")
   ctx.route('**/*',route);page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('response',lambda r:missing.append(r.url) if r.status==404 else None)
   page.goto(origin+'/hub/');page.wait_for_function('window.BaselineAuth');page.evaluate('([u,p])=>BaselineAuth.signIn(u,p)',[uid+'@example.invalid',password]);page.wait_for_function('(uid)=>BaselineAuth.currentUser()?.uid===uid',arg=uid);page.reload();page.wait_for_function("document.querySelector('#session').textContent.includes('active')")
   check(uid+'_persistent_normal_arrival',page.locator('#main .card').count()==6)
   page.locator('#main [data-view=dashboard]').click();page.wait_for_function("document.querySelector('#navScope').textContent.includes('admin')")
   keys=page.locator('#dashNav button').evaluate_all('(es)=>es.map(e=>e.dataset.house)');check(uid+'_eleven_houses',len(keys)==len(set(keys))==11)
   def choose(key):
    if width<760 and not page.locator('#sidebar').is_visible():page.locator('#menuToggle').click()
    page.locator('[data-house="'+key+'"]').click()
   for lang in ['en','ne']:
    page.locator('#i18nbar button').nth(0 if lang=='en' else 1).click()
    for key in [k for k in keys if k not in ['baseline','sample']]:
     choose(key)
     if key=='training':page.wait_for_function("document.querySelector('#houseTrainingReadStatus').textContent.includes('Complete')")
     elif key!='5ws':check(uid+'_'+lang+'_'+key+'_authorised_unavailable','Authorised' in page.locator('#dashOther').inner_text() and page.locator('#dashOther .v').all_text_contents()==['—']*3)
     check(uid+'_'+lang+'_'+key+'_no_overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
    choose('training');page.wait_for_function("document.querySelector('#houseTrainingRows tbody')?.children.length===2")
    check(uid+'_'+lang+'_cross_org',set(page.locator('#houseTrainingRows tbody tr td:nth-child(3)').all_text_contents())=={'TPO','CMC'})
    check(uid+'_'+lang+'_metric_unit','not unique people' in page.locator('#houseTrainingTotals').inner_text())
    page.screenshot(path=str(EV/f'{uid}-{lang}-{width}.png'))
   with page.expect_download() as d:page.locator('#houseTrainingExport').click()
   text=Path(d.value.path()).read_text();(EV/(uid+'.csv')).write_text(text);rows=list(csv.DictReader(io.StringIO(text)));check(uid+'_true_provider_csv',len(rows)==2 and {r['org'] for r in rows}=={'TPO','CMC'} and all(json.loads(r['participants']) for r in rows))
   # Main all-forms catalogue uses locked safe registry routes, never deleted roots.
   page.goto(origin+'/hub/?view=forms');page.wait_for_selector('#formList a');links=page.locator('#formList a').evaluate_all('(es)=>es.map(e=>e.getAttribute("href"))');check(uid+'_safe_generated_forms',len(links)==8 and all('/contact.html' not in x and '/referral.html' not in x and '/drafts/' not in x for x in links))
   for href in links:
    response=s.get(origin+'/hub/'+href,timeout=10);check(uid+'_link_'+href,response.status_code==200)
   page.goto(origin+'/hub/?view=dashboard&house=training');page.wait_for_function("document.querySelector('#houseTrainingRows tbody')?.children.length===2")
   time.sleep(1.1);auth.revoke_refresh_tokens(uid,app=app);page.locator('#houseTrainingRefresh').click();page.wait_for_function("document.querySelector('#houseTrainingReadStatus').textContent.includes('could not be read')");check(uid+'_revoked_UI_clears',page.locator('#houseTrainingRows').inner_text()=='' and page.locator('#houseTrainingExport').is_disabled() and page.locator('#houseTrainingTotals .v').all_text_contents()==['—']*3)
   page.evaluate('([u,p])=>BaselineAuth.signIn(u,p)',['manager@example.invalid',password]);page.wait_for_function("BaselineAuth.currentUser()?.uid==='manager'");page.wait_for_function("document.querySelector('#houseTrainingRows tbody')?.children.length===1");check(uid+'_manager_own_org',page.locator('#houseTrainingRows tbody tr td:nth-child(3)').all_text_contents()==['TPO'])
   page.evaluate('([u,p])=>BaselineAuth.signIn(u,p)',['field@example.invalid',password]);page.wait_for_function("BaselineAuth.currentUser()?.uid==='field'");page.wait_for_function("!document.querySelector('#houseTrainingRows')||document.querySelector('#houseTrainingRows').textContent===''");check(uid+'_field_clear','SYNTHETIC' not in page.locator('body').inner_text())
   # Explicitly exercise denied own reader and raw route through real client.
   refused=page.evaluate("async()=>{try{await TRAINING_API.create(BaselineAuth).current();return false}catch(e){return true}}")
   check(uid+'_field_training_denied',refused)
   check(uid+'_field_raw_denied',page.evaluate("async()=>{try{await STAFF_API.create(BaselineAuth).admin();return false}catch(e){return true}}"))
   page.evaluate('([u,p])=>BaselineAuth.signIn(u,p)',['denied@example.invalid',password]);page.wait_for_function("BaselineAuth.currentUser()?.uid==='denied'");check(uid+'_denied_training',page.evaluate("async()=>{try{await TRAINING_API.create(BaselineAuth).current();return false}catch(e){return true}}"))
   page.goto(origin+'/hub/');page.wait_for_function("document.querySelector('#session').textContent.includes('unregistered')");page.locator('#signOut').click();page.wait_for_function('BaselineAuth.currentUser()===null');check(uid+'_signout_clear','SYNTHETIC' not in page.content());check(uid+'_no_page_errors',not errors,errors);check(uid+'_no_404',not missing,missing);ctx.close()
  # Provider revoked-token refusal on actual admin client (not disabled-grant simulation).
  ctx=browser.new_context(service_workers='block');ctx.add_init_script("window.__syntheticToken="+json.dumps(tokens['primary'])+';');ctx.route('**/*',route);p=ctx.new_page();p.goto(origin+'/hub/');p.wait_for_function('window.TRAINING_API');time.sleep(1.1);auth.revoke_refresh_tokens('primary',app=app)
  check('revoked_admin_true_provider_403',s.get(API+'/training/current',headers={'Authorization':'Bearer '+tokens['primary'],'Origin':origin},timeout=20).status_code==403);ctx.close();browser.close();browser=None
 check('no_fictional_route',not any(c['path']=='/dashboard/training' for c in calls))
 check('only_5ws_raw',all(c['path']=='/admin/entries' for c in calls if 'admin/' in c['path']))
 check('no_clinical_requests',not any(any(k in c['path'] for k in ['phq9','selfreport','clinical','contacts','referrals']) for c in calls))
except Exception:
 traceback.print_exc();raise
finally:
 if browser:
  try:browser.close()
  except Exception:pass
 if server:server.shutdown()
 if http:http.shutdown()
 if db:db.close()
 for proc in reversed(procs):
  if proc.poll() is None:
   os.killpg(proc.pid,signal.SIGTERM)
   try:proc.wait(timeout=8)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=3)
 result=dict(verdict='PASS' if checks and all(c['passed'] for c in checks) and sys.exc_info()[0] is None else 'BLOCK',checks=checks,production_access=False,provider_stopped=all(p.poll() is not None for p in procs),backend_pin='3fd05578f8588786410ca42c6a0275bb0ac2cfe9',frontend_base='96c3613d3d6542831f6e0cf10c0daffdc5d7d15a',http_requests=len(calls));(EV/'provider-result.json').write_text(json.dumps(result,indent=2));(EV/'http.json').write_text(json.dumps(calls,indent=2));print(json.dumps(result))
