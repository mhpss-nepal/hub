from pathlib import Path
import re
R=Path(__file__).resolve().parents[1]; p=R/'index.html'; s=p.read_text()
# Repaint and rearrange this document only. Preserve existing runtime scripts.
css='''
/* Reference4 entry correction: page-local horizontal shell, no shared CSS. */
body.hub.dashboard-selected{padding-left:0;--who:#2d79d7;--who-d:#1d3d60;--who-dd:#1d3d60}
body.hub.dashboard-selected .top{padding:18px 28px;background:#1d3d60;display:flex;align-items:center}
body.hub.dashboard-selected .top h1{margin:0;font:700 25px/1.25 Arial,sans-serif;color:#fff}
body.hub.dashboard-selected .top .sub{margin-top:5px;font-size:13px;letter-spacing:0;text-transform:none;font-weight:400}
body.hub.dashboard-selected .rail{position:static;inset:auto;width:auto;overflow:visible;display:flex;align-items:center;flex-wrap:wrap;gap:8px;padding:0 28px;background:white;border:0;border-bottom:1px solid #d8e1ec}
body.hub.dashboard-selected .rail :is(.railid,.where,.rmenu,.rfoot){display:none}
body.hub.dashboard-selected .rail nav{display:flex;flex:1 1 auto;flex-direction:row;align-items:center;flex-wrap:wrap;padding:0;max-height:none;overflow:visible;gap:4px}
body.hub.dashboard-selected .rail .rg{margin:0;position:relative}
body.hub.dashboard-selected .rail .rg[data-g=coord]>.rgh{display:none}
body.hub.dashboard-selected .rail .rgb{border:0;margin:0;padding:0}
body.hub.dashboard-selected .rail .rg.open>.rgb{display:flex;flex-wrap:wrap;gap:2px}
body.hub.dashboard-selected .rail .rgb>a{padding:11px 10px;font-size:12px;min-height:44px;display:inline-flex;align-items:center;border-radius:0;box-shadow:none;white-space:normal}
body.hub.dashboard-selected .rail .rgb>a.on{background:#edf4fa;box-shadow:inset 0 -3px #2d79d7}
body.hub.dashboard-selected .rail .rgh{min-height:44px;padding:8px 10px;font-size:12px}
body.hub.dashboard-selected .rail .rgh :is(em,.dot){display:none}
body.hub.dashboard-selected .rail .rg:not([data-g=coord]).open>.rgb{position:absolute;right:0;top:100%;z-index:45;width:200px;background:#fff;border:1px solid #d8e1ec;border-radius:8px;padding:8px;box-shadow:0 5px 12px #1d3d6020}
body.hub.dashboard-selected .rail .railtoggle{padding:0;margin:0;display:inline-flex}
body.hub.dashboard-selected #band{background:transparent!important;color:#455569!important;border:0;padding:0!important;text-align:left;font-size:12px;margin:0}
body.hub.dashboard-selected #band span{color:#455569!important}
body.hub.dashboard-selected .wrap.wide{max-width:1600px;margin:0 auto;padding:16px 28px 48px}
body.hub.dashboard-selected #loader{padding:0;border:0;background:transparent;margin-bottom:14px}
body.hub.dashboard-selected .source-start{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:8px}
body.hub.dashboard-selected .source-start .btn{background:#1d3d60;color:#fff;font-size:13px}
body.hub.dashboard-selected #access-options{border:1px solid #d8e1ec;background:#fff;border-radius:8px;padding:0 14px}
body.hub.dashboard-selected #access-options>summary{font-size:13px;padding:10px 0;min-height:44px}
body.hub.dashboard-selected #drop{padding:12px 0;border:0;border-radius:0;text-align:left;background:transparent}
body.hub.dashboard-selected #drop .btns{justify-content:flex-start!important}
body.hub.dashboard-selected #drop hr{margin:12px 0!important}
body.hub.dashboard-selected #drop p{max-width:95ch;font-size:13px}
body.hub.dashboard-selected #drop .row{gap:12px}
body.hub.dashboard-selected #drop .row input{max-width:100%}
body.hub.dashboard-selected .entry-filters{display:flex;gap:8px;flex-wrap:wrap;padding:12px;background:white;border:1px solid #d8e1ec;border-radius:10px;font-size:12px;color:#455569}
body.hub.dashboard-selected .entry-filters span{border:1px solid #d8e1ec;border-radius:6px;padding:9px 12px}
body.hub.dashboard-selected .entry-filters p{margin:0;align-self:center}
body.hub.dashboard-selected .entry-note{font-size:12px;color:#455569;margin:0 0 12px}
body.hub.dashboard-selected .entry-row{display:grid;grid-template-columns:210px 1fr 22px;gap:12px;align-items:center;margin:18px 0;font-size:13px;color:#455569}
body.hub.dashboard-selected .entry-track{height:14px;border-radius:2px;background:#f3f6f9}
body.hub.dashboard-selected .entry-time{display:flex;align-items:center;justify-content:center;min-height:160px;background:#f8fafc;border-radius:6px;color:#455569;font-size:13px}
body.hub.dashboard-selected .entry-secondary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
body.hub.dashboard-selected .entry-secondary .ovcolb{min-height:100px}
body.hub.dashboard-selected .stats{margin:14px 0;gap:12px}
body.hub.dashboard-selected .stat{min-height:130px;padding:16px 18px}
body.hub.dashboard-selected .stat .v{font-size:34px;color:#20313b}
body.hub.dashboard-selected .stat .k{font-size:11px;text-transform:uppercase;letter-spacing:.04em;font-weight:700}
body.hub.dashboard-selected .primary-grid{align-items:stretch}
body.hub.dashboard-selected .primary-grid>.ovcol{min-height:285px}
body.hub.dashboard-selected .ovcolh{border:0;padding:18px 20px 6px}
body.hub.dashboard-selected .ovcolh h2{font-size:18px;color:#20313b}
body.hub.dashboard-selected .ovcolb{padding:10px 20px 20px}
body.hub.dashboard-selected #ovFam .ovbt i{background:#2d79d7!important}
body.hub.dashboard-selected #ovFam .ovbt{height:18px}
body.hub.dashboard-selected #srcNote{margin-bottom:10px;padding:8px 12px;border:1px solid #d8e1ec;border-radius:8px;background:#fff;color:#455569;font-size:12px}
body.hub.dashboard-selected #srcNote::before{content:'Draft · ';font-weight:700}
body.hub.dashboard-selected .filters .grid{grid-template-columns:repeat(6,minmax(0,1fr));gap:8px 10px}
body.hub.dashboard-selected .filters .grid>.w2{grid-column:span 1}
body.hub.dashboard-selected .filters>summary{min-height:44px;padding:0}
body.hub.dashboard-selected .filters>summary .xs{display:none}
body.hub.dashboard-selected .filters label{color:#455569;font-size:10px}
body.hub.dashboard-selected .filters .grid input,body.hub.dashboard-selected .filters .grid select{min-width:0;width:100%;font-size:12px}
body.hub.dashboard-selected .analysis-detail{margin:16px 0}
body.hub.dashboard-selected #fbbar{position:static!important;margin:0 auto;font-size:12px!important}
body.hub.dashboard-selected #fbbar[data-observational=true]{background:#f3f6f9!important;color:#455569!important;border:0!important;padding:4px 28px!important;font-weight:400!important}
body.hub.dashboard-selected #fbbar:not([data-observational=true]){padding:8px 28px!important}
@media(max-width:1100px){body.hub.dashboard-selected .filters .grid{grid-template-columns:repeat(4,minmax(0,1fr))}}
@media(max-width:650px){
 body.hub.dashboard-selected .top{padding:16px 12px}body.hub.dashboard-selected .top h1{font-size:21px}
 body.hub.dashboard-selected .rail{padding:0 12px;gap:0}body.hub.dashboard-selected .rail nav{flex-basis:100%;gap:0}
 body.hub.dashboard-selected .rail .rgb>a{font-size:11px;padding:9px 7px}
 body.hub.dashboard-selected .rail .rg[data-g=coord]{flex-basis:100%}
 body.hub.dashboard-selected .rail .railtoggle{margin-left:auto}
 body.hub.dashboard-selected .wrap.wide{padding:12px}
 body.hub.dashboard-selected .source-start{align-items:flex-start;gap:8px}
 body.hub.dashboard-selected .source-start .btn{width:100%}
 body.hub.dashboard-selected .filters .grid{grid-template-columns:repeat(2,minmax(0,1fr))}
 body.hub.dashboard-selected .entry-filters{gap:6px;padding:10px}.entry-filters span{flex:1 1 auto}
 body.hub.dashboard-selected .entry-row{grid-template-columns:1fr 24px;gap:4px;font-size:12px;margin:14px 0}
 body.hub.dashboard-selected .entry-track{grid-column:1;grid-row:auto;height:8px}.entry-row b{grid-column:2;grid-row:span 2}
 body.hub.dashboard-selected .entry-secondary{grid-template-columns:1fr}
 body.hub.dashboard-selected .stat{min-height:108px;padding:12px}
 body.hub.dashboard-selected .primary-grid>.ovcol{min-height:240px}
 body.hub.dashboard-selected .ovcolh{padding:14px 14px 6px}body.hub.dashboard-selected .ovcolb{padding:10px 14px 14px}
 body.hub.dashboard-selected #fbbar[data-observational=true]{padding:4px 12px!important}
}
'''
s=s.replace('</style>\n</head>',css+'</style>\n</head>',1)
# Remove repeated headers, replace with one semantic masthead. Existing rail JS untouched.
a=s.index('<div class="topline">');z=s.index('<!--NAV:rail hubindex-->')
s=s[:a]+'''<header class="top"><div><h1>MHPSS 5Ws — coordination dashboard</h1><div class="sub">Nepal · Rasuwa / Bhote Koshi flood response · restricted coordination</div></div></header>

'''+s[z:]
a=s.index('<div id="band"');z=s.index('<main class="wrap wide"',a)
s=s[:a]+s[z:]
a=s.index('  <div class="card" id="loader">');z=s.index('    <div class="drop"',a)
s=s[:a]+'''  <div class="card" id="loader">
    <div class="source-start">
      <div id="band">Draft · No source loaded. Choose a source or explore the explicitly synthetic demo.</div>
      <button type="button" class="btn" id="useDemo">Explore synthetic demo</button>
    </div>
    <details id="access-options"><summary>Access live register or import a file</summary>
'''+s[z:]
s=s.replace('      <p style="margin:0 0 4px"><b>Read the live register</b> — every figure on the dashboard updates as reports arrive.</p>','      <p style="margin:0 0 8px"><b>Read the live register</b> — access is checked by the existing register service.</p>')
s=re.sub(r'      <p class="xs" style="margin:0 0 12px">A Firestore listener.*?</p>','      <p class="xs" style="margin:0 0 12px">Sign-in alone does not grant record access. The register enforces the account and role requirements. Files are read in this page, never uploaded.</p>',s,count=1)
s=s.replace('        <button type="button" class="btn grey" id="useDemo">Load synthetic demonstration data</button>\n','')
s=s.replace('      <p class="xs" style="margin:14px 0 0">Synthetic data is generated in the page and is not real. It exists so the dashboard can be shown before any operational data has been collected — which is also the position agreed while the three governance questions are open.</p>','      <p class="xs" style="margin:12px 0 0">The synthetic demo is generated locally and is not operational data. Coverage denominators use the holding-centre roster; loaded figures are not independently validated.</p>')
marker='''    </div>
  </div>

  <div id="app" hidden>'''
