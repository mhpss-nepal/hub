"""Genuine Firebase browser SDK persistence, demo Auth emulator only. No email/grant/Firestore."""
import os,json,socket,subprocess,time,signal,tempfile
from pathlib import Path
from threading import Thread
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def run():
 with tempfile.TemporaryDirectory(prefix='training-auth-',dir=os.environ.get('TMPDIR','/root/.hermes/cache/scratch')) as tmp:
  t=Path(tmp);a,h,l=[port() for _ in range(3)];cfg=t/'firebase.json';cfg.write_text(json.dumps({'emulators':{'auth':{'host':'127.0.0.1','port':a},'hub':{'host':'127.0.0.1','port':h},'logging':{'host':'127.0.0.1','port':l},'ui':{'enabled':False}}}))
  env={k:v for k,v in os.environ.items() if not any(x in k for x in ['GOOGLE','GCLOUD','FIREBASE','CREDENTIAL','TOKEN','PROXY'])};env.update(HOME=tmp,CI='true')
  with open(t/'auth.log','w') as log:
   proc=subprocess.Popen(['firebase','emulators:start','--only','auth','--project','demo-training-browser','--config',str(cfg)],env=env,cwd=tmp,stdout=log,stderr=log,start_new_session=True)
   server=None
   try:
    end=time.monotonic()+45
    while True:
     if proc.poll() is not None:raise RuntimeError((t/'auth.log').read_text())
     try:
      with socket.create_connection(('127.0.0.1',a),.2):break
     except OSError:
      if time.monotonic()>end:raise RuntimeError('demo Auth startup timeout')
      time.sleep(.1)
    class Handler(BaseHTTPRequestHandler):
     def log_message(self,format,*args):pass
     def do_GET(self):
      if self.path=='/current-auth.js':data=(ROOT/'review-current-v51/current-auth.js').read_bytes();mime='application/javascript'
      elif self.path=='/training-api.js':data=(ROOT/'assets/training-api.js').read_bytes();mime='application/javascript'
      else:
       data=('''<script>window.FB_CONFIG={apiKey:'demo-key',authDomain:'demo-training-browser.firebaseapp.com',projectId:'demo-training-browser'};</script><script type="module">import {initializeApp} from 'https://www.gstatic.com/firebasejs/10.13.0/firebase-app.js';import {getAuth,connectAuthEmulator,signInAnonymously} from 'https://www.gstatic.com/firebasejs/10.13.0/firebase-auth.js';const auth=getAuth(initializeApp(FB_CONFIG));connectAuthEmulator(auth,'http://127.0.0.1:PORT',{disableWarnings:true});window.demoSignIn=()=>signInAnonymously(auth);await import('/current-auth.js');await import('/training-api.js');</script>'''.replace('PORT',str(a))).encode();mime='text/html'
      self.send_response(200);self.send_header('Content-Type',mime);self.end_headers();self.wfile.write(data)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
    with sync_playwright() as pw:
     b=pw.chromium.launch(headless=True);c=b.new_context(service_workers='block');c.route('**/*',lambda r:r.continue_() if r.request.url.startswith(('http://127.0.0.1:','https://www.gstatic.com/firebasejs/10.13.0/')) else r.abort());p=c.new_page();p.goto(base);p.wait_for_function("window.BaselineAuth && window.TRAINING_API",timeout=45000);p.evaluate('demoSignIn()');p.wait_for_function('BaselineAuth.currentUser()!==null');uid=p.evaluate('BaselineAuth.currentUser().uid');p.reload();p.wait_for_function('window.BaselineAuth && BaselineAuth.currentUser()!==null');assert p.evaluate('BaselineAuth.currentUser().uid')==uid
     assert p.evaluate("async()=>{try{await TRAINING_API.create(BaselineAuth).enqueue({});return false}catch(e){return e.message.includes('Verified sign-in required')}}")
     p.evaluate('BaselineAuth.signOut()');p.reload();p.wait_for_function('window.BaselineAuth');p.wait_for_timeout(1000);assert p.evaluate('BaselineAuth.currentUser()') is None;b.close()
    print(json.dumps({'genuine_firebase_sdk':'10.13.0','demo_project':'demo-training-browser','persistent_reload_same_uid':True,'unverified_training_refused':True,'signout_persists':True,'verified_training_end_to_end':False,'production_access':False}))
   finally:
    if server:server.shutdown()
    if proc.poll() is None:
     os.killpg(proc.pid,signal.SIGTERM)
     try:proc.wait(timeout=8)
     except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
if __name__=='__main__':run()
