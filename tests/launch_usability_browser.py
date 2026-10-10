"""Launch acceptance at the actual existing entry. Synthetic SDK/API, no provider proof."""
from pathlib import Path
import ast, json, threading, http.server, sys, hashlib
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1]; W=R.parent
sys.path[:0]=[str(W/'backend/tests'),str(W/'backend/functions'),str(W/'backend/tools')]
from test_baseline import Backend, call
E=Path(sys.argv[1]); E.mkdir(parents=True,exist_ok=True)
constants={}
for n in ast.parse((R/'tests/automatic_baseline_browser.py').read_text()).body:
 if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant):
  for t in n.targets:
   if isinstance(t,ast.Name):constants[t.id]=n.value.value
APP=constants['APP']; AUTH=constants['AUTH'].replace('currentUser:u','currentUser:localStorage.getItem("fixture-session")?u:null').replace('window.QA.auth(true)}','window.QA.auth(true);return {user:u}}').replace('export const sendSignInLinkToEmail=async()=>{}','export const sendSignInLinkToEmail=async()=>{window.QA.sdk.push("sendLink")}')
POISON=constants['POISON']; body=call(Backend(),headers={'Origin':'https://mhpss-nepal.github.io'}).data
class H(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**k):super().__init__(*a,directory=str(R),**k)
 def log_message(self,*a):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),H);threading.Thread(target=server.serve_forever,daemon=True).start(); origin=f'http://127.0.0.1:{server.server_port}'
