from pathlib import Path
import json,hashlib,subprocess,datetime,re
R=Path(__file__).resolve().parent; H=R/'hub'; E=H/'design-preview';BASE='180a64e8ccb077e26d0905adffa320e107ffb45f'
q=json.loads((E/'qa-report.json').read_text());cand=[x for x in q['runs'] if not x['base']]
assert q['candidate_index_sha256']==hashlib.sha256((H/'index.html').read_bytes()).hexdigest()
assert sorted(x['width'] for x in cand)==[320,390,1280]
assert set(q['parity'])=={'320','390','1280'}
for width,checks in q['parity'].items():assert len(checks)==13 and all(v is True for v in checks.values()),(width,checks)
for r in cand:
 assert not r['errors'] and not r['axe'] and r['lang']=='ne',r
 assert r['initialLanguage']=='en' and all(not x for x in r['axeStates'].values()),r
 assert r['initialStorage']==r['storageBefore']==r['storageBeforeLanguage'],r
 assert r['remoteWrites']==[],r
 before=json.loads(r['storageBefore']);after=json.loads(r['storageAfter'])
 assert after.pop('mhpss-np-lang',None)=='en'
 before.pop('mhpss-np-lang',None)
 assert before==after,r
 for name in ['overview','reports','matrix','activities','expanded','neGeometry']:
  g=r[name];assert g['root']==[r['width'],r['width']] and not g['overflow'] and not g['small'],(r['width'],name,g)
assert (R/'baseline.html').read_bytes()==subprocess.check_output(['git','show',BASE+':index.html'],cwd=H)
inv=json.loads((E/'PRESERVATION-INVENTORY.json').read_text())
for f,pin in inv['assets'].items():
 b=(H/f).read_bytes();assert hashlib.sha256(b).hexdigest()==pin['sha256'];assert b==subprocess.check_output(['git','show',BASE+':'+f],cwd=H)
for p in [H/'index.html',*E.glob('*'),H/'tests/test_dashboard_visual_contract.py']:
 if not p.is_file() or p.suffix=='.png':continue
 t=p.read_text();assert not re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY|"type"\s*:\s*"service_account"|gh[pousr]_[A-Za-z0-9]{30}',t),p
summary={'timestamp_wib':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).isoformat(),'base':BASE,'candidate_index_sha256':hashlib.sha256((H/'index.html').read_bytes()).hexdigest(),'contract_tests':5,'viewports':[320,390,1280],'parity_checks_per_viewport':{k:len(v) for k,v in q['parity'].items()},'axe_A_AA_violations':0,'page_errors':0,'overflow':0,'small_targets':0,'actual_language_journey':'ENG initial → NEP click → ne resolved → English reset','storage_unchanged':True,'mock_remote_writes':0,'unchanged_assets':len(inv['assets']),'limitations':['Synthetic fixture only; no operational API/store reconciliation','Nepali choice operates but dashboard translation remains incomplete','Existing source/cloud initialization behavior unchanged; no claim of whole-system no-write safety','No installed-client service-worker test; root has no worker/manifest call site']}
(E/'final-verification.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
