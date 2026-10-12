"""Browser acceptance with explicit synthetic Auth transport. No live endpoints."""
import json,threading,http.server,functools
from pathlib import Path
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1];E=R/'landing-evidence';E.mkdir(exist_ok=True)
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
s=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(R)));threading.Thread(target=s.serve_forever,daemon=True).start();origin=f'http://127.0.0.1:{s.server_port}'
wire=json.loads((R/'tests/current-v51/native-wire.json').read_text());row={'id':'fixture-01','document_path':'mhpss5wsReportsV2/fixture-01','kind':'activity','schema':wire['schema'],'operational_schema':'mhpss-5ws-operational/2-candidate','revision':2,'event_id':'637d2988-ac87-4b6e-bbd3-da835b38a642','request_sha256':'a'*64,'payload':wire,'created_at':'2026-10-11T04:00:00Z','updated_at':'2026-10-11T04:00:00Z'}
checks=[];errors=[];requests=[]
def check(n,v):checks.append({'name':n,'pass':bool(v)});assert v,n
stub="""(()=>{let u={uid:'fixture-only',email:'fixture@example.invalid',emailVerified:true,getIdToken:async()=> 'fixture-only'},f=[];window.BaselineAuth={currentUser:()=>u,token:async()=> 'fixture-only',onChange:x=>{f.push(x);x(u,{ready:true,restoration:'signed-in',linkPending:false});},signOut:async()=>{u=null;f.forEach(x=>x(null,{ready:true,restoration:'signed-out',linkPending:false}));},sendLink:async()=>{},finishLink:async()=>{}}})();"""
with sync_playwright() as p:
 b=p.chromium.launch(headless=True)
 for width in [390,1280]:
  for role,sections in [('field',[]),('manager',['5ws']),('coordinator',['5ws','gbv']),('partner',['5ws']),('admin',['5ws'])]:
   state={'protocol':'staff-account/1','status':'active','role':role,'scope':{'org':wire['org'],'cluster':None},'sections':sections,'profile':None,'reportingAccess':True}
   c=b.new_context(viewport={'width':width,'height':900});page=c.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
   page.route('**/review-current-v51/current-auth.js',lambda r:r.fulfill(body=stub,content_type='text/javascript'))
   def api(r):
    path=r.request.url.split('.app')[-1];requests.append({'path':path,'method':r.request.method,'headers':r.request.headers})
    data=state if path=='/account/profile' else {'protocol':'staff-entries/1','complete':True,'rows':[{'id':'entry-fixture','form':'5ws','enteredAt':'2026-10-11T04:00:00Z','updatedAt':'2026-10-11T04:00:00Z','status':'received','revision':2}]} if path=='/account/entries' else {'protocol':'staff-dashboard/1','section':'5ws','rows':[row],'complete':True,'scope':state['scope']} if path=='/dashboard/5ws' else {'protocol':'staff-admin-entries/1','rows':[],'complete':True}
    r.fulfill(json=data,headers={'Cache-Control':'no-store'})
   page.route('https://mhpss5ws-tdp3xtfnsq-as.a.run.app/**',api)
   page.goto(origin+'/?view=login');page.wait_for_selector('#entries:not([hidden])' if role=='field' else '#dashboard:not([hidden])')
   if role=='field':
    page.locator('[data-period="all"]').click();page.wait_for_selector('#entryRows tr');check(f'{width} field own history', 'entry-fixture' in page.locator('#entryRows').inner_text());check(f'{width} no manager nav',page.locator('#dashNav button').count()==0)
   else:
    page.wait_for_function("document.getElementById('dashboardStatus').textContent.startsWith('Complete authorized')")
    page.wait_for_function("document.getElementById('dashboardFrame').contentDocument?.getElementById('stats')?.textContent.includes('Confirmed reports')")
    if role=='manager':print('CHART GEOMETRY',page.locator('#dashboardFrame').evaluate("f=>[...f.contentDocument.querySelectorAll('#analysis-primary>*,#ovcols>*')].map(x=>({cls:x.className,display:getComputedStyle(x).display,rect:x.getBoundingClientRect().toJSON()}))"))
    check(f'{width} {role} sidebar exact',page.locator('#dashNav button').count()==len(sections));check(f'{width} {role} no shell overflow',page.locator('#dashboardFrame').evaluate('(f)=>f.contentDocument.documentElement.scrollWidth===f.contentWindow.innerWidth'))
    if role=='coordinator':
     if width==390:page.locator('#menuToggle').click()
     page.locator('#dashNav button').nth(1).click();check(f'{width} gbv not self granted','not commissioned' in page.locator('#dashOther').inner_text())
    if role=='admin':
     if width==390:page.locator('#menuToggle').click()
     page.locator('#openAdmin').click();page.wait_for_function("document.getElementById('dashboardStatus').textContent.startsWith('Complete authorized operational')")
   check(f'{width} {role} no document overflow',page.evaluate('document.documentElement.scrollWidth===innerWidth'))
   page.screenshot(path=str(E/f'{role}-{width}.png'),full_page=True)
   page.locator('[data-view="landing"]:visible').first.click();page.locator('#signOut').click();check(f'{width} {role} signout clears frame',page.locator('#dashboardFrame').get_attribute('src') is None);c.close()
 # Signed-in API refusal must stay unknown, never zeros.
 c=b.new_context();pg=c.new_page();pg.route('**/review-current-v51/current-auth.js',lambda r:r.fulfill(body=stub,content_type='text/javascript'));pg.route('https://mhpss5ws-tdp3xtfnsq-as.a.run.app/**',lambda r:r.fulfill(status=503,json={'error':'unavailable'}));pg.goto(origin+'/?view=entries');pg.wait_for_function("document.getElementById('accountNotice').textContent.includes('503')");check('503 no fake entries',pg.locator('#entryRows tr').count()==0);c.close();b.close()
s.shutdown();print('SCRIPT ERRORS',errors);check('no browser script errors',not errors);check('API no scope headers',all('x-selected-org' not in x['headers'] for x in requests));result={'fixture':True,'production_access':False,'checks':checks,'errors':errors,'requests':[{'path':x['path'],'method':x['method']}for x in requests]};(E/'accounts.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
