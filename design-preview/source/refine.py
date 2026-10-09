from pathlib import Path
import re
p=Path('hub/index.html');s=p.read_text();locked=re.findall(r'<script>(.*?)</script>',s,re.S)
a=s.index('    <div id="analysis-primary">');b=s.index('    <!-- WHERE,',a)
chunk=s[a:b];starts=[m.start() for m in re.finditer('      <div class="ovcol">',chunk)]
assert len(starts)==3
end=chunk.rfind('    </div>\n    </div>')
who=chunk[starts[0]:starts[1]];what=chunk[starts[1]:starts[2]];whom=chunk[starts[2]:end]
time='<section class="ovcol time-card"><div class="ovcolh"><h2>When — reports by day</h2></div><div class="ovcolb"><p class="xs">Follows the selected period and date basis. Existing daily attendance table; no weekly conversion.</p><div id="dayWrap" tabindex="0" role="region" aria-label="Reports by day, scroll horizontally if needed"></div></div></section>'
old='<h2>Reports per day</h2>\n      <p class="secsay">Follows the period and the date basis chosen above.</p>\n      <div id="dayWrap"></div>'
assert old in s;s=s.replace(old,'')
a=s.index('    <div id="analysis-primary">');b=s.index('    <!-- WHERE,',a)
s=s[:a]+'<div id="analysis-primary" class="primary-grid">'+what+time+'</div>\n<div class="ovcols" id="ovcols">'+who+whom+'</div>\n'+s[b:]
css='''
body.hub.dashboard-selected .primary-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px;margin-bottom:16px;align-items:start}
body.hub.dashboard-selected .ovcols{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}
body.hub.dashboard-selected .ovcol:nth-child(2){order:initial}
body.hub.dashboard-selected #i18nbar button{min-width:44px;min-height:44px;color:#1d3d60}
body.hub.dashboard-selected #i18nbar button[aria-pressed=true]{background:#dcebf7;color:#1d3d60}
body.hub.dashboard-selected #dayWrap{overflow:auto;max-width:100%}
body.hub.dashboard-selected #dayWrap .tbl-wrap{border:0;box-shadow:none;overflow:visible}
body.hub.dashboard-selected .time-card table.data{min-width:530px;font-size:12px}
body.hub.dashboard-selected .time-card th{white-space:normal}
body.hub.dashboard-selected .ovcols .ovcol:last-child{grid-column:auto}
@media(max-width:650px){body.hub.dashboard-selected .primary-grid,body.hub.dashboard-selected .ovcols{grid-template-columns:minmax(0,1fr)}}
'''
s=s.replace('</style>',css+'</style>',1)
assert locked==re.findall(r'<script>(.*?)</script>',s,re.S)
p.write_text(s)
print('primary What/When; Who/For whom secondary; existing day renderer unchanged')
