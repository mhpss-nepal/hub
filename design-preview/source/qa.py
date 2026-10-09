from pathlib import Path
import json,threading,http.server,functools,subprocess,hashlib,sys,urllib.request
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent; R=ROOT/'hub'; E=R/'design-preview'; E.mkdir(exist_ok=True)
BASE='180a64e8ccb077e26d0905adffa320e107ffb45f'
BASE_BYTES=subprocess.check_output(['git','show',BASE+':index.html'],cwd=R)
assert BASE_BYTES==(ROOT/'baseline.html').read_bytes()
PIN=hashlib.sha256((R/'index.html').read_bytes()).hexdigest()
axe=ROOT/'axe.min.js'
if not axe.exists():axe.write_bytes(urllib.request.urlopen('https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.3/axe.min.js').read())
# Exact static assets, bounded server fixture. No directory listings or data.
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_GET(self):
  p=self.path.split('?')[0]
  if p=='/nonce':b=b'B38-dashboard-only'
  elif p in ['/index.html','/base.html']:b=(R/'index.html').read_bytes() if p=='/index.html' else (ROOT/'baseline.html').read_bytes()
  elif p.startswith('/assets/') and p.count('/')==2 and (R/p[1:]).is_file():b=(R/p[1:]).read_bytes()
  else:self.send_error(404);return
  self.send_response(200);self.send_header('Content-Type','text/html' if p.endswith('html') else 'text/css' if p.endswith('css') else 'text/javascript');self.end_headers();self.wfile.write(b)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start();origin='http://127.0.0.1:'+str(server.server_port)
