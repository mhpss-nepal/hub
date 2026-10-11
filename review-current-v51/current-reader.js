/* Read-only exact-schema adapter. No Firestore SDK, queue, write or legacy fallback. */
(function(root){'use strict';
const SCHEMA='mhpss-5ws-session/0.4.0-approved-joint-review',SCOPE='reporter-own-org-current',OP='mhpss-5ws-operational/2-candidate',BASE='https://mhpss5ws-tdp3xtfnsq-as.a.run.app';
const exact=(o,keys)=>o&&typeof o==='object'&&!Array.isArray(o)&&Object.keys(o).sort().join(',')===keys.split(',').sort().join(',');
const id=v=>typeof v==='string'&&/^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/.test(v)&&!/[\r\n]/.test(v);
const stamp=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+]00:00)$/.test(v)&&Number.isFinite(Date.parse(v));
function validateRow(r,org){
 if(!exact(r,'id,document_path,kind,schema,operational_schema,revision,event_id,request_sha256,payload,created_at,updated_at')||!id(r.id)||r.document_path!=='mhpss5wsReportsV2/'+r.id||r.kind!=='activity'||r.schema!==SCHEMA||r.operational_schema!==OP||!Number.isSafeInteger(r.revision)||r.revision<1||r.revision>2147483647||typeof r.event_id!=='string'||!(/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/).test(r.event_id)||typeof r.request_sha256!=='string'||!(/^[a-f0-9]{64}$/).test(r.request_sha256)||!stamp(r.created_at)||!stamp(r.updated_at)||r.payload?.schema!==SCHEMA||r.payload?.org!==org||root.JOINT.validate(r.payload).length)throw Error('Exact approved joint current row required; legacy/TEST data are not substituted');
 return r;
}
function state(rows,org){rows.forEach(r=>validateRow(r,org));const s=root.JOINT_HUB.load(rows);if(!s.complete||s.rejected.length||s.overflow.length||s.records.length!==rows.length)throw Error('Complete validated joint state required');return s;}
function create(auth){
 let generation=0,installed=null,controller=null;
 const user=()=>{const u=auth.currentUser();if(!u||u.emailVerified!==true||typeof u.uid!=='string'||!u.uid||typeof u.getIdToken!=='function')throw Error('Verified sign-in and an explicit institutional reporter grant required');return u;};
 function invalidate(){generation++;installed=null;if(controller)controller.abort();controller=null;}
 function view(){if(!installed||user()!==installed.owner||Date.now()-installed.at>240000){invalidate();throw Error('Refresh a complete authorised snapshot before viewing or exporting');}return installed;}
 async function refresh(org){
  invalidate();const mine=generation,u=user();if(typeof org!=='string'||!/^[A-Z]{2,12}$/.test(org))throw Error('Enter the exact institution-assigned organisation code');
  const ctl=new AbortController();controller=ctl;const timer=setTimeout(()=>ctl.abort(),120000);const active=()=>{if(generation!==mine||auth.currentUser()!==u||ctl.signal.aborted)throw Error('Read superseded, expired or authentication changed');};
  try{const token=await auth.token();active();let cursor=null,readTime=null,previous='',rows=[],pages=0;const seen=new Set();
   do{active();if(++pages>50)throw Error('Read budget reached; partial snapshot withheld');
    const response=await fetch(BASE+'/current',{method:'GET',headers:{Authorization:'Bearer '+token,'X-Selected-Org':org,...(cursor===null?{}:{'X-Listing-Cursor':cursor})},cache:'no-store',credentials:'omit',redirect:'error',signal:ctl.signal});active();
    if(!response.ok)throw Error('Current read refused (HTTP '+response.status+'). Sign-in is not reporter entitlement; no cached success or historical substitution.');
    const text=await response.text();active();if(text.length>2000000)throw Error('Page byte budget exceeded');const d=JSON.parse(text);
    if(!exact(d,'protocol,rows,scope,pageComplete,snapshotComplete,readTime,pageCount,nextCursor')||d.protocol!=='own-current-pages/1'||d.scope!==SCOPE||d.pageComplete!==true||!Array.isArray(d.rows)||d.rows.length>10||d.pageCount!==d.rows.length||!stamp(d.readTime)||d.snapshotComplete!==(cursor===null&&d.nextCursor===null)||(d.nextCursor!==null&&(typeof d.nextCursor!=='string'||!/^[A-Za-z0-9_-]{1,2048}$/.test(d.nextCursor)))||(d.nextCursor!==null)!==(d.rows.length===10)||(readTime!==null&&readTime!==d.readTime))throw Error('Mixed, malformed or incomplete snapshot refused');
    readTime=d.readTime;for(const r of d.rows){validateRow(r,org);if(r.id<=previous)throw Error('Duplicate or unordered current identity refused');previous=r.id;rows.push(r);}if(rows.length>500)throw Error('Report budget reached; partial snapshot withheld');
    cursor=d.nextCursor;if(cursor!==null){if(seen.has(cursor))throw Error('Cursor replay refused');seen.add(cursor);}
   }while(cursor!==null);
   const parsed=state(rows,org);active();installed={owner:u,org,readTime,rows,parsed,pages,at:Date.now()};return {superseded:false,count:rows.length,readTime,pages};
  }catch(e){if(mine!==generation)return {superseded:true};installed=null;throw e;}
  finally{clearTimeout(timer);if(controller===ctl)controller=null;}
 }
 function filtered(filters={}){const s=view();if(!exact(filters,'district,from,through')||typeof filters.district!=='string'||typeof filters.from!=='string'||typeof filters.through!=='string'||[filters.from,filters.through].some(x=>x!==''&&!/^\d{4}-\d{2}-\d{2}$/.test(x))||(filters.from&&filters.through&&filters.from>filters.through))throw Error('Valid date and district filters required');const rows=s.rows.filter(r=>(!filters.district||r.payload.district===filters.district)&&(!filters.from||r.payload.dateAD>=filters.from)&&(!filters.through||r.payload.dateAD<=filters.through));return {...s,rows,parsed:state(rows,s.org),filters};}
 function csv(filters){const s=filtered(filters),meta=[s.readTime,s.org,s.rows.length,s.rows.length===s.parsed.records.length,JSON.stringify(s.filters)],byID=new Map(s.rows.map(r=>[r.id,r]));const cell=v=>'"'+String(v).replace(/"/g,'""')+'"';const matrix=root.JOINT_HUB.exportCSV(s.parsed).trimEnd().split(/\r?\n/);return matrix.map((line,i)=>{if(!i)return 'snapshot_read_time,selected_org,filtered_report_count,validated_complete,filter_definition,event_id,request_sha256,document_path,created_at,updated_at,'+line;const r=byID.get(line.split(',')[0]);if(!r)throw Error('CSV source identity mismatch');return [...meta,r.event_id,r.request_sha256,r.document_path,r.created_at,r.updated_at].map(cell).join(',')+','+line;}).join('\r\n')+'\r\n';}
 return Object.freeze({refresh,invalidate,view,filtered,csv});
}
root.CURRENT_READER=Object.freeze({create,validateRow,state,SCHEMA,SCOPE});
})(window);
