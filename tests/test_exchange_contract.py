#!/usr/bin/env python3
"""Contract tests for the pull-only exchange feed. Failing-first, stdlib only.

Every test here is a guard: break the contract and the build must refuse. The
guard that catches a defect's return is exercised by deliberately breaking it.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "tools" / "exchange"))

import build_exchange as bx  # noqa: E402


def _fresh_source() -> Path:
    """A throwaway copy of the frozen source, so a test can mutate it."""
    d = Path(tempfile.mkdtemp(prefix="exchange-src-"))
    for name in ("baseline.json", "pcode-map.json"):
        shutil.copy(_ROOT / "exchange" / "source" / name, d / name)
    return d


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


class ExchangeContract(unittest.TestCase):
    def setUp(self):
        self.src = _fresh_source()
        self.out = Path(tempfile.mkdtemp(prefix="exchange-out-"))

    def tearDown(self):
        shutil.rmtree(self.src, ignore_errors=True)
        shutil.rmtree(self.out, ignore_errors=True)

    # --- happy path --------------------------------------------------------
    def test_build_emits_dated_latest_and_schema(self):
        res = bx.build(self.src, self.out, write=True)
        self.assertEqual(res["rows"], 10)
        self.assertTrue((self.out / res["dated"]).exists())
        self.assertTrue((self.out / "mhpss_np_5w_latest.csv").exists())
        self.assertTrue((self.out / "schema.json").exists())
        # latest is a byte-for-byte copy of the dated file
        self.assertEqual(
            (self.out / res["dated"]).read_text(encoding="utf-8"),
            (self.out / "mhpss_np_5w_latest.csv").read_text(encoding="utf-8"),
        )

    def test_csv_has_hxl_header_and_pcodes(self):
        bx.build(self.src, self.out, write=True)
        lines = (self.out / "mhpss_np_5w_latest.csv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], ",".join(bx.HEADERS))
        self.assertEqual(lines[1], ",".join(bx.HXL_ROW))
        self.assertTrue(all(t.startswith("#") for t in lines[1].split(",")))

    def test_every_row_has_a_child_pcode_hierarchy(self):
        bx.build(self.src, self.out, write=True)
        import csv as _csv
        import io as _io
        text = (self.out / "mhpss_np_5w_latest.csv").read_text(encoding="utf-8")
        lines = text.splitlines()
        # line 0 = header, line 1 = HXL tag row, line 2.. = data
        body = "\n".join([lines[0]] + lines[2:])
        rows = list(_csv.DictReader(_io.StringIO(body)))
        self.assertGreaterEqual(len(rows), 2)
        for r in rows:
            self.assertTrue(r["adm3_pcode"].startswith(r["adm2_pcode"]), r)
            self.assertTrue(r["adm2_pcode"].startswith(r["adm1_pcode"]), r)

    def test_verify_accepts_a_good_build(self):
        bx.build(self.src, self.out, write=True)
        self.assertTrue(bx.verify(self.src, self.out)["verified"])

    # --- guards: deliberately break the contract, prove it bites -----------
    def test_below_floor_value_is_refused(self):
        b = _load(self.src / "baseline.json")
        b["rows"][0]["reached"] = 6          # below the floor of 10
        _save(self.src / "baseline.json", b)
        with self.assertRaises(bx.ContractError):
            bx.build(self.src, self.out, write=False)

    def test_identity_key_in_source_is_refused(self):
        b = _load(self.src / "baseline.json")
        b["rows"][0]["focalName"] = "someone"   # must never travel
        _save(self.src / "baseline.json", b)
        with self.assertRaises(bx.ContractError):
            bx.build(self.src, self.out, write=False)

    def test_unknown_palika_pcode_is_refused(self):
        b = _load(self.src / "baseline.json")
        b["palika_pcodes"]["Bidur Municipality"] = "NP9999999"
        _save(self.src / "baseline.json", b)
        with self.assertRaises(bx.ContractError):
            bx.build(self.src, self.out, write=False)

    def test_single_row_feed_is_refused(self):
        b = _load(self.src / "baseline.json")
        b["rows"] = b["rows"][:1]
        _save(self.src / "baseline.json", b)
        with self.assertRaises(bx.ContractError):
            bx.build(self.src, self.out, write=False)

    def test_verify_catches_a_tampered_committed_file(self):
        bx.build(self.src, self.out, write=True)
        p = self.out / "mhpss_np_5w_latest.csv"
        p.write_text(p.read_text(encoding="utf-8").replace("32", "33", 1), encoding="utf-8")
        with self.assertRaises(bx.ContractError):
            bx.verify(self.src, self.out)

    def test_verify_catches_a_schema_drift(self):
        bx.build(self.src, self.out, write=True)
        s = _load(self.out / "schema.json")
        s["suppressed_below"] = 1
        _save(self.out / "schema.json", s)
        with self.assertRaises(bx.ContractError):
            bx.verify(self.src, self.out)

    def test_basis_must_state_non_additivity(self):
        b = _load(self.src / "baseline.json")
        # If the source loses its non-additivity statement the build must refuse.
        orig = bx.BASIS
        try:
            bx.BASIS = "people reached"       # additive-looking, no statement
            with self.assertRaises(bx.ContractError):
                bx.build(self.src, self.out, write=False)
        finally:
            bx.BASIS = orig

    def test_missing_source_is_a_clean_failure_not_a_traceback(self):
        # An "automatic" job must fail loudly but cleanly: exit 2, no traceback.
        rc = bx.main(["--source-dir", str(self.src / "nope"),
                      "--exchange-dir", str(self.out), "--check"])
        self.assertEqual(rc, 2)

    def test_check_writes_nothing(self):
        before = set(self.out.iterdir()) if self.out.exists() else set()
        bx.build(self.src, self.out, write=False)
        after = set(self.out.iterdir()) if self.out.exists() else set()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
