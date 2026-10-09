from pathlib import Path
import subprocess,json,hashlib,re
import struct
class Image:
 @staticmethod
 def open(p):
  class Size: pass
  o=Size(); o.size=struct.unpack('>II',p.read_bytes()[16:24]); return o
R=Path(__file__).resolve().parents[1]; E=R/'ref4-evidence'
BASE='b02e14a73edc7c0061bdeeaab652c66dd7224883'
b=subprocess.check_output(['git','show',BASE+':index.html'],cwd=R); (E/'baseline.html').write_bytes(b)
files=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=R).decode().splitlines()
inv={'base':BASE,'files':{p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in files},'inline_scripts':[hashlib.sha256(s.encode()).hexdigest() for s in re.findall(r'<script>(.*?)</script>',b.decode(),re.S)],'cache_references':{}}
for p in files:
 if p.endswith(('.js','.html')):
  t=(R/p).read_text(); hits=[l for l in t.splitlines() if any(k in l for k in ['serviceWorker','caches.','sw.js'])]
  if hits: inv['cache_references'][p]=hits
(E/'PRESERVATION-INVENTORY.json').write_text(json.dumps(inv,indent=2))
for p in [Path('/root/.hermes/outputs/mhpss-dashboard-design-references/MHPSS 5Ws Dashboard Mockup (illustrative) 27Sep2026.png'),Path('/root/.hermes/images/upload_20261009_155708_1.png')]:
 im=Image.open(p); print(p,im.size,hashlib.sha256(p.read_bytes()).hexdigest())
print('cache refs',inv['cache_references'])
print('prior evidence README\n'+(R/'design-preview/README.md').read_text())
for rel in ['../01-cache-foundation/HANDOFF.md','../02-readiness-evidence/HANDOFF.md','../INDICATOR-LEDGER.json']:
 p=R.parent/rel
 print(str(p),p.exists())
 if p.exists():print(p.read_text())
