"""Lane-C canonical-source browser QA. Synthetic only; exact-origin HTTP fixture; all other requests refused."""
from pathlib import Path
import os,json,hashlib,subprocess,threading,http.server,functools,time,urllib.request,uuid
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]; REPO=ROOT; OUT=REPO/'design-preview'; OUT.mkdir(exist_ok=True)
BASE='1775af56d9be12e2f76d8d9a4e45631f6933cd58'
ASSETS=['app.css','design.css','hub-shell.css','codes.js','store.js','fb-config.js','fb.js','mark.js','icons.js','i18n-strings.js','i18n.js']
AXE=ROOT/'tools/lane-c-tests/axe.min.js'
if not AXE.exists(): AXE.write_bytes(urllib.request.urlopen('https://cdn.jsdelivr.net/npm/axe-core@4.10.3/axe.min.js',timeout=30).read())
NONCE=uuid.uuid4().hex
FB_STUB='''window.__FB_CALLS=[];window.FB={status:function(){return {configured:true,ready:true,user:null}},onStatus:function(cb){setTimeout(()=>cb(window.FB.status()),0);return ()=>{}},watchKind:function(kind,cb,err){window.__FB_CALLS.push({method:'watchKind',kind});setTimeout(()=>cb(window.__SYNTHETIC_ROWS||[]),0)},myRole:function(){return Promise.resolve(null)},readPublic:function(){return Promise.resolve(null)},publish:function(){throw Error('Preview: publishing disabled')},signIn:function(){return Promise.reject(Error('Preview: account operations disabled'))}};'''
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*a): pass
 def do_GET(self):
  path=urlparse(self.path).path
  if path=='/__nonce': data=NONCE.encode(); mime='text/plain'
  elif path in ['/base/index.html','/head/index.html']:
   data=subprocess.check_output(['git','show',BASE+':index.html'],cwd=REPO) if path.startswith('/base') else (REPO/'index.html').read_bytes(); mime='text/html'
  elif path in ['/base/assets/fb.js','/head/assets/fb.js']: data=FB_STUB.encode();mime='application/javascript'
  elif path.startswith(('/base/assets/','/head/assets/')) and path.split('/')[-1] in ASSETS+['dashboard-task.css']:
   name=path.split('/')[-1]; data=(REPO/'assets'/name).read_bytes();mime='text/css' if name.endswith('.css') else 'application/javascript'
  else: self.send_error(404);return
  self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
FIXTURE_JS='''(()=>{let sites=CODES.ROSTER_SITES;let a=sites[0];let b=sites.find(s=>s.district!==a.district)||sites[1];return [a,a,b].map((s,i)=>({id:'QA-SYNTHETIC-'+i,kind:'activity',createdAt:'2026-10-0'+(i+1)+'T06:00:00Z',dateAD:'2026-10-0'+(i+1),district:s.district,site:s.code,org:i<2?'TPO':'CMC',donor:'UNICEF',activity:i<2?'3.1':'2.2',modality:'COM',status:'CMP',targetGroups:['TG-COM'],reachedTotal:30,countBasis:'CONTACTS',fU18:10,mU18:5,f18:10,m18:5,schemaVersion:'5ws-np-0.2.0',description:'SYNTHETIC TEST ONLY'}))})()'''
GEOMETRY='''(()=>{let w=innerWidth;let visible=e=>!!(e.getClientRects().length)&&getComputedStyle(e).visibility!=='hidden';let interactive=[...document.querySelectorAll('button,a,input,select,textarea,summary')].filter(visible).map(e=>{let target=e.matches('input[type=checkbox],input[type=radio]')?(e.closest('label')||e):e;let r=target.getBoundingClientRect();return {tag:e.tagName,id:e.id,text:(e.textContent||e.getAttribute('aria-label')||'').trim().slice(0,70),width:r.width,height:r.height}});let overflow=[...document.querySelectorAll('body *')].filter(e=>visible(e)&&!e.closest('.tbl-wrap,pre')&&e.tagName!=='SCRIPT'&&e.tagName!=='STYLE').map(e=>{let r=e.getBoundingClientRect();return {tag:e.tagName,id:e.id,cls:e.className,left:r.left,right:r.right,width:r.width}}).filter(r=>r.left < -1 || r.right>w+1);return {width:w,rootScroll:document.documentElement.scrollWidth,rootClient:document.documentElement.clientWidth,overflow,smallTargets:interactive.filter(x=>x.width<43.9||x.height<43.9),interactive}})()'''
def digest(data): return hashlib.sha256(data).hexdigest()
def export(pg,id):
 if not pg.locator('#'+id).is_visible(): pg.locator('.tab[data-p="raw"]').click()
 with pg.expect_download() as ev: pg.locator('#'+id).click()
 return Path(ev.value.path()).read_bytes()
