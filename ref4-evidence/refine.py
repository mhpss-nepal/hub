from pathlib import Path
import re
R=Path(__file__).resolve().parents[1];p=R/'index.html';s=p.read_text()
# Keep every existing filter id and handler; expose reference row, fold secondary dimensions.
a=s.index('      <div class="grid">',s.index('<details class="filters"'));z=s.index('    </details>',a)
old=s[a:z]; controls=re.findall(r'        <div[^\n]*</div>',old)
assert len(controls)==13
primary=['fPeriod','fProv','fDist','fPal','fOrg','fGrp','fMod']
ordered=[next(c for c in controls if 'for="'+i+'"' in c) for i in primary]
secondary=[c for c in controls if c not in ordered]
s=s[:a]+'      <div class="grid">\n'+'\n'.join(ordered)+'\n      </div>\n      <details class="filter-more"><summary>More filters and custom dates</summary><div class="grid">\n'+'\n'.join(secondary)+'\n      </div></details>\n'+s[z:]
s=s.replace('<div class="k">Roster sites with a report</div>','<div class="k">Roster sites reached</div>').replace('<div class="k">Palikas with a report</div>','<div class="k">Roster sites with no report</div>')
s=s.replace('Existing daily attendance table; no weekly conversion.','Daily reports and attendances; no epidemiological-week inference.')
css='''
body.hub.dashboard-selected .filters .grid{grid-template-columns:repeat(7,minmax(0,1fr))}
body.hub.dashboard-selected .filter-more>summary{font-size:12px;min-height:44px;padding:10px 0 0}
body.hub.dashboard-selected .filter-more .grid{grid-template-columns:repeat(6,minmax(0,1fr));padding-top:8px}
body.hub.dashboard-selected .rail .rgb>a{min-width:0}
body.hub.dashboard-selected .top>div{min-width:0}
body.hub.dashboard-selected .entry-filters span{color:#657386;background:#f8fafc;border-style:dashed}
@media(max-width:1100px){body.hub.dashboard-selected .filters .grid,body.hub.dashboard-selected .filter-more .grid{grid-template-columns:repeat(4,minmax(0,1fr))}}
@media(max-width:650px){body.hub.dashboard-selected .filters .grid,body.hub.dashboard-selected .filter-more .grid{grid-template-columns:repeat(2,minmax(0,1fr))}body.hub.dashboard-selected .rail .rg[data-g=coord]>.rgb{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));width:100%}body.hub.dashboard-selected .rail .rg[data-g=coord]{width:100%;min-width:0}}
'''
s=s.replace('</style>\n</head>',css+'</style>\n</head>');p.write_text(s)
print('refined filters to primary horizontal row + secondary disclosure')
