"""Ordinary accepted-form CR-1 journey, SYNTHETIC Auth/HTTP only, no providers."""
import importlib.util,json,hashlib
from pathlib import Path
from threading import Thread
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright
spec=importlib.util.spec_from_file_location('fixture',Path(__file__).with_name('training-browser.py'))
assert spec is not None and spec.loader is not None
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
def run():
 server=ThreadingHTTPServer(('127.0.0.1',0),fixture.Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
 state={'bodies':[],'sources':{},'drop':False,'hold':False,'held':[]};checks=[]
 def check(value,label):
  assert value,label
  checks.append(label)
 def receipt(b):return dict(protocol='training-receipt/1',reportId=b['reportId'],revision=1,request_sha256=hashlib.sha256(json.dumps(b['payload'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),stored=True)
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True)
   try:
    c=browser.new_context(service_workers='block');p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
    def route(r):
     if r.request.url.startswith(base):r.continue_();return
     if '/training/' not in r.request.url:r.abort();return
     if r.request.method!='POST':r.abort();return
     b=r.request.post_data_json;state['bodies'].append(b);key=b['reportId'];old=state['sources'].get(key)
     if old is not None:assert old==b,'fixture refuses ID rebound to a different payload'
     state['sources'][key]=b
     if state['drop']:state['drop']=False;r.abort();return
     if state['hold']:state['held'].append((r,b));return
     r.fulfill(status=200,content_type='application/json',body=json.dumps(receipt(b)))
    c.route('**/*',route);p.goto(base+'/form/training-report.html?lang=en')
    p.evaluate("""()=>{const ev=e=>{e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));};document.querySelectorAll('#f select').forEach(e=>{const o=[...e.options].find(o=>o.value&&!['OTHER','OTH'].includes(o.value));if(o){e.value=o.value;ev(e)}});document.querySelectorAll('#f input[type=text],#f input[type=tel],#f textarea').forEach(e=>{e.value=e.type==='tel'?'0000000000':'SYNTHETIC CR1';ev(e)});document.querySelectorAll('#f input[type=number]').forEach(e=>{e.value='1';ev(e)});document.querySelector('#dateAD').value='2026-10-01';}""")
    p.fill('#u18','');p.fill('#pwd','0')
    submit=lambda:p.locator('#f button[type=submit]').click()
    received=lambda:p.wait_for_function("document.querySelector('#trainingStatus').textContent.includes('Received')")
    queue=lambda:p.evaluate('TrainingForm.api.outbox()')
    storage=lambda:p.evaluate('JSON.stringify(Object.fromEntries(Object.entries(localStorage).filter(([k])=>k.startsWith("mhpss-training-"))))')
    submit();received();first=queue()[0];submit();received()
    check(len(queue())==1 and state['bodies'][0]==state['bodies'][1],'ordinary repeated Submit is exact same acknowledged event')
    check(p.locator('#trainingNew').count()==1,'CR-1 explicit Start new training event must exist in ordinary form')
    p.locator('#trainingNew').click();submit();received();second=queue()[1]
    check(first['body']['payload']==second['body']['payload'] and first['body']['reportId']!=second['body']['reportId'],'two identical events have distinct crypto IDs')
    check(queue()[0]==first and first['hash']==second['hash'],'prior envelope receipt and canonical hash preserved')
    check(len(state['sources'])==2,'synthetic receiving fixture retains two event sources, not payload dedup')
    p.fill('#title','EDITED AFTER ACK');before=queue();count=len(state['bodies']);submit();p.wait_for_function("document.querySelector('#trainingStatus').textContent.includes('Start new training event')")
    check(queue()==before and len(state['bodies'])==count,'edit after ACK controlled refusal, no overwritten envelope or send')
    p.reload();p.locator('#trainingRestore').click();check(p.input_value('#title')=='EDITED AFTER ACK','restoration retains edited draft')
    submit();p.wait_for_function("document.querySelector('#trainingStatus').textContent.includes('Start new training event')");check(queue()==before,'restored changed payload cannot bind to received ID')
    p.fill('#title','SYNTHETIC CR1');p.locator('#trainingNew').click();state['drop']=True;submit();p.wait_for_function("document.querySelector('#trainingStatus').textContent.includes('retained')");lost=queue()[-1]
    check(lost['receipt'] is None and len(state['sources'])==3,'lost successful ACK retains pending immutable envelope')
    p.reload();p.locator('#trainingRestore').click();submit();received()
    check(state['bodies'][-1]==state['bodies'][-2] and queue()[-1]['body']==lost['body'],'reload and Submit retry exact lost-ACK request')
    p.locator('#trainingNew').click();state['hold']=True
    p.evaluate("()=>{const b=document.querySelector('#f button[type=submit]');b.click();b.click()}");p.wait_for_function("TrainingForm.api.outbox().length===4")
    p.wait_for_timeout(100);check(len(state['held'])==1,'double-click dispatches one immutable event request')
    held=state['held'].pop();oldpending=queue()[-1];p.locator('#trainingNew').click();newactive=p.evaluate('TrainingForm.api.activeEvent()');status=p.locator('#trainingStatus').inner_text()
    check(queue()[-1]==oldpending,'New while sending preserves old pending outbox')
    held[0].fulfill(status=200,content_type='application/json',body=json.dumps(receipt(held[1])));state['hold']=False;p.wait_for_function('!document.querySelector("#trainingRetry").disabled')
    check(p.evaluate('TrainingForm.api.activeEvent()')==newactive and p.locator('#trainingStatus').inner_text()==status,'old send completion cannot hijack new editor/status')
    check(queue()[-1]['receipt']['reportId']==oldpending['body']['reportId'],'old completion may save only its exact receipt')
    # Crypto refusal through actual New control; compare whole training storage.
    before=storage();p.evaluate("()=>{window.originalUUID=crypto.randomUUID;crypto.randomUUID=()=>{throw Error('synthetic crypto failure')}}");p.locator('#trainingNew').click()
    check(storage()==before and 'crypto failure' in p.locator('#trainingStatus').inner_text(),'crypto failure controlled with no training storage change');p.evaluate('()=>{crypto.randomUUID=window.originalUUID}')
    state['hold']=True;submit();p.wait_for_function('TrainingForm.api.outbox().length===5');p.wait_for_timeout(100);held=state['held'].pop();before=queue();p.evaluate('BaselineAuth.switch()')
    held[0].fulfill(status=200,content_type='application/json',body=json.dumps(receipt(held[1])));p.wait_for_timeout(100)
    check(queue()==[],'account switch cannot adopt old account outbox')
    check(json.loads(p.evaluate("localStorage.getItem('mhpss-training-outbox-v1:fixture-A')"))==before,'account switch suppresses stale ACK application')
    count=len(state['bodies']);submit();p.wait_for_timeout(50);check(len(state['bodies'])==count,'prior-account editor cannot submit under new UID')
    p.reload();p.locator('#trainingRestore').click();check(len(queue())==5,'reload returns original account persisted events')
    state['hold']=False;p.locator('#trainingNew').click();active=p.evaluate('TrainingForm.api.activeEvent()');before=queue();p.locator('#trainingRetry').click();received()
    check(p.evaluate('TrainingForm.api.activeEvent()')==active and queue()[:4]==before[:4],'Retry old pending after New preserves active editor and every prior receipt')
    check(queue()[4]['receipt']['reportId']==before[4]['body']['reportId'] and state['bodies'][-1]==before[4]['body'],'Retry sends exact historical pending payload, not current editor')
    check(not errors,'no unhandled browser errors')
    print(json.dumps({'fixture':'SYNTHETIC ONLY; not provider closure','passed':len(checks),'assertions':checks,'source_ids':list(state['sources']),'page_errors':errors}))
   finally:browser.close()
 finally:server.shutdown();server.server_close();thread.join(timeout=5)
if __name__=='__main__':run()
