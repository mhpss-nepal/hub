from pathlib import Path
from html.parser import HTMLParser
import subprocess,json,hashlib,re,sys
ROOT=Path(__file__).resolve().parents[2]
BASE='1775af56d9be12e2f76d8d9a4e45631f6933cd58'
def base(path): return subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT).decode()
class Inventory(HTMLParser):
 def __init__(self): super().__init__(); self.controls=[]; self.assets=[]; self.ids=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if a.get('id'): self.ids.append(a['id'])
  if tag in ['input','select','textarea','button']: self.controls.append([tag]+[a.get(k,'') for k in ['type','id','name','data-dim','data-p','accept','checked','disabled','required']])
  if tag=='script' and a.get('src'): self.assets.append(a['src'])
def inventory(s):
 i=Inventory(); i.feed(s); return i
b=base('index.html'); c=(ROOT/'index.html').read_text(); bi=inventory(b); ci=inventory(c)
assert sorted(bi.controls)==sorted(ci.controls),'Control contract changed'
assert bi.assets==ci.assets,'Runtime script inventory changed'
assert len(ci.ids)==len(set(ci.ids)),'Duplicate ids'
# The only executable delta allowed is the headline presentation block.
def normalized(s):
 s=s.replace('<div class="tbl-wrap" tabindex="0" role="region" aria-label="Scrollable report table">','<div class="tbl-wrap">')
 return re.sub(r'    \$\("stats"\)\.innerHTML = \[.*?    \]\.join\(""\);','HEADLINE_PRESENTATION',s,flags=re.S)
def scripts(s): return re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>',s,re.S)
assert [normalized(x) for x in scripts(b)]==[normalized(x) for x in scripts(c)],'Handler/counter/export/auth/publication delta'
assets=bi.assets+['assets/app.css','assets/design.css','assets/hub-shell.css','assets/form.css']
for p in assets: assert (ROOT/p).read_text()==base(p),p+' changed'
assert 'No confirmed reports' in c,'Honest empty state missing'
assert '<details id="analysisDetails"' in c,'Secondary analysis not disclosed'
assert '<details id="advancedSections"' in c,'Advanced sections not disclosed'
assert 'stat(covered.length' not in c and 'stat(GAPS.length' not in c,'More than three primary cards'
result={'passed':9,'failed':0,'controls':len(ci.controls),'runtime_scripts':len(ci.assets),'ids':len(ci.ids),'base':BASE,'source_sha256':hashlib.sha256(c.encode()).hexdigest(),'controls_inventory':ci.controls,'asset_hashes':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in assets}}
print(json.dumps(result,indent=2))
(ROOT/'design-preview').mkdir(exist_ok=True)
(ROOT/'design-preview/source-contract.json').write_text(json.dumps(result,indent=2)+'\n')
