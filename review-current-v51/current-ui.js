(function(){'use strict';
const $=id=>document.getElementById(id),reader=CURRENT_READER.create(BaselineAuth);
let authority=0,profile=null,reading=null,authState={};
const notice=t=>{$('status').textContent=t;};
function clear(){authority++;profile=null;reading=null;reader.invalidate();$('org').value='';$('fieldPanel').hidden=true;$('result').hidden=true;$('rows').replaceChildren();$('metrics').textContent='';$('source').textContent='';$('export').disabled=true;}
const filters=()=>({district:$('district').value,from:$('from').value,through:$('through').value});
function paint(){try{const d=reader.filtered(filters()),s=d.parsed.summary;$('rows').replaceChildren();for(const r of d.parsed.records){const tr=document.createElement('tr');for(const value of [r.id,r.revision,r.payload.dateAD,r.payload.district,r.sessionAttendance,r.activityParticipations,r.staffSessions]){const td=document.createElement('td');td.textContent=String(value);tr.append(td);}$('rows').append(tr);}$('source').textContent='Source: own-current-pages/1 · schema '+CURRENT_READER.SCHEMA+' · organisation '+d.org+' · fixed snapshot '+d.readTime+' · '+d.pages+' page(s) · complete authorised snapshot';$('metrics').textContent=s.acceptedReports+' reports · '+s.sessionAttendance+' session attendances · '+s.activityParticipations+' activity participations · '+s.staffSessions+' staff-sessions · unique people unknown';$('result').hidden=false;$('export').disabled=false;}catch(e){clear();window.dispatchEvent(new Event('reporting-access-lost'));notice(String(e));throw e;}}
// One discovery/read lane per owner. Read consumers share its completion, never
// invalidate it by probing view(). A changed auth generation rejects old callers.
function refresh(){
 const u=BaselineAuth.currentUser();
 if(reading&&reading.owner===u)return reading.job;
 clear();const mine=authority;
 window.dispatchEvent(new Event('reporting-reading'));
 if(!u||!u.emailVerified){notice(u?'Verified email required. No report data loaded.':'Sign in required. No current report data loaded.');window.dispatchEvent(new Event('reporting-access-lost'));return Promise.reject(Error('Verified sign-in required'));}
 const active=()=>{if(mine!==authority||BaselineAuth.currentUser()!==u)throw Error('Reporting read superseded by authentication or refresh change');};
 notice('Reading a bounded fixed-time snapshot; table and CSV withheld until complete.');
 const job=(async()=>{try{
  const token=await BaselineAuth.token();active();
  const r=await fetch('https://mhpss5ws-tdp3xtfnsq-as.a.run.app/profile',{headers:{Authorization:'Bearer '+token},cache:'no-store',credentials:'omit',redirect:'error',signal:AbortSignal.timeout(15000)});active();
  if(r.status!==200)throw Error('Reporting access unavailable (HTTP '+r.status+'). Retry access; no reports loaded.');
  const v=await r.json();active();
  if(v.protocol!=='own-reporter-profile/1')throw Error('Reporting access response refused');
  if(v.access==='no_access'&&v.reason==='enabled_reporter_grant_required')throw Error('Signed in, but no enabled reporter assignment. Ask your reporting coordinator; administrator access alone does not permit reporting.');
  if(v.access!=='reporter'||Object.keys(v).sort().join(',')!=='access,org,protocol'||typeof v.org!=='string'||!/^[A-Z]{2,12}$/.test(v.org))throw Error('Reporting access response refused');
  const d=await reader.refresh(v.org);active();if(d.superseded)throw Error('Reporting snapshot superseded');
  const snapshot=reader.view();if(snapshot.owner!==u||snapshot.org!==v.org)throw Error('Reporting snapshot owner changed');
  const districts=[...new Set(snapshot.rows.map(r=>r.payload.district))].sort();$('district').replaceChildren(new Option('All districts',''),...districts.map(x=>new Option(x,x)));
  paint();active();profile={owner:u,org:v.org};$('org').value=v.org;
  notice('Signed in. Reporting access verified for '+v.org+'. Own reports loaded.');window.dispatchEvent(new Event('reporting-ready'));return profile;
 }catch(e){if(mine===authority){clear();window.dispatchEvent(new Event('reporting-access-lost'));notice(String(e));}throw e;}
 finally{if(reading?.job===job)reading=null;}})();
 reading={owner:u,job};return job;
}
const requestRefresh=()=>refresh().catch(()=>{});
$('refresh').onclick=requestRefresh;for(const id of ['district','from','through'])$(id).onchange=()=>{try{paint();}catch(e){}};
$('export').onclick=()=>{try{const text=reader.csv(filters()),url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download='own-current-joint.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){clear();window.dispatchEvent(new Event('reporting-access-lost'));notice(String(e));}};
$('signIn').onclick=()=>BaselineAuth.sendLink($('email').value).then(()=>notice('Email sign-in link requested. Reporter access still requires your assigned grant.')).catch(()=>notice('Could not request sign-in link.'));
$('finishLink').onclick=()=>BaselineAuth.finishLink($('email').value).catch(()=>notice(authState.error||'Email sign-in could not complete (auth/unknown). Existing sign-in has not been cleared.'));
$('signOut').onclick=()=>{clear();BaselineAuth.signOut().catch(()=>notice('Sign-out provider unavailable; reader remains cleared.'));};
BaselineAuth.onChange((u,s)=>{authState=s;const restoring=s.restoration==='restoring';$('signIn').disabled=restoring||!s.ready;$('finishLink').disabled=restoring||!s.ready;if(!u||s.linkPending){clear();window.dispatchEvent(new Event('reporting-access-lost'));}$('signIn').hidden=!!u||!!s.linkPending;$('email').hidden=!!u;$('finishLink').hidden=!s.linkPending;$('signOut').hidden=!u;if(u&&!s.linkPending)requestRefresh();else notice(s.error||(restoring?'Restoring your browser sign-in… No new email link is needed while this check runs.':u?'Signed in. Discovering reporting access…':'Sign in required. No current report data loaded.'));});
window.addEventListener('offline',()=>{clear();window.dispatchEvent(new Event('reporting-access-lost'));notice('Offline. No cached current success or CSV available.');});setInterval(()=>{if($('result').hidden)return;try{reader.view();}catch(e){clear();window.dispatchEvent(new Event('reporting-access-lost'));notice('Snapshot expired or sign-in changed. Refresh before viewing or exporting.');}},1000);
window.CURRENT_UI=Object.freeze({refresh,reader,clear,paint,profile:()=>profile,state:()=>({generation:authority,reading:!!reading,ready:!!profile,ownerCurrent:!!profile&&profile.owner===BaselineAuth.currentUser()})});})();
