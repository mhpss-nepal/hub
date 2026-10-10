"""W40 actual DOM regression. Static-only narrow fixture; no cloud records."""
from pathlib import Path
import json,threading,http.server,subprocess,hashlib,sys,secrets
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1]
BASE='71cd85c3794c1e558d159feb94f32b7f5b78fee0'
E=Path(sys.argv[1]);E.mkdir(parents=True,exist_ok=False)
LIVE=sys.argv[2] if len(sys.argv)>2 else None
old=subprocess.check_output(['git','show',BASE+':index.html'],cwd=R)
assets={('/'+str(p.relative_to(R))):p.read_bytes() for p in (R/'assets').iterdir() if p.is_file() and p.suffix in {'.js','.css','.svg','.png','.woff2'}}
assets.update({'/':(R/'index.html').read_bytes(),'/index.html':(R/'index.html').read_bytes(),'/base.html':old})
nonce=secrets.token_hex(16).encode();assets['/nonce']=nonce
class H(http.server.BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_GET(self):
  path=urlsplit(self.path).path
  if path not in assets:self.send_error(404);return
  b=assets[path];self.send_response(200);self.send_header('Content-Type','text/html' if path=='/' or path.endswith('html') else 'text/css' if path.endswith('css') else 'text/javascript');self.end_headers();self.wfile.write(b)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),H)
threading.Thread(target=server.serve_forever,daemon=True).start()
origin=f'http://127.0.0.1:{server.server_port}'
MOCK="""window.QA={reads:[],writes:[]};window.FB={status:()=>({configured:false,ready:false,user:null,pending:0}),onStatus:f=>f(FB.status()),myRole:()=>Promise.resolve(null),watchKind:(k,ok,err)=>{QA.reads.push(k)},publish:()=>{QA.writes.push('publish');throw Error('blocked')}};"""
report={'base':BASE,'head_index_sha256':hashlib.sha256(assets['/index.html']).hexdigest(),'runs':[],'checks':[],'production_data':False}
def check(value,label):
 report['checks'].append({'name':label,'pass':bool(value)})
 assert value,label
