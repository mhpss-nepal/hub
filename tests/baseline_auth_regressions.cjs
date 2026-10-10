// Actual Auth module with synthetic SDK only; no credentials or external calls.
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../assets/baseline-auth.js'), 'utf8');
const turn = () => new Promise(resolve => setImmediate(resolve));
async function fixture(options = {}) {
  let callback, finishSignout, finishSignin, finishToken;
  const events = [], storage = new Map();
  const user = { getIdToken: async () => { events.push('token'); if (options.holdToken) return new Promise(r => { finishToken = r; }); return 'synthetic-token'; } };
  const sdk = {
    getAuth: () => ({}), browserLocalPersistence: {}, setPersistence: async () => {},
    onIdTokenChanged: (auth, f) => { callback = f; f(options.signedIn ? user : null); },
    isSignInWithEmailLink: () => !!options.link,
    signInWithEmailLink: async () => { events.push('finishLink'); if (options.rejectLink) throw Error('synthetic failure'); callback(user); return {user}; },
    signInWithEmailAndPassword: async () => { events.push('signIn'); if (options.holdSignin) await new Promise(r => { finishSignin = r; }); if (options.rejectSignin) throw Error('synthetic failure'); callback(user); return {user}; },
    signOut: async () => { events.push('signOut'); if (options.holdSignout) await new Promise(r => { finishSignout = r; }); if (options.rejectSignout) throw Error('synthetic failure'); callback(null); },
    sendSignInLinkToEmail: async () => { events.push('sendLink'); }
  };
  const sandbox = {
    window: {FB_CONFIG:{}}, location:{href:'https://fixture.invalid/?mode=signIn&oobCode=synthetic',origin:'https://fixture.invalid',pathname:'/index.html'},
    document:{title:'Fixture'}, history:{replaceState:()=>events.push('stripURL')},
    localStorage:{getItem:k=>{if(options.deniedStorage)throw Error('denied');return storage.get(k)||null},setItem:(k,v)=>{if(options.deniedStorage)throw Error('denied');storage.set(k,v)},removeItem:k=>{if(options.deniedStorage)throw Error('denied');storage.delete(k)}},
    sdkImport: async url => url.endsWith('firebase-app.js') ? {getApps:()=>[],initializeApp:()=>({})} : sdk,
    Error, Object
  };
  // Replace only the loader expression; run all shipped control flow unchanged.
  vm.runInNewContext(source.replaceAll('import(', 'sdkImport('), sandbox);
  await turn();
  return {auth:sandbox.window.BaselineAuth,events,user,emit:value=>callback(value),finishSignout:()=>finishSignout(),finishSignin:()=>finishSignin(),finishToken:()=>finishToken('synthetic-token'),options};
}
(async () => {
  const f = await fixture({signedIn:true,holdSignout:true,rejectSignout:true});
  const changes=[];f.auth.onChange(u=>changes.push(u));
  const pending=f.auth.signOut().catch(()=>{});
  assert.equal(f.auth.currentUser(),null,'F1: intent immediately hides the SDK user');
  await assert.rejects(f.auth.token(),/Sign in required/);
  f.emit(f.user);assert.equal(f.auth.currentUser(),null,'same old callback cannot unlock pending intent');
  await turn();f.finishSignout();await pending;
  f.emit(f.user);assert.equal(f.auth.currentUser(),null,'same old callback cannot unlock rejected intent');
  f.emit(null);f.emit(f.user);assert.equal(f.auth.currentUser(),null,'callback cycling is not an explicit sign-in');
  f.options.rejectSignin=true;await assert.rejects(f.auth.signIn('fixture@example.invalid','synthetic-not-a-credential'));
  assert.equal(f.auth.currentUser(),null,'failed sign-in cannot unlock');
  f.options.rejectSignin=false;f.options.holdSignin=true;
  const login=f.auth.signIn('fixture@example.invalid','synthetic-not-a-credential');await turn();
  f.emit(f.user);assert.equal(f.auth.currentUser(),null,'callback before explicit sign-in resolves cannot unlock');
  f.finishSignin();await login;assert.equal(f.auth.currentUser(),f.user,'completed explicit sign-in restores access');
  const t=await fixture({signedIn:true,holdToken:true});const token=t.auth.token();await turn();const out=t.auth.signOut();t.finishToken();await assert.rejects(token,/Sign in required/);await out;
  const race=await fixture({signedIn:true,holdSignin:true});const oldLogin=race.auth.signIn('fixture@example.invalid','synthetic');await turn();await race.auth.signOut();race.finishSignin();await oldLogin;assert.equal(race.auth.currentUser(),null,'signout supersedes earlier sign-in');
  console.log('PASS F1 Auth intent barrier, rejected/pending sign-out, callback/token/sign-in races');
  for (const deniedStorage of [false,true]) {
    const link=await fixture({link:true,deniedStorage});
    let state;link.auth.onChange((u,s)=>{state=s;});
    assert.equal(state.ready,true,'F3 missing hint must not poison initialization');
    assert.ok(state.error.includes('email'),'missing hint gives actionable address guidance');
    assert.ok(!link.events.includes('stripURL'),'uncompleted link retains URL');
    await link.auth.sendLink('fixture@example.invalid');assert.ok(link.events.includes('sendLink'),'replacement request reaches SDK even without storage');
    await link.auth.signIn('fixture@example.invalid','synthetic');assert.ok(link.auth.currentUser(),'password recovery remains usable');
    assert.ok(!link.events.includes('stripURL'),'password recovery is not completion of the email link');
  }
  const failed=await fixture({link:true,rejectLink:true});
  await assert.rejects(failed.auth.finishLink('fixture@example.invalid'));
  assert.ok(!failed.events.includes('stripURL'),'failed link does not strip credentials');
  failed.options.rejectLink=false;await failed.auth.finishLink('fixture@example.invalid');
  assert.ok(failed.events.includes('stripURL'),'only actual link success strips URL');
  assert.ok(failed.auth.currentUser(),'address reentry completes link');
  console.log('PASS F3 missing/denied hint storage, replacement/password recovery, retry and successful-only URL stripping');
})().catch(e=>{console.error(e);process.exitCode=1});
