/* Native form bridge. Validation/UI retained; parent owns delivery and receipts. */
(()=>{'use strict';const form=document.getElementById('f'),old=form.onsubmit;
for(const id of ['iuPreviewNotice','iuSyncStatus'])document.getElementById(id).textContent='Restricted 5Ws reporting · explicit reporter access required. Submit saves a device request; only a matched receipt confirms server storage.';
const ribbon=document.querySelector('.ribbon');if(ribbon)ribbon.textContent='5Ws field report · no client names or individual clinical information';
document.querySelector('[data-iu-operational-copy="offline"]').textContent='Keep this page open if the connection fails. Pending submitted requests are retained on this browser for the same signed-in account. Offline page reload is not certified. Reconnect and sign in to retry. Do not clear browser storage.';
document.querySelector('[data-iu-operational-copy="save"]').textContent='Submit validates and saves an immutable request on this device, then requests a storage receipt. A network success alone is not delivery.';
const sample=document.getElementById('syntheticExample');sample.hidden=true;
for(const x of document.querySelectorAll('button[type=submit]'))x.textContent='Save and send report';
const notice=document.createElement('p');notice.id='authenticatedSubmitState';notice.setAttribute('role','status');form.after(notice);
form.onsubmit=async e=>{old(e);if(!window.REVIEW_RESULT)return;document.getElementById('reviewProjection').hidden=true;try{const result=await parent.FIELD_JOURNEY.submit(window.REVIEW_RESULT.record);notice.textContent=result.state==='remotely_acknowledged'?'Server storage receipt matched for '+result.session+' · revision '+result.receipt.revision+'. Check delivery status above for dashboard visibility.':'Saved on this device, awaiting connection/retry. Do not clear browser storage.';}catch(e){notice.textContent='Not confirmed stored on server. '+String(e)+'. Keep the form open; check pending/recovery above before retrying.';}};
})();
