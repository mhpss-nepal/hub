// Synthetic-only executable adapter regression; no operational data.
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const nodes=new Map();
function node(){return {hidden:true,value:'',textContent:'',children:[],handlers:{},addEventListener(k,f){this.handlers[k]=f},appendChild(n){this.children.push(n)},replaceChildren(){this.children=[]},click(){this.handlers.click?.()},};}
const get=id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id)};
const sandbox={document:{getElementById:get,createElement:node},MutationObserver:class{observe(){}},URLSearchParams,location:{search:''},Object,Number,Date,JSON,Error,Blob,URL,setTimeout};
vm.runInNewContext(fs.readFileSync(require('node:path').join(__dirname,'../assets/historical-baseline.js'),'utf8'),sandbox);
const x={schema:'mhpss-private-historical-summary-v1',version:'historical-master-v1',classification:'private-owner-reading',historical_entries:40,known_service_contacts:900,unknown_count_entries:2,unverified_form_entries:10,backup_capture_utc:'2026-09-25T01:00:00.123456+00:00',original_export_date:'2026-09-13',historical_date_status:'unresolved-bs-dates',unit:'service contacts, not unique people',combine_classes:false};
async function load(v){get('historical-file').handlers.change({target:{files:[{size:1000,text:()=>Promise.resolve(JSON.stringify(v))}]}});await new Promise(r=>setImmediate(r));}
(async()=>{
 await load(x);assert.equal(get('historical-results').hidden,false);
 for(const patch of [{original_export_date:['2026-09-13']},{backup_capture_utc:[x.backup_capture_utc]},{original_export_date:'2026-02-30'},{backup_capture_utc:'2026-02-30T01:00:00.123456+00:00'},{historical_entries:true},{known_service_contacts:NaN},{extra:'not-permitted'}]){
  await load(x);await load({...x,...patch});assert.equal(get('historical-results').hidden,true);assert.equal(get('historical-summary').textContent,'');assert.equal(get('historical-provenance').textContent,'');
 }
 await load(x);get('historical-clear').click();assert.equal(get('historical-summary').textContent,'');assert.equal(get('historical-provenance').textContent,'');assert.equal(get('historical-stats').children.length,0);
 let resolve;get('historical-file').handlers.change({target:{files:[{size:1000,text:()=>new Promise(r=>resolve=r)}]}});get('historical-clear').click();resolve(JSON.stringify(x));await new Promise(r=>setImmediate(r));assert.equal(get('historical-results').hidden,true);
 console.log('PASS synthetic adapter: strict dates/types/keys, complete Clear/refusal erasure, delayed-read fencing');
})().catch(e=>{console.error(e);process.exitCode=1});