assert urllib.request.urlopen(origin+'/nonce').read()==b'B38-dashboard-only'
report={'origin':origin,'base':BASE,'candidate_index_sha256':PIN,'runs':[],'parity':{},'network':'All non-fixture requests blocked; Firebase bridge replaced at request boundary, no remote read/write.'}
MOCK="""window.QA={reads:[],writes:[],callbacks:[]}; window.FB={status:()=>({configured:false,ready:false,user:null,pending:0}),onStatus:f=>{QA.callbacks.push(f);f(FB.status())},myRole:()=>Promise.resolve(null),watchKind:(k,ok,err)=>{QA.reads.push(k);QA.ok=ok;QA.err=err},readPublic:()=>Promise.reject(Error('QA blocked')),publish:()=>{QA.writes.push('publish');throw Error('QA blocked')}};"""
geometry="""() => {const visible=e=>!!e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden';let w=innerWidth;return {root:[document.documentElement.scrollWidth,document.documentElement.clientWidth],overflow:[...document.querySelectorAll('body *')].filter(e=>visible(e)&&!e.closest('.tbl-wrap')&&!e.closest('.skip')&&e.getBoundingClientRect().width>0&&(e.getBoundingClientRect().right>w+1||e.getBoundingClientRect().left < -1)).map(e=>({tag:e.tagName,id:e.id,cls:e.className,rect:e.getBoundingClientRect().toJSON()})).slice(0,15),small:[...document.querySelectorAll('button,a,input,select,textarea,summary')].filter(visible).map(e=>{let x=e.type==='checkbox'?e.closest('label')||e:e;let r=x.getBoundingClientRect();return {id:e.id,text:e.textContent.slice(0,35),w:r.width,h:r.height}}).filter(x=>x.w<43.9||x.h<43.9)}}"""
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=str(next(Path('/root/.cache/ms-playwright').glob('**/chrome'))),args=['--no-sandbox'])
  for base in [True,False]:
   for width in ([320] if base else [320,390,1280]):
    ctx=browser.new_context(viewport={'width':width,'height':900},timezone_id='Asia/Kathmandu',reduced_motion='reduce')
    blocked=[]
    def route(rt):
     u=rt.request.url
     if u==origin+'/assets/fb.js':rt.fulfill(body=MOCK,content_type='text/javascript')
     elif urlsplit(u).scheme==urlsplit(origin).scheme and urlsplit(u).netloc==urlsplit(origin).netloc and rt.request.method=='GET':rt.continue_()
     else:blocked.append(u);rt.abort()
    ctx.route('**/*',route);page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    response=page.goto(origin+('/base.html' if base else '/index.html')+'?source=choose',wait_until='load')
    assert hashlib.sha256(response.body()).hexdigest()==(hashlib.sha256(BASE_BYTES).hexdigest() if base else PIN)
    initial_storage=page.evaluate('JSON.stringify(localStorage)')
    page.locator('#useDemo').click();page.wait_for_timeout(100)
    run={'base':base,'width':width,'errors':errors,'overview':page.evaluate(geometry)}
    page.add_script_tag(path=str(axe))
    def axecheck():
     a=page.evaluate("async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})")
     return [{'id':v['id'],'impact':v['impact'],'nodes':[n['target'] for n in v['nodes']]} for v in a['violations']]
    run['axeStates']={'overview':axecheck()}
    run['initialLanguage']=page.evaluate('I18N.lang()')
    run['initialStorage']=initial_storage
    if not base:page.screenshot(path=str(E/f'desktop-{width}.png'),full_page=True)
    before=page.evaluate('JSON.stringify(localStorage)')
    snap={}
    for sel in ['stats','covBody','dupBody','pxBody','actBody','disBody','dayWrap','rawBody']:
     snap[sel]=page.locator('#'+sel).text_content()
    page.locator('#filters > summary').click()
    page.select_option('#fOrg',index=1);snap['filteredStats']=page.locator('#stats').text_content();snap['filterSummary']=page.locator('#fSum').text_content()
    page.locator('#fClear').click()
    # Export through real existing handlers, capturing only synthetic downloads.
    page.evaluate('window.QAexports=[];STORE.download=(n,t,m)=>QAexports.push({n,t,m})')
    page.locator('.tab[data-p=raw]').click();page.locator('#expAll').click();snap['csv']=page.evaluate('QAexports[0].t')
    run['reports']=page.evaluate(geometry)
    run['axeStates']['reports']=axecheck()
    page.locator('#rawFind').fill('D0-0');snap['find']=page.locator('#rawBody').text_content()
    page.locator('#rawFind').fill('')
    page.locator('.tab[data-p=who]').click();page.locator('#expMx').click();snap['matrixCSV']=page.evaluate('QAexports[1].t')
    run['matrix']=page.evaluate(geometry)
    run['axeStates']['matrix']=axecheck()
    page.locator('.tab[data-p=act]').click();run['activities']=page.evaluate(geometry);run['axeStates']['activities']=axecheck()
    page.locator('.tab[data-p=ov]').click()
    for d in page.locator('.analysis-detail').all():d.locator('summary').first.click()
    run['expanded']=page.evaluate(geometry)
    run['axe']=axecheck();run['axeStates']['expanded']=run['axe']
    run['storageBeforeLanguage']=page.evaluate('JSON.stringify(localStorage)')
    # Actual language click journey; unkeyed Hub remains English as its baseline states.
    run['toggleButtons']=page.locator('#i18nbar button').all_text_contents()
    page.locator('#i18nbar button').filter(has_text='ने').first.click() if page.locator('#i18nbar button').filter(has_text='ने').count() else page.locator('#i18nbar button').last.click()
    run['lang']=page.evaluate('I18N.lang()');run['neGeometry']=page.evaluate(geometry);run['axeStates']['ne']=axecheck()
    page.evaluate("I18N.setLang('en')")
    # Only existing language-choice key may change.
    after=page.evaluate('JSON.stringify(localStorage)');run['storageBefore']=before;run['storageAfter']=after;run['remoteWrites']=page.evaluate('QA.writes')
    if not base:
     page.screenshot(path=str(E/f'expanded-{width}.png'),full_page=True)
     report['parity'][str(width)]={k:snap[k]==reference[k] for k in snap}
    else:reference=snap
    run['blockedRequestCount']=len(blocked)
    report['runs'].append(run);ctx.close()
  browser.close()
finally:server.shutdown();server.server_close()
(E/'qa-report.json').write_text(json.dumps(report,indent=2))
for r in report['runs']:print('BASE' if r['base'] else 'HEAD',r['width'],'errors',r['errors'],'axe',r['axe'],'geometries',{k:r[k] for k in ['overview','reports','matrix','expanded']})
print('PARITY',report['parity'])
