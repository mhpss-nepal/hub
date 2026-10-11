const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const paths=['review-analytics-v48/assets/historical-baseline.js','review-baseline-v47/assets/historical-baseline.js'];
(async()=>{const findings=[];for(const path of paths){
 const elements=new Map();function el(id){if(!elements.has(id))elements.set(id,{hidden:false,value:'',textContent:'',open:false,classList:{add(){},remove(){}},replaceChildren(){},appendChild(){},addEventListener(){},focus(){}});return elements.get(id);}
 let callback;const user={getIdToken:async()=> 'synthetic-only'};const window={BASELINE_ONLY:true,HistoricalAnalytics:{clear(){},render(){}},addEventListener(){},BaselineAuth:{currentUser:()=>user,token:async()=>{throw Error('test backend unavailable');},onChange:f=>{callback=f;}}};
 const sandbox={window,document:{getElementById:el,body:{classList:{add(){},remove(){}}},createElement:()=>el('temporary')},location:{search:'?source=historical'},MutationObserver:class{observe(){}},URLSearchParams,AbortController,setTimeout,clearTimeout,URL,Blob,fetch:()=>{throw Error('network forbidden');}};
 vm.runInNewContext(fs.readFileSync(path,'utf8'),sandbox);
 const error='Authentication could not complete. Existing sign-in has not been cleared. (auth/invalid-email)';
 callback(user,{ready:true,restoration:'signed-in',linkPending:true,error,errorCode:'auth/invalid-email',failureStage:'email-link'});
 const immediate=el('historical-status').textContent;await new Promise(r=>setImmediate(r));const settled=el('historical-status').textContent;
 assert(immediate.includes('auth/invalid-email'));assert(settled.includes('auth/invalid-email'));
 findings.push({path,immediate,settled,pass:'safe email-link diagnostic preserved after restored-user observer'});
 }fs.writeFileSync(process.argv[2],JSON.stringify({diagnostic_lost:false,findings},null,2)+'\n');console.log(JSON.stringify(findings));})().catch(e=>{console.error(e);process.exitCode=1;});
