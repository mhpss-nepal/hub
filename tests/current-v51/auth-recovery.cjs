/* Isolated scheduling/error regression. SDK persistence is separately rehearsed. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const paths=['review-current-v51/current-auth.js','review-analytics-v48/assets/baseline-auth.js','review-baseline-v47/assets/baseline-auth.js'];
async function run(path){
 let observer,resolvePersistence;const persistence=new Promise(r=>resolvePersistence=r),user={getIdToken:async()=> 'synthetic-only'};
 const sdk={getAuth:()=>({}),browserLocalPersistence:{},setPersistence:()=>persistence,onIdTokenChanged:(a,f)=>{observer=f;},isSignInWithEmailLink:()=>true,signInWithEmailLink:async()=>{throw {code:'auth/invalid-action-code',message:'secret email token action URL'};},signOut:async()=>observer(null)};
 const app={getApps:()=>[],initializeApp:()=>({})};
 const sandbox={window:{FB_CONFIG:{}},localStorage:{getItem:()=> 'synthetic@example.invalid',removeItem(){}},location:{href:'https://example.invalid/?mode=signIn',pathname:'/',origin:'https://example.invalid'},history:{replaceState(){}},document:{title:''},load:async s=>s.endsWith('firebase-app.js')?app:sdk};
 vm.runInNewContext(fs.readFileSync(path,'utf8').replaceAll('import(', 'load('),sandbox);
 let state;sandbox.window.BaselineAuth.onChange((u,s)=>state=s);
 assert.equal(state.restoration,'restoring','must distinguish restoration from signed out');
 resolvePersistence();await new Promise(r=>setImmediate(r));
 assert.equal(state.restoration,'restoring');observer(user);await new Promise(r=>setImmediate(r));
 assert.equal(sandbox.window.BaselineAuth.currentUser(),user,'failed link must retain existing session');
 assert.equal(state.errorCode,'auth/invalid-action-code');assert.equal(state.failureStage,'email-link');assert.equal(state.restoration,'signed-in');assert(!JSON.stringify(state).includes('secret'));
 await sandbox.window.BaselineAuth.finishLink('synthetic@example.invalid').catch(()=>{});
 assert.equal(state.errorCode,'auth/invalid-action-code');assert(!state.error.includes('replacement'));
 sdk.signInWithEmailLink=async()=>{throw {code:'auth/private-email-and-token',message:'secret'};};
 await sandbox.window.BaselineAuth.finishLink('synthetic@example.invalid').catch(()=>{});
 assert.equal(state.errorCode,'auth/unknown');assert(!JSON.stringify(state).includes('private-email'));
 await sandbox.window.BaselineAuth.signOut();assert.equal(sandbox.window.BaselineAuth.currentUser(),null);
 console.log('PASS',path);
}
(async()=>{for(const path of paths)await run(path);})().catch(e=>{console.error(e);process.exitCode=1;});
