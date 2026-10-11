"""W38 runner pattern, genuine demo Auth/Firestore and unchanged W48 backend.
No production credentials or data; only browser auth boot and loopback routing adapted.
"""
import os,sys,json,socket,subprocess,signal,time,secrets,threading,hashlib,csv,io,traceback
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse
R=Path('/root/mhpss-nepal-final-forms/2026-10-06/51-operational-closure');S=R.parent
H=(R/'publication/current-hub/review-current-v51').resolve();F=S/'48-historical-analytics/backend/functions';N=S/'43-backend-completion/cache/form/review-5ws-admin-test-v35/releases/native-test-rc01-20261011'
PROJECT='demo-mhpss-current-v51'; UID='synthetic-reporter-v51'; EMAIL='reporter-v51@example.invalid'
E=Path(sys.argv[1]).resolve();E.relative_to(R);E.mkdir(exist_ok=False)
checks=[];regressions=[];processes=[];logs=[];servers=[];ports=[];success=False
def regression(n,v):
 if not v:raise AssertionError(n)
 regressions.append(n)

def check(n,v):
 if not v:raise AssertionError(n)
 checks.append(n)
def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));p=s.getsockname()[1];ports.append(p);return p
def ready(proc,p):
 end=time.monotonic()+45
 while time.monotonic()<end:
  if proc.poll() is not None:raise RuntimeError('emulator startup failed')
  try:
   with socket.create_connection(('127.0.0.1',p),.2):return
  except OSError:time.sleep(.1)
 raise RuntimeError('emulator startup deadline')
