from pathlib import Path
import json,re,subprocess,hashlib
E=Path(__file__).resolve().parent;R=E.parent
q=json.loads((E/'qa-report.json').read_text())
for r in q['firstscreen']:print('ENTRY',r['route'],r['width'],r['checks'],'axe',r.get('axe'), 'keyboard',r.get('keyboardAccessOpen'),r.get('keyboardAccessClosed'),'status',[r.get(k) for k in ['warningPreserved','pendingPreserved','errorPreserved']])
for r in q['runs']:print('BASE' if r['base'] else 'HEAD',r['width'],'errors',r['errors'],'axe',r['axe'],'geo',r['geometry'],'lang',r['lang'],'storage',r['storageBefore'],r['storageAfter'],'writes',r['remoteWrites'])
print('PARITY',q['parity']);print('MUTATION',q['mutation'])
b=(E/'baseline.html').read_text();s=(R/'index.html').read_text();a=re.findall('<script>(.*?)</script>',b,re.S);c=re.findall('<script>(.*?)</script>',s,re.S)
print('INLINE',len(a),len(c),[x==y for x,y in zip(a,c)]);print('RUNTIME EXACT except guard',a[-1].replace('if (done || !st || !st.ready) return;','if (done || !st || !st.ready || !st.user) return;')==c[-2])
print('source read labels',[(m.start(),s[m.start():m.start()+250]) for m in re.finditer('stats.*innerHTML',s)])