assert marker in s
kpis=['Reports','Attendances','Organisations reporting','Roster sites with a report','Palikas with a report']
shell='''    </div></details>
  </div>
  <section id="entry-shell" aria-label="Dashboard awaiting a data source">
    <div class="entry-filters" aria-label="Filters available after loading a source"><span>Period —</span><span>Province —</span><span>District —</span><span>Palika —</span><span>Organisation —</span><span>Activity layer —</span><span>Service setting —</span></div>
    <div class="stats">'''+''.join('<div class="stat"><div class="k">'+k+'</div><div class="v">—</div><div class="s">Awaiting a source</div></div>' for k in kpis)+'''</div>
    <p class="entry-note">No figures have been loaded. A dash means unavailable, not zero. Filters and analysis become available after you choose a source.</p>
    <div class="primary-grid">
      <section class="ovcol"><div class="ovcolh"><h2>What — attendances by IASC layer</h2></div><div class="ovcolb"><p class="xs">Reported activity, without an inferred unique-person count.</p>'''+''.join('<div class="entry-row"><span>'+k+'</span><span class="entry-track" aria-hidden="true"></span><b>—</b></div>' for k in ['Layer 1 · Basic services','Layer 2 · Community & family','Layer 3 · Focused support','Layer 4 · Specialist care'])+'''</div></section>
      <section class="ovcol"><div class="ovcolh"><h2>When — reports by day</h2></div><div class="ovcolb"><p class="xs">Dates follow the chosen period and date basis.</p><div class="entry-time">— &nbsp; No reports loaded</div></div></section>
    </div>
    <div class="entry-secondary">'''+''.join('<section class="ovcol"><div class="ovcolh"><h2>'+k+'</h2></div><div class="ovcolb"><p class="xs">— '+v+'</p></div></section>' for k,v in [('Who','Organisations reporting in the selection'),('For whom','Existing sex and age breakdowns'),('Where','Reported activity by palika')])+'''</div>
  </section>
  <div id="app" hidden>'''
