#!/usr/bin/env python3
"""Red/green demo for the per-layer language default.

Materialises the BASE trees (the Hub at this task's base commit, the field-form
build at the commit before this task's page change), drops the new test suite
into the base Hub tree, and runs it. The suite must FAIL there and PASS on the
delivered trees. Nothing is asserted from a stored transcript: both runs happen
here, in throwaway directories.

    python3 tools/per-layer-default-red-green.py

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
FORM_DIR = Path(os.environ.get(
    "MHPSS_FORM_DIR", "/root/mhpss-nepal-work/perlayer/form")).resolve()
SUITE = "test_i18n_per_layer_default.py"
# The Hub tree this task started from (its branch point), and the field-form
# build before this task's page change.
HUB_BASE = "8273e9013b163549640d04b2ec86fa42c840a91b"
FORM_BASE = "9c3a41eeccc768fcef5d8f241430ba831e8ad9a8"


def run(cmd, cwd, env=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)


def summarise(stream: str) -> str:
    """Run output, minus the giant source dump an assertIn failure prints."""
    out = []
    for line in stream.splitlines():
        if len(line) > 300:
            line = line[:160] + " … [%d chars of source elided]" % len(line)
        out.append(line)
    return "\n".join(out)


def materialise_base_hub(dest: Path) -> None:
    tar = subprocess.run(
        ["git", "archive", HUB_BASE], cwd=ROOT, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=tar, check=True)


def materialise_base_form(dest: Path) -> None:
    tar = subprocess.run(
        ["git", "archive", FORM_BASE], cwd=FORM_DIR, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=tar, check=True)


def main() -> int:
    if not FORM_DIR.is_dir():
        print("field-form worktree missing at %s" % FORM_DIR)
        return 2
    with tempfile.TemporaryDirectory(prefix="per-layer-red-green-") as temp:
        temp = Path(temp)
        base_hub, base_form = temp / "hub", temp / "form"
        base_hub.mkdir(); base_form.mkdir()
        materialise_base_hub(base_hub)
        materialise_base_form(base_form)
        shutil.copy(ROOT / SUITE, base_hub / SUITE)

        env = dict(os.environ, MHPSS_FORM_DIR=str(base_form))
        red = run([sys.executable, "-m", "unittest", "-v", SUITE.rstrip(".py")],
                  cwd=base_hub, env=env)
        green = run([sys.executable, "-m", "unittest", "-v", SUITE.rstrip(".py")],
                    cwd=ROOT, env=dict(os.environ, MHPSS_FORM_DIR=str(FORM_DIR)))

    print("=" * 74)
    print("RED  — base hub %s + base form %s" % (HUB_BASE[:7], FORM_BASE[:7]))
    print("=" * 74)
    print(summarise(red.stderr.strip() or red.stdout.strip()))
    print()
    print("=" * 74)
    print("GREEN — delivered hub tree + delivered form tree")
    print("=" * 74)
    print(summarise(green.stderr.strip() or green.stdout.strip()))
    red_failed = "FAILED" in red.stderr
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
