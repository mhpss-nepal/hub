from pathlib import Path
import json,threading,http.server,subprocess,hashlib,sys,os
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
E=Path(__file__).resolve().parent; R=E.parent
BASE='b02e14a73edc7c0061bdeeaab652c66dd7224883'
BASE_BYTES=subprocess.check_output(['git','show',BASE+':index.html'],cwd=R)
assert BASE_BYTES==(E/'baseline.html').read_bytes()
E=Path(os.environ.get('REF4_OUTPUT',str(E)));E.mkdir(parents=True,exist_ok=True)
PIN=hashlib.sha256((R/'index.html').read_bytes()).hexdigest()
MOCK="""window.QA={reads:[],writes:[],callbacks:[],st:{configured:true,ready:true,user:null,pending:0,online:true}}; window.FB={status:()=>QA.st,onStatus:f=>{QA.callbacks.push(f);f(FB.status())},myRole:()=>Promise.resolve(null),watchKind:(k,ok,err)=>{QA.reads.push(k);QA.ok=ok;QA.err=err;setTimeout(()=>err('permission-denied: synthetic test'),0)},readPublic:()=>Promise.reject(Error('QA blocked')),publish:()=>{QA.writes.push('publish');throw Error('QA blocked')},signIn:()=>{QA.writes.push('signIn');return Promise.reject(Error('QA blocked'))}};
document.addEventListener('DOMContentLoaded',()=>{let bar=document.createElement('div');bar.id='fbbar';bar.innerHTML='<span class="m"><b>Connected.</b> Records reach coordination as you save them.</span>';document.body.prepend(bar);QA.emit=(cls,text)=>{bar.className=cls;bar.innerHTML='<span class="m"></span>';bar.firstChild.textContent=text;QA.callbacks.forEach(f=>f(QA.st))};});"""
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_GET(self):
  p=self.path.split('?')[0]
  if p in ['/','/index.html','/base.html','/mutant.html']:
   b=BASE_BYTES if p=='/base.html' else (R/'index.html').read_bytes()
   if p=='/mutant.html':b=b.replace(b'</head>',b'<style>body.hub.dashboard-selected{padding-left:250px!important}</style></head>')
  elif p.startswith('/assets/') and p.count('/')==2 and (R/p[1:]).is_file():b=(R/p[1:]).read_bytes()
  else:self.send_error(404);return
  self.send_response(200);self.send_header('Content-Type','text/css' if p.endswith('css') else 'text/javascript' if p.endswith('js') else 'text/html');self.end_headers();self.wfile.write(b)
