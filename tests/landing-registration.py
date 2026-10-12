"""Profile durability/resume fixtures. Auth is explicit test adapter, no email sent."""
import json,threading,http.server,functools
from pathlib import Path
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1]
s=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(R)));threading.Thread(target=s.serve_forever,daemon=True).start();origin=f'http://127.0.0.1:{s.server_port}'
checks=[]
def check(n,v):checks.append({'name':n,'pass':bool(v)});assert v,n
stub="""(()=>{const u={uid:'fixture-only',email:'fixture@example.invalid',emailVerified:true,getIdToken:async()=> 'fixture-only'};window.BaselineAuth={currentUser:()=>u,token:async()=> 'fixture-only',onChange:f=>setTimeout(()=>f(u,{ready:true,restoration:'signed-in',linkPending:false}),50),sendLink:async()=>{},signOut:async()=>{}}})();"""
with sync_playwright() as p:
 b=p.chromium.launch(headless=True);c=b.new_context(viewport={'width':390,'height':900});page=c.new_page();saved=[];profile=None
 def api(route):
  global profile
  path=route.request.url.split('.app')[-1]
  if path=='/account/register':
   profile=route.request.post_data_json;saved.append(profile);data={'protocol':'staff-registration/1','status':'pending'}
  elif path=='/account/entries':data={'protocol':'staff-entries/1','rows':[],'complete':True}
  else:data={'protocol':'staff-account/1','status':'pending' if profile else 'unregistered','role':None,'scope':{'org':None,'cluster':None},'sections':[],'profile':profile,'reportingAccess':False}
  route.fulfill(json=data)
 page.route('**/review-current-v51/current-auth.js',lambda r:r.fulfill(body=stub,content_type='text/javascript'));page.route('https://mhpss5ws-tdp3xtfnsq-as.a.run.app/**',api)
 page.goto(origin+'/?view=register');page.wait_for_function("document.getElementById('accountNotice').textContent.includes('No staff profile')")
 page.locator('#name').fill('Synthetic Staff');page.locator('#email').fill('fixture@example.invalid');page.locator('#accountRole').select_option('manager');page.locator('#organisation').select_option('TPO');page.locator('#profession').select_option(index=1);page.locator('#subcluster').select_option('mhpss');page.locator('#province').select_option('Bagmati');page.locator('#district').select_option('NUW');page.locator('#palika').select_option(index=1);page.locator('#service').select_option(index=1);page.locator('#ack').check();page.locator('#registration button[type=submit]').click();page.wait_for_function("document.getElementById('accountNotice').textContent.includes('awaiting confirmation')")
 check('durable registration invoked once',len(saved)==1);check('exact profile fields no role authority',set(saved[0])=={'name','organisation','profession','subcluster','province','district','palika','base','service','requestedRole'});check('draft cleared only after profile readback',page.evaluate("localStorage.getItem('mhpss-staff-registration-draft-v1')===null"));check('manager request no dashboard grant',page.locator('#dashNav button').count()==0)
 # Resume is bound to verified email; another browser account must not upsert.
 draft={'saved':0,'email':'different@example.invalid','profile':saved[0]};page.evaluate("d=>{d.saved=Date.now();localStorage.setItem('mhpss-staff-registration-draft-v1',JSON.stringify(d));}",draft);page.goto(origin+'/?view=register');page.wait_for_function("document.getElementById('accountNotice').textContent.includes('another email')");check('other email draft does not register',len(saved)==1)
 page.screenshot(path=str(R/'landing-evidence/registration-390.png'),full_page=True)
 c.close();b.close()
s.shutdown();(R/'landing-evidence/registration.json').write_text(json.dumps({'fixture':True,'production_access':False,'checks':checks},indent=2));print(json.dumps(checks))
