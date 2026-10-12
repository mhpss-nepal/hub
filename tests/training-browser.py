"""Synthetic-only actual source journey. All outbound traffic denied; ACK fixtures labelled."""
import json,mimetypes
from pathlib import Path
from threading import Thread
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
HUB=Path(__file__).resolve().parents[1]; FORM=HUB.parent/'non5ws-integration'
AUTH="""window.BaselineAuth={u:{uid:'fixture-A',emailVerified:true,email:'fixture@example.invalid'},currentUser(){return this.u},async token(){return 'EXPLICIT-SYNTHETIC-'+this.u.uid},callbacks:[],onChange(f){this.callbacks.push(f);f(this.u,{ready:true,restoration:'signed-in'})},switch(){this.u={uid:'fixture-B',emailVerified:true};this.callbacks.forEach(f=>f(this.u,{ready:true,restoration:'signed-in'}))}};"""
class Handler(BaseHTTPRequestHandler):
 def log_message(self,format,*args):pass
 def do_GET(self):
  p=urlparse(self.path).path
  if p.endswith('current-auth.js'):data=AUTH.encode();mime='application/javascript'
  elif p.endswith('pwa.js'):data=b'/* service worker disabled in fixture */';mime='application/javascript'
  else:
   f=(HUB/p.removeprefix('/hub/')) if p.startswith('/hub/') else FORM/p.removeprefix('/form/')
   if not f.is_file():self.send_error(404);return
   data=f.read_bytes();mime=mimetypes.guess_type(f.name)[0] or 'text/plain'
  self.send_response(200);self.send_header('Content-Type',mime);self.end_headers();self.wfile.write(data)
def run():
 assert (HUB/'training.html').exists(),'actual training reader page missing'
 assert 'TrainingForm.submit' in (FORM/'training-report.html').read_text(),'accepted form not wired to training transport'
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True);c=browser.new_context(accept_downloads=True,service_workers='block');state={'offline':True,'bodies':[],'rows':[]}
  def route(r):
   if r.request.url.startswith(base):r.continue_();return
   if '/training/' not in r.request.url:r.abort();return
   if r.request.method=='POST':
    b=r.request.post_data_json;state['bodies'].append(b)
    if state['offline']:r.abort();return
    import hashlib
    sha=hashlib.sha256(json.dumps(b['payload'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    state['rows']=[dict(reportId=b['reportId'],revision=1,request_sha256=sha,subject='fixture-A',org=b['payload']['org'],createdAt='2026-10-12T00:00:00+00:00',updatedAt='2026-10-12T00:00:00+00:00',payload=b['payload'])]
    d=dict(protocol='training-receipt/1',reportId=b['reportId'],revision=1,request_sha256=sha,stored=True)
   else:
    if r.request.headers.get('authorization','').endswith('fixture-B'):
     r.fulfill(status=403,content_type='application/json',body='{"error":"fixture uncommissioned"}');return
    rows=json.loads(json.dumps(state['rows']))
    if r.request.url.endswith('/current'):
     for row in rows:
      for k in ['focal_name','focal_phone','note','_saved']:row['payload'].pop(k,None)
    d=dict(protocol='training-list/1',rows=rows,complete=True,nextCursor=None)
   r.fulfill(status=200,content_type='application/json',body=json.dumps(d))
  c.route('**/*',route);p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(base+'/form/training-report.html?lang=en')
  p.evaluate("""()=>{const ev=e=>{e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));};document.querySelectorAll('#f select').forEach(e=>{const o=[...e.options].find(o=>o.value&&!['OTHER','OTH'].includes(o.value));if(o){e.value=o.value;ev(e)}});document.querySelectorAll('#f input[type=text],#f input[type=tel],#f textarea').forEach(e=>{e.value=e.type==='tel'?'0000000000':'SYNTHETIC ONLY';ev(e)});document.querySelectorAll('#f input[type=number]').forEach(e=>{e.value='1';ev(e)});document.querySelector('#dateAD').value='2026-10-01';}""")
  p.evaluate("()=>L1.save('training',{kind:'training',title:'LEGACY SYNTHETIC PRESERVE ONLY'})");legacy=p.evaluate("JSON.stringify(L1.all('training'))")
  p.fill('#u18','');p.fill('#pwd','0');p.locator('#f button[type=submit]').click();p.wait_for_function("document.querySelector('#trainingStatus').textContent.includes('retained')")
  assert p.evaluate("JSON.stringify(L1.all('training'))")==legacy,'legacy records must remain byte-equivalent and never auto-upload'
  queued=p.evaluate("TrainingForm.api.outbox()");assert len(queued)==1 and queued[0]['receipt'] is None
  assert p.input_value('#title')=='SYNTHETIC ONLY';state['offline']=False;p.locator('#trainingRetry').click();p.wait_for_function("document.querySelector('#trainingStatus').textContent.includes('Received')")
  assert state['bodies'][0]==state['bodies'][1]
  p.set_viewport_size({'width':390,'height':844});assert p.evaluate('document.documentElement.scrollWidth <= innerWidth')
  p.goto(base+'/hub/training.html?view=own');p.wait_for_function("document.querySelector('#trainingReadStatus').textContent.includes('Complete')");assert p.locator('#trainingRows').inner_text().find('SYNTHETIC ONLY')>=0
  p.goto(base+'/hub/training.html?view=current');p.wait_for_function("document.querySelector('#trainingReadStatus').textContent.includes('Complete')");assert p.locator('#trainingTotals').inner_text().find('3 people trained')>=0
  with p.expect_download() as dl:p.locator('#trainingExport').click()
  import csv,io
  text=Path(dl.value.path()).read_text();record=next(csv.DictReader(io.StringIO(text)));assert json.loads(record['participants'])[0]['female']==1;assert 'focal_phone' not in record
  p.evaluate('BaselineAuth.switch()');assert p.locator('#trainingExport').is_disabled();assert p.locator('#trainingRows').inner_text()==''
  # Reload the actual form and recover its account-scoped draft, without resubmission.
  p.goto(base+'/form/training-report.html?lang=en');p.wait_for_function("window.TrainingForm && typeof window.TrainingForm.restoreDraft === 'function'")
  p.locator('#trainingRestore').click();assert p.input_value('#title')=='SYNTHETIC ONLY'
  assert len(state['bodies'])==2,'restoring a draft must never auto-upload it'
  draft_before=p.evaluate("localStorage.getItem('mhpss-training-draft-v1:fixture-A')");p.locator('#trainingRestore').click();assert p.evaluate("localStorage.getItem('mhpss-training-draft-v1:fixture-A')")==draft_before
  p.goto(base+'/hub/index.html');p.wait_for_selector('a[href="training.html?view=current"]');assert p.locator('#main a[href="training.html?view=current"]').count()==1;assert p.locator('#formList a[href="../form/training-report.html"]').count()==1
  p.evaluate('BaselineAuth.switch()');assert p.locator('#main a[href="training.html?view=current"]').count()==0
  assert not errors,errors
  result={'fixture':'EXPLICIT SYNTHETIC Auth/HTTP ONLY — NOT provider proof','form_to_queue_exact_retry_receipt_own_history_processed_csv':True,'account_switch_private_clear':True,'legacy_not_written':True,'page_errors':errors}
  print(json.dumps(result));browser.close()
 server.shutdown()
if __name__=='__main__':run()
