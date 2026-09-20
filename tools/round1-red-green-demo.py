#!/usr/bin/env python3
"""Red/green demonstration for the round-1 rendered-checker fix (t_46e4cb25).

Review round 1 found that `tools/hub-trial-scope-render-check.py` accepted every
unapproved URL under `/form/`: `APPROVED_FORM_PATHS` held `/form/` and the
comparison was a substring membership test, so `../form/contact.html` was waved
through. This script proves the fix is a real red-then-green change, using the
pre-fix checker kept verbatim at
`tools/fixtures/render-check-prefix-15d35b3.py` (the file as it stood at commit
`15d35b3`, i.e. the version the reviewer probed at head `435a2c3`).

  A. classifier: RED against the pre-fix checker, GREEN against the fixed one.
  B. served-DOM probe: blind (accepts a planted link) against the pre-fix
     checker, catches it against the fixed checker.

Writes nothing into the worktree; every tree is a throwaway temp dir.

  python3 tools/round1-red-green-demo.py      # exit 0 when both hold
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRE_FIX = ROOT / "tools" / "fixtures" / "render-check-prefix-15d35b3.py"
CLASSIFIER_TEST = (
    "test_trial_scope.HubTrialScopeTest."
    "test_rendered_link_check_uses_exact_normalized_form_paths"
)


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, check=False)


def main():
    if not PRE_FIX.is_file():
        print("missing pre-fix fixture: %s" % PRE_FIX)
        return 1
    pre_fix_src = PRE_FIX.read_text(encoding="utf-8")
    ok = True

    # A1: the classifier test must be RED against the pre-fix checker.
    with tempfile.TemporaryDirectory(prefix="hub-red-") as temp:
        root = Path(temp)
        (root / "tools").mkdir()
        shutil.copy2(ROOT / "test_trial_scope.py", root / "test_trial_scope.py")
        (root / "tools" / "hub-trial-scope-render-check.py").write_text(pre_fix_src)
        red = run(["python3", "-m", "unittest", CLASSIFIER_TEST], root)
        red_ok = red.returncode != 0
        print("A1 pre-fix classifier test: exit=%d (%s)"
              % (red.returncode, "RED as required" if red_ok
                 else "GREEN -- the subframe bug is not reproduced"))
        ok = ok and red_ok

    # A2: the same test must be GREEN against the fixed checker.
    green = run(["python3", "-m", "unittest", CLASSIFIER_TEST], ROOT)
    green_ok = green.returncode == 0
    print("A2 fixed classifier test: exit=%d (%s)"
          % (green.returncode, "GREEN" if green_ok else "RED -- fix broken"))
    ok = ok and green_ok

    # B: the served-DOM probe against both checkers.
    probe = str(ROOT / "tools" / "render-check-adversarial-probe.py")
    for label, checker_path in (("fixed", None), ("pre-fix", PRE_FIX)):
        cmd = ["python3", probe]
        if checker_path is not None:
            cmd.append(str(checker_path))
        out = run(cmd, ROOT)
        blind = "checker is blind" in out.stdout
        if label == "fixed":
            good = out.returncode == 0
            print("B  probe vs %s checker: exit=%d (%s)"
                  % (label, out.returncode,
                     "planted link rejected as required" if good
                     else "ACCEPTED -- checker still blind"))
        else:
            good = blind
            print("B  probe vs %s checker: exit=%d (%s)"
                  % (label, out.returncode,
                     "checker blind -- bug reproduced" if good
                     else "unexpectedly rejected the planted link"))
        ok = ok and good

    print("red/green demonstration: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
