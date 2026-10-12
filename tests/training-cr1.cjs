'use strict';
// Synthetic transport only: exercises real event/outbox code, never a provider.
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict'),{webcrypto}=require('crypto');
const ctx={window:{},TextEncoder,crypto:webcrypto,AbortController,setTimeout,clearTimeout};vm.createContext(ctx);
vm.runInContext(fs.readFileSync(require('path').join(__dirname,'../assets/training-api.js'),'utf8'),ctx);
(async()=>{
 const T=ctx.window.TRAINING_API,store=new Map(),storage={getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v)};
 const a={uid:'fixture-A',emailVerified:true};let current=a,bodies=[],lost=true;
 const auth={currentUser:()=>current,token:async()=> 'SYNTHETIC'};let api=T.create(auth,storage);
 ctx.fetch=async(url,o)=>{const body=JSON.parse(o.body);bodies.push(o.body);if(lost)throw Error('synthetic ACK loss after fixture storage');return {status:200,text:async()=>JSON.stringify({protocol:'training-receipt/1',reportId:body.reportId,revision:1,request_sha256:await T.hash(body.payload),stored:true})};};
 const p={kind:'training',title:'identical legitimate events',participants:[]};
 const first=await api.enqueue(p);await assert.rejects(api.send(first.body.reportId));
 api=T.create(auth,storage);assert.equal((await api.enqueue(p)).body.reportId,first.body.reportId,'reload retains pending event identity');
 lost=false;await api.send(first.body.reportId);assert.equal(bodies[0],bodies[1],'ACK loss exact request retry');
 assert.equal((await api.enqueue(p)).body.reportId,first.body.reportId,'ordinary Submit after ACK remains the same event');
 const old=JSON.stringify(api.outbox()[0]);
 // On the exact old source this falls through to ordinary Submit, reproducing
 // the material undercount rather than failing merely on a missing method.
 if(api.startNewEvent)api.startNewEvent();
 const second=await api.enqueue(p);
 assert.notEqual(second.body.reportId,first.body.reportId,'CR-1: explicit new identical event needs a distinct crypto ID');
 assert.equal(api.outbox().length,2);assert.equal(JSON.stringify(api.outbox()[0]),old);
 await api.send(second.body.reportId);assert.equal(api.outbox()[0].hash,api.outbox()[1].hash);
 assert.notEqual(api.outbox()[0].receipt.reportId,api.outbox()[1].receipt.reportId);
 const before=JSON.stringify([...store]);await assert.rejects(api.enqueue({...p,title:'edited after ACK'}),/Start new training event/);assert.equal(JSON.stringify([...store]),before);
 const double=await Promise.all([api.enqueue(p),api.enqueue(p)]);assert.equal(double[0].body.reportId,second.body.reportId);assert.equal(double[1].body.reportId,second.body.reportId);assert.equal(api.outbox().length,2);
 current={uid:'fixture-B',emailVerified:true};api.invalidate();assert.equal(api.outbox().length,0);await api.enqueue(p);current=a;api.invalidate();assert.equal((await api.enqueue(p)).body.reportId,second.body.reportId);
 const snapshot=JSON.stringify([...store]);ctx.crypto={subtle:webcrypto.subtle,randomUUID(){throw Error('crypto unavailable');}};assert.throws(()=>api.startNewEvent(),/crypto unavailable/);assert.equal(JSON.stringify([...store]),snapshot);ctx.crypto=webcrypto;
 api.startNewEvent();const pending=await api.enqueue(p);const pendingBytes=JSON.stringify(api.outbox().find(e=>e.body.reportId===pending.body.reportId));api.startNewEvent();assert.equal(JSON.stringify(api.outbox().find(e=>e.body.reportId===pending.body.reportId)),pendingBytes,'New never deletes an old pending envelope');
 // Enqueue captures the event before async hashing; a subsequent New refuses
 // stale binding rather than assigning this payload to the new editor.
 const inflight=api.enqueue(p);api.startNewEvent();await assert.rejects(inflight,/event changed/);
 assert.equal(api.outbox().length,3);
 // Upgrade from the old account-wide-dedup source: no active pointer means
 // fail closed, not guess which old receipt the restored draft belongs to.
 store.delete('mhpss-training-active-v1:'+a.uid);const legacy=JSON.stringify([...store]);
 await assert.rejects(api.enqueue(p),/unbound draft/);assert.equal(JSON.stringify([...store]),legacy);
 await api.send(pending.body.reportId);assert.equal(api.outbox().length,3,'legacy pending remains explicitly retryable');
 api.startNewEvent();const created=await Promise.all([api.enqueue(p),api.enqueue(p)]);assert.equal(created[0].body.reportId,created[1].body.reportId);assert.equal(api.outbox().length,4,'concurrent first enqueue binds one ID');
 api.startNewEvent();const mutable={title:'captured before await'},capture=api.enqueue(mutable);mutable.title='changed after call';const captured=await capture;assert.equal(captured.body.payload.title,'captured before await');
 const beforeFirst=JSON.stringify([...store]);current={uid:'fresh-crypto',emailVerified:true};ctx.crypto={subtle:webcrypto.subtle,randomUUID(){throw Error('crypto unavailable');}};await assert.rejects(api.enqueue(p),/crypto unavailable/);assert.equal(JSON.stringify([...store]),beforeFirst,'default first-submit crypto failure changes no storage');
 console.log('PASS CR-1: distinct identical events; exact ACK-loss/reload/double-submit identity; immutable payload; UID isolation; crypto failure; pending retention; stale binding refused');
})().catch(e=>{console.error(e);process.exitCode=1;});
