#!/usr/bin/env python3
"""Red/green demo for the ward field's Layer 2 side.

Materialises the BASE hub tree (this task's branch point = `main`, `ff2d4e2`)
plus the form build's ward commit, drops the new test suite and its node probe
into the base tree, and runs the suite there. It must FAIL there and PASS on
the delivered tree. Nothing is asserted from a stored transcript: both runs
happen here, in throwaway directories.

    python3 tools/ward-field-red-green.py

Exit 0 when the demonstration is exactly red -> green.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITE = "test_ward_field.py"
PROBE = "tools/fixtures/store-probe.js"
# The hub tree this task started from: `main` at the branch point.
HUB_BASE = os.environ.get("MHPSS_HUB_BASE", "ff2d4e2")
FORM_REPO = Path(os.environ.get("MHPSS_FORM_REPO",
                                "/root/mhpss-nepal-work/form-frontend")).resolve()


def run(cmd, cwd, env=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)


def summarise(stream: str) -> str:
    """Run output, minus the giant source dump an assert failure prints."""
    out = []
    for line in stream.splitlines():
        if len(line) > 300:
            line = line[:160] + " … [%d chars elided]" % len(line)
        out.append(line)
    return "\n".join(out)


def materialise_base_hub(dest: Path) -> None:
    tar = subprocess.run(["git", "archive", HUB_BASE], cwd=ROOT,
                         capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=tar, check=True)


def main() -> int:
    if not FORM_REPO.is_dir():
        print("form repository missing at %s" % FORM_REPO)
        return 2
    with tempfile.TemporaryDirectory(prefix="ward-field-red-green-") as temp:
        base = Path(temp) / "hub"
        base.mkdir()
        materialise_base_hub(base)
        # The suite and its probe are the new files under test; the rest of the
        # base tree is the base tree.
        shutil.copy(ROOT / SUITE, base / SUITE)
        probe_dest = base / PROBE
        probe_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / PROBE, probe_dest)

        env = dict(os.environ, MHPSS_FORM_REPO=str(FORM_REPO))
        red = run([sys.executable, "-m", "unittest", SUITE.rstrip(".py")],
                  cwd=base, env=env)
        green = run([sys.executable, "-m", "unittest", SUITE.rstrip(".py")],
                    cwd=ROOT, env=env)

    print("=" * 74)
    print("RED  — base hub %s (no ward in CSV_COLUMNS, no ward strings)" % HUB_BASE[:7])
    print("=" * 74)
    print(summarise(red.stderr.strip() or red.stdout.strip()))
    print()
    print("=" * 74)
    print("GREEN — delivered hub tree")
    print("=" * 74)
    print(summarise(green.stderr.strip() or green.stdout.strip()))
    red_failed = "FAILED" in red.stderr or red.returncode != 0
    green_ok = "OK" in green.stderr and green.returncode == 0
    print()
    print("red failed as required : %s" % red_failed)
    print("green passed           : %s" % green_ok)
    if red_failed and green_ok:
        print("red/green demonstration: PASS")
        return 0
    print("red/green demonstration: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