report={'synthetic_only':True,'source_sha256':hashlib.sha256((R/'index.html').read_bytes()).hexdigest(),'checks':[],'states':[]}
def check(v,name):report['checks'].append({'name':name,'pass':bool(v)})
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=str(next(Path('/root/.cache/ms-playwright').glob('**/chrome'))),args=['--no-sandbox'])
  for width in [320,390,1280]:
   for signedin in [False,True]:
    ctx=browser.new_context(viewport={'width':width,'height':844},service_workers='block',accept_downloads=True,reduced_motion='reduce');requests=[];errors=[]
    ctx.add_init_script('window.QA={sdk:[],forbidden:[],requests:[]};localStorage.setItem("mhpss-np-queue-v1",'+json.dumps(POISON)+');'+('localStorage.setItem("fixture-session","yes");' if signedin else ''))
    def route(rt):
     u=urlsplit(rt.request.url)
     if u.netloc=='www.gstatic.com' and u.path.endswith('firebase-app.js'):rt.fulfill(body=APP,content_type='text/javascript')
     elif u.netloc=='www.gstatic.com' and u.path.endswith('firebase-auth.js'):rt.fulfill(body=AUTH,content_type='text/javascript')
     elif u.netloc=='mhpss5ws-tdp3xtfnsq-as.a.run.app':
      requests.append({'method':rt.request.method,'path':u.path});rt.fulfill(status=200,body=body,content_type='application/json')
     elif u.netloc==urlsplit(origin).netloc:rt.continue_()
     else:rt.abort()
    ctx.route('**/*',route);pg=ctx.new_page();pg.on('pageerror',lambda e:errors.append(str(e)));pg.goto(origin+'/index.html',wait_until='networkidle')
    name=f'{width} '+('returning' if signedin else 'signedout');state={'name':name}
    pg.screenshot(path=str(E/(name.replace(' ','-')+'-arrival.png')))
    state['targets']=pg.locator('button,input,select,summary,a').evaluate_all('(es)=>es.filter(e=>e.getClientRects().length).map(e=>{let r=e.getBoundingClientRect();return {id:e.id,text:e.textContent.trim().slice(0,60),width:r.width,height:r.height}})')
    check(all(t['height']>=44 and t['width']>=44 for t in state['targets'] if t['text']!='Skip to dashboard'),name+' visible touch targets')
    state['contrast']=pg.locator('h1,.top .sub,#historical-status,#historical-stats .v').evaluate_all('(es)=>es.map(e=>{let c=getComputedStyle(e);return {text:e.textContent,color:c.color,background:c.backgroundColor}})')
    pg.keyboard.press('Tab');check(pg.locator('.skip').evaluate('(e)=>e===document.activeElement'),name+' skip link first keyboard stop')
    check(not pg.locator('#useDemo').is_visible(),name+' source chooser secondary')
    check(not pg.locator('#historical-clear').is_visible(),name+' clear secondary')
    check(not pg.locator('#historical-password').is_visible(),name+' password secondary')
    if signedin:
     pg.wait_for_function('document.querySelectorAll("#historical-stats .v").length===5')
     boxes=pg.locator('#historical-stats .v').evaluate_all('(es)=>es.map(e=>{let r=e.getBoundingClientRect();return {top:r.top,bottom:r.bottom,text:e.textContent}})');state['values']=boxes
     check(all(x['top']>=0 and x['bottom']<=844 for x in boxes),name+' all five KPI values above fold')
     check(pg.locator('#historical-export').is_visible() and pg.locator('#historical-refresh').is_visible(),name+' refresh CSV available')
     check(not pg.locator('#historical-signout').is_visible(),name+' signout in account menu')
     with pg.expect_download() as dl:pg.locator('#historical-export').click()
     check('historical-master-v1,2,7,1,1,' in Path(dl.value.path()).read_text(encoding='utf-8-sig'),name+' CSV snapshot parity')
     pg.reload(wait_until='networkidle');pg.wait_for_function('document.querySelectorAll("#historical-stats .v").length===5');check(pg.locator('#historical-login').is_hidden(),name+' reload automatic fixture session')
    else:
     check(pg.locator('#historical-signin').inner_text()=='Send sign-in link',name+' email primary')
     check(not pg.locator('#historical-refresh').is_visible() and not pg.locator('#historical-signout').is_visible(),name+' signed-in actions absent')
     box=pg.locator('#historical-signin').bounding_box();state['primary']=box;check(box['y']+box['height']<=844,name+' primary above fold')
     pg.locator('#historical-email').fill('fixture@example.invalid');pg.locator('#historical-signin').click();pg.wait_for_timeout(80)
     check(pg.evaluate('QA.sdk.includes("sendLink")'),name+' primary actually requests link')
     check(not requests,name+' signedout zero reads')
    check(pg.evaluate('document.documentElement.scrollWidth===document.documentElement.clientWidth'),name+' no root overflow')
    check(pg.evaluate('localStorage.getItem("mhpss-np-queue-v1")')==POISON,name+' queue bytes unchanged')
    pg.add_script_tag(path=str(R/'design-preview/source/axe.min.js'));state['axe']=pg.evaluate('async()=>{let r=await axe.run(document,{runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag21a","wcag21aa"]}});return {violations:r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)})),incomplete:r.incomplete.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))}}');check(not state['axe']['violations'],name+' axe')
    pg.screenshot(path=str(E/(name.replace(' ','-')+'.png')));pg.screenshot(path=str(E/(name.replace(' ','-')+'-full.png')),full_page=True)
    state['navigation']=[]
    for group in ['forms','public']:
     trigger=pg.locator('.rg[data-g='+group+']>.rgh');trigger.click();box=pg.locator('.rg[data-g='+group+']>.rgb').bounding_box();state['navigation'].append({'group':group,'rect':box})
     check(box['x']>=0 and box['x']+box['width']<=width,name+' '+group+' menu in viewport')
     pg.keyboard.press('Escape');check(trigger.evaluate('(e)=>e===document.activeElement'),name+' '+group+' escape focus')
    check(not errors,name+' no page errors');report['states'].append(state);ctx.close()
  browser.close()
finally:
 server.shutdown();server.server_close();report['passes']=sum(x['pass'] for x in report['checks']);report['count']=len(report['checks']);report['failures']=[x for x in report['checks'] if not x['pass']];(E/'RESULT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if report['failures']:sys.exit(1)