try:
 env={k:v for k,v in os.environ.items() if not any(x in k for x in ['GOOGLE','GCLOUD','FIREBASE','CREDENTIAL','TOKEN','PROXY','MHPS5WS'])}
 W=E/'runtime';W.mkdir();(W/'home').mkdir()
 a,f,h,l=port(),port(),port(),port()
 env.update(FIREBASE_AUTH_EMULATOR_HOST=f'127.0.0.1:{a}',FIRESTORE_EMULATOR_HOST=f'127.0.0.1:{f}',GCLOUD_PROJECT=PROJECT,NO_PROXY='127.0.0.1',HOME=str(W/'home'),XDG_CONFIG_HOME=str(W/'home/.config'),CI='true',PYTHONDONTWRITEBYTECODE='1')
 os.environ.clear();os.environ.update(env)
 cfg=W/'firebase.json';cfg.write_text(json.dumps({'emulators':{'auth':{'host':'127.0.0.1','port':a},'hub':{'host':'127.0.0.1','port':h},'logging':{'host':'127.0.0.1','port':l},'ui':{'enabled':False},'singleProjectMode':True}}))
 rules=S/'38-parallel-backend-dashboard/backend/parent-final-harness/tests/active-v3.rules'
 commands=[(['firebase','emulators:start','--only','auth','--project',PROJECT,'--config',str(cfg)],a),(['/usr/lib/jvm/java-21-openjdk-amd64/bin/java','-jar','/root/.cache/firebase/emulators/cloud-firestore-emulator-v1.22.0.jar','--host','127.0.0.1','--port',str(f),'--project_id',PROJECT,'--single_project_mode','--single_project_mode_error','--rules',str(rules)],f)]
 for i,(cmd,p) in enumerate(commands):
  log=open(W/f'start-{i}.log','w');logs.append(log);proc=subprocess.Popen(cmd,cwd=W,env=env,stdout=log,stderr=log,start_new_session=True);processes.append(proc);ready(proc,p)
 sys.path.insert(0,str(F));import firebase_admin,requests,identity,intake,backend,adapter
 from firebase_admin import auth
 from google.auth.credentials import AnonymousCredentials
 from google.cloud import firestore
 from flask import Flask,request
 from werkzeug.serving import make_server
 browser_site=next((S/'44-baseline-master-dashboard/.venv/lib').glob('python*/site-packages'))
 sys.path.append(str(browser_site))
 from playwright.sync_api import sync_playwright
 app=firebase_admin.initialize_app(options={'projectId':PROJECT,'httpTimeout':5},name='current-v51-proof');password=secrets.token_urlsafe(32)
 auth.create_user(uid=UID,email=EMAIL,email_verified=True,password=password,app=app)
 def client():return firestore.Client(project=PROJECT,credentials=AnonymousCredentials())
 db=client();grant={'version':2,'uid':UID,'email':EMAIL,'role':'reporter','org':'TPO','enabled':True};gref=db.document('mhpss5wsGrantsV2/'+UID);gref.create(grant);check('demo-only exact reporter grant readback',gref.get().to_dict()==grant)
 class DemoBackend(backend.Backend):
  project=PROJECT
  def client(self):return client()
  def verify(self,token):
   try:return auth.verify_id_token(token,app=app,check_revoked=True)
   except Exception:raise identity.AuthenticationError('demo identity refused') from None
 service=DemoBackend();flask=Flask('current-proof');nonce=secrets.token_hex(16);origin=''
 @flask.route('/profile',methods=['GET','OPTIONS'])
 @flask.route('/current',methods=['GET','OPTIONS'])
 @flask.route('/intake',methods=['POST','OPTIONS'])
 def api():return adapter.handle(request,service,origin=origin)
 api_server=make_server('127.0.0.1',0,flask,threaded=True);servers.append(api_server);apiport=api_server.server_port;ports.append(apiport);threading.Thread(target=api_server.serve_forever,daemon=True).start()
 sourcehash={str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in H.iterdir() if p.is_file()}
 nativebytes=(N/'form/5ws-report.html').read_bytes()
 session=requests.Session();session.trust_env=False
 sign=session.post(f'http://127.0.0.1:{a}/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=emulator-only',json={'email':EMAIL,'password':password,'returnSecureToken':True},timeout=10);check('genuine demo Auth token issued',sign.status_code==200);token=sign.json()['idToken']
 headers={'Authorization':'Bearer '+token,'X-Selected-Org':'TPO','Content-Type':'application/json'}

 profileurl=f'http://127.0.0.1:{apiport}/profile';ph={'Authorization':'Bearer '+token,'Origin':origin}
 def profile(hh=ph,**kw):return session.get(profileurl,headers=hh,timeout=10,**kw)
 check('profile missing authentication refused',profile({}).status_code==401)
 got=profile();check('exact own profile minimal response no public identity',got.status_code==200 and got.json()=={'protocol':'own-reporter-profile/1','access':'reporter','org':'TPO'} and got.headers['Cache-Control']=='no-store')
 for field,value in [('enabled',False),('role','admin'),('uid','someone-else'),('email','other@example.invalid'),('org','INVALID')]:
  changed={**grant,field:value};gref.set(changed);r=profile();check('profile refuses '+field+' '+str(value),r.status_code==200 and r.json()=={'protocol':'own-reporter-profile/1','access':'no_access','reason':'enabled_reporter_grant_required'})
 gref.delete();check('missing grant safe specific no access',profile().json().get('access')=='no_access');gref.set(grant)
 for path,hh in [('/profile?uid=other',ph),('/profile',{**ph,'X-Selected-Org':'WHO'}),('/profile',{**ph,'X-UID':'other'}),('/profile',{**ph,'Origin':'https://wrong.invalid'})]:
  r=session.get(f'http://127.0.0.1:{apiport}'+path,headers=hh,timeout=10);check('profile selection and identity/origin refusal '+str(hh.keys())+path,r.status_code in [400,403])
 anon=session.post(f'http://127.0.0.1:{a}/identitytoolkit.googleapis.com/v1/accounts:signUp?key=emulator-only',json={'returnSecureToken':True},timeout=10)
 check('genuine anonymous identity refused',profile({'Authorization':'Bearer '+anon.json()['idToken']}).status_code==403)
 auth.update_user(UID,disabled=True,app=app);check('disabled Auth identity refused before profile disclosure',profile().status_code==403);auth.update_user(UID,disabled=False,app=app)
 check('wrong org current still refused',session.get(f'http://127.0.0.1:{apiport}/current',headers={**ph,'X-Selected-Org':'WHO'},timeout=10).status_code==403)

 wire=None;receipts={};mutation_enabled=False
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def reply(self,status,data,typ='application/json'):
   if not isinstance(data,bytes):data=json.dumps(data).encode()
   self.send_response(status);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
  def do_GET(self):
   if self.path=='/nonce':self.reply(200,{'nonce':nonce});return
   if self.path=='/fixture':self.reply(200,{'email':EMAIL,'password':password,'project':PROJECT});return
   if self.path=='/native.html':self.reply(200,nativebytes,'text/html');return
   if self.path.startswith('/sdk/'):
    name=self.path[5:];p=N/'sdk'/name
    if '/' in name or not p.is_file():self.reply(404,{});return
    self.reply(200,p.read_bytes(),'text/javascript');return
   if self.path=='/current-auth.js':
    data=(H/'current-auth.js').read_text().replace("https://www.gstatic.com/firebasejs/10.13.0/",'/sdk/').replace("auth = api.getAuth(app.getApps().length ? app.getApp() : app.initializeApp(window.FB_CONFIG));", "auth = api.getAuth(app.getApps().length ? app.getApp() : app.initializeApp({apiKey:'emulator-only',projectId:'"+PROJECT+"'}));api.connectAuthEmulator(auth,location.origin,{disableWarnings:true});")
    data=data.replace('function notify() {', 'function notify() { window.fixtureRepeatAuth = notify;')
    data+="\nwindow.fixtureAuthReady=(localStorage.getItem('fixture-signed-once')||location.search.includes('skipFixtureAuto'))?Promise.resolve():fetch('/fixture').then(r=>r.json()).then(f=>BaselineAuth.signIn(f.email,f.password)).then(()=>localStorage.setItem('fixture-signed-once','yes'));"
    self.reply(200,data.encode(),'text/javascript');return
   if self.path=='/field-release.js':
    self.reply(200,b"window.FIELD_RELEASE=Object.freeze({activationEnabled:true,classification:'SYNTHETIC_EMULATOR_ONLY'});",'text/javascript');return
   if self.path in ['/current-ui.js','/field-journey.js']:
    data=b"fixtureAuthReady.then(()=>{"+(H/self.path[1:]).read_bytes()+b"});";self.reply(200,data,'text/javascript');return
   if self.path in ['/current','/profile']:
    self.proxy();return
   path=urlparse(self.path).path;name='index.html' if path in ['/','/index.html'] else path[1:]
   p=H/name
   if '/' in name or not p.is_file():self.reply(404,{});return
   self.reply(200,p.read_bytes(),{'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json'}.get(p.suffix,'text/plain'))
  def proxy(self):
   raw=self.rfile.read(int(self.headers.get('Content-Length','0')));hh={k:v for k,v in self.headers.items() if k.lower() not in ['host','connection']};hh['Origin']=origin
   res=session.request(self.command,f'http://127.0.0.1:{apiport}'+self.path,headers=hh,data=raw,timeout=40)
   self.reply(res.status_code,res.content)
  def do_POST(self):
   if self.path.startswith(('/identitytoolkit.googleapis.com/','/securetoken.googleapis.com/')):
    raw=self.rfile.read(int(self.headers.get('Content-Length','0')));res=session.post(f'http://127.0.0.1:{a}'+self.path,data=raw,headers={'Content-Type':self.headers.get('Content-Type','application/json')},timeout=10);self.reply(res.status_code,res.content);return
   if self.path=='/intake':self.proxy();return
   self.reply(404,{})
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);servers.append(server);ports.append(server.server_port);origin=f'http://127.0.0.1:{server.server_port}';threading.Thread(target=server.serve_forever,daemon=True).start()
 check('intended scoped fixture nonce',session.get(origin+'/nonce',timeout=5).json()=={'nonce':nonce})
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome',headless=True,args=['--no-sandbox','--disable-background-networking','--proxy-server=http://127.0.0.1:1','--proxy-bypass-list=127.0.0.1'])
  c=b.new_context(accept_downloads=True);errors=[];api_calls=[];http=[]
  def routing(route):
   u=urlparse(route.request.url)
   if u.scheme+'://'+u.netloc==origin:route.continue_();return
   if u.scheme+'://'+u.netloc=='https://mhpss5ws-tdp3xtfnsq-as.a.run.app' and u.path in ['/current','/intake','/profile']:
    api_calls.append(route.request.method)
    hh={k:v for k,v in route.request.headers.items() if k.lower() not in ['host','origin','referer','content-length']};hh['Origin']=origin
    if route.request.method=='OPTIONS':route.fulfill(status=204,headers={'Access-Control-Allow-Origin':origin,'Access-Control-Allow-Methods':'GET','Access-Control-Allow-Headers':'authorization,x-selected-org,x-listing-cursor'});return
    res=session.request(route.request.method,f'http://127.0.0.1:{apiport}'+u.path,headers=hh,data=route.request.post_data_buffer,timeout=40);http.append({'method':route.request.method,'path':u.path,'status':res.status_code});route.fulfill(status=res.status_code,body=res.content,headers={'Content-Type':'application/json','Access-Control-Allow-Origin':origin,'Cache-Control':'no-store'});return
   route.abort()
  c.route('**/*',routing)
  try:
   p=c.new_page();p.set_viewport_size({'width':390,'height':844});p.on('pageerror',lambda e:errors.append(str(e)));p.add_init_script('''window.se1Gate={blocked:false,release:null};const se1Fetch=window.fetch;window.fetch=async(...args)=>{const r=await se1Fetch(...args);if(String(args[0]).endsWith('/current')&&!se1Gate.blocked){se1Gate.blocked=true;await new Promise(resolve=>se1Gate.release=resolve);}return r;};''');p.goto(origin+'/',wait_until='domcontentloaded');p.wait_for_function('()=>window.FIELD_JOURNEY&&typeof se1Gate.release==="function"&&typeof document.getElementById("fieldForm").contentWindow.INTEGRATION_REVIEW==="object"');
   regression('SE1 native loaded between profile HTTP200 and snapshot installation',p.evaluate('()=>CURRENT_UI.profile()===null&&CURRENT_UI.state().reading&&document.getElementById("fieldPanel").hidden'))
   p.evaluate('()=>{for(let i=0;i<4;i++)fixtureRepeatAuth();document.getElementById("fieldForm").dispatchEvent(new Event("load"));FIELD_JOURNEY.setup();se1Gate.release();}')
   p.wait_for_function('()=>!document.getElementById("fieldPanel").hidden')
   regression('SE1 repeated same-user SDK notifications coalesce startup current read',len([x for x in http if x['path']=='/current'])==1)
   p.wait_for_function('()=>window.FIELD_JOURNEY&&BaselineAuth.currentUser()?.emailVerified===true');p.wait_for_timeout(3000);print('SETUP',p.locator('#delivery').inner_text(),errors,p.locator('#fieldForm').evaluate('(e)=>typeof e.contentWindow.INTEGRATION_REVIEW'));p.wait_for_function('()=>!document.getElementById("fieldPanel").hidden',timeout=10000)
   check('automatic own-profile discovery opens existing native flow without code or access click',p.locator('#fieldPanel').is_visible() and p.locator('#org').input_value()=='TPO' and p.locator('#org').get_attribute('readonly') is not None)
   check('native organisation locked to server assignment',p.frame_locator('#fieldForm').locator('#org').is_disabled() and p.frame_locator('#fieldForm').locator('#org').input_value()=='TPO')
   f=p.frame_locator('#fieldForm');f.locator('#syntheticExample').evaluate('(e)=>e.click()');wire=p.locator('#fieldForm').evaluate('(e)=>e.contentWindow.REVIEW.wire()');intake.validate_session(wire)
   def submit():
    return p.evaluate('async()=>{const f=document.getElementById("fieldForm").contentWindow;return FIELD_JOURNEY.submit(f.REVIEW.wire());}')
   # Exercise the real accepted native Submit control, not direct intake harness.
   f.locator('#f').evaluate('(e)=>e.requestSubmit()');p.wait_for_timeout(3000);print('DEBUG',p.locator('#delivery').inner_text(),f.locator('#authenticatedSubmitState').inner_text(),f.locator('#problems').inner_text(),errors);p.wait_for_function('()=>document.getElementById("delivery").textContent.startsWith("Visible in dashboard:")',timeout=60000)
   state=p.evaluate('()=>SESSION_QUEUE.all()');check('native Submit -> durable outbox -> operational intake -> receipt -> automatic dashboard',len(state)==1 and state[0]['state']=='remotely_acknowledged')
   sid=state[0]['session'];ack=state[0]['ack'];doc=db.document('mhpss5wsReportsV2/'+sid).get().to_dict();check('persisted canonical exact body and matching receipt',doc['revision']==1 and doc['request_sha256']==state[0]['sha256'] and doc['event_id']==ack['event_id'] and doc['payload']==wire)
   check('normal dashboard one same ID/revision not TEST collection',p.locator('#rows tr').count()==1 and sid in p.locator('#rows').inner_text() and not list(db.collection('mhpss5wsTestReportsV1').stream()))
   with p.expect_download() as down:p.locator('#export').click()
   down.value.save_as(str(E/'field.csv'));csvrows=list(csv.DictReader(io.StringIO((E/'field.csv').read_text())));check('actual downloaded CSV same identity revision digest counts',len(csvrows)==60 and all(x['record_id']==sid and x['revision']=='1' and x['request_sha256']==ack['request_sha256'] for x in csvrows) and sum(int(x['count']) for x in csvrows if x['matrix_scope']=='session')==30)
   f.locator('#sessionTime').fill('10:45');result=submit();check('same editor correction -> revision2 visible',result['receipt']['revision']==2 and result['session']==sid and 'revision 2' in p.locator('#delivery').inner_text())
   first=state[0];reply=p.evaluate('async x=>{const ack=await fetch("https://mhpss5ws-tdp3xtfnsq-as.a.run.app/intake",{method:"POST",headers:{Authorization:"Bearer "+await BaselineAuth.token(),"Content-Type":"application/json","X-Selected-Org":"TPO","X-Session-Id":x.session,"X-Retry-Token":x.token},body:x.body});return ack.json();}',first);check('exact original retry cannot overwrite newer correction',reply==ack and db.document('mhpss5wsReportsV2/'+sid).get().to_dict()['revision']==2)
   # Drop transport acknowledgement after backend commit. Browser retains immutable request.
   drop=[True]
   def dropped(route):
    u=urlparse(route.request.url);hh={k:v for k,v in route.request.headers.items() if k.lower() not in ['host','origin','referer','content-length']};hh['Origin']=origin
    res=session.post(f'http://127.0.0.1:{apiport}/intake',headers=hh,data=route.request.post_data_buffer,timeout=40)
    if drop[0]:drop[0]=False;route.abort()
    else:route.fulfill(status=res.status_code,body=res.content,headers={'Content-Type':'application/json','Access-Control-Allow-Origin':origin,'Cache-Control':'no-store'})
   p.route('**/intake',dropped);f.locator('#sessionTime').fill('11:15');result=submit();check('lost ACK remains device-pending despite server commit',result['state']=='durably_queued' and db.document('mhpss5wsReportsV2/'+sid).get().to_dict()['revision']==3)
   p.reload(wait_until='domcontentloaded');p.wait_for_function('()=>typeof se1Gate.release==="function"&&typeof document.getElementById("fieldForm").contentWindow.INTEGRATION_REVIEW==="object"');p.evaluate('()=>{fixtureRepeatAuth();fixtureRepeatAuth();se1Gate.release();}');p.wait_for_function('()=>window.FIELD_JOURNEY&&BaselineAuth.currentUser()?.emailVerified===true');p.wait_for_timeout(2500);print('RELOAD',p.locator('#status').inner_text(),p.locator('#delivery').inner_text(),errors,p.evaluate('()=>({profile:CURRENT_UI.profile()?.org,native:typeof document.getElementById("fieldForm").contentWindow.INTEGRATION_REVIEW,queue:typeof SESSION_QUEUE})'));p.wait_for_function('()=>Array.from(document.querySelectorAll("#pendingReports button")).filter(x=>x.textContent.startsWith("Retry this")).length===1',timeout=40000);p.get_by_role('button',name='Retry this exact report',exact=True).click();p.wait_for_function('()=>document.getElementById("delivery").textContent.includes("revision 3")&&document.getElementById("delivery").textContent.startsWith("Visible")',timeout=40000)
   check('reload signbackin and exact retry recovers lost ACK without duplicate',len(list(db.collection('mhpss5wsReportsV2').stream()))==1 and len(list(db.document('mhpss5wsReportsV2/'+sid).collection('events').stream()))==3)
   # BEFORE server ACK: connection abort, original pending survives then exact retry.
   p.route('**/intake',lambda route:route.abort());f=p.frame_locator('#fieldForm');f.locator('#syntheticExample').evaluate('(e)=>e.click()');result=submit();newid=result['session'];check('interrupted request retained, no server row',result['state']=='durably_queued' and not db.document('mhpss5wsReportsV2/'+newid).get().exists)
   p.unroute('**/intake');beforeEpoch=p.evaluate('()=>FIELD_JOURNEY.state().epoch');p.evaluate('()=>{se1Gate.blocked=false;se1Gate.release=null;document.getElementById("refresh").click();}');p.wait_for_function('()=>typeof se1Gate.release==="function"');regression('SE1 refresh hides stale pending retry actions while read incomplete',p.locator('#pendingReports button').count()==0 and p.locator('#fieldPanel').is_hidden());p.evaluate('()=>{fixtureRepeatAuth();fixtureRepeatAuth();FIELD_JOURNEY.setup();se1Gate.release();}');p.wait_for_function('()=>Array.from(document.querySelectorAll("#pendingReports button")).filter(x=>x.textContent.startsWith("Retry this")).length===1',timeout=40000);p.get_by_role('button',name='Retry this exact report',exact=True).click();p.wait_for_function('()=>document.getElementById("delivery").textContent.startsWith("Visible")',timeout=40000);regression('SE1 same-owner refresh/auth notifications preserve serialized editor epoch',p.evaluate('()=>FIELD_JOURNEY.state().epoch')==beforeEpoch);check('retry before ACK creates exactly one second report',len(list(db.collection('mhpss5wsReportsV2').stream()))==2)
   check('mobile no root horizontal overflow',p.evaluate('document.documentElement.scrollWidth<=innerWidth'))
   for width in [320,390,1280]:
    p.set_viewport_size({'width':width,'height':844});check('existing journey no root horizontal overflow '+str(width),p.evaluate('document.documentElement.scrollWidth<=innerWidth'))
    p.screenshot(path=str(E/('journey-'+str(width)+'.png')))
   p.set_viewport_size({'width':390,'height':844})
   gref.update({'enabled':False});p.locator('#refresh').click();p.wait_for_function('()=>document.getElementById("status").textContent.includes("no enabled reporter assignment")',timeout=40000);check('revocation clears table and downloaded-export availability',p.locator('#result').is_hidden() and p.locator('#export').is_disabled())
   denied=session.post(origin+'/intake',headers={**headers,'X-Session-Id':sid,'X-Retry-Token':sid+'-denied'},data=state[0]['body'],timeout=40);check('revoked identity denied intake without overwrite',denied.status_code==403 and db.document('mhpss5wsReportsV2/'+sid).get().to_dict()['revision']==3)
   check('revocation hides native reporting panel',p.locator('#fieldPanel').is_hidden())
   gref.set(grant);p.locator('#refresh').click();p.wait_for_function('()=>!document.getElementById("fieldPanel").hidden',timeout=40000)
   p.route('**/profile',lambda route:route.fulfill(status=503,body='{"error":"reporting access unavailable"}',content_type='application/json',headers={'Access-Control-Allow-Origin':origin}))
   p.locator('#refresh').click();p.wait_for_function('()=>document.getElementById("status").textContent.includes("HTTP 503")',timeout=40000)
   check('profile HTTP refusal withholds table export and native',p.locator('#result').is_hidden() and p.locator('#export').is_disabled() and p.locator('#fieldPanel').is_hidden())
   p.unroute('**/profile')
   p.evaluate("()=>{window.releaseProfile=null;window.nativeFetch=window.fetch;window.fetch=async(...args)=>{const r=await nativeFetch(...args);if(String(args[0]).endsWith('/profile'))await new Promise(resolve=>{releaseProfile=resolve;});return r;};CURRENT_UI.refresh().catch(e=>window.se1Cancelled=String(e));}")
   p.wait_for_function('()=>typeof releaseProfile==="function"',timeout=40000)
   p.locator('#signOut').click();p.evaluate('()=>releaseProfile()');p.wait_for_timeout(300)
   check('late profile after signout cannot leak org rows or native',p.locator('#org').input_value()=='' and p.locator('#result').is_hidden() and p.locator('#fieldPanel').is_hidden())
   regression('SE1 superseded late-profile read rejects cleanly',p.evaluate('()=>String(window.se1Cancelled).includes("superseded")'));check('signout hides form pending and export; no queue deletion',p.locator('#fieldPanel').is_hidden() and p.locator('#pendingReports li').count()==0 and p.locator('#export').is_disabled())
   check('signed-out primary action no completion burden',p.locator('#signIn').is_visible() and p.locator('#finishLink').is_hidden())
   p.evaluate('()=>window.fetch=window.nativeFetch')
   def request_link(page):
    page.locator('#email').fill(EMAIL);page.locator('#signIn').click();page.wait_for_function('()=>document.getElementById("status").textContent.includes("link requested")')
    codes=session.get(f'http://127.0.0.1:{a}/emulator/v1/projects/{PROJECT}/oobCodes',timeout=10).json()['oobCodes']
    code=[x['oobCode'] for x in codes if x.get('email')==EMAIL][-1]
    return origin+'/?skipFixtureAuto=1&apiKey=emulator-only&mode=signIn&oobCode='+code
   link=request_link(p);p.goto(link,wait_until='domcontentloaded');p.wait_for_function('()=>typeof se1Gate.release==="function"&&typeof document.getElementById("fieldForm").contentWindow.INTEGRATION_REVIEW==="object"');regression('SE1 email-link profile withheld while native is loaded and current held',p.evaluate('()=>CURRENT_UI.profile()===null&&document.getElementById("fieldPanel").hidden'));p.evaluate('()=>{fixtureRepeatAuth();fixtureRepeatAuth();document.getElementById("fieldForm").dispatchEvent(new Event("load"));se1Gate.release();}');p.wait_for_timeout(2000);print('LINKSTATE',p.locator('#status').inner_text(),p.locator('#delivery').inner_text(),errors,p.evaluate('()=>({profile:CURRENT_UI.profile()?.org,native:typeof document.getElementById("fieldForm").contentWindow.INTEGRATION_REVIEW,uid:BaselineAuth.currentUser()?.uid})'));p.wait_for_function('()=>!document.getElementById("fieldPanel").hidden',timeout=40000)
   check('same-browser email link completes automatically and autoloads reports',p.locator('#finishLink').is_hidden() and p.locator('#org').input_value()=='TPO' and p.locator('#rows tr').count()==2)
   p.locator('#signOut').click();link=request_link(p)
   c2=b.new_context();c2.route('**/*',routing);q=c2.new_page();q.goto(link);q.wait_for_function('()=>BaselineAuth.currentUser()===null&&!document.getElementById("finishLink").hidden')
   check('cross-browser only email confirmation needed no org entry',q.locator('#email').is_visible() and q.locator('#signIn').is_hidden() and q.locator('#fieldPanel').is_hidden())
   q.locator('#email').fill(EMAIL);q.locator('#finishLink').click();q.wait_for_function('()=>!document.getElementById("fieldPanel").hidden',timeout=40000)
   check('cross-browser email confirmation autoloads permitted reports',q.locator('#org').input_value()=='TPO' and q.locator('#rows tr').count()==2)
   c2.close()
   late=c.new_page();heldNative=[];late.route('**/field-form.html',lambda route:heldNative.append(route));late.goto(origin+'/',wait_until='domcontentloaded');late.wait_for_function('()=>window.FIELD_JOURNEY');late.evaluate('async f=>BaselineAuth.signIn(f.email,f.password)',{'email':EMAIL,'password':password});late.wait_for_function('()=>window.CURRENT_UI?.profile()?.org==="TPO"');regression('SE1 complete snapshot before native load keeps editor hidden',late.locator('#fieldPanel').is_hidden() and len(heldNative)==1);lateReads=len(http);heldNative[0].fulfill(status=200,body=(H/'field-form.html').read_bytes(),content_type='text/html');late.wait_for_function('()=>!document.getElementById("fieldPanel").hidden');regression('SE1 deferred native load consumes installed snapshot without new read',late.evaluate('()=>CURRENT_UI.profile().owner===BaselineAuth.currentUser()&&FIELD_JOURNEY.state().verified') and len(http)==lateReads);late.evaluate('()=>BaselineAuth.signOut()');late.close()
   # Second genuine demo owner: a late prior-owner snapshot must never install.
   otherEmail='second-reporter@example.invalid';otherUID='synthetic-second-v51';auth.create_user(uid=otherUID,email=otherEmail,email_verified=True,password=password,app=app);db.document('mhpss5wsGrantsV2/'+otherUID).set({**grant,'uid':otherUID,'email':otherEmail})
   iso=c.new_page();iso.add_init_script('''window.ownerGate={release:null};const ownerFetch=window.fetch;window.fetch=async(...args)=>{const r=await ownerFetch(...args);if(String(args[0]).endsWith('/current')&&!ownerGate.release)await new Promise(resolve=>ownerGate.release=resolve);return r;};''');iso.goto(origin+'/',wait_until='domcontentloaded');iso.wait_for_function('()=>window.FIELD_JOURNEY');iso.evaluate('async f=>BaselineAuth.signIn(f.email,f.password)',{'email':EMAIL,'password':password});iso.wait_for_function('()=>typeof ownerGate.release==="function"');iso.evaluate('()=>{window.oldOwnerRead=CURRENT_UI.refresh().then(()=>false,()=>true);return BaselineAuth.signOut();}');iso.evaluate('async f=>BaselineAuth.signIn(f.email,f.password)',{'email':otherEmail,'password':password});iso.wait_for_function('()=>CURRENT_UI.profile()?.owner===BaselineAuth.currentUser()&&!document.getElementById("fieldPanel").hidden');iso.evaluate('()=>ownerGate.release()');regression('SE1 late prior-owner read rejects without replacing new owner snapshot',iso.evaluate('async()=>await oldOwnerRead&&CURRENT_UI.reader.view().owner===BaselineAuth.currentUser()&&CURRENT_UI.reader.view().rows.length===0&&FIELD_JOURNEY.state().ownerCurrent'));iso.evaluate('()=>BaselineAuth.signOut()');iso.close()
   # Activation fixture is removed for the shipped held-mode gate exercise.
   p.route('**/field-release.js',lambda route:route.fulfill(status=200,body=(H/'field-release.js').read_bytes(),content_type='text/javascript'))
   p.goto(origin+'/',wait_until='domcontentloaded');p.wait_for_function('()=>window.FIELD_JOURNEY&&document.getElementById("signIn").hidden===false')
   p.evaluate('async f=>BaselineAuth.signIn(f.email,f.password)',{'email':EMAIL,'password':password});p.wait_for_function('()=>typeof se1Gate.release==="function"');p.evaluate('()=>se1Gate.release()');p.wait_for_function('()=>!document.getElementById("fieldPanel").hidden',timeout=40000)
   held=p.evaluate('async()=>{const n=document.getElementById("fieldForm").contentWindow;n.document.getElementById("syntheticExample").click();const before=(await SESSION_QUEUE.all()).length;try{await FIELD_JOURNEY.submit(n.REVIEW.wire());return false;}catch(e){return String(e).includes("activation held")&&before===(await SESSION_QUEUE.all()).length;}}')
   check('shipped activation false refuses submit without new queue or server mutation',held and len(list(db.collection('mhpss5wsReportsV2').stream()))==2)
   check('no JS page errors',not errors)
   result={'completion':'ALL_CASES_COMPLETED','checks':checks,'count':len(checks),'regressions':regressions,'regression_count':len(regressions),'production_write':False,'state':'PASS_REAL_BROWSER_DEMO_AUTH_FIRESTORE_NOT_DEPLOYED_PRODUCTION','identity':UID,'org':'TPO','namespace':PROJECT,'activation':'Enabled only by fixture HTTP response; shipped field-release remains false','source_hashes':sourcehash,'backend_hashes':{n:hashlib.sha256((F/n).read_bytes()).hexdigest() for n in ['backend.py','adapter.py','identity.py']}}
   (E/'RESULT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));success=True
  except Exception as exc:
   diagnostic={'exception':str(exc),'checks':checks,'count':len(checks),'regressions':regressions,'http':http,'page_errors':errors}
   try:diagnostic['browser']=p.evaluate('''async()=>{let queue=[],reader;try{queue=(await SESSION_QUEUE.all()).map(x=>({state:x.state,revision:x.ack?.revision}));}catch(e){queue=[{error:String(e)}];}try{const s=CURRENT_UI.reader.view();reader={installed:true,org:s.org,rows:s.rows.length,ownerCurrent:s.owner===BaselineAuth.currentUser()};}catch(e){reader={installed:false,error:String(e)};}return {status:document.getElementById('status').textContent,delivery:document.getElementById('delivery').textContent,profile:CURRENT_UI.profile()?{org:CURRENT_UI.profile().org,ownerCurrent:CURRENT_UI.profile().owner===BaselineAuth.currentUser()}:null,ui:CURRENT_UI.state(),journey:FIELD_JOURNEY.state(),reader,queue,hidden:Object.fromEntries(['fieldPanel','result','signIn','finishLink','signOut'].map(id=>[id,document.getElementById(id).hidden])),pendingButtons:document.querySelectorAll('#pendingReports button').length,native:typeof document.getElementById('fieldForm').contentWindow.INTEGRATION_REVIEW};}''')
   except Exception as de:diagnostic['diagnostic_error']=str(de)
   (E/'FAILURE.json').write_text(json.dumps(diagnostic,indent=2));(E/'PARTIAL.json').write_text(json.dumps({'checks':checks,'count':len(checks),'regressions':regressions,'completed':False},indent=2));raise
  finally:c.close();b.close()
 db.close();firebase_admin.delete_app(app)
finally:
 for server in reversed(servers):server.shutdown();server.server_close()
 for proc in reversed(processes):
  if proc.poll() is None:
   os.killpg(proc.pid,signal.SIGTERM)
   try:proc.wait(timeout=8)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=3)
 for log in logs:log.close()
 closed=[]
 for p in ports:
  with socket.socket() as sock:closed.append(sock.connect_ex(('127.0.0.1',p))!=0)
 (E/'CLEANUP.json').write_text(json.dumps({'success':success,'all_listeners_closed':all(closed),'all_processes_stopped':all(p.poll() is not None for p in processes),'ports':ports},indent=2)+'\n')
 if not all(closed):raise RuntimeError('cleanup failed')
