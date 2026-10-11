/* Isolated receiving reader: no IO, persistence, exports or ID synthesis.
   Intake remains responsible for authoritative full contract validation. */
(function(root){
'use strict';
const SCHEMA='mhpss-5ws-session/0.3.0-review';
const LEGACY=['0.2.0','0.3.0','0.4.0','0.5.0','0.6.0','0.7.0'].map(v=>'5ws-np-'+v);
const BANDS=[['04','0–4'],['5to9','5–9'],['10to19','10–19'],['20to59','20–59'],['60','60+']];
const CELLS=BANDS.flatMap(([key])=>['f','m','o'].map(s=>s+key));
// v2 contract: absent legacy cells are optional; supplied null means unknown.
const LEGACY_CELLS=['04','5to9','10to19','20to59','60','514','1549','5059','517','1859','U18','18'].flatMap(k=>['f','m','o'].map(s=>s+k));
const integer=v=>Number.isSafeInteger(v)&&v>=0;
const clone=x=>JSON.parse(JSON.stringify(x));
// Check before adding: never construct an unsafe/rounded numeric total.
function sum(xs,key){let n=0;for(const x of xs){const v=x[key];if(!integer(v)||v>Number.MAX_SAFE_INTEGER-n)return null;n+=v;}return n;}
function matrixSum(m){return sum(CELLS.map(k=>({value:m[k]})),'value');}
function matrixOverflow(m){return m && typeof m==='object' && !Array.isArray(m) && CELLS.every(k=>integer(m[k])) && matrixSum(m)===null;}
function matrixValid(m,total){return m===null || (m && typeof m==='object' && !Array.isArray(m) && Object.keys(m).length===CELLS.length && CELLS.every(k=>integer(m[k])) && matrixSum(m)===total);}
function aggregate(records,rejected=[],inheritedOverflow=[]){
 const metrics=['sessionAttendance','activityParticipations','staffSessions'],known={},overflow=[...inheritedOverflow];
 for(const metric of metrics){known[metric]=sum(records.filter(r=>r[metric]!==null),metric);if(known[metric]===null&&!overflow.some(e=>e.metric===metric))overflow.push({metric,message:'Aggregate overflow: '+metric+' exceeds the non-negative safe-integer range; all totals withheld.'});}
 const complete=rejected.length===0&&overflow.length===0;
 const activityComplete=complete&&records.every(r=>r.activityParticipations!==null),workforceComplete=complete&&records.every(r=>r.staffSessions!==null),attendanceComplete=complete&&records.every(r=>r.sessionAttendance!==null);
 return {complete,overflow,known:Object.fromEntries(metrics.map(k=>[k,complete?known[k]:null])),totals:{sessions:attendanceComplete?records.length:null,sessionAttendance:attendanceComplete?known.sessionAttendance:null,activityParticipations:activityComplete?known.activityParticipations:null,staffSessions:workforceComplete?known.staffSessions:null,uniquePeople:null,activityComplete,workforceComplete}};
}
function guard(r){
 if(!r || r.kind!=='activity') return 'Unsupported record kind: only activity projections are accepted.';
 if(typeof r.id!=='string'||!r.id.trim()) return 'Invalid record: source ID is required; IDs are never invented.';
 if(r.schema===SCHEMA){
  const p=r.payload;
  if(!p || p.schema!==SCHEMA) return 'Mismatch between wrapper and payload schema.';
  if(p.ageBandVersion!=='legacy-20260921') return 'Invalid ageBandVersion: unsupported bands for this schema.';
  if(matrixOverflow(p.sessionDisaggregation)||(Array.isArray(p.activities)&&p.activities.some(a=>a&&matrixOverflow(a.disaggregation)))) return 'Row overflow: age-cell matrix sum exceeds the non-negative safe-integer range.';
  if(!integer(r.revision)||!integer(p.attendance)||!matrixValid(p.sessionDisaggregation,p.attendance)) return 'Invalid session revision, attendance or disaggregation.';
  if(!Array.isArray(p.activities)||!p.activities.length||p.activities.some(a=>!a||typeof a.code!=='string'||!integer(a.attendance)||a.attendance>p.attendance||!matrixValid(a.disaggregation,a.attendance))||new Set(p.activities.map(a=>a.code)).size!==p.activities.length) return 'Invalid activity attendance or matrix: each activity counts separately within session attendance.';
  if(!Array.isArray(p.cadres)||!p.cadres.length||p.cadres.some(c=>!c||typeof c.code!=='string'||!integer(c.count))||new Set(p.cadres.map(c=>c.code)).size!==p.cadres.length) return 'Invalid cadre count.';
  if(sum(p.activities,'attendance')===null) return 'Row overflow: activityParticipations exceeds the non-negative safe-integer range.';
  if(sum(p.cadres,'count')===null) return 'Row overflow: staffSessions exceeds the non-negative safe-integer range.';
  return '';
 }
 const explicit=LEGACY.some(v=>r.schema==='mhpss-np-5ws/'+v)||(r.schema===undefined&&LEGACY.includes(r.schemaVersion));
 if(!explicit) return 'Unsupported schema: this candidate does not infer unknown or future versions.';
 if(r.payload!==undefined) return 'Invalid legacy record: nested session payload is not a legacy activity.';
 if(r.schemaVersion!==undefined&&!LEGACY.includes(r.schemaVersion)) return 'Unsupported legacy schemaVersion.';
 if(!integer(r.reachedTotal)) return 'Invalid legacy attendance: no coercion to zero.';
 const invalid=LEGACY_CELLS.filter(k=>Object.hasOwn(r,k)&&r[k]!==null&&!integer(r[k]));
 if(invalid.length) return 'Invalid legacy age cell(s): '+invalid.join(', ')+'. Supplied cells must be null (unknown) or non-negative safe integers; no coercion or key loss.';
 return '';
}
function read(rows){
 if(!Array.isArray(rows)) throw new TypeError('Reader requires an array of activity projections.');
 const rejected=[],records=[],idCounts=new Map();
 rows.forEach(r=>{if(r&&typeof r.id==='string')idCounts.set(r.id,(idCounts.get(r.id)||0)+1);});
 rows.forEach((source,index)=>{
  const message=source&&idCounts.get(source.id)>1?'Repeated source ID: current-document snapshot must contain exactly one row per ID; all repeated rows excluded.':guard(source);
  if(message){rejected.push({index,id:source&&source.id||null,message});return;}
  const r=clone(source);
  if(r.schema===SCHEMA){
   const p=r.payload;
   records.push({type:'session',id:r.id,revision:r.revision,schema:r.schema,payload:p,under18:null,
    ageBands:BANDS.map(([key,label])=>({key,label,f:p.sessionDisaggregation?p.sessionDisaggregation['f'+key]:null,m:p.sessionDisaggregation?p.sessionDisaggregation['m'+key]:null,o:p.sessionDisaggregation?p.sessionDisaggregation['o'+key]:null})),
    sessionAttendance:p.attendance,sessionDisaggregation:p.sessionDisaggregation,activities:p.activities,cadres:p.cadres,
    activityParticipations:sum(p.activities,'attendance'),staffSessions:sum(p.cadres,'count')});
  }else{
   records.push({type:'legacy',id:r.id,revision:r.revision,schema:r.schema,original:r,
    sessionAttendance:r.countBasis==='CONTACTS'?r.reachedTotal:null,activityParticipations:null,staffSessions:null});
  }
 });
 return {records,rejected,...aggregate(records,rejected)};
}
root.SESSION_READER={SCHEMA,CONTRACT:'hub-reader/2-safe-counts',LEGACY_CELLS:Object.freeze(LEGACY_CELLS),aggregate,read};
})(window);
