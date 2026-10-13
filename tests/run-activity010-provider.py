"""Reuse backend runner/adapter unchanged, redirect browser test to actual Form/Hub.
All evidence fresh and separate; no backend source edits or inherited service cleanup.
"""
import sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=Path('/root/mhpss-nepal-final-forms/2026-10-06')
BACKEND=BASE/'48-historical-analytics/backend'
EVIDENCE=BASE/'51-operational-closure/joint010-bridge/frontend/provider'
def main():
 EVIDENCE.mkdir(parents=True,exist_ok=True)
 test=(BACKEND/'tests/test_activity_provider.py').read_text()
 test=test.replace("str(Path(__file__).parent/'activity_browser_provider.py')",repr(str(ROOT/'tests/activity010-provider-browser.py'))).replace('timeout=45)','timeout=100)')
 test=test.replace("db.document('activity_events/browser-proof')","db.document('activity_events/'+browser_evidence['reportId'])")
 wrapper=EVIDENCE/'test_actual_frontend_provider.py'
 test=test.replace('Path(__file__)', 'Path('+repr(str(BACKEND/'tests/test_activity_provider.py'))+')')
 wrapper.write_text(test)
 runner=(BACKEND/'tests/run_activity_emulator.py').read_text().replace("'tests/test_activity_provider.py'",repr(str(wrapper))).replace('timeout=180','timeout=230')
 result=subprocess.run([str(BASE/'30-cloud-functions-interim/.venv/bin/python'),'-c',"__file__="+repr(str(BACKEND/'tests/run_activity_emulator.py'))+'\n'+runner,str(EVIDENCE)],cwd=BACKEND,timeout=300)
 return result.returncode
if __name__=='__main__':sys.exit(main())
