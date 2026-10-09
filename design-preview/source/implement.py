from pathlib import Path
import re
R=Path('hub'); s=(R/'index.html').read_text()
# Transform existing containers in place; all inline runtime scripts stay byte exact.
s=s.replace('<body class="hub">','<body class="hub dashboard-selected">\n<a class="skip" href="#dashboard-main">Skip to dashboard</a>')
s=s.replace('<div class="wrap wide">','<main class="wrap wide" id="dashboard-main">',1)
s=s.replace('\n</div>\n\n<div id="toast">','\n</main>\n\n<div id="toast">',1)
# Remove marketing-height framing, retain wording behind a disclosure.
a=s.index('<p class="lede">'); b=s.index('</p>',a)+4
s=s[:a]+'<details class="intro-details"><summary>About this dashboard</summary>'+s[a:b]+'</details>'+s[b:]
# Put existing scope and filters before metrics; no duplicate inputs.
a=s.index('    <div class="scope" id="scope">'); b=s.index('\n    </details>',s.index('<details class="filters"',a))+len('\n    </details>')
block=s[a:b]; s=s[:a]+s[b:]; pos=s.index('    <div class="stats"');s=s[:pos]+block+'\n'+s[pos:]
# Existing Who/What/For whom cards stay intact, ordered What, Who, For whom via CSS.
s=s.replace('<div class="ovcols" id="ovcols">','<div id="analysis-primary">\n    <div class="ovcols" id="ovcols">',1)
pos=s.index('    <!-- WHERE,'); s=s[:pos]+'    </div>\n'+s[pos:]
# Secondary analyses closed until selected, preserving their own IDs and children.
a=s.index('    <div class="ovfig" id="ovWhere">');b=s.index('    <!-- The scope line',a)
s=s[:a]+'<details class="analysis-detail"><summary>Where and delivery status</summary>\n'+s[a:b]+'</details>\n'+s[b:]
a=s.index('      <h2 class="sechead">Coverage of the roster'); b=s.index('      <h2>Who was reached</h2>',a)
s=s[:a]+'<details class="analysis-detail"><summary>Roster coverage and coordination checks</summary>\n'+s[a:b]+'</details>\n'+s[b:]
# Header semantics and accessible existing controls.
s=s.replace('id="rawFind" placeholder=','id="rawFind" aria-label="Find reports" placeholder=')
s=s.replace('<div class="tbl-wrap">','<div class="tbl-wrap" tabindex="0" role="region" aria-label="Data table, scroll horizontally if needed">')
# Static table headers; dynamic headers remain preserved in their runtime.
s=re.sub(r'<th(?![^>]*scope)([^>]*)>',r'<th scope="col"\1>',s)
css='''
/* Owner-selected 27 Sep reference. Dashboard only, no shared token changes.
   Presentation source of truth: navy masthead, pale canvas, outlined cards.
   English UI additions are non-clinical; Nepali review remains pending. */
body.hub.dashboard-selected{--bg:#f3f6f9;background:var(--bg);font-family:Arial,"Noto Sans",sans-serif;line-height:1.5}
body.dashboard-selected .top{background:#1d3d60;box-shadow:none;position:static;padding:22px 28px}
body.dashboard-selected .top .brand{font:700 25px/1.2 Arial,sans-serif}
body.dashboard-selected .top .sub{color:#e0e9f3;font-size:12px}
body.dashboard-selected .phead{background:#fff;margin:0;padding:16px 0;border-bottom:1px solid #d8e1ec}
body.dashboard-selected .phead h1{font:700 21px/1.25 Arial,sans-serif;color:#1d3d60}
body.dashboard-selected .phead .eyebrow{display:none}
body.dashboard-selected .phead .lede{font-size:14px;max-width:none}
body.dashboard-selected .intro-details{margin-top:8px}
body.dashboard-selected .wrap.wide{max-width:1600px;padding:22px 24px 60px}
body.dashboard-selected .stats{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:18px 0}
body.dashboard-selected .stat,body.dashboard-selected .ovcol,body.dashboard-selected .ovfig,body.dashboard-selected .filters,body.dashboard-selected .card,body.dashboard-selected .tbl-wrap{border:1px solid #d8e1ec;box-shadow:none;border-radius:12px;background:#fff}
body.dashboard-selected .stat{border-top:1px solid #d8e1ec;padding:16px}
body.dashboard-selected .stat .v{font:700 30px/1.15 Arial,sans-serif;color:#1d3d60}
body.dashboard-selected .stat .k{font-size:12px;color:#455569;letter-spacing:.02em}
body.dashboard-selected .stat .s{font-size:12px;color:#455569;margin-top:7px}
body.dashboard-selected .filters{padding:10px 16px}
body.dashboard-selected .filters .grid{grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
body.dashboard-selected .scope{padding:8px 0;margin:0;font-size:14px}
body.dashboard-selected .ovcols{grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;align-items:start}
body.dashboard-selected .ovcol:nth-child(2){order:-1}
body.dashboard-selected .ovcolh{padding:12px 16px;border-bottom:1px solid #d8e1ec;flex-wrap:wrap}
body.dashboard-selected .ovcolh h2{font-size:16px;letter-spacing:0;text-transform:none;color:#1d3d60}
body.dashboard-selected .ovcolb{padding:16px}
body.dashboard-selected .ovico{display:none}
body.dashboard-selected .ovnum .n{font-size:24px;color:#1d3d60}
body.dashboard-selected .ovnum .l{font-size:12px;color:#455569}
body.dashboard-selected .ovsubh{color:#1d3d60;font-size:12px;letter-spacing:0;text-transform:none}
body.dashboard-selected .ovbars{gap:12px}
body.dashboard-selected .ovbl small,body.dashboard-selected .ovlegend,body.dashboard-selected .xs{color:#455569}
body.dashboard-selected .ovbt{height:10px;background:#edf2f7;border-radius:2px}
body.dashboard-selected .analysis-detail{border:1px solid #d8e1ec;border-radius:12px;background:#fff;padding:12px 16px;margin:16px 0}
body.dashboard-selected summary{min-height:44px;cursor:pointer;padding:10px 0;color:#1d3d60;font-weight:700}
body.dashboard-selected .tab{min-height:44px;padding:10px 14px;color:#455569}
body.dashboard-selected .tab.on{color:#1d3d60;border-bottom-color:#2674be}
body.dashboard-selected .btn,body.dashboard-selected select,body.dashboard-selected input:not([type=checkbox]):not([type=file]),body.dashboard-selected .rgh,body.dashboard-selected .rmenu,body.dashboard-selected .rgb a,body.dashboard-selected .lyr,body.dashboard-selected #i18nwrap button{min-height:44px;min-width:44px}
body.dashboard-selected .ovcolf select{max-width:100%;font-size:12px}
body.dashboard-selected .ovcolf{flex:1 1 140px}
body.dashboard-selected .chipf button{width:44px;height:44px}
body.dashboard-selected .tbl-wrap{max-width:100%;overflow:auto}
body.dashboard-selected table.data{min-width:650px}
body.dashboard-selected .tbl-wrap:focus{outline:3px solid #2674be;outline-offset:2px}
body.dashboard-selected :is(button,a,input,select,summary,textarea):focus-visible{outline:3px solid #2674be;outline-offset:3px}
body.dashboard-selected #toast:not(.show){display:none}
body.dashboard-selected .ovso{border-left:0;border:1px solid #d8e1ec;background:#edf4fa;border-radius:8px}
body.dashboard-selected .skip{position:absolute;left:8px;top:-100px;z-index:999;background:white;padding:12px;color:#1d3d60}
body.dashboard-selected .skip:focus{top:8px}
@media(max-width:1100px){body.dashboard-selected .stats{grid-template-columns:repeat(3,minmax(0,1fr))}body.dashboard-selected .ovcols{grid-template-columns:1fr 1fr}body.dashboard-selected .ovcol:last-child{grid-column:1/-1}}
@media(max-width:650px){body.dashboard-selected .wrap.wide{padding:16px 12px 40px}body.dashboard-selected .stats{grid-template-columns:1fr 1fr}body.dashboard-selected .stat{padding:12px}body.dashboard-selected .stat:last-child{grid-column:1/-1}body.dashboard-selected .ovcols{grid-template-columns:1fr}body.dashboard-selected .top{padding:18px 16px}body.dashboard-selected .top .brand{font-size:22px}body.dashboard-selected .row{grid-template-columns:1fr}body.dashboard-selected .filters .grid{grid-template-columns:1fr}body.dashboard-selected .w2{grid-column:span 1}body.dashboard-selected .btns>*{max-width:100%}body.dashboard-selected .ovcolf{max-width:100%}body.dashboard-selected .ovfigh>*{max-width:100%}}
'''
s=s.replace('</style>','\n'+css+'</style>',1)
original=(R/'index.html').read_text()
locked=re.findall(r'<script>(.*?)</script>',original,re.S)
it=iter(locked)
s=re.sub(r'<script>.*?</script>',lambda m:'<script>'+next(it)+'</script>',s,flags=re.S)
(R/'index.html').write_text(s)
print('transformed existing root; scripts preserved')
