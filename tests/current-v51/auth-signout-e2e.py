"""Focused genuine SDK/demo Auth rehearsal. No production identity or grants."""
import os,sys,json,socket,subprocess,signal,time,threading,hashlib,secrets
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse
R=Path(__file__).resolve().parents[4]; S=R.parent
H=R/'publication/current-hub'; N=S/'43-backend-completion/cache/form/review-5ws-admin-test-v35/releases/native-test-rc01-20261011/sdk'
sys.path.append(str(next((S/'44-baseline-master-dashboard/.venv/lib').glob('python*/site-packages'))))
import requests
from playwright.sync_api import sync_playwright
E=Path(sys.argv[1]).resolve();E.relative_to(R);E.mkdir(parents=True,exist_ok=False)
PROJECT='demo-mhpss-login-recovery';EMAIL='recovery@example.invalid';PASSWORD=secrets.token_urlsafe(32)
paths=['review-current-v51/current-auth.js','review-analytics-v48/assets/baseline-auth.js','review-baseline-v47/assets/baseline-auth.js']
def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
a,h,l=port(),port(),port();origin='';checks=[];errors=[];proc=None;server=None;contexts=[];success=False
session=requests.Session();session.trust_env=False
def check(name,value):
 if not value:raise AssertionError(name)
 checks.append(name);print('PASS',name,flush=True)
