"""Final bounded synthetic CSV comparator; no application changes or real records."""
from pathlib import Path
import importlib.util,json,threading,hashlib,csv,io
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[2]
P=R;O=P/'design-preview'
spec=importlib.util.spec_from_file_location('harness',R/'tools/lane-c-tests/05-browser.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
server=h.http.server.ThreadingHTTPServer(('127.0.0.1',0),h.Handler);t=threading.Thread(target=server.serve_forever,daemon=True);t.start();origin='http://127.0.0.1:'+str(server.server_port)
checks=[];outputs={};external=[]
def ck(n,v,d=None):checks.append({'name':n,'passed':bool(v),'detail':d})
def sha(v):return hashlib.sha256(v).hexdigest()
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome',args=['--no-sandbox'])
  for variant in ['base','head']:
   ctx=browser.new_context(viewport={'width':1280,'height':900},service_workers='block',accept_downloads=True)
   def route(rt):
    if rt.request.url.startswith(origin+'/'):rt.continue_()
    else:external.append({'url':rt.request.url,'action':'aborted-before-network'});rt.abort()
   ctx.route('**/*',route);pg=ctx.new_page();errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
   pg.goto(origin+'/'+variant+'/index.html?source=choose&lang=en',wait_until='load')
   fixture=pg.evaluate(h.FIXTURE_JS);pg.locator('#file').set_input_files({'name':'SYNTHETIC-IDENTICAL.json','mimeType':'application/json','buffer':json.dumps(fixture).encode()})
   pg.wait_for_function('document.getElementById("srcNote").textContent.includes("SYNTHETIC-IDENTICAL.json")')
   pg.evaluate('STORE.stamp=()=>"QA-FIXED"');before=h.export(pg,'expAll')
   pg.locator('#file2').set_input_files({'name':'SYNTHETIC-ROUNDTRIP.csv','mimeType':'text/csv','buffer':before})
   pg.wait_for_function('document.getElementById("srcNote").textContent.includes("SYNTHETIC-ROUNDTRIP.csv")')
   after=h.export(pg,'expAll');outputs[variant]={'before_sha256':sha(before),'after_sha256':sha(after),'own_roundtrip_byte_equal':before==after,'before_rows':list(csv.DictReader(io.StringIO(before.decode('utf-8-sig')))),'after_rows':list(csv.DictReader(io.StringIO(after.decode('utf-8-sig'))))}
   (O/(variant+'-bounded-before.csv')).write_bytes(before);(O/(variant+'-bounded-after.csv')).write_bytes(after)
   ck(variant+' before 3 records',len(outputs[variant]['before_rows'])==3);ck(variant+' after 3 records',len(outputs[variant]['after_rows'])==3);ck(variant+' no page errors',not errs,errs)
   ctx.close()
  browser.close()
 for state in ['before','after']:
  ck('baseline/candidate '+state+' CSV bytes identical',(O/('base-bounded-'+state+'.csv')).read_bytes()==(O/('head-bounded-'+state+'.csv')).read_bytes())
 # Explain any within-version difference field by field; it is not the cross-version preservation assertion.
 for variant in outputs:
  a=outputs[variant]['before_rows'];b=outputs[variant]['after_rows'];diff=[]
  for i,(x,y) in enumerate(zip(a,b)):
   for key in sorted(set(x)|set(y)):
    if x.get(key)!=y.get(key):diff.append({'row':i,'field':key,'before':x.get(key),'after':y.get(key)})
  outputs[variant]['own_roundtrip_differences']=diff
finally:
 server.shutdown();server.server_close();t.join(timeout=5);ck('listener cleanup',not t.is_alive())
 result={'checks':checks,'passed':sum(x['passed'] for x in checks),'failed':sum(not x['passed'] for x in checks),'outputs':outputs,'external_attempts_blocked':external,'external_requests_dispatched':0,'production_requests_dispatched':0,'cleanup':not t.is_alive(),'interpretation':'Baseline versus candidate bytes must match for each identical synthetic state. A version comparing its own initial and reimported export is a different assertion; differences are recorded, not patched.'}
 (O/'bounded-csv.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if result['failed']:raise SystemExit(1)
