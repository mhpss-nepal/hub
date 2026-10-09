from pathlib import Path
import tempfile,subprocess,shutil,json,sys,os
R=Path(__file__).resolve().parents[1]; E=R/'ref4-evidence'
BASE='b02e14a73edc7c0061bdeeaab652c66dd7224883'
files=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=R).decode().splitlines()
results=[]
with tempfile.TemporaryDirectory(prefix='ref4-baseline-',dir=os.environ['TMPDIR']) as d:
 b=Path(d)/'hub';b.mkdir()
 for f in files:
  dest=b/f;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(subprocess.check_output(['git','show',BASE+':'+f],cwd=R))
 (b/'.git').symlink_to(R/'.git',target_is_directory=True)
 for name,root in [('baseline',b),('candidate',R)]:
  for suite,args in [('discover',['-m','unittest','discover','-s',str(root/'tests'),'-v']),('root',['-m','unittest','test_store_data_path_contract','test_trial_scope','test_ward_field','-v'])]:
   proc=subprocess.run([sys.executable]+args,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
   (E/f'existing-{name}-{suite}.txt').write_text(proc.stdout)
   results.append({'name':name,'suite':suite,'returncode':proc.returncode,'log':f'existing-{name}-{suite}.txt'});print(name,suite,proc.returncode,proc.stdout[-400:])
(E/'existing-results.json').write_text(json.dumps(results,indent=2))
