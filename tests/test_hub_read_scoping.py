#!/usr/bin/env python3
"""Unit-test wrapper for the hub read-scoping guard (defect C1).

The guard lives at tools/hub-live-read-scoping-check.py. It fails if any hub
surface reads the register without naming a kind -- which under Firestore rules
v4 would be refused for a restricted role (an empty dashboard) and under the
older ruleset would return the whole register.

This wrapper runs the guard AND its break-on-purpose self-test, so a future
change that silently removes the fix turns this red.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "tools" / "hub-live-read-scoping-check.py"


class HubReadScoping(unittest.TestCase):
    def test_guard_passes_on_the_current_tree(self):
        p = subprocess.run([sys.executable, str(GUARD)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_guard_bites_when_the_defect_is_reintroduced(self):
        p = subprocess.run([sys.executable, str(GUARD), "--break"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, "the self-test itself failed\n" + p.stdout + p.stderr)
        self.assertIn("SELF-TEST OK", p.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
