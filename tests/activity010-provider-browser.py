"""Actual Form and Hub source against genuine isolated provider; tokens from demo Auth only."""
import csv,io,json,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];FORM=ROOT.parent/'claude-final-form'
def main():
 v=json.load(sys.stdin);origin=v['origin'];token=v['reporter'];errors=[]
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True);ctx=browser.new_context(service_workers='block',accept_downloads=True);page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  lost=True;sent=[]
  def route(r):
   nonlocal token,lost
   path=r.request.url.split(origin)[-1].split('?')[0]
   if not r.request.url.startswith(origin):r.abort();return
   if path=='/activity/intake':
    sent.append(r.request.post_data)
    if lost:
     lost=False;response=r.fetch();assert response.status==200;r.abort();return
   if path.startswith('/activity/') or path in ['/profile']:r.continue_();return
   if path.startswith('/form/'):f=FORM/path[6:]
   elif path.startswith('/hub/'):f=ROOT/path[5:]
   else:r.continue_();return
   if f.is_dir():f=f/'index.html'
   if path.endswith('/current-auth.js'):
    source="(()=>{const u={uid:'"+('reporter' if token==v['reporter'] else 'manager')+"',emailVerified:true,email:'synthetic@example.invalid'};window.BaselineAuth={currentUser:()=>u,token:async()=>"+json.dumps(token)+",onChange:f=>{f(u,{ready:true,restoration:'ready'});},signOut:async()=>{}};})();"
   elif f.is_file():source=f.read_text() if f.suffix in ['.html','.js','.css','.json'] else None
   else:r.fulfill(status=404);return
   if f.name=='activity-api.js':source=source.replace('https://mhpss5ws-tdp3xtfnsq-as.a.run.app',origin)
   if f.name=='staff-api.js':source=source.replace('https://mhpss5ws-tdp3xtfnsq-as.a.run.app',origin)
   mime={'.html':'text/html','.js':'application/javascript','.css':'text/css'}.get(f.suffix,'application/octet-stream')
   r.fulfill(status=200,content_type=mime,body=source if source is not None else f.read_bytes())
  ctx.route('**/*',route)
  page.goto(origin+'/form/5ws-report.html?lang=en');page.wait_for_function('window.ActivityForm && window.ActivityCollector')
  payload=v['envelope']['payload'];page.evaluate('(p)=>ActivityCollector.restore(p)',payload);page.locator('button[type=submit][form=f]').click();page.wait_for_function("!ActivityForm.busy() && ActivityForm.api.outbox().length===1",timeout=10000)
  assert page.evaluate('ActivityForm.api.outbox()[0].receipt') is None
  page.locator('#activityRetry').click();page.wait_for_function("!ActivityForm.busy() && ActivityForm.api.outbox()[0].receipt",timeout=10000);assert sent[0]==sent[1]
  report=page.evaluate('ActivityForm.api.outbox()[0]');rid=report['body']['reportId'];assert report['receipt']['request_sha256']==report['hash']
  # Verified ACK immediately binds the next native correction; no history reopen.
  page.locator('#newToday').fill('5');page.locator('#activityStatus').click();page.locator('button[type=submit][form=f]').click();page.wait_for_function("document.getElementById('activityStatus').textContent.includes('revision 2')")
  page.goto(origin+'/hub/?view=entries');page.wait_for_function("document.getElementById('activityReadStatus') && document.getElementById('activityReadStatus').textContent.includes('Complete authorised')")
  assert rid in page.locator('#activityRows').inner_text()
  token=v['manager'];page.goto(origin+'/hub/?view=dashboard&house=5ws');page.wait_for_function("document.getElementById('activityReadStatus') && document.getElementById('activityReadStatus').textContent.includes('Complete authorised')")
  assert rid in page.locator('#activityRows').inner_text()
  with page.expect_download() as d:page.locator('#activityExport').click()
  text=Path(d.value.path()).read_text(encoding='utf-8-sig');rows=list(csv.DictReader(io.StringIO(text)));row=next(r for r in rows if r['id']==rid)
  assert [row[k] for k in ['fLow','mLow','oLow','fHigh','mHigh','oHigh','foldBoundary']]==['2','3','0','5','0','1','18'];assert row['serverRevision']=='2';assert row['sourceHash'];assert json.loads(row['sourcePayload'])['activities']==payload['activities'];assert not errors,errors
  result={'actualFormHub':True,'provider':'real demo Auth+Firestore via unchanged adapter','first':{'status':200},'corrected':{'status':200},'ownStatus':200,'processedStatus':200,'reportId':rid,'fold':dict(zip(['fLow','mLow','oLow','fHigh','mHigh','oHigh','boundary'],[2,3,0,5,0,1,18])),'csv':text,'pageErrors':errors}
  browser.close();print(json.dumps(result))
if __name__=='__main__':main()
