from pathlib import Path
import importlib.util,threading,http.server,json,hashlib,urllib.request
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[2];P=R;OUT=P/'design-preview'
checks=[]
def ck(name,condition,detail=None): checks.append({'name':name,'passed':bool(condition),'detail':detail})
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_GET(self):
  if self.path!='/dashboard-preview.html':self.send_error(404);return
  data=(OUT/'dashboard-preview.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);t=threading.Thread(target=server.serve_forever,daemon=True);t.start();url='http://127.0.0.1:'+str(server.server_port)+'/dashboard-preview.html'
try:
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path='/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome',args=['--no-sandbox'])
  for width in [320,390,1280]:
   c=b.new_context(viewport={'width':width,'height':900},service_workers='block');pg=c.new_page();requests=[];errs=[]
   c.route('**/*',lambda r:r.continue_() if r.request.url==url else r.abort());pg.on('request',lambda r:requests.append(r.url));pg.on('pageerror',lambda e:errs.append(str(e)))
   pg.goto(url,wait_until='load');pg.locator('#useDemo').click();pg.add_script_tag(content=(R/'tools/lane-c-tests/axe.min.js').read_text())
   ck(str(width)+' preview warning','PREVIEW ONLY' in pg.locator('body').inner_text())
   ck(str(width)+' three cards',pg.locator('#stats .stat').count()==3)
   ck(str(width)+' actual source read','this is not real data' in pg.locator('#srcNote').inner_text())
   ck(str(width)+' source period per card',pg.locator('#stats .s').evaluate_all('(els)=>els.every(e=>e.textContent.includes("source period"))'))
   ck(str(width)+' no nonstatic requests',requests==[url],requests)
   # Independent planted CSS defect proves the geometry checker is not a source-only assertion.
   pg.evaluate('document.body.insertAdjacentHTML("beforeend",\'<div id="qa-planted" style="width:2000px">QA ONLY</div>\')')
   ck(str(width)+' geometry detects planted defect',pg.evaluate('document.documentElement.scrollWidth>document.documentElement.clientWidth'))
   pg.locator('#qa-planted').evaluate('(e)=>e.remove()')
   ck(str(width)+' geometry restored',pg.evaluate('document.documentElement.scrollWidth===document.documentElement.clientWidth'))
   if width<900:pg.locator('.rmenu').click()
   pg.locator('[data-i18n-toggle] button[data-lang="ne"]').click()
   ck(str(width)+' Nepali state',pg.locator('html').get_attribute('lang')=='ne')
   ck(str(width)+' honest English fallback',pg.locator('#mtnote').get_attribute('data-mt')=='partial')
   ax=pg.evaluate('''async()=>{let r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}});return r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))}''')
   ck(str(width)+' Nepali axe',not ax,ax)
   pg.screenshot(path=str(OUT/('preview-'+str(width)+'-ne.png')),full_page=True)
   pg.locator('[data-i18n-toggle] button[data-lang="en"]').click()
   pg.evaluate('document.body.setAttribute("tabindex","-1");document.body.focus();document.body.removeAttribute("tabindex")');pg.keyboard.press('Tab')
   ck(str(width)+' skip link first',pg.evaluate('document.activeElement.classList.contains("a11y-skip")'))
   pg.keyboard.press('Enter');ck(str(width)+' skip main',pg.evaluate('document.activeElement.id')=='main')
   if width<900 and pg.locator('.rail').evaluate('(e)=>e.classList.contains("menu-open")'):pg.locator('.rmenu').click()
   # Real Tab sequence into report controls. Ensure no fixed overlay covers focused controls.
   overlaps=[];focus=[]
   for _ in range(35):
    pg.keyboard.press('Tab')
    val=pg.evaluate('''(()=>{let e=document.activeElement,r=e.getBoundingClientRect();let overlays=[...document.querySelectorAll('body *')].filter(x=>x!==e&&getComputedStyle(x).position==='fixed'&&x.getClientRects().length);return {id:e.id,tag:e.tagName,text:e.textContent.slice(0,40),outline:getComputedStyle(e).outlineStyle,overlaps:overlays.filter(x=>{if(x.contains(e)||e===document.body||e===document.documentElement)return false;let a=x.getBoundingClientRect();let cx=(Math.max(0,r.left)+Math.min(innerWidth,r.right))/2,cy=(Math.max(0,r.top)+Math.min(innerHeight,r.bottom))/2;let top=document.elementFromPoint(cx,cy);return a.bottom>r.top&&a.top<r.bottom&&a.right>r.left&&a.left<r.right&&top&&!e.contains(top)&&x.contains(top)}).map(x=>x.id||x.className)}})()''')
    focus.append(val)
    if val['overlaps']:overlaps.append(val)
   ck(str(width)+' keyboard no covering overlays',not overlaps,overlaps)
   (OUT/('keyboard-'+str(width)+'.json')).write_text(json.dumps(focus,indent=2)+'\n')
   ck(str(width)+' page errors',not errs,errs)
   c.close()
  b.close()
finally:
 server.shutdown();server.server_close();t.join(timeout=5)
 ck('listener cleanup',not t.is_alive())
 result={'checks':checks,'passed':sum(x['passed'] for x in checks),'failed':sum(not x['passed'] for x in checks),'preview_sha256':hashlib.sha256((OUT/'dashboard-preview.html').read_bytes()).hexdigest(),'cleanup':not t.is_alive()}
 (OUT/'preview-qa.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if result['failed']:raise SystemExit(1)
