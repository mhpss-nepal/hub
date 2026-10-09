from pathlib import Path
import subprocess,re,json,hashlib,urllib.request
from html.parser import HTMLParser
ROOT=Path(__file__).parent; repo=ROOT/'hub'; base='180a64e8ccb077e26d0905adffa320e107ffb45f'
class Parser(HTMLParser):
 def __init__(self): super().__init__(); self.controls=[];self.assets=[];self.ids=[]
 def handle_starttag(self,t,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
  if t in ['input','select','textarea','button']:self.controls.append([t]+[a.get(k,'') for k in ['type','id','name','form','data-dim','data-p','required']])
  if t in ['script','link'] and ('src' in a or 'href' in a): self.assets.append(a.get('src',a.get('href')))
s=(repo/'index.html').read_text(); p=Parser();p.feed(s)
assets={}
for path in p.assets:
 if not path.startswith('http'):
  b=(repo/path).read_bytes();assets[path]={'sha256':hashlib.sha256(b).hexdigest(),'size':len(b)}
inv={'executor':'Thar Lay/server','repository':'mhpss-nepal/hub','base':base,'branch':'feat/dashboard-owner-reference-20261009','controls':p.controls,'ids':p.ids,'assets':assets,'external_assets':[x for x in p.assets if x.startswith('http')],'inline_script_sha256':[hashlib.sha256(x.encode()).hexdigest() for x in re.findall(r'<script>(.*?)</script>',s,re.S)],'handlers':re.findall(r'\$\("([^"]+)"\)\.addEventListener\("([^"]+)"',s),'storage':['mhpss-np-4ws-v1','mhpss-np-queue-v1','mhpss-np-lang','mhpss-rail-groups'],'network':['FB.watchKind(activity) only upon existing live selection/auto-live','FB.signIn explicit user action','FB.readPublic on publish section','FB.publish explicit existing privileged action','Firebase SDK initialization and existing reconnect queue flush in fb.js'],'formulas':'Entire inline script byte locked; STORE and CODES byte locked; all export handlers byte locked. No schema-v2 adapter.','states':'Existing file/browser/synthetic/live reader retained; no live verification authorised. Existing acknowledgement semantics not upgraded.','interface':'../backend/INTERFACE-STATUS.json frozen read-only; no_hub_integration true','limitations':['Existing source contains stale September governance/age copy; not silently corrected in calculation','No service worker or manifest referenced by root Hub','Existing public publisher not reviewed/activated by cosmetic task; real data not loaded']}
(repo/'design-preview').mkdir(); (repo/'design-preview/PRESERVATION-INVENTORY.json').write_text(json.dumps(inv,indent=2))
(ROOT/'baseline.html').write_text(s)
# Public static bytes only; no data endpoint.
served=urllib.request.urlopen('https://mhpss-nepal.github.io/hub/index.html?baseline=38',timeout=30).read()
(ROOT/'served-baseline.html').write_bytes(served)
print('live static parity',served==s.encode(),hashlib.sha256(served).hexdigest())
print('controls',len(p.controls),'assets',len(assets),'scripts',len(inv['inline_script_sha256']))
