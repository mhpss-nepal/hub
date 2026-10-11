const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const paths=['review-current-v51/current-auth.js','review-analytics-v48/assets/baseline-auth.js','review-baseline-v47/assets/baseline-auth.js'];
const tick=()=>new Promise(r=>setImmediate(r));
async function run(path){
 let observer,release,durable=null,calls=0;
 const old={getIdToken:async()=> 'synthetic-old'},later={getIdToken:async()=> 'synthetic-later'};
 const sdk={getAuth:()=>({}),browserLocalPersistence:{},setPersistence:async()=>{},onIdTokenChanged:(a,f)=>{observer=f;queueMicrotask(()=>f(durable));},isSignInWithEmailLink:()=>true,signInWithEmailLink:()=>{calls++;return new Promise(r=>release=()=>{durable=old;observer(old);r({user:old});});},signInWithEmailAndPassword:async()=>{durable=later;observer(later);return {user:later};},signOut:async()=>{durable=null;observer(null);}};
 const app={getApps:()=>[],initializeApp:()=>({})};
 const sandbox={window:{FB_CONFIG:{}},localStorage:{getItem:()=> 'synthetic@example.invalid',removeItem(){}},location:{href:'https://example.invalid/?mode=signIn',pathname:'/',origin:'https://example.invalid'},history:{replaceState(){}},document:{title:''},load:async s=>s.endsWith('firebase-app.js')?app:sdk};
 vm.runInNewContext(fs.readFileSync(path,'utf8').replaceAll('import(', 'load('),sandbox);
 const auth=sandbox.window.BaselineAuth;
 for(let i=0;i<20&&!release;i++)await tick();assert.equal(calls,1,'automatic link must actually start');
 await auth.signOut();assert.equal(durable,null,'explicit signout clears immediately while automatic link pending');
 const laterJob=auth.signIn('synthetic@example.invalid','synthetic-only');
 release();await laterJob;await tick();
 assert.equal(durable,later,'new deliberate sign-in after signout must follow cleanup, not be erased by it');assert.equal(auth.currentUser(),later);
 await auth.signOut();await tick();assert.equal(durable,null);assert.equal(auth.currentUser(),null);
 console.log('PASS automatic pending completion/signout/later deliberate ordering',path);
}
(async()=>{for(const p of paths)await run(p);})().catch(e=>{console.error(e);process.exitCode=1;});