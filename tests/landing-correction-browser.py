"""Real Chromium, explicit synthetic Auth/API adapters. Not provider proof."""
import json,threading,http.server,functools,os
from pathlib import Path
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1];E=Path(os.environ.get('CORRECTION_EVIDENCE',R/'landing-correction-evidence'));E.mkdir(parents=True,exist_ok=True)
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,format,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(R)));threading.Thread(target=server.serve_forever,daemon=True).start();origin=f'http://127.0.0.1:{server.server_port}'
stub="""(()=>{let u={uid:'synthetic',email:'fixture@example.invalid',emailVerified:true},listeners=[];window.testIdentity=()=>{u={uid:'other',email:'other@example.invalid',emailVerified:true}};window.BaselineAuth={currentUser:()=>u,token:async()=> 'synthetic',onChange:f=>{listeners.push(f);setTimeout(()=>f(u,{ready:true,linkPending:false}),20)},sendLink:async()=>{},signOut:async()=>{u=null;listeners.forEach(f=>f(null,{ready:true,linkPending:false}))}}})();"""
wire=json.loads((R/'tests/current-v51/native-wire.json').read_text());row={'id':'fixture-01','document_path':'mhpss5wsReportsV2/fixture-01','kind':'activity','schema':wire['schema'],'operational_schema':'mhpss-5ws-operational/2-candidate','revision':2,'event_id':'637d2988-ac87-4b6e-bbd3-da835b38a642','request_sha256':'a'*64,'payload':wire,'created_at':'2026-10-11T04:00:00Z','updated_at':'2026-10-11T04:00:00Z'}
checks=[]
def check(n,v):checks.append({'name':n,'pass':bool(v)});assert v,n
with sync_playwright() as p:
 b=p.chromium.launch()
 for width in [390,1280]:
  c=b.new_context(viewport={'width':width,'height':900},locale='en-US');pg=c.new_page();errors=[];pg.on('pageerror',lambda e:errors.append(str(e)));state={'profile':None,'posts':0,'mode':'register'}
  pg.route('**/review-current-v51/current-auth.js',lambda r:r.fulfill(body=stub,content_type='text/javascript'))
  def api(r):
   path=r.request.url.split('.app')[-1]
   if path=='/account/register':
    state['posts']+=1
    if state['posts']==1:r.fulfill(status=503,json={'error':'synthetic retry'});return
    state['profile']=r.request.post_data_json;data={'protocol':'staff-registration/1','status':'pending'}
   elif path=='/account/profile':data={'protocol':'staff-account/1','status':'active' if state['mode']=='dashboard' else 'pending' if state['profile'] else 'unregistered','role':'manager' if state['mode']=='dashboard' else None,'scope':{'org':wire['org'] if state['mode']=='dashboard' else None,'cluster':None},'sections':['5ws'] if state['mode']=='dashboard' else [],'profile':state['profile'],'reportingAccess':state['mode']=='dashboard'}
   elif path=='/dashboard/5ws':
    continuation=bool(r.request.headers.get('x-listing-cursor'));second={**row,'id':'fixture-02','document_path':'mhpss5wsReportsV2/fixture-02'}
    data={'protocol':'staff-dashboard/1','section':'5ws','rows':[second if continuation else row],'complete':continuation,'nextCursor':None if continuation else 'synthetic-continuation','scope':{'org':wire['org'],'cluster':None}}
    if state.get('malformed'):data['unexpected']=True
   else:data={'protocol':'staff-entries/1','rows':[],'complete':True,'nextCursor':None}
   r.fulfill(json=data)
  pg.route('https://mhpss5ws-tdp3xtfnsq-as.a.run.app/**',api)
  pg.goto(origin+'/');pg.wait_for_selector('#i18nbar');check(f'{width} English default',pg.locator('html').get_attribute('data-lang')=='en');pg.locator('#i18nbar [data-lang=ne]').click();check(f'{width} live Nepali title','छान्नुहोस्' in pg.locator('.hero h1').inner_text());pg.locator('[data-view=register]').first.click();check(f'{width} navigation preserves language','lang=ne' in pg.url);pg.locator('#i18nbar [data-lang=en]').click()
  pg.locator('#name').fill('Synthetic');pg.locator('#email').fill('fixture@example.invalid');pg.locator('#accountRole').select_option('field');pg.locator('#organisation').select_option('OTHER');pg.locator('#otherOrganisation').fill('Synthetic other');pg.locator('#profession').select_option(index=1);pg.locator('#subcluster').select_option('other');pg.locator('#otherSubcluster').fill('Synthetic area');pg.locator('#province').select_option('Bagmati');pg.locator('#district').select_option('NUW');pg.locator('#palika').select_option(index=1);pg.locator('#service').select_option(index=1);pg.locator('#ack').check();pg.locator('#registration button[type=submit]').click();pg.wait_for_function("document.getElementById('registrationResult').textContent.includes('503')")
  check(f'{width} failure retains draft',pg.evaluate("!!localStorage.getItem('mhpss-staff-registration-draft-v1')"));pg.reload();pg.wait_for_function("document.getElementById('accountNotice').textContent.includes('awaiting confirmation')")
  check(f'{width} restored visible email',pg.locator('#email').input_value()=='fixture@example.invalid');check(f'{width} native validity restored',pg.locator('#email').evaluate('(e)=>e.validity.valid'));check(f'{width} safe retry exact optional empty base',state['posts']==2 and state['profile']['base']=='' and state['profile']['otherOrganisation']=='Synthetic other');check(f'{width} readback clears draft',pg.evaluate("localStorage.getItem('mhpss-staff-registration-draft-v1')===null"))
  state['mode']='dashboard';pg.goto(origin+'/?view=login');pg.wait_for_function("document.getElementById('dashboardStatus').textContent.startsWith('Complete authorized')");pg.wait_for_function("document.getElementById('dashboardFrame').contentDocument?.getElementById('stats')?.textContent.includes('Roster sites reached')")
  frame=pg.frame_locator('#dashboardFrame');labels=frame.locator('#stats .k').all_text_contents();check(f'{width} aggregated both pages',frame.locator('#stats .v').first.inner_text()=='2');check(f'{width} exact KPI labels',labels==['Reports loaded','Attendances','Organisations reporting','Roster sites reached','Roster sites with no report']);check(f'{width} unknown roster dash',frame.locator('#stats .v').all_text_contents()[-2:]==['—','—'])
  with pg.expect_download() as download:frame.locator('#expAll').click()
  path=download.value.path();check(f'{width} actual CSV contains report','fixture-01' in Path(path).read_text())
  pg.evaluate('testIdentity()');frame.locator('#expAll').click();check(f'{width} stale identity clears export surface',pg.locator('#dashboardStatus').inner_text()=='Account changed or read expired.');check(f'{width} no overflow',pg.evaluate('document.documentElement.scrollWidth===innerWidth'));check(f'{width} no script errors',not errors);state['malformed']=True;pg.goto(origin+'/?view=login');pg.wait_for_function("document.getElementById('dashboardStatus').textContent.includes('invalid')");check(f'{width} malformed no partial metrics',pg.locator('#dashboardFrame').evaluate("f=>f.contentDocument?.getElementById('stats')?.children.length===0"));pg.screenshot(path=str(E/f'correction-{width}.png'));c.close()
 # Browser preference and URL override independently from saved language.
 for locale,query,expected in [('ne-NP','','ne'),('ne-NP','?lang=en','en'),('en-US','?lang=ne','ne')]:
  c=b.new_context(locale=locale);pg=c.new_page();pg.route('**/review-current-v51/current-auth.js',lambda r:r.fulfill(body=stub,content_type='text/javascript'));pg.route('https://mhpss5ws-tdp3xtfnsq-as.a.run.app/**',lambda r:r.fulfill(status=503,json={}));pg.goto(origin+'/'+query);pg.wait_for_selector('#i18nbar');check(locale+query,pg.locator('html').get_attribute('data-lang')==expected);c.close()
 b.close()
server.shutdown();(E/'browser.json').write_text(json.dumps({'synthetic':True,'provider_proof':False,'checks':checks},indent=2));print(json.dumps(checks))
