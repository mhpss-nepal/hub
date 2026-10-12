/* Actual reader callback regression: initial null is a settled state. */
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const nodes=new Map(); const get=id=>{if(!nodes.has(id))nodes.set(id,{textContent:id==='trainingReadStatus'?'Restoring persistent sign-in…':'',disabled:true,hidden:true,replaceChildren(){this.cleared=true;}});return nodes.get(id);};
let observer,invalidations=0,reads=0;
vm.runInNewContext(fs.readFileSync('assets/training-reader.js','utf8'),{BaselineAuth:{onChange(fn){observer=fn;}},TRAINING_API:{create(){return {invalidate(){invalidations++;},entries(){reads++;throw Error('unexpected read');},current(){reads++;throw Error('unexpected read');}};}},document:{getElementById:get,createElement(){return {};}},location:{search:'?view=own'},URLSearchParams,window:{addEventListener(){}},setInterval(){},Date,Number,Error});
observer(null,{ready:false,error:''});
assert.equal(get('trainingReadStatus').textContent,'Restoring persistent sign-in…');
observer(null,{ready:true,error:''});
assert.match(get('trainingReadStatus').textContent,/Sign in at Home/);
assert.equal(get('trainingExport').disabled,true);
assert.equal(get('trainingTotals').textContent,'');
assert.equal(reads,0);
observer(null,{ready:true,error:'Email sign-in link could not be completed.'});
assert.equal(get('trainingReadStatus').textContent,'Email sign-in link could not be completed.');
assert.equal(reads,0);assert.equal(invalidations,2);
console.log('PASS actual reader initial signedout and safe error states');
