"""Fresh isolated Chromium, actual page+bridge+store, synthetic SDK at import boundary.
No listeners, credentials, network, actual reports, or hosted writes.
"""
import csv, io, json, pathlib, mimetypes
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[1]
FS = """
export const getFirestore=()=>({});
export const collection=(db,coll)=>({coll});
export const doc=(db,coll,id)=>({coll,id});
export const query=(coll,...constraints)=>({coll:coll.coll,constraints});
export const where=(...args)=>({type:'where',args});
export const orderBy=(...args)=>({type:'orderBy',args});
export const limit=(...args)=>({type:'limit',args});
export const startAfter=(...args)=>({type:'startAfter',args});
export const documentId=()=> '__name__';
export const serverTimestamp=()=>({seconds:1,nanoseconds:0});
export const setDoc=async(ref,body)=>{window.__sdk.writes.push({ref,body});};
export const getDocsFromServer=async(q)=>{
 let s=window.__sdk;s.queries.push(q);if(s.refuse)throw Error('synthetic permission-denied');
 let rows=s.rows;let kind=q.constraints.find(c=>c.type==='where');
 if(!kind)throw Error('unscoped query forbidden');rows=rows.filter(r=>r.kind===kind.args[2]);
 let after=q.constraints.find(c=>c.type==='startAfter');if(after)rows=rows.filter(r=>r._id>after.args[0].id);
 let size=q.constraints.find(c=>c.type==='limit').args[0];rows=rows.slice(0,size);
 let docs=rows.map(r=>({id:r._id,data:()=>{let v={...r};delete v._id;return v;}}));
 return {docs,size:docs.length,metadata:{fromCache:false},forEach:fn=>docs.forEach(fn)};
};
export const getDocs=getDocsFromServer;
export const onSnapshot=()=>{throw Error('old capped listener forbidden')};
export const getDoc=async()=>({exists:()=>false});
export const deleteDoc=()=>{throw Error('deletion forbidden')};
"""
AUTH = """
export const getAuth=()=>({});
export const onAuthStateChanged=(a,cb)=>cb({uid:'SYNTHETIC',email:'synthetic@example.invalid'});
export const isSignInWithEmailLink=()=>false;
export const signOut=()=>Promise.resolve();
export const signInWithEmailAndPassword=()=>{throw Error('no sign in')};
export const sendSignInLinkToEmail=()=>{throw Error('no mail')};
export const signInWithEmailLink=()=>{throw Error('no sign in')};
"""
checks=[]
def check(name,condition):
    assert condition,name
    checks.append({'name':name,'pass':True})
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context(accept_downloads=True)
    context.add_init_script("window.__sdk={rows:[],writes:[],queries:[],refuse:false};")
    blocked=[]
    def route(req):
        u=req.request.url
        if u.startswith('https://www.gstatic.com/firebasejs/10.13.0/'):
            name=u.split('/')[-1]
            body={'firebase-app.js':'export const initializeApp=()=>({});','firebase-firestore.js':FS,'firebase-auth.js':AUTH}[name]
            req.fulfill(status=200,content_type='application/javascript',body=body,headers={'Access-Control-Allow-Origin':'*'});return
        if u.startswith('https://synthetic.invalid/'):
            rel=u.split('https://synthetic.invalid/',1)[1].split('?')[0].split('#')[0]
            f=ROOT/rel
            if rel=='assets/fb-config.js':
                req.fulfill(status=200,content_type='application/javascript',body="window.FB_CONFIG={projectId:'SYNTHETIC_ONLY',apiKey:'NOT_A_KEY'};");return
            if f.is_file():req.fulfill(status=200,content_type=mimetypes.guess_type(str(f))[0] or 'application/octet-stream',body=f.read_bytes());return
        blocked.append(u);req.abort()
    context.route('**/*',route)
    page=context.new_page(); errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('https://synthetic.invalid/index.html?source=choose')
    page.wait_for_function('window.FB && FB.status().ready')
    # Guarded export is a real browser download of unchanged opaque bytes.
    legacy=' [ {"_rid":"PRESERVE_exact", "unknown": {"x":7}} ]\n'
    page.evaluate("raw=>localStorage.setItem('mhpss-np-queue-v1',raw)",legacy)
    page.evaluate("FB.flush()")
    page.wait_for_selector('#fbbar button',state='attached')
    page.on('dialog',lambda dialog:dialog.accept())
    with page.expect_download() as legacy_download:
        page.get_by_text('Export private legacy outbox',exact=True).click()
    check('real guarded legacy download exact byte preservation',pathlib.Path(legacy_download.value.path()).read_bytes()==legacy.encode())
    check('legacy remains unchanged after consent export',page.evaluate("localStorage.getItem('mhpss-np-queue-v1')")==legacy)
    page.evaluate("""() => {
      let r={org:'TPO',site:'SYNTHETIC',district:'RAS',dateAD:'2000-01-01',dateBS:'2056-09-17',activity:'1.1',modality:'COMM',sessionTime:'00:00',reachedTotal:1,countBasis:'CONTACTS',f04:1,disF0_17:0,disAsked:'No',total:1};
      let a=STORE.save(r); window.__sourceRecord=a.record;
      window.__sdk.rows=Array.from({length:2501},(_,i)=>({...STORE.registerBody(a.record),_id:'row-'+String(i).padStart(6,'0'),id:'SYNTHETIC-'+String(i).padStart(6,'0')}));
      window.__downloads=[];
    }""")
    page.evaluate("document.getElementById('useLive').click()")
    page.wait_for_function("!document.getElementById('app').hidden",timeout=30000)
    check('actual root STORE save dispatched through SDK',page.evaluate('__sdk.writes.length')>0)
    check('rendered complete count exceeds former cap', '2,501' in page.locator('#fSum').inner_text())
    check('actual scoped server pages used',page.evaluate("__sdk.queries.length===12 && __sdk.queries.every(q=>q.constraints.some(c=>c.type==='where' && c.args[2]==='activity'))"))
    with page.expect_download() as csv_download:
        page.evaluate("document.getElementById('expAll').click()")
    output=pathlib.Path(csv_download.value.path()).read_text(encoding='utf-8-sig')
    rows=list(csv.DictReader(io.StringIO(output.lstrip('\ufeff'))))
    check('actual export has all 2501 source rows',len(rows)==2501)
    check('CSV source identity + attendance parity',len({r['id'] for r in rows})==2501 and all(r['reachedTotal']=='1' for r in rows))
    check('age-sex and disability keys preserved in CSV',all(k in rows[0] for k in ['f04','disF0_17','disAsked']))
    check('table includes synthetic source ID',page.locator('#rawBody').inner_text().find('SYNTHETIC-')>=0)
    displayed=page.locator('#rawBody tr td:last-child').all_text_contents()
    check('rendered 400-row subset identity parity with complete CSV',len(displayed)==400 and set(displayed).issubset({r['id'] for r in rows}))
    check('rendered table limit is disclosed','first 400 shown' in page.locator('#rawCount').inner_text())
    check('truthful non-atomic label rendered','not an atomic snapshot' in page.locator('#liveStrip').inner_text())
    # Trigger actual next scheduled refresh immediately without waiting a minute.
    # New watch is independent; exercises actual page callback by replacing timer
    # registration before loading in second context below.
    context2=browser.new_context()
    context2.add_init_script("""window.__sdk={rows:[],writes:[],queries:[],refuse:false};window.__refresh=[];
    const old=window.setInterval;window.setInterval=(fn,ms)=>{if(ms===60000){window.__refresh.push(fn);return 12345;}return old(fn,ms)};""")
    context2.route('**/*',route)
    pg=context2.new_page();pg.goto('https://synthetic.invalid/index.html?source=choose');pg.wait_for_function('window.FB && FB.status().ready')
    pg.evaluate("""() => {__sdk.rows=[{_id:'one',id:'SYNTHETIC-one',kind:'activity',org:'TPO',site:'SYNTHETIC',activity:'1.1',reachedTotal:1}];window.__downloads=[];STORE.download=(...args)=>__downloads.push(args);} """)
    pg.evaluate("document.getElementById('useLive').click()");pg.wait_for_function("!document.getElementById('app').hidden")
    pg.evaluate("__sdk.refuse=true;__refresh[0]()")
    pg.wait_for_function("document.getElementById('app').hidden")
    pg.evaluate("document.getElementById('expAll').click()")
    check('refresh refusal hides stale outputs and blocks programmatic CSV',pg.evaluate('__downloads.length')==0)
    check('refresh refusal explicitly shows incomplete', 'Incomplete' in pg.locator('#livePanel').inner_text() or 'refused' in pg.locator('#livePanel').inner_text())
    formpage=context2.new_page();formerrors=[];formpage.on('pageerror',lambda e:formerrors.append(str(e)))
    formpage.goto('https://synthetic.invalid/forms.html')
    formpage.wait_for_function('window.FB && FB.status().ready && window.__refresh.length===4')
    formpage.evaluate("""async() => {__sdk.rows=Array.from({length:2501},(_,i)=>({_id:'contact-'+String(i).padStart(6,'0'),kind:'service_contact',org:'TPO',site:'SYNTHETIC',contact_code:'SYNTHETIC-'+i,date_ad:'2000-01-01'}));await __refresh[0]();window.__downloads=[];L1.download=(...args)=>__downloads.push(args);} """)
    formpage.wait_for_function("document.getElementById('stripTxt').textContent.includes('2501')")
    formpage.evaluate("document.querySelector('button.exp[data-k=service_contact]').click()")
    contact_csv=formpage.evaluate('__downloads.at(-1)[1]')
    check('forms shared-runtime complete CSV has 2501 contacts',len(list(csv.DictReader(io.StringIO(contact_csv.lstrip('\ufeff')))))==2501)
    formpage.evaluate("__sdk.refuse=true;__refresh[0]()")
    formpage.wait_for_function("document.getElementById('stripTxt').textContent.includes('Incomplete')")
    formpage.evaluate("document.querySelector('button.exp[data-k=service_contact]').click()")
    check('forms incomplete kind cannot export stale contacts',formpage.evaluate('__downloads.length')==1)
    check('forms shared runtime no browser errors',not formerrors)
    home=context2.new_page();home.goto('https://synthetic.invalid/field-output-home.html')
    home.wait_for_function('window.FB && FB.status().ready')
    home.evaluate("__sdk.rows=[{_id:'one',id:'SYNTHETIC-one',kind:'activity',org:'TPO',site:'SYNTHETIC',activity:'1.1',reachedTotal:1}];OUTPUT_HOME.read()")
    home.wait_for_function('OUTPUT_HOME.state.ok')
    home.evaluate('__sdk.refuse=true;__refresh[0]()')
    home.wait_for_function('!OUTPUT_HOME.state.ok')
    check('field output reader clears stale rows on incomplete refresh',home.evaluate('OUTPUT_HOME.state.rows.length')==0)
    check('no actual root browser errors',not errors)
    context2.close();context.close();browser.close()
print(json.dumps({'all_pass':True,'count':len(checks),'checks':checks,'blocked_nonfixture_requests':len(blocked),'scope':'Actual Chromium page with synthetic Firebase SDK imports; no real network or data.'},indent=2))
