"""Labelled HTTP fixture: actual Form DOM -> transport -> Hub history/current -> CSV. No provider claim."""
import contextlib, csv, hashlib, io, json, threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
FORM=ROOT.parent/'claude-final-form'
FIXTURE=ROOT.parents[2]/'48-historical-analytics/backend/tests/fixtures/activity-browser.json'
# resolve source fixture independently of repository alias layout
FIXTURE=Path('/root/mhpss-nepal-final-forms/2026-10-06/48-historical-analytics/backend/tests/fixtures/activity-browser.json')
records={}; requests=[]; mode={'value':'ok'}
AUTH="""(()=>{let u={uid:'synthetic-a',emailVerified:true,email:'synthetic@example.invalid'},listeners=[];window.BaselineAuth={currentUser:()=>u,token:async()=>'fixture-token',onChange:f=>{listeners.push(f);f(u,{ready:true,restoration:'ready'});return ()=>{};},signOut:async()=>{u=null;listeners.forEach(f=>f(u,{}));}};})();"""
class Handler(SimpleHTTPRequestHandler):
 def log_message(self,format,*a):pass
 def do_GET(self):
  path=self.path.split('?')[0]
  if path.startswith('/form/'):
   self.path='/'+path[6:];self.directory=str(FORM)
  elif path.startswith('/hub/'):
   self.path='/'+path[5:];self.directory=str(ROOT)
  else:self.send_error(404);return
  if self.path=='/review-current-v51/current-auth.js':
   self.send_response(200);self.send_header('Content-Type','application/javascript');self.end_headers();self.wfile.write(AUTH.encode());return
  super().do_GET()
def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start();base='http://127.0.0.1:'+str(server.server_port)
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True);ctx=browser.new_context(service_workers='block',accept_downloads=True);page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)+' '+str(e.stack)))
   def route(r):
    req=r.request;path=req.url.split('.run.app')[-1]
    if '.run.app' not in req.url:
     if req.url.startswith(base):r.continue_()
     else:r.abort()
     return
    if path=='/profile':
     # Actual STAFF_API profile contract handled separately; fixture avoid guessing it, use data from source-aware below.
     r.fulfill(status=503,body='{}');return
    if path=='/activity/intake':
     body=json.loads(req.post_data);requests.append(req.post_data);p=body['payload'];h=hashlib.sha256(json.dumps(p,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
     receipt={'protocol':'activity-receipt/1','reportId':body['reportId'],'revision':body['revision'],'request_sha256':h,'stored':True}
     records[body['reportId']]={'reportId':body['reportId'],'revision':body['revision'],'request_sha256':h,'subject':'synthetic-a','org':p['org'],'createdAt':'2026-10-13T01:00:00Z','updatedAt':'2026-10-13T01:00:00Z','payload':p}
     if mode['value']=='lost':mode['value']='ok';r.abort();return
     r.fulfill(status=200,content_type='application/json',body=json.dumps(receipt));return
    if path in ['/activity/entries','/activity/current']:
     rows=json.loads(json.dumps(list(records.values())))
     if path.endswith('/current'):
      for row in rows:
       for k in ['focalName','focalPhone','focalEmail','description','id','createdAt','revision','schemaVersion','revisedAt']:
        row['payload'].pop(k,None)
     r.fulfill(status=200,content_type='application/json',body=json.dumps({'protocol':'activity-list/1','rows':rows,'complete':True,'nextCursor':None}));return
    r.fulfill(status=503,body='{}')
   ctx.route('**/*',route)
   page.goto(base+'/form/5ws-report.html?lang=en');page.wait_for_function('window.ActivityForm && window.ActivityCollector',timeout=5000)
   fixture=json.loads(FIXTURE.read_text());fixture={k:v for k,v in fixture.items() if k not in ['id','createdAt','revision','schemaVersion','kind','schema']}
   page.evaluate('(p)=>ActivityCollector.restore(p)',fixture)
   collected=page.evaluate('ActivityCollector.collect()');assert collected['activities'][0]['cells']==fixture['activities'][0]['cells'];assert not page.evaluate('STORE.validate(ActivityCollector.collect())'),page.evaluate('STORE.validate(ActivityCollector.collect())')
   mode['value']='lost';page.locator('button[type=submit][form=f]').click();page.wait_for_function("document.getElementById('activityStatus').textContent.includes('retained; no receipt assumed')")
   assert len(records)==1;first=requests[0];assert page.evaluate('ActivityForm.api.outbox()[0].receipt') is None
   page.locator('#activityRetry').click();page.wait_for_function("document.getElementById('activityStatus').textContent.includes('Verified server received')");assert requests[1]==first
   # Correction follows verified Retry ACK directly; no forced history reopen.
   page.locator('#newToday').fill('5');page.locator('#activityStatus').click();page.locator('button[type=submit][form=f]').click();page.wait_for_function("document.getElementById('activityStatus').textContent.includes('revision 2')");assert list(records.values())[0]['revision']==2;assert json.loads(requests[-1])['predecessor']['revision']==1;assert json.loads(requests[-1])['predecessor']['request_sha256']==hashlib.sha256(json.dumps(json.loads(first)['payload'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
   page.goto(base+'/hub/?view=entries');page.wait_for_function("document.getElementById('activityRows') && document.getElementById('activityRows').textContent.includes('Verified server received')")
   assert 'r2' in page.locator('#activityRows').inner_text()
   page.goto(base+'/hub/?view=dashboard&house=5ws');page.wait_for_function("document.getElementById('activityReadStatus') && document.getElementById('activityReadStatus').textContent.includes('Complete authorised')")
   assert 'Under18' in page.locator('#activityJoint').inner_text();assert '2' in page.locator('#activityJoint').inner_text()
   with page.expect_download() as dl:page.locator('#activityExport').click()
   download=dl.value;data=Path(download.path()).read_text(encoding='utf-8-sig');rows=list(csv.DictReader(io.StringIO(data)));assert len(rows)==1;assert rows[0]['fLow']=='2';assert rows[0]['mLow']=='3';assert rows[0]['fHigh']=='5';assert rows[0]['oHigh']=='1';assert rows[0]['foldBoundary']=='18';assert rows[0]['serverRevision']=='2';assert json.loads(rows[0]['sourcePayload'])['activities']==fixture['activities']
   assert not errors,errors
   print(json.dumps({'fixture':'labelled HTTP ACK fixture; not genuine provider','actualDOM':True,'ackLossExactRetry':True,'verifiedCorrectionRevision2':True,'actualHubOwnHistory':True,'actualHubProcessedCSV':True,'fold':[rows[0][k] for k in ['fLow','mLow','oLow','fHigh','mHigh','oHigh']],'requests':len(requests),'pageErrors':errors}))
   browser.close()
 finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
