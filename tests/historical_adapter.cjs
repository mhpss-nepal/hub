// Synthetic-only executable automatic reader regression; no operational data.
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const nodes=new Map();
function node(){return {hidden:true,value:'',textContent:'',children:[],handlers:{},addEventListener(k,f){this.handlers[k]=f},appendChild(n){this.children.push(n)},replaceChildren(){this.children=[]},click(){return this.handlers.click?.()},};}
const get=id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id)};
let body, resolveText, rejectText, authCallback, status=200;const user={};
const auth={currentUser:()=>user,token:async()=> 'fixture',onChange:f=>{authCallback=f},signOut:async()=>{}};
const sandbox={window:{BASELINE_ONLY:true,BaselineAuth:auth,addEventListener(){}},document:{getElementById:get,createElement:node},MutationObserver:class{observe(){}},URLSearchParams,location:{search:''},Object,Number,Date,JSON,Error,Blob,URL,setTimeout,clearTimeout,AbortController,fetch:async()=>({ok:status>=200&&status<300,status,text:()=>body===undefined?new Promise((r,j)=>{resolveText=r;rejectText=j}):Promise.resolve(JSON.stringify(body))})};
vm.runInNewContext(fs.readFileSync(require('node:path').join(__dirname,'../assets/historical-baseline.js'),'utf8'),sandbox);
const x={schema:'mhpss-private-historical-summary-v1',version:'historical-master-v1',classification:'private-owner-reading',historical_entries:40,known_service_contacts:900,unknown_count_entries:2,unverified_form_entries:10,backup_capture_utc:'2026-09-25T01:00:00.123456+00:00',original_export_date:'2026-09-13',historical_date_status:'unresolved-bs-dates',unit:'service contacts, not unique people',combine_classes:false};
async function load(v){body=v;await get('historical-refresh').click();}
(async()=>{
 await load(x);assert.equal(get('historical-results').hidden,false);
 for(const patch of [{version:['historical-master-v1']},{original_export_date:['2026-09-13']},{backup_capture_utc:[x.backup_capture_utc]},{original_export_date:'2026-02-30'},{backup_capture_utc:'2026-02-30T01:00:00.123456+00:00'},{historical_entries:true},{known_service_contacts:NaN},{extra:'not-permitted'}]){
  await load(x);await load({...x,...patch});assert.equal(get('historical-results').hidden,true);assert.equal(get('historical-summary').textContent,'');assert.equal(get('historical-provenance').textContent,'');
 }
 for(const refused of [201,202,204,206,301,401,403,500]){
  status=200;await load(x);status=refused;await load(x);
  assert.equal(get('historical-results').hidden,true,`F2 exact HTTP200 only: ${refused}`);
  assert.equal(get('historical-stats').children.length,0);assert.equal(get('historical-summary').textContent,'');assert.equal(get('historical-provenance').textContent,'');
  get('historical-export').click();
 }
 status=200;
 await load(x);get('historical-clear').click();assert.equal(get('historical-summary').textContent,'');assert.equal(get('historical-provenance').textContent,'');assert.equal(get('historical-stats').children.length,0);
 body=undefined;let pending=get('historical-refresh').click();await new Promise(r=>setImmediate(r));get('historical-clear').click();resolveText(JSON.stringify(x));await pending;assert.equal(get('historical-results').hidden,true);
 pending=get('historical-refresh').click();await new Promise(r=>setImmediate(r));get('historical-clear').click();rejectText(Error('delayed failure'));await pending;assert.equal(get('historical-results').hidden,true);
 console.log('PASS synthetic automatic adapter: strict dates/types/keys, complete Clear/refusal erasure, delayed success/failure fencing');
})().catch(e=>{console.error(e);process.exitCode=1});