geometry="""() => {const vis=e=>!!e.getClientRects().length;return {root:[document.documentElement.scrollWidth,document.documentElement.clientWidth],left:parseFloat(getComputedStyle(document.body).paddingLeft),shell:document.querySelector('#entry-shell')?.getBoundingClientRect().toJSON(),accessOpen:!!document.querySelector('#access-options')?.open,kpis:[...document.querySelectorAll('#entry-shell .stat .v')].map(e=>e.textContent),reads:QA.reads,writes:QA.writes,appHidden:document.querySelector('#app').hidden,connectedClaim:document.body.innerText.includes('Records reach coordination as you save them')}}"""
def firstscreen(g):
 return {'no_sidebar':g['left']==0,'shell_visible':bool(g['shell']) and g['shell']['height']>0,'access_collapsed':not g['accessOpen'],'unknown_kpis':len(g['kpis'])==5 and set(g['kpis'])=={'—'},'no_data':g['appHidden'],'no_implicit_read':not g['reads'],'no_write':not g['writes'],'no_delivery_claim':not g['connectedClaim'],'no_overflow':g['root'][0]<=g['root'][1]}
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start();origin='http://127.0.0.1:'+str(server.server_port)
report={'base':BASE,'candidate_index_sha256':PIN,'origin':origin,'firstscreen':[],'runs':[],'parity':{},'network':'All non-local requests blocked. fb.js replaced only at request boundary. Synthetic input only.'}
red='--red' in sys.argv
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=str(next(Path('/root/.cache/ms-playwright').glob('**/chrome'))),args=['--no-sandbox'])
  def context(width,auth=False):
   ctx=browser.new_context(viewport={'width':width,'height':900},timezone_id='Asia/Kathmandu',reduced_motion='reduce');blocked=[]
   def route(rt):
    u=rt.request.url
    if u==origin+'/assets/fb.js':rt.fulfill(body=MOCK.replace('user:null','user:{email:"synthetic@example.invalid"}') if auth else MOCK,content_type='text/javascript')
    elif urlsplit(u).netloc==urlsplit(origin).netloc and rt.request.method=='GET':rt.continue_()
    else:blocked.append(u);rt.abort()
   ctx.route('**/*',route);return ctx,blocked
  for path in ['/','/index.html?source=choose&design=20261010']:
   for width in ([1280] if red else [320,390,1280]):
    ctx,blocked=context(width);p=ctx.new_page();resp=p.goto(origin+path,wait_until='load');assert hashlib.sha256(resp.body()).hexdigest()==PIN;p.wait_for_timeout(200)
    g=p.evaluate(geometry);checks=firstscreen(g)
    if width==1280:checks['analysis_in_firstscreen']=bool(g['shell']) and p.locator('#entry-shell .primary-grid').bounding_box()['y']<650
    item={'route':path,'width':width,'geometry':g,'checks':checks,'overflow':p.evaluate("()=>[...document.querySelectorAll('body *')].filter(e=>e.getClientRects().length && (e.getBoundingClientRect().right>innerWidth+1 || e.getBoundingClientRect().left < -1)).map(e=>({id:e.id,tag:e.tagName,cls:e.className,text:e.textContent.slice(0,80),rect:e.getBoundingClientRect().toJSON()})).slice(0,20)")};report['firstscreen'].append(item)
    p.screenshot(path=str(E/(('red' if red else 'signedout')+('-root' if path=='/' else '-exact')+f'-{width}.png')),full_page=True)
    if not red:
     p.add_script_tag(path=str(R/'design-preview/source/axe.min.js'));item['axe']=p.evaluate("async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})).violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))")
     p.locator('#access-options summary').focus();p.keyboard.press('Enter');item['keyboardAccessOpen']=p.locator('#access-options').evaluate('(e)=>e.open');p.keyboard.press('Enter');item['keyboardAccessClosed']=not p.locator('#access-options').evaluate('(e)=>e.open')
     p.evaluate("QA.emit('warn','Not connected to the database. Retrying. TEST WARNING')");p.wait_for_timeout(50);item['warningPreserved']='TEST WARNING' in p.locator('#fbbar').inner_text()
     p.evaluate("QA.emit('warn','3 record(s) still to send. TEST PENDING')");p.wait_for_timeout(50);item['pendingPreserved']='TEST PENDING' in p.locator('#fbbar').inner_text()
     p.evaluate("QA.emit('stop','TEST ERROR: permission denied')");p.wait_for_timeout(50);item['errorPreserved']='TEST ERROR' in p.locator('#fbbar').inner_text()
    if not red:
     p.locator('#useDemo').click();p.wait_for_timeout(50);item['explicitDemoLoaded']=p.locator('#stats').inner_text().startswith('63');item['shellHiddenAfterDemo']=p.locator('#entry-shell').is_hidden();item['noRemoteWriteAfterDemo']=not p.evaluate('QA.writes')
    ctx.close()
  if not red:
   report['authJourneys']=[]
   for auth in [False,True]:
    ctx,_=context(1280,auth);p=ctx.new_page();p.goto(origin+'/');p.wait_for_timeout(100)
    journey={'signedIn':auth,'initialReads':p.evaluate('QA.reads')}
    if not auth:
     p.locator('#access-options > summary').click();p.locator('#useLive').click();p.wait_for_timeout(100);journey['explicitRead']=p.evaluate('QA.reads');journey['refusalVisible']='register' in p.locator('#livePanel').inner_text().lower()
    journey['accessOpen']=p.locator('#access-options').evaluate('(e)=>e.open');journey['livePanelVisible']=p.locator('#livePanel').is_visible()
    p.screenshot(path=str(E/('access-signedin.png' if auth else 'access-signedout.png')),full_page=True)
    report['authJourneys'].append(journey);ctx.close()
   ctx,_=context(1280);p=ctx.new_page();p.goto(origin+'/mutant.html?source=choose');p.wait_for_timeout(100);report['mutation']={'checks':firstscreen(p.evaluate(geometry))};report['mutation']['killed']=not all(report['mutation']['checks'].values());ctx.close()
   # Reuse exercised legacy parity journeys, exact new base and three widths.
   for base in [True,False]:
    for width in ([320] if base else [320,390,1280]):
     ctx,blocked=context(width);p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));resp=p.goto(origin+('/base.html' if base else '/index.html')+'?source=choose&design=20261010',wait_until='load')
     assert hashlib.sha256(resp.body()).hexdigest()==(hashlib.sha256(BASE_BYTES).hexdigest() if base else PIN)
     before=p.evaluate('JSON.stringify(localStorage)');p.locator('#useDemo').click();p.wait_for_timeout(100);p.add_script_tag(path=str(R/'design-preview/source/axe.min.js'))
     def axecheck():return p.evaluate("async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})).violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))")
     def geo():return p.evaluate("()=>({scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth})")
     run={'base':base,'width':width,'errors':errors,'axe':{'overview':axecheck()},'geometry':{'overview':geo()},'storageBefore':before}
     if not base:p.screenshot(path=str(E/f'demo-{width}.png'),full_page=True)
     snap={sel:p.locator('#'+sel).text_content() for sel in ['stats','covBody','dupBody','pxBody','actBody','disBody','dayWrap','rawBody','ovWho','ovWhat','ovWhom','ovFam','ovMod','ovSadd','ovPal','ovStatus']}
     if not p.locator('#filters').evaluate('(e)=>e.open'):p.locator('#filters > summary').click()
     p.select_option('#fOrg',index=1);snap['filteredStats']=p.locator('#stats').text_content();snap['filterSummary']=p.locator('#fSum').text_content();snap['filteredRows']=p.locator('#rawBody').text_content();p.locator('#fClear').click()
     if p.locator('.filter-more').count():p.locator('.filter-more > summary').click()
     p.select_option('#fPeriod','custom');p.fill('#fFrom','2026-09-04');p.fill('#fTo','2026-09-08');p.locator('#fTo').dispatch_event('change');snap['periodStats']=p.locator('#stats').text_content();snap['periodRows']=p.locator('#rawBody').text_content();p.locator('#fClear').click()
     p.evaluate('()=>{window.QAexports=[];STORE.download=(n,t,m)=>QAexports.push({n,t,m});}');p.locator('.tab[data-p=raw]').click();p.locator('#expAll').click();snap['csv']=p.evaluate('QAexports[0].t');run['axe']['reports']=axecheck();run['geometry']['reports']=geo()
     p.locator('#rawFind').fill('D0-0');snap['find']=p.locator('#rawBody').text_content();p.locator('#rawFind').fill('')
     if not isinstance(snap['csv'],str):
      print('EXPORT DEBUG',base,width,p.evaluate('QAexports'),errors,flush=True)
      raise AssertionError('CSV must be an actual string, not null')
     p.locator('#file2').set_input_files({'name':'synthetic-roundtrip.csv','mimeType':'text/csv','buffer':snap['csv'].encode()});p.wait_for_timeout(50)
     snap['importStats']=p.locator('#stats').text_content();snap['importRows']=p.locator('#rawBody').text_content();snap['importDaily']=p.locator('#dayWrap').text_content()
     p.locator('.tab[data-p=who]').click();p.locator('#expMx').click();snap['matrixCSV']=p.evaluate('QAexports[1].t');run['axe']['matrix']=axecheck();run['geometry']['matrix']=geo()
     p.locator('.tab[data-p=act]').click();run['axe']['activities']=axecheck();p.locator('.tab[data-p=ov]').click()
     for d in p.locator('.analysis-detail').all():
      if not d.evaluate('(e)=>e.open'):d.locator('summary').first.click()
     run['axe']['expanded']=axecheck();run['geometry']['expanded']=geo()
     if not base:
      run['primaryOrder']=p.evaluate("()=>{let ids=['filters','stats','analysis-primary','ovcols','ovWhere'];return ids.map(id=>({id,y:document.getElementById(id).getBoundingClientRect().top+scrollY}))}")
      run['inputLabels']=p.evaluate("()=>[...document.querySelectorAll('input,select,textarea')].filter(e=>e.getClientRects().length && e.type!=='hidden').map(e=>({id:e.id,hasLabel:!!(e.labels?.length||e.getAttribute('aria-label'))}))")
     p.locator('#i18nbar button').last.click();run['lang']=p.evaluate('I18N.lang()');run['axe']['ne']=axecheck();p.evaluate("I18N.setLang('en')");run['storageAfter']=p.evaluate('JSON.stringify(localStorage)');run['remoteWrites']=p.evaluate('QA.writes');run['reads']=p.evaluate('QA.reads');run['blockedRequestCount']=len(blocked)
     if not base:
      report['parity'][str(width)]={k:snap[k]==reference[k] for k in snap};p.screenshot(path=str(E/f'expanded-{width}.png'),full_page=True)
     else:reference=snap
     run['snapshotProof']={k:{'sha256':hashlib.sha256(v.encode()).hexdigest(),'characters':len(v)} for k,v in snap.items()}
     assert isinstance(snap['matrixCSV'],str) and 'organisation,district,palika' in snap['matrixCSV']
     assert isinstance(snap['csv'],str) and 'D0-0' in snap['csv']
     report['runs'].append(run);ctx.close()
  browser.close()
finally:server.shutdown();server.server_close()
name='red-report.json' if red else 'qa-report.json';(E/name).write_text(json.dumps(report,indent=2))
print(json.dumps({'report':str(E/name),'firstscreen':report['firstscreen'],'parity':report['parity'],'runs':report['runs'],'mutation':report.get('mutation')},indent=2))
if red:assert any(not all(r['checks'].values()) for r in report['firstscreen'])
