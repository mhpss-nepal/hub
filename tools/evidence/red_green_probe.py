#!/usr/bin/env python3
"""Adversarial probes: each guarded defect is planted back, one at a time, and
the suite must go red. A test that cannot fail is not a guard.
"""
import re, shutil, subprocess, sys, tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parents[2]
STALE_HEADER = """   Deliberately has NO backend. Records are held in this browser only,
   and leave it only when a person exports it. A form with no server cannot
   breach that rule.
"""

PLANTS = {
    "store.js header reverted to the local-only text": (
        "assets/store.js",
        lambda t: re.sub(r"   The device copy is the first durable copy\..*?those contact details\.\n",
                         STALE_HEADER, t, count=1, flags=re.S)),
    "a Nepali value added to a protected key (clinical.phq9ValidatedTextWarning)": (
        "assets/i18n-strings.js",
        lambda t: t.replace('  ne: {\n',
                            '  ne: {\n    "clinical.phq9ValidatedTextWarning": "केही नेपाली",\n', 1)),
    "the validated Nepali PHQ-9 removed": (
        "assets/i18n-strings.js",
        lambda t: "\n".join(l for l in t.split("\n")
                            if not l.strip().startswith('"phq9.item1":')),),
    "the validated instrument struck from _meta.source.human": (
        "assets/i18n-strings.js",
        lambda t: t.replace('      "phq9.item1",\n', '', 1)),
    "the render-forced declaration removed for sr.p001": (
        "assets/i18n-strings.js",
        lambda t: t.replace('      "sr.p001",          /* the free-text risk warning */\n', '', 1)),
    "a palika's ward count emptied without declaring its source": (
        "assets/codes.js",
        lambda t: t.replace('wards: 5, district: "RAS"', 'district: "RAS"', 1)),
}


def run_suite(root: Path) -> tuple[int, str]:
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-p", "test_*.py"],
                       cwd=root, capture_output=True, text=True)
    return r.returncode, r.stderr


def main() -> int:
    failures = []
    for name, (relpath, mutate) in PLANTS.items():
        with tempfile.TemporaryDirectory(prefix="probe-") as tmp:
            root = Path(tmp) / "hub"
            shutil.copytree(SRC, root, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            path = root / relpath
            original = path.read_text(encoding="utf-8")
            mutated = mutate(original)
            assert mutated != original, "probe %r changed nothing" % name
            path.write_text(mutated, encoding="utf-8")
            code, err = run_suite(root)
            caught = code != 0
            failed = [l.split(" ")[1].split("(")[0]
                      for l in err.splitlines() if l.startswith("FAIL:")]
            print("%-4s %s" % ("RED" if caught else "GREEN", name))
            if caught:
                print("       caught by: %s" % ", ".join(failed[:4]))
            else:
                failures.append(name)
    print()
    print("probes:", len(PLANTS), "| caught:", len(PLANTS) - len(failures),
          "| NOT caught:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
