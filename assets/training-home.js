/* Independent training capability discovery. STAFF_API.SECTIONS stays unchanged. */
(function(){'use strict';const api=TRAINING_API.create(BaselineAuth);let epoch=0;const nodes=[];function clear(){epoch++;api.invalidate();nodes.splice(0).forEach(n=>n.remove());}function link(parent,text,url){const a=document.createElement('a');a.textContent=text;a.href=url;a.className='secondary';parent?.append(a);nodes.push(a);return a;}
BaselineAuth.onChange((u)=>{clear();if(!u||u.emailVerified!==true)return;const mine=epoch;
api.entries().then(()=>{if(mine!==epoch)return;link(document.querySelector('#entries .workactions'),'My received training history (separate)','training.html?view=own');link(document.getElementById('formList'),'Training and orientation — separate reporter approval required','../form/training-report.html');}).catch(()=>{});
api.current().then(()=>{if(mine!==epoch)return;link(document.querySelector('#dashboard .dashbar'),'Training results (separately authorized)','training.html?view=current');link(document.getElementById('main'),'Training results — separate approved capability','training.html?view=current');}).catch(()=>{});
});window.addEventListener('offline',clear);
})();