def run():
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);t=threading.Thread(target=server.serve_forever,daemon=True);t.start();origin='http://127.0.0.1:'+str(server.server_port)
 assert urllib.request.urlopen(origin+'/__nonce').read().decode()==NONCE
 report={'base':BASE,'index_sha256':digest((REPO/'index.html').read_bytes()),'axe_sha256':digest(AXE.read_bytes()),'origin':origin,'scenarios':[],'blocked_requests':[],'checks':[],'errors':[],'cleanup':False}
 def check(name,condition,detail=None): report['checks'].append({'name':name,'passed':bool(condition),'detail':detail})
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(executable_path='/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome',headless=True,args=['--no-sandbox'])
   for variant in ['base','head']:
    for width in [320,390,1280]:
     ctx=browser.new_context(viewport={'width':width,'height':900},locale='en-GB',service_workers='block',accept_downloads=True)
     def route(r):
      u=urlparse(r.request.url)
      if (u.scheme,u.netloc)==('http',urlparse(origin).netloc): r.continue_()
      else: report['blocked_requests'].append(r.request.url);r.abort()
     ctx.route('**/*',route)
     pg=ctx.new_page();errors=[];pg.on('pageerror',lambda e:errors.append(str(e)))
     pg.goto(origin+'/'+variant+'/index.html?source=choose&lang=en',wait_until='load')
     pg.wait_for_timeout(100)
     pg.add_script_tag(content=AXE.read_text())
     rows=pg.evaluate(FIXTURE_JS)
     pg.locator('#file').set_input_files({'name':'SYNTHETIC-TEST.json','mimeType':'application/json','buffer':json.dumps(rows).encode()})
     pg.wait_for_timeout(100)
     # Export must retain exact existing selection/CSV contract, not a reconstructed model.
     pg.evaluate('window.STORE.stamp=()=>"QA-FIXED"')
     full=export(pg,'expAll'); check(variant+str(width)+' CSV 3 rows',len(full.splitlines())==4,digest(full))
     inventory=pg.evaluate('''[...document.querySelectorAll('input,select,textarea,button')].map(e=>[e.tagName,e.type,e.id,e.name,e.getAttribute('data-dim'),e.getAttribute('data-p')]).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)))''')
     counters=pg.evaluate('''Object.fromEntries(['ovWho','ovWhat','ovWhom','ovWhereNums','covBody','offBody','dupBody','disBody','dayWrap','rawBody','mxBody','actBody','pxBody'].map(x=>[x,document.getElementById(x).textContent]))''')
     (OUT/(variant+'-'+str(width)+'-full.csv')).write_bytes(full)
     (OUT/(variant+'-'+str(width)+'-contract.json')).write_text(json.dumps({'controls':inventory,'counters':counters},indent=2)+'\n')
     # Every unchanged counter/table and CSV compared later across base/head.
     org_value=pg.locator('#fOrg option').evaluate_all('(els)=>els.find(e=>e.value && e.textContent.includes("TPO")).value')
     for key,value in [('fDist',rows[0]['district']),('fOrg',org_value),('fFrom','2026-10-02')]:
      loc=pg.locator('#'+key)
      if variant=='base' and not loc.is_visible():pg.locator('#filters summary').click()
      if key=='fFrom':loc.fill(value);loc.dispatch_event('change')
      else:loc.select_option(value)
     filtered=export(pg,'expAll');(OUT/(variant+'-'+str(width)+'-filtered.csv')).write_bytes(filtered)
     check(variant+str(width)+' filtered 1 row',len(filtered.splitlines())==2,digest(filtered))
     pg.locator('#fClear').click()
     # Cold English -> live Nepali -> English is the reader's actual switch path.
     buttons=pg.locator('[data-i18n-toggle] button')
     lang_buttons=buttons.evaluate_all('(els)=>els.map(e=>({text:e.textContent,lang:e.getAttribute("data-lang")}))')
     print(variant,width,'language controls',lang_buttons)
     ne=pg.locator('[data-i18n-toggle] button[data-lang="ne"]');en=pg.locator('[data-i18n-toggle] button[data-lang="en"]')
     if ne.count():
      if not ne.is_visible(): pg.locator('.rmenu').click()
      ne.click()
     pg.wait_for_timeout(100)
     check(variant+str(width)+' Nepali switch',pg.locator('html').get_attribute('lang')=='ne')
     check(variant+str(width)+' CSV after language switch',export(pg,'expAll')==full)
     geom_ne=pg.evaluate(GEOMETRY)
     if en.count():en.click()
     if variant=='head':
      check('head'+str(width)+' Nepali no overflow',geom_ne['rootScroll']==geom_ne['rootClient'] and not geom_ne['overflow'],geom_ne['overflow'])
      check('head'+str(width)+' Nepali targets',not geom_ne['smallTargets'],geom_ne['smallTargets'])
      pg.evaluate('document.activeElement.blur();window.scrollTo(0,0)')
      pg.keyboard.press('Tab')
      # Reset keyboard navigation through a fresh document focus so first Tab is deterministic.
      pg.evaluate('document.body.setAttribute("tabindex","-1");document.body.focus();document.body.removeAttribute("tabindex")')
      pg.keyboard.press('Tab')
      check('head'+str(width)+' skip first',pg.evaluate('document.activeElement.classList.contains("a11y-skip")'))
      pg.keyboard.press('Enter')
      check('head'+str(width)+' skip reaches main',pg.evaluate('document.activeElement.id')=='main')
     # Primary overview and reports, advanced modules separately measured.
     if variant=='base':pg.locator('#filters').evaluate('(e)=>e.open=false')
     for section in ['overview','reports','analysis','roster','who','activities','publish']:
      pg.evaluate('window.scrollTo(0,0)')
      if section=='reports':pg.locator('.tab[data-p="raw"]').click()
      elif section=='overview':pg.locator('.tab[data-p="ov"]').click()
      elif section=='analysis' and variant=='head':pg.locator('#analysisDetails').evaluate('(e)=>e.open=true')
      elif section=='roster' and variant=='head':pg.locator('.tab[data-p="ov"]').click();pg.locator('#rosterDetails').evaluate('(e)=>e.open=true')
      elif section in ['who','activities','publish']:
       if variant=='head':pg.locator('#advancedSections').evaluate('(e)=>e.open=true')
       pg.locator('.tab[data-p="'+{'who':'who','activities':'act','publish':'pub'}[section]+'"]').click()
      if width<900 and pg.locator('.rail').evaluate('(e)=>e.classList.contains("menu-open")'):pg.locator('.rmenu').click()
      pg.evaluate('window.scrollTo(0,0)')
      geom=pg.evaluate(GEOMETRY)
      axe=pg.evaluate('''async()=>{let r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}});return {violations:r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),passes:r.passes.length,incomplete:r.incomplete.map(v=>v.id)}}''')
      if variant=='head':
       check('head'+str(width)+' '+section+' geometry',geom['rootScroll']==geom['rootClient'] and not geom['overflow'],geom['overflow'])
       check('head'+str(width)+' '+section+' targets',not geom['smallTargets'],geom['smallTargets'])
       check('head'+str(width)+' '+section+' axe',not axe['violations'],axe['violations'])
      report['scenarios'].append({'variant':variant,'width':width,'section':section,'geometry':geom,'axe':axe,'ne_geometry':geom_ne if section=='overview' else None})
      if section in ['overview','reports','analysis','roster','publish']:
       pg.screenshot(path=str(OUT/(variant+'-'+str(width)+'-'+section+'.png')),full_page=section in ['overview','reports'])
     # Process new-source reset / truthful empty register with empty synthetic read.
     pg.locator('.tab[data-p="raw"]').click();pg.locator('#reload').click();pg.locator('#useLive').click();pg.wait_for_timeout(150)
     check(variant+str(width)+' empty state',pg.locator('#emptyReg').is_visible(),pg.locator('#emptyReg').inner_text())
     if variant=='head':
      check('head'+str(width)+' honest no confirmed label','No confirmed reports' in pg.locator('#emptyReg').inner_text())
      check('head'+str(width)+' no stale primary figures in empty state',not pg.locator('#stats').is_visible())
      check('head'+str(width)+' no stale secondary figures in empty state',not pg.locator('#analysisDetails').is_visible())
      check('head'+str(width)+' no stale export in empty state',not pg.locator('#expAll').is_visible())
      pg.screenshot(path=str(OUT/(variant+'-'+str(width)+'-empty.png')),full_page=False)
      pg.locator('#emptyOff').click();pg.locator('#useDemo').click()
      check('head'+str(width)+' built-in synthetic data works','this is not real data' in pg.locator('#srcNote').inner_text())
      check('head'+str(width)+' primary card count',pg.locator('#stats .stat').count()==3)
     if variant=='base':pg.screenshot(path=str(OUT/(variant+'-'+str(width)+'-empty.png')),full_page=False)
     check(variant+str(width)+' page errors',not errors,errors)
     check(variant+str(width)+' kind-scoped read',pg.evaluate('window.__FB_CALLS')==[{'method':'watchKind','kind':'activity'}])
     check(variant+str(width)+' no storage records',pg.evaluate('localStorage.getItem("mhpss-np-4ws-v1")') is None)
     ctx.close()
   browser.close()
  for width in [320,390,1280]:
   for suffix in ['full.csv','filtered.csv','contract.json']:
    check(str(width)+' base/head '+suffix+' parity',(OUT/('base-'+str(width)+'-'+suffix)).read_bytes()==(OUT/('head-'+str(width)+'-'+suffix)).read_bytes())
 finally:
  server.shutdown();server.server_close();t.join(timeout=5);report['cleanup']=not t.is_alive()
  report['passed']=sum(c['passed'] for c in report['checks']);report['failed']=sum(not c['passed'] for c in report['checks'])
  (OUT/'browser-report.json').write_text(json.dumps(report,indent=2)+'\n')
  print('checks',report['passed'],'pass',report['failed'],'fail','cleanup',report['cleanup'])
  for sc in report['scenarios']:
   print(sc['variant'],sc['width'],sc['section'],'overflow',len(sc['geometry']['overflow']),'small',len(sc['geometry']['smallTargets']),'axe',[(v['id'],len(v['nodes'])) for v in sc['axe']['violations']])
 if report['failed']: raise SystemExit(1)
if __name__=='__main__':run()
