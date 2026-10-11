/* Release regression: exercise tracked bytes, not an ignored local fixture. */
'use strict';
const fs=require('fs'),path=require('path'),os=require('os'),assert=require('assert'),cp=require('child_process');
const root=path.resolve(__dirname,'../..'), fixture='tests/current-v51/native-wire.json';
const run=(args,options={})=>cp.execFileSync(args[0],args.slice(1),{cwd:root,...options});
const committed=run(['git','show','HEAD:'+fixture]);
assert(committed.equals(fs.readFileSync(path.join(root,fixture))),'Fixture must match the committed candidate');
const wire=JSON.parse(committed);
assert.equal(wire.siteOther,'SYNTHETIC community venue');
assert.equal(wire.description,'');assert.equal(wire.coordinationNotes,'');assert.deepEqual(wire.partners,[]);
const runtime=run(['git','ls-tree','-r','--name-only','HEAD','review-current-v51'],{encoding:'utf8'}).trim().split('\n');
for(const name of runtime){
 const bytes=run(['git','show','HEAD:'+name],{encoding:'utf8'});
 assert(!bytes.includes('native-wire.json')&&!bytes.includes('tests/current-v51'),'Runtime must not load test fixtures');
}
const scratch=process.env.TMPDIR;
assert(scratch&&path.isAbsolute(scratch),'An explicit private scratch TMPDIR is required');
fs.mkdirSync(scratch,{recursive:true});
const dir=fs.mkdtempSync(path.join(scratch,'current-reader-package-'));
try{
 const archive=run(['git','archive','HEAD','review-current-v51','tests/current-v51']);
 run(['tar','-xf','-','-C',dir],{input:archive});
 const result=run([process.execPath,path.join(dir,'tests/current-v51/reader.cjs')],{cwd:dir,encoding:'utf8'});
 assert(result.includes('"completion":"ALL_CASES_COMPLETED"'));
 process.stdout.write(result);
 console.log(JSON.stringify({completion:'PACKAGED_CANDIDATE_COMPLETED',fixtureTracked:true,runtimeFixtureReferences:0}));
}finally{fs.rmSync(dir,{recursive:true,force:true});}