try:
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path=str(next(Path('/root/.cache/ms-playwright').glob('**/chrome'))),args=['--no-sandbox'])
  for width in [320,390,1280,1748]:
   c=b.new_context(viewport={'width':width,'height':1022},service_workers='block',reduced_motion='reduce');errors=[];blocked=[]
   def route(rt):
    u=urlsplit(rt.request.url);o=urlsplit(LIVE or origin)
    path=u.path.removeprefix('/hub') if LIVE else u.path
    if rt.request.method=='GET' and u.scheme==o.scheme and u.netloc==o.netloc and path=='/assets/fb.js':rt.fulfill(body=MOCK,content_type='text/javascript')
    elif rt.request.method=='GET' and u.scheme==o.scheme and u.netloc==o.netloc and path in assets:rt.continue_()
    else:blocked.append(rt.request.url);rt.abort()
   c.route('**/*',route);pg=c.new_page();pg.on('pageerror',lambda e:errors.append(str(e)))
   if not LIVE:check(c.request.get(origin+'/nonce').body()==nonce,f'{width} exact fixture nonce')
   url=LIVE or origin+'/index.html?source=choose'
   res=pg.goto(url,wait_until='load');check(hashlib.sha256(res.body()).hexdigest()==report['head_index_sha256'],f'{width} served pin')
   check(pg.locator('#useDemo').is_visible() and pg.locator('#app').is_hidden(),f'{width} signed-out first screen retained')
   pg.screenshot(path=str(E/f'entry-{width}.png'))
   forms=pg.locator('.rg[data-g=forms]>.rgh');public=pg.locator('.rg[data-g=public]>.rgh')
   state=lambda:pg.evaluate("()=>[...document.querySelectorAll('.rg.open:not([data-g=coord])')].map(e=>e.dataset.g)")
   forms.click();public.click();check(state()==['public'],f'{width} exclusive click')
   check(forms.get_attribute('aria-expanded')=='false' and public.get_attribute('aria-expanded')=='true',f'{width} truthful aria')
   pg.keyboard.press('Escape');check(state()==[],f'{width} escape closes');check(public.evaluate('(e)=>e===document.activeElement'),f'{width} escape focus')
   forms.focus();pg.keyboard.press('Enter');check(state()==['forms'],f'{width} keyboard Enter')
   pg.keyboard.press('Tab');check(pg.locator('.rg[data-g=forms] .rgb>a').first.evaluate('(e)=>e===document.activeElement'),f'{width} Tab enters links')
   pg.keyboard.press('Escape');check(forms.evaluate('(e)=>e===document.activeElement'),f'{width} link escape focus')
   pg.keyboard.press('Space');check(state()==['forms'],f'{width} Space opens')
   pg.locator('h1').click();check(state()==[],f'{width} outside closes')
   check(pg.locator('h1').evaluate('(e)=>e!==document.activeElement'),f'{width} no forced outside focus')
   forms.click();pg.locator('.rg[data-g=forms] .rgb>a').first.click();pg.wait_for_load_state('load');check(state()==[],f'{width} selection closes')
   check(urlsplit(pg.url).fragment=='reports',f'{width} navigation retained')
   check(pg.locator('.rg[data-g=coord] a[href="./#reports"]').get_attribute('aria-current')=='page',f'{width} route highlight')
   pg.evaluate("localStorage.setItem('mhpss-rail-groups',JSON.stringify({forms:true,public:true,coord:false,admin:true}));localStorage.setItem('w40-pending-sentinel','UNCHANGED');localStorage.setItem('mhpss-lang','en')")
   pg.reload(wait_until='load');check(state()==[],f'{width} legacy state closed after reload')
   check(pg.locator('.rg[data-g=coord] .rgb').is_visible(),f'{width} coordination remains visible')
   check(pg.evaluate("localStorage.getItem('w40-pending-sentinel')")=='UNCHANGED',f'{width} unrelated storage preserved')
   check(pg.evaluate("localStorage.getItem('mhpss-lang')")=='en',f'{width} language untouched')
   for trigger in [forms,public]:
    trigger.click();rect=pg.locator('.rg.open:not([data-g=coord]) .rgb').bounding_box()
    check(rect['x']>=-1 and rect['x']+rect['width']<=width+1,f'{width} popup viewport')
    check(pg.evaluate('document.documentElement.scrollWidth===document.documentElement.clientWidth'),f'{width} root no overflow')
    check(len(state())==1,f'{width} no popup intersection')
    check(trigger.bounding_box()['height']>=44,f'{width} touch target')
    pg.add_script_tag(path=str(R/'design-preview/source/axe.min.js'))
    violations=pg.evaluate("async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})).violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)}))")
    check(violations==[],f'{width} open popup axe')
    report.setdefault('geometry',[]).append({'width':width,'open':state(),'rect':rect,'axe':violations})
    pg.screenshot(path=str(E/f'menu-{width}-{state()[0]}.png'))
    pg.keyboard.press('Escape')
   # Actual same-snapshot/filter/row/CSV comparison to fresh W39 base.
   snapshots=[]
   for target in ([url] if LIVE else [origin+'/base.html?source=choose',url]):
    pg.goto(target,wait_until='load');pg.locator('#useDemo').click()
    pg.select_option('#fOrg',index=1)
    snap={sel:pg.locator('#'+sel).text_content() for sel in ['stats','rawBody','covBody','actBody','fSum']}
    pg.evaluate('()=>{window.QAexports=[];STORE.download=(n,t,m)=>QAexports.push({n,t,m});}')
    pg.locator('.tab[data-p=raw]').click();pg.locator('#expAll').click();check(pg.evaluate('QAexports.length===1 && typeof QAexports[0].t === "string"'),f'{width} genuine CSV');snap['csv']=pg.evaluate('QAexports[0].t');snapshots.append(snap)
   if not LIVE:check(snapshots[0]==snapshots[1],f'{width} same filtered rows summaries CSV')
   check(pg.evaluate('QA.writes.length===0 && QA.reads.length===0'),f'{width} no backend reads/writes')
   check(errors==[],f'{width} no page errors')
   report['runs'].append({'width':width,'blocked':blocked,'errors':errors,'csv_sha256':hashlib.sha256(snapshots[-1]['csv'].encode()).hexdigest()})
   c.close()
  b.close()
finally:
 server.shutdown();server.server_close();report['listener_closed']=True
 (E/'RESULT.json').write_text(json.dumps(report,indent=2));print(json.dumps({'checks':len(report['checks']),'passes':sum(x['pass'] for x in report['checks']),'evidence':str(E)},indent=2))