def state(p):return p.evaluate('()=>({signedIn:!!BaselineAuth.currentUser(),...window.authState})')
def loaded(p):p.wait_for_function("()=>window.authState&&authState.restoration!=='restoring'")
def signed(p):p.wait_for_function('()=>!!BaselineAuth.currentUser()')
try:
 env={k:v for k,v in os.environ.items() if not any(x in k for x in ['GOOGLE','GCLOUD','FIREBASE','CREDENTIAL','TOKEN','PROXY'])}
 home=E/'home';home.mkdir();env.update(HOME=str(home),XDG_CONFIG_HOME=str(home/'.config'),CI='true',GCLOUD_PROJECT=PROJECT,NO_PROXY='127.0.0.1')
 cfg=E/'firebase.json';cfg.write_text(json.dumps({'emulators':{'auth':{'host':'127.0.0.1','port':a},'hub':{'host':'127.0.0.1','port':h},'logging':{'host':'127.0.0.1','port':l},'ui':{'enabled':False}}}))
 log=open(os.devnull,'w');proc=subprocess.Popen(['/usr/local/bin/firebase','emulators:start','--only','auth','--project',PROJECT,'--config',str(cfg)],cwd=E,env=env,stdout=log,stderr=log,start_new_session=True)
 end=time.monotonic()+50
 while True:
  if proc.poll() is not None:raise RuntimeError('Auth emulator failed')
  try:
   with socket.create_connection(('127.0.0.1',a),.2):break
  except OSError:
   if time.monotonic()>end:raise RuntimeError('Auth emulator startup deadline')
   time.sleep(.1)
 r=session.post(f'http://127.0.0.1:{a}/identitytoolkit.googleapis.com/v1/accounts:signUp?key=emulator-only',json={'email':EMAIL,'password':PASSWORD,'returnSecureToken':True});check('demo Auth fixture created',r.status_code==200)
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,format,*args):pass
  def do_GET(self):
   path=urlparse(self.path).path
   if path.startswith('/sdk/'):
    p=N/path[5:];data=p.read_bytes();typ='text/javascript'
   elif path=='/auth.js':
    route=dict(current=paths[0],historical=paths[1],baseline=paths[2])[self.headers.get('Referer','').split('/')[-1].split('?')[0] or 'current']
    src=(H/route).read_text().replace('https://www.gstatic.com/firebasejs/10.13.0/','/sdk/')
    needle='auth = api.getAuth(app.getApps().length ? app.getApp() : app.initializeApp(window.FB_CONFIG));'
    assert needle in src
    src=src.replace(needle,needle+f" api.connectAuthEmulator(auth,'http://127.0.0.1:{a}',{{disableWarnings:true}});")
    src+="\nBaselineAuth.onChange((u,s)=>{window.authState=s;});"
    data=src.encode();typ='text/javascript'
   else:
    data=("<!doctype html><script>window.FB_CONFIG="+json.dumps({'apiKey':'emulator-only','projectId':PROJECT,'authDomain':'example.invalid'})+"</script><script src='/auth.js'></script>").encode();typ='text/html'
   self.send_response(200);self.send_header('Content-Type',typ);self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);origin=f'http://127.0.0.1:{server.server_port}';threading.Thread(target=server.serve_forever,daemon=True).start()
 with sync_playwright() as pw:
  def context():
   c=pw.chromium.launch_persistent_context(str(E/'profile'),executable_path='/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome',headless=True,args=['--no-sandbox','--disable-background-networking','--proxy-server=http://127.0.0.1:1','--proxy-bypass-list=127.0.0.1'])
   def route(rt):
    u=urlparse(rt.request.url)
    if u.hostname=='127.0.0.1':rt.continue_()
    else:rt.abort()
   c.route('**/*',route);c.on('page',lambda p:p.on('pageerror',lambda e:errors.append(str(e))));contexts.append(c);return c
  c=context();p=c.new_page();p.goto(origin+'/current');loaded(p)
  check('initial restoration reaches honest signed-out',state(p)['restoration']=='signed-out')
  p.evaluate('async f=>BaselineAuth.signIn(f.email,f.password)',{'email':EMAIL,'password':PASSWORD});signed(p)
  p.reload();loaded(p);check('real SDK reload restores persistent session',state(p)['signedIn'])
  q=c.new_page();q.goto(origin+'/current');loaded(q);check('new tab restores persistent session',state(q)['signedIn'])
  for route in ['historical','baseline','current']:
   q.goto(origin+'/'+route);loaded(q);check('crossroute '+route+' restores session',state(q)['signedIn'])
  c.close();contexts.remove(c);c=context();p=c.new_page();p.goto(origin+'/historical');loaded(p);check('closed browser persistent profile reopens signed in',state(p)['signedIn'])
  def link(page):
   page.evaluate('e=>BaselineAuth.sendLink(e)',EMAIL)
   codes=session.get(f'http://127.0.0.1:{a}/emulator/v1/projects/{PROJECT}/oobCodes').json()['oobCodes']
   code=[x['oobCode'] for x in codes if x.get('email')==EMAIL][-1]
   return origin+'/current?source=current&mode=signIn&apiKey=emulator-only&oobCode='+code
  good=link(p)
  # Remove only the synthetic email hint to exercise manual wrong-email path.
  p.evaluate("()=>localStorage.removeItem('mhpss-np-linkmail')")
  p.goto(good);loaded(p)
  p.evaluate("async()=>{try{await BaselineAuth.finishLink('wrong@example.invalid');}catch(e){}}")
  check('wrong email retains valid session',state(p)['signedIn'])
  print('WRONG_EMAIL_SAFE_STATE',json.dumps(state(p)),flush=True)
  check('wrong email exposes allowlisted error only',state(p)['errorCode'] in ['auth/invalid-action-code','auth/invalid-email'] and EMAIL not in json.dumps(state(p)))
  check('failed completion preserves action query for correct retry',p.url==good)
  p.evaluate('e=>BaselineAuth.finishLink(e)',EMAIL);signed(p)
  check('correct email completes same action and sanitizes query','oobCode' not in p.url and '?source=current' in p.url)
  p.goto(good);loaded(p);p.evaluate('async e=>{try{await BaselineAuth.finishLink(e);}catch(e){}}',EMAIL)
  check('used link retains valid restored session',state(p)['signedIn'] and state(p)['errorCode']=='auth/invalid-action-code')
  p.goto(origin+'/historical?mode=signIn&apiKey=emulator-only&oobCode=invalid-synthetic');loaded(p);p.evaluate('async e=>{try{await BaselineAuth.finishLink(e);}catch(e){}}',EMAIL)
  check('historical invalid link retains session and error stage',state(p)['signedIn'] and state(p)['failureStage']=='email-link')
  # Independent race: the successful link response arrives after SDK signout.
  p.goto(origin+'/current');loaded(p)
  race_link=link(p);p.evaluate("()=>localStorage.removeItem('mhpss-np-linkmail')")
  p.goto(race_link);loaded(p)
  held=[]
  def hold_completion(rt):
   if 'accounts:signInWithEmailLink' in rt.request.url:held.append(rt)
   else:rt.continue_()
  p.route('**/identitytoolkit.googleapis.com/**',hold_completion)
  p.evaluate('e=>{window.raceDone=false;window.racePromise=BaselineAuth.finishLink(e).then(()=>{window.raceDone=true;},()=>{window.raceDone=true;});}',EMAIL)
  end=time.monotonic()+8
  while not held:
   if time.monotonic()>end:raise AssertionError('completion transport was not held')
   p.wait_for_timeout(50)
  p.evaluate('()=>BaselineAuth.signOut()')
  check('independent: signout masks current user before held completion',not state(p)['signedIn'])
  held.pop().continue_();p.wait_for_function('()=>window.raceDone')
  check('independent: late successful completion cannot expose current adapter user',not state(p)['signedIn'])
  p.unroute('**/identitytoolkit.googleapis.com/**',hold_completion)
  p.reload();loaded(p)
  # Record observed failure as a finding, not a fabricated passing safety assertion.
  observed=state(p)
  check('AUTH-R1 late completion stays signed out after reload',not observed['signedIn'])
  rtab=c.new_page();rtab.goto(origin+'/current');loaded(rtab);check('AUTH-R1 new tab stays signed out',not state(rtab)['signedIn']);rtab.close()
  p.evaluate('async f=>BaselineAuth.signIn(f.email,f.password)',{'email':EMAIL,'password':PASSWORD});signed(p);p.reload();loaded(p);check('AUTH-R1 later deliberate sign-in can restore after reload',state(p)['signedIn'])
  print('INDEPENDENT_RACE_OBSERVATION',json.dumps({'late_link_after_signout_restores_on_reload':observed['signedIn'],'restoration':observed['restoration']}),flush=True)
  (E/'SIGNOUT-RACE.json').write_text(json.dumps({'late_link_after_signout_restores_on_reload':observed['signedIn'],'restoration':observed['restoration'],'demo_only':True},indent=2))
  p.goto(origin+'/current');loaded(p);p.evaluate('()=>BaselineAuth.signOut()');p.wait_for_function('()=>!BaselineAuth.currentUser()');p.reload();loaded(p)
  check('explicit shared device signout remains signedout after reload',not state(p)['signedIn'])
  # Controlled legacy TEST interaction; not evidence it occurred on owner Safari.
  p.evaluate('async f=>BaselineAuth.signIn(f.email,f.password)',{'email':EMAIL,'password':PASSWORD});signed(p)
  q=c.new_page();q.goto(origin+'/current');loaded(q)
  q.evaluate("async()=>{const a=await import('/sdk/firebase-app.js'),s=await import('/sdk/firebase-auth.js');await s.setPersistence(s.getAuth(a.getApp()),s.inMemoryPersistence);}")
  # The live observer need not fire; reload is the decisive persistence check.
  # Defect-positive isolation evidence, NOT owner-Safari causation or a fix.
  p.reload();loaded(p)
  check('defect-positive: controlled default-app inMemory switch prevents next persistent reload',not state(p)['signedIn'])
  check('no browser JS errors',not errors)
  c.close();contexts.remove(c)
 success=True
finally:
 for c in contexts:
  try:c.close()
  except Exception:pass  # Playwright context manager already closed on failure.
 contexts.clear()
 if server:server.shutdown();server.server_close()
 if proc and proc.poll() is None:
  os.killpg(proc.pid,signal.SIGTERM)
  try:proc.wait(timeout=8)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
 result={'success':success,'checks':checks,'count':len(checks),'page_errors':errors,'production_access':False,'sdk_version':'10.13.0','source_hashes':{p:hashlib.sha256((H/p).read_bytes()).hexdigest() for p in paths},'cleanup':{'emulator_stopped':proc is None or proc.poll() is not None,'browser_closed':not contexts},'scope':'Chromium persistent profile, genuine demo Auth; not owner Safari recovery or backend access proof'}
 (E/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
