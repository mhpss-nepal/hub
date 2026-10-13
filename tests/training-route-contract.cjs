/* Real frontend client against route literals in the pinned backend adapter.
   No fictional route is accepted by this test transport. */
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const backend=process.env.MHPSS_BACKEND||'/root/mhpss-nepal-final-forms/2026-10-06/48-historical-analytics/backend';
const source=fs.readFileSync(backend+'/functions/adapter.py','utf8');
assert(source.includes('/training/current'));assert(!source.includes('/dashboard/training'));
const paths=[];const user={uid:'synthetic-admin',emailVerified:true};const window={localStorage:{getItem:()=>null}};
vm.runInNewContext(fs.readFileSync('assets/training-api.js','utf8'),{window,crypto:require('crypto').webcrypto,TextEncoder,AbortController,setTimeout,clearTimeout,URL,fetch:async(url)=>{const path=new URL(url).pathname;paths.push(path);const exists=source.includes("'"+path+"'")||source.includes('"'+path+'"');return {status:exists?200:404,text:async()=>JSON.stringify({protocol:'training-list/1',rows:[],complete:true,nextCursor:null})};}});
(async()=>{const api=window.TRAINING_API.create({currentUser:()=>user,token:async()=>'synthetic'});await api.current(true);await api.current(false);await api.entries();assert.deepEqual(paths,['/training/current','/training/current','/training/entries']);console.log('PASS actual backend route contract: admin and ordinary current; own entries');})().catch(e=>{console.error(e);process.exitCode=1});