s=s.replace(marker,shell,1)
s=s.replace('<details class="filters" id="filters">','<details class="filters" id="filters" open>',1)
s=s.replace('<details class="analysis-detail"><summary>Where and delivery status</summary>','<details class="analysis-detail" open><summary>Where and delivery status</summary>',1)
# Only runtime delta: signed-out root no longer implicitly requests restricted data.
s=s.replace('if (done || !st || !st.ready) return;','if (done || !st || !st.ready || !st.user) return;',1)
# Observational presentation: no bridge mutation, no auth/storage/data calls.
observer='''
<script>
/* Page-local presentation observer. Never changes FB state or handlers. */
(function () {
  var app=document.getElementById('app'), shell=document.getElementById('entry-shell');
  function syncEntry(){shell.hidden=!app.hidden;}
  new MutationObserver(syncEntry).observe(app,{attributes:true,attributeFilter:['hidden']});
  syncEntry();
  function observeBridge(){
    var bar=document.getElementById('fbbar'); if(!bar)return;
    var m=bar.querySelector('.m'); if(!m)return;
    /* Replace only the exact healthy delivery assertion. Every warning,
       pending indicator, error and bridge action remains visible unchanged. */
    if(!bar.classList.contains('warn') && !bar.classList.contains('off') && m.textContent.indexOf('Connected. Records reach coordination as you save them.')===0){
      m.textContent='Database service reachable · dashboard source and access are shown below.';
      bar.setAttribute('data-observational','true');
    } else if(m.textContent!=='Database service reachable · dashboard source and access are shown below.') {
      bar.removeAttribute('data-observational');
    }
  }
  new MutationObserver(observeBridge).observe(document.body,{childList:true,subtree:true,characterData:true});
  observeBridge();
})();
</script>
'''
s=s.replace('</body>',observer+'</body>')
p.write_text(s)
print('index written; runtime preserved except signed-out auto-connect guard + presentation observer')
