from pathlib import Path
p=Path(__file__).resolve().parents[1]/'index.html';s=p.read_text()
css='''
body.hub.dashboard-selected p{text-align:left}
body.hub.dashboard-selected .ovcolh h2{flex-shrink:1;min-width:0;max-width:100%;white-space:normal;overflow-wrap:break-word}
body.hub.dashboard-selected input[type=file]{display:block;width:100%;max-width:100%;font:inherit;font-size:12px;padding:8px 0;min-height:44px}
body.hub.dashboard-selected .file-choice{display:block;font-size:13px;font-weight:700;color:#1d3d60;max-width:100%}
'''
s=s.replace('</style>\n</head>',css+'</style>\n</head>')
s=s.replace('<label class="btn ghost" style="cursor:pointer">Choose a file<input type="file" id="file" accept=".json,.csv" hidden></label>','<label class="file-choice">Choose a file<input type="file" id="file" accept=".json,.csv"></label>')
s=s.replace('<label class="btn ghost sm" style="cursor:pointer">Import a file<input type="file" id="file2" accept=".json,.csv" hidden></label>','<label class="file-choice">Import a file<input type="file" id="file2" accept=".json,.csv"></label>')
p.write_text(s)
print('mobile title wrapping and accessible native file inputs')
