"""Explicit deterministic HTTP fixture; real native DOM, collector, outbox and API. No provider claim."""
import importlib.util, json, sys, threading, os, subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
spec=importlib.util.spec_from_file_location('journey',Path(__file__).with_name('activity010-browser.py'))
assert spec and spec.loader
j=importlib.util.module_from_spec(spec);spec.loader.exec_module(j)
def main():
 j.AUTH=j.AUTH.replace('signOut:async()=>', 'switchUser:()=>{u={uid:"synthetic-b",emailVerified:true};listeners.forEach(f=>f(u,{}));},signOut:async()=>')
 server=j.ThreadingHTTPServer(('127.0.0.1',0),j.Handler);threading.Thread(target=server.serve_forever,daemon=True).start();base='http://127.0.0.1:'+str(server.server_port)
 results=[]
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True)
   for case in sys.argv[1:] or ['retry-correction','revocation']:
    ctx=browser.new_context(service_workers='block',accept_downloads=True);page=ctx.new_page();errors=[];downloads=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('download',lambda d:downloads.append(d))
    records={};requests=[];state={'deny':False,'offline':False,'gets':0}
    def route(r):
     req=r.request;path=req.url.split('.run.app')[-1]
     if '.run.app' not in req.url:
      if req.url.endswith('/hub/assets/activity-surface.js'):
       source=(subprocess.check_output(['git','show','fcb868eb872f2f81a5bb521aa05b6dedd38a04f0:assets/activity-surface.js'],cwd=j.ROOT,text=True) if os.environ.get('CR2_NEGATIVE_CONTROL') else (j.ROOT/'assets/activity-surface.js').read_text())+"\nconst originalMount=ActivitySurface.mount;window.ActivitySurface={mount:(...a)=>window.fixtureSurface=originalMount(...a)};"
       r.fulfill(status=200,content_type='application/javascript',body=source);return
      r.continue_() if req.url.startswith(base) else r.abort();return
     if path=='/activity/intake':
      body=json.loads(req.post_data);requests.append(body)
      if state['offline']:r.abort();return
      p=body['payload'];h=j.hashlib.sha256(json.dumps(p,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
      records[body['reportId']]={'reportId':body['reportId'],'revision':body['revision'],'request_sha256':h,'subject':'synthetic-a','org':p['org'],'createdAt':'2026-10-13T01:00:00Z','updatedAt':'2026-10-13T01:00:00Z','payload':p}
      r.fulfill(status=200,content_type='application/json',body=json.dumps({'protocol':'activity-receipt/1','reportId':body['reportId'],'revision':body['revision'],'request_sha256':h,'stored':True}));return
     if path in ['/activity/entries','/activity/current']:
      state['gets']+=1
      if state['deny']:r.fulfill(status=403,body='{}');return
      rows=json.loads(json.dumps(list(records.values())))
      if path.endswith('/current'):
       for row in rows:
        for k in ['focalName','focalPhone','focalEmail','description','previous']:row['payload'].pop(k,None)
      r.fulfill(status=200,content_type='application/json',body=json.dumps({'protocol':'activity-list/1','rows':rows,'complete':True,'nextCursor':None}));return
     r.fulfill(status=503,body='{}')
    ctx.route('**/*',route);page.goto(base+'/form/5ws-report.html?lang=en');page.wait_for_function('window.ActivityForm && window.ActivityCollector')
    fixture=json.loads(j.FIXTURE.read_text());fixture={k:v for k,v in fixture.items() if k not in ['id','createdAt','revision','schemaVersion','kind','schema']};page.evaluate('(p)=>ActivityCollector.restore(p)',fixture)
    state['offline']=True;page.locator('button[type=submit][form=f]').click();page.wait_for_function("!ActivityForm.busy() && ActivityForm.api.outbox().length===1")
    original=page.evaluate('ActivityForm.api.outbox()[0]');assert original['receipt'] is None
    state['offline']=False;page.locator('#activityRetry').click();page.wait_for_function("!ActivityForm.busy() && ActivityForm.api.outbox()[0].receipt")
    if case.startswith('race-'):
     kind,action=case[5:].split('-')
     # Mount actual received Open control before holding the delivery completion.
     page.locator('#activityHistory').click();page.wait_for_function("document.querySelector('#activityReceived button') && !ActivityForm.busy()")
     if kind=='retry':
      # A distinct pending event, same native fields; earlier receipt remains immutable.
      page.locator('#activityNew').click();state['offline']=True;page.locator('button[type=submit][form=f]').click();page.wait_for_function('!ActivityForm.busy()');state['offline']=False
     page.evaluate("""()=>{const f=window.fetch;window.fetch=async(...args)=>{if(String(args[0]).endsWith('/activity/intake')){window.held=true;await new Promise(r=>window.release=r);}return f(...args);};}""")
     if kind=='submit':page.locator('#newToday').fill('5');page.locator('#activityStatus').click();page.locator('button[type=submit][form=f]').click()
     else:page.locator('#activityRetry').click()
     page.wait_for_function('window.held && ActivityForm.busy()');pointer=page.evaluate('ActivityForm.api.activeEvent()');queue=page.evaluate('ActivityForm.api.outbox()')
     if action in ['new','restore','open']:
      selector={'new':'#activityNew','restore':'#activityRestore','open':'#activityReceived button'}[action]
      page.evaluate('(s)=>document.querySelector(s).onclick()',selector)
      assert page.evaluate('ActivityForm.api.activeEvent()')==pointer
      page.locator('#newToday').fill('6');page.evaluate('window.release()');page.wait_for_function('!ActivityForm.busy()')
      assert page.locator('#newToday').input_value()=='6'
      page.evaluate('window.held=false');page.locator('#activityStatus').click();page.locator('button[type=submit][form=f]').click();page.wait_for_function('window.held');page.evaluate('window.release()');page.wait_for_function('!ActivityForm.busy()')
      q=page.evaluate('ActivityForm.api.outbox()');assert q[-1]['body']['revision']==pointer['revision']+1;assert q[-1]['receipt'];assert q[-1]['body']['payload']['newToday']=='6';assert q[-2]['body']==queue[-1]['body']
     else:
      page.evaluate('BaselineAuth.switchUser()');notice=page.locator('#activityStatus').inner_text();page.evaluate('window.release()');page.wait_for_function('!ActivityForm.busy()')
      assert page.locator('#activityStatus').inner_text()==notice
      assert page.evaluate('ActivityForm.api.activeEvent()') is None
      assert page.evaluate('ActivityForm.api.outbox()')==[]
    elif case=='open-refusal':
     page.locator('#activityHistory').click();page.wait_for_function("document.querySelector('#activityReceived button') && !ActivityForm.busy()")
     before=page.evaluate('ActivityForm.api.activeEvent()')
     page.evaluate("""()=>{const f=window.fetch;window.fetch=async(...a)=>{if(String(a[0]).endsWith('/activity/entries')){window.held=true;await new Promise(r=>window.release=r);}return f(...a);};}""")
     page.locator('#activityReceived button').click();page.wait_for_function('window.held');page.locator('#newToday').fill('6');page.evaluate('window.release()');page.wait_for_function('!ActivityForm.busy()');assert page.locator('#newToday').input_value()=='6';assert page.evaluate('ActivityForm.api.activeEvent()')==before
     page.locator('#activityStatus').click();page.locator('button[type=submit][form=f]').click();page.wait_for_function('!ActivityForm.busy()');assert page.evaluate('ActivityForm.api.outbox().at(-1).body.revision')==2
    elif case=='unchanged-save':
     page.locator('button[type=submit][form=f]').click();page.wait_for_function('!ActivityForm.busy()');assert len(page.evaluate('ActivityForm.api.outbox()'))==1,'unchanged Save created a spurious correction'
    elif case.startswith('csv-'):
     action=case[4:];page.goto(base+'/hub/?view=entries');page.wait_for_function("document.getElementById('activityRows')?.textContent.includes('Verified server received')")
     page.locator('.house-filters select').first.select_option('CMC')
     page.evaluate("""()=>{const f=window.fetch;window.fetch=async(...a)=>{if(String(a[0]).endsWith('/activity/entries')){window.held=true;await new Promise(r=>window.release=r);}return f(...a);};}""")
     page.locator('#activityExport').click();page.wait_for_function('window.held')
     page.locator('.house-filters select').first.select_option('CMC');assert page.locator('#activityExport').is_disabled(),'export must remain busy through filter repaint'
     if action=='signout':page.evaluate('BaselineAuth.signOut()')
     elif action=='account':page.evaluate('BaselineAuth.switchUser()')
     elif action=='destroy':page.evaluate('window.fixtureSurface.destroy()')
     elif action=='fresh':
      # Change source version/hash after initial read. Filter membership must survive freshness.
      row=next(iter(records.values()));row['revision']=2;row['payload']['newToday']='5';row['request_sha256']=j.hashlib.sha256(json.dumps(row['payload'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
     page.evaluate('window.release()');page.wait_for_timeout(400)
     if action=='fresh':
      assert len(downloads)==1;data=Path(downloads[0].path()).read_text(encoding='utf-8-sig');out=list(j.csv.DictReader(j.io.StringIO(data)));assert out[0]['serverRevision']=='2';assert out[0]['sourceHash']==row['request_sha256'];assert json.loads(out[0]['sourcePayload'])['newToday']=='5'
     else:assert not downloads,'stale async export after '+action
    elif case=='retry-correction':
     page.locator('#newToday').fill('5');page.locator('#activityStatus').click();page.locator('button[type=submit][form=f]').click();page.wait_for_function('!ActivityForm.busy()');page.wait_for_timeout(100)
     queue=page.evaluate('ActivityForm.api.outbox()');assert len(queue)==2,{'status':page.locator('#activityStatus').inner_text(),'queue':queue}
     assert queue[1]['body']['revision']==2 and queue[1]['body']['predecessor']=={'revision':1,'request_sha256':original['hash']};assert queue[0]['body']==original['body'];assert queue[1]['receipt'];assert queue[1]['body']['payload']['newToday']=='5'
    elif case=='null-roundtrip':
     row=next(iter(records.values()));row['payload']['description']=None;row['payload']['focalEmail']='';row['payload']['ofPreg']=None;row['payload'].pop('distinctPeople',None)
     row['request_sha256']=j.hashlib.sha256(json.dumps(row['payload'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
     page.locator('#activityHistory').click();page.wait_for_function("document.querySelector('#activityReceived button') && !ActivityForm.busy()")
     page.locator('#activityReceived button').click();page.wait_for_function('!ActivityForm.busy()')
     state['offline']=True;page.locator('#newToday').fill('5');page.locator('#activityStatus').click();page.locator('button[type=submit][form=f]').click();page.wait_for_function('!ActivityForm.busy()');state['offline']=False
     page.locator('#activityRetry').click();page.wait_for_function('!ActivityForm.busy()');page.locator('#newToday').fill('6');page.locator('#activityStatus').click();page.locator('button[type=submit][form=f]').click();page.wait_for_function('!ActivityForm.busy()')
     q=page.evaluate('ActivityForm.api.outbox()');assert q[-1]['body']['revision']==3;raw=q[-1]['body']['payload'];assert raw['description'] is None and raw['ofPreg'] is None and raw['focalEmail']=='' and 'distinctPeople' not in raw;assert q[-1]['receipt']
    elif case=='revocation':
     page.goto(base+'/hub/?view=entries');page.wait_for_function("document.getElementById('activityRows')?.textContent.includes('Verified server received')")
     state['deny']=True;assert page.evaluate("async()=> (await fetch('https://mhpss5ws-tdp3xtfnsq-as.a.run.app/activity/entries')).status")==403
     before=state['gets'];page.locator('#activityExport').click();page.wait_for_timeout(400)
     assert not downloads, 'CR2: cached private download occurred after authority denied'
     assert state['gets']>before,'export did not recheck server authority'
     assert page.locator('#activityRows').inner_text()=='';assert page.locator('#activityExport').is_disabled();assert page.locator('.house-stat .v').all_text_contents()==['—']*5
    assert not errors,errors;results.append({'case':case,'pass':True,'downloads':len(downloads),'listingRequests':state['gets']});ctx.close()
   browser.close()
 finally:server.shutdown();server.server_close()
 print(json.dumps({'fixture':'deterministic HTTP, not provider','results':results}))
if __name__=='__main__':main()
