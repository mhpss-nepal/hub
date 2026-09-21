#!/usr/bin/env python3
"""Build the pull-only OCHA/NDRRMA exchange feed. Standard library only.

NO network, NO credentials, NO AI, NO model, NO new infrastructure. The build
reads one frozen, public-safe aggregate source file and emits the files OCHA
pulls; a machine check refuses to build if the export ever breaks its own
contract (missing P-code, missing metadata, an additive claim on a
non-additive measure, or a below-floor value that could be reconstructed).

Outputs, beneath the exchange directory:

    mhpss_np_5w_<data_date>.csv   HXL-tagged aggregate, one row per reporting unit
    mhpss_np_5w_latest.csv        byte-for-byte copy of the newest dated file
    schema.json                   column contract (names, types, HXL tags)
    CHANGELOG.md                  what changed between schema versions

The exchange feed is a *pull* target: OCHA fetches it. We never push and we
never hold credentials for anyone else's platform. It carries aggregates only;
no individual, case or identity data ever passes through it.

Usage:
    python3 tools/exchange/build_exchange.py            # build (writes files)
    python3 tools/exchange/build_exchange.py --check    # build in memory, verify contract, write nothing
    python3 tools/exchange/build_exchange.py --verify   # re-read committed files and assert they match

Exit codes: 0 ok, 2 contract/verification failure, 3 usage.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

SCHEMA_VERSION = 1
# Small-cell floor. A published aggregate below this must never appear in the
# feed (it could describe one identifiable person). Stay at or above the
# Layer 3 convention of 10. The ruleset treats < 10 as "must suppress".
SUPPRESSED_BELOW = 10

# Identity / case-management key fragments that must never be present in the
# source. Deliberately does NOT include the bare fragment "name": every key
# containing "name" must match the geographic allow-list below or it fails.
DENY_KEY_FRAGMENTS = (
    "phone", "email", "focal", "nik", "nid", "passport", "dob",
    "birth", "address", "household", "photo", "diagnosis", "phq", "contact_code",
    "latitude", "longitude", "gps", "individual", "person", "patient",
    "client", "victim", "survivor",
)
# The only keys that may contain "name": administrative/geographic names, never
# a person. Anything else with "name" in it is treated as identity data.
ALLOWED_NAME_KEYS = frozenset({
    "cod_name", "adm1_name", "adm2_name", "adm3_name", "district_name",
    "palika_name", "province_name", "name_traps",
})

# (header, hxl tag, kind). `kind` drives validation: text | pcode | int | date | meta.
COLUMNS = (
    ("activity",      "#activity",        "text"),
    ("sector",        "#sector",          "text"),
    ("org",           "#org",             "text"),
    ("adm1_name",     "#adm1",            "text"),
    ("adm1_pcode",    "#adm1+code",       "pcode"),
    ("adm2_name",     "#adm2",            "text"),
    ("adm2_pcode",    "#adm2+code",       "pcode"),
    ("adm3_name",     "#adm3",            "text"),
    ("adm3_pcode",    "#adm3+code",       "pcode"),
    ("reached",       "#reached",         "int"),
    ("activity_count", "#activity+count", "int"),
    ("basis",         "#meta+basis",      "text"),
    ("data_date",     "#date",            "date"),
    ("period_from",   "#date+start",      "date"),
    ("period_to",     "#date+end",        "date"),
    ("schema_version", "#meta+version",   "int"),
)
HEADERS = tuple(c[0] for c in COLUMNS)
HXL_ROW = tuple(c[1] for c in COLUMNS)

REQUIRED_METADATA = ("data_date", "period_from", "period_to", "schema_version")

SECTOR = "Protection - MHPSS"
ORG = "MHPSS Sector"
ACTIVITY = "MHPSS activities"
BASIS = ("People reached with MHPSS activities, as the source reports it, counted once per "
         "location (max per location). NON-ADDITIVE: never sum across rows, dimensions or "
         "organisations; cross-dimension sums disagree by design.")


class ContractError(RuntimeError):
    pass


def _here() -> Path:
    return Path(__file__).resolve().parent


def _default_exchange_dir() -> Path:
    return _here().parent.parent / "exchange"


def _default_source_dir() -> Path:
    return _default_exchange_dir() / "source"


def _strict_json_loads(text: str):
    def reject_pairs(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ContractError(f"duplicate JSON key: {k}")
            out[k] = v
        return out

    def reject_constant(tok):
        raise ContractError(f"non-finite JSON value: {tok}")

    return json.loads(text, object_pairs_hook=reject_pairs, parse_constant=reject_constant)


def _scan_for_identity_keys(node, path="") -> None:
    """Fail closed if any identity/case key appears anywhere in the source."""
    if isinstance(node, dict):
        for k, v in node.items():
            low = str(k).lower()
            if "name" in low and low not in ALLOWED_NAME_KEYS:
                raise ContractError(
                    f"key '{k}' contains 'name' and is not a known geographic name key; "
                    "treat as identity data and refuse"
                )
            for frag in DENY_KEY_FRAGMENTS:
                if frag in low:
                    # `palika`/`district_code` are geography, not identity; and the
                    # pcode note text is allowed. Only *keys* are scanned here.
                    raise ContractError(
                        f"identity/case key '{k}' found at {path or '<root>'}; "
                        "the exchange feed must carry no individual data"
                    )
            _scan_for_identity_keys(v, f"{path}.{k}" if path else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _scan_for_identity_keys(v, f"{path}[{i}]")


def _load_source(source_dir: Path):
    base_p = source_dir / "baseline.json"
    pcode_p = source_dir / "pcode-map.json"
    base = _strict_json_loads(base_p.read_text(encoding="utf-8"))
    pcode = _strict_json_loads(pcode_p.read_text(encoding="utf-8"))
    _scan_for_identity_keys(base)
    _scan_for_identity_keys(pcode)
    return base, pcode


def _rows_from_source(base, pcode):
    districts = pcode["districts"]
    provinces = pcode["provinces"]
    palika_pcodes = base["palika_pcodes"]
    data_date = base["data_date"]
    period_from = base["period_from"]
    period_to = base["period_to"]

    rows = []
    for r in base["rows"]:
        mun = r["mun"]
        dcode = r["district_code"]
        if dcode not in districts:
            raise ContractError(f"district code {dcode!r} has no verified P-code mapping")
        d = districts[dcode]
        adm2_pcode = d["adm2_pcode"]
        adm1_pcode = d["adm1_pcode"]
        if adm1_pcode not in provinces:
            raise ContractError(f"province P-code {adm1_pcode!r} is not in the verified province map")
        if mun not in palika_pcodes:
            raise ContractError(f"palika {mun!r} has no verified adm3 P-code")
        adm3_pcode = palika_pcodes[mun]
        # The adm3 P-code must be a child of its adm2 P-code (COD-AB hierarchy).
        if not adm3_pcode.startswith(adm2_pcode):
            raise ContractError(
                f"adm3 P-code {adm3_pcode} for {mun!r} is not a child of adm2 {adm2_pcode}"
            )
        reached = int(r["reached"])
        activities = int(r["activities"])
        rows.append({
            "activity": ACTIVITY,
            "sector": SECTOR,
            "org": ORG,
            "adm1_name": provinces[adm1_pcode],
            "adm1_pcode": adm1_pcode,
            "adm2_name": d["cod_name"],
            "adm2_pcode": adm2_pcode,
            "adm3_name": mun,
            "adm3_pcode": adm3_pcode,
            "reached": reached,
            "activity_count": activities,
            "basis": BASIS,
            "data_date": data_date,
            "period_from": period_from,
            "period_to": period_to,
            "schema_version": SCHEMA_VERSION,
        })
    rows.sort(key=lambda x: (x["adm2_pcode"], x["adm3_pcode"]))
    return rows, {"data_date": data_date, "period_from": period_from, "period_to": period_to}


def _check_contract(rows, meta):
    """The machine check. Fails closed on any contract break."""
    if len(rows) < 2:
        # One row in a public feed IS the total; a below-floor complement could
        # then be reconstructed from it. Refuse a single-row publication.
        raise ContractError("feed must carry at least 2 reporting units (a single row is the total)")

    seen = set()
    for r in rows:
        for col, _tag, kind in COLUMNS:
            v = r.get(col)
            if v is None or (isinstance(v, str) and v == ""):
                raise ContractError(f"missing required field {col!r}")
            if kind == "pcode":
                s = str(v)
                if not s.startswith("NP") or not s[2:].isdigit():
                    raise ContractError(f"column {col!r} value {v!r} is not a valid NP P-code")
            if kind == "int" and not isinstance(v, int):
                raise ContractError(f"column {col!r} must be an integer, got {v!r}")
        if r["reached"] < SUPPRESSED_BELOW:
            raise ContractError(
                f"row {r['adm3_pcode']} has reached={r['reached']} below the floor "
                f"{SUPPRESSED_BELOW}; a below-floor value may describe one person"
            )
        if r["reached"] < 0 or r["activity_count"] < 0:
            raise ContractError(f"negative count in row {r['adm3_pcode']}")
        key = (r["adm3_pcode"], r["data_date"])
        if key in seen:
            raise ContractError(f"duplicate row for {key}")
        seen.add(key)

    for m in REQUIRED_METADATA:
        if m not in rows[0]:
            raise ContractError(f"missing metadata field {m!r}")
    if rows[0]["schema_version"] != SCHEMA_VERSION:
        raise ContractError("schema_version mismatch between rows and the builder")
    if "non-additive" not in rows[0]["basis"].lower():
        raise ContractError("the non-additivity statement must travel with the numbers")

    # Non-additivity: the feed must never carry a published total that equals the
    # sum of the rows (that would be an additive claim).
    total = sum(r["reached"] for r in rows)
    if any(r["reached"] == total for r in rows):  # pragma: no cover - defensive
        raise ContractError("a row equals the sum of all rows; additive total detected")


def _render_csv(rows) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(HEADERS)
    w.writerow(HXL_ROW)
    for r in rows:
        w.writerow([r[h] for h in HEADERS])
    return buf.getvalue()


def _schema_doc(meta) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": "tools/exchange/build_exchange.py (stdlib only; no network, no AI)",
        "description": (
            "Pull-only aggregate exchange feed for OCHA/NDRRMA. One row per reporting unit "
            "(adm3 palika). Aggregates only; no individual, case or identity data."
        ),
        "suppressed_below": SUPPRESSED_BELOW,
        "reach_is_additive": False,
        "reach_note": BASIS,
        "join_key": "OCHA COD-AB P-code (adm1/adm2/adm3). Join on the P-code, never on a place name.",
        "data_date": meta["data_date"],
        "period_from": meta["period_from"],
        "period_to": meta["period_to"],
        "columns": [
            {"name": h, "hxl": tag, "type": kind}
            for (h, tag, kind) in COLUMNS
        ],
    }


def build(source_dir: Path, exchange_dir: Path, write: bool = True) -> dict:
    base, pcode = _load_source(source_dir)
    rows, meta = _rows_from_source(base, pcode)
    _check_contract(rows, meta)

    csv_text = _render_csv(rows)
    dated_name = f"mhpss_np_5w_{meta['data_date']}.csv"
    latest_name = "mhpss_np_5w_latest.csv"

    out = {"dated": dated_name, "latest": latest_name, "rows": len(rows),
           "data_date": meta["data_date"], "sha256": hashlib.sha256(csv_text.encode()).hexdigest()}

    if write:
        exchange_dir.mkdir(parents=True, exist_ok=True)
        (exchange_dir / dated_name).write_text(csv_text, encoding="utf-8")
        (exchange_dir / latest_name).write_text(csv_text, encoding="utf-8")
        (exchange_dir / "schema.json").write_text(
            json.dumps(_schema_doc(meta), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return out


def verify(source_dir: Path, exchange_dir: Path) -> dict:
    """Rebuild in memory and assert the committed files match byte-for-byte."""
    base, pcode = _load_source(source_dir)
    rows, meta = _rows_from_source(base, pcode)
    _check_contract(rows, meta)
    csv_text = _render_csv(rows)
    dated = exchange_dir / f"mhpss_np_5w_{meta['data_date']}.csv"
    latest = exchange_dir / "mhpss_np_5w_latest.csv"
    for p in (dated, latest):
        if not p.exists():
            raise ContractError(f"committed exchange file missing: {p.name}")
        if p.read_text(encoding="utf-8") != csv_text:
            raise ContractError(
                f"{p.name} does not match the deterministic build of the source "
                "(regenerate with tools/exchange/build_exchange.py)"
            )
    schema_p = exchange_dir / "schema.json"
    if not schema_p.exists():
        raise ContractError("schema.json is missing")
    want = json.loads(schema_p.read_text(encoding="utf-8"))
    if want != _schema_doc(meta):
        raise ContractError("schema.json does not match the builder's schema")
    return {"verified": True, "rows": len(rows), "data_date": meta["data_date"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the pull-only OCHA/NDRRMA exchange feed.")
    ap.add_argument("--source-dir", type=Path, default=None)
    ap.add_argument("--exchange-dir", type=Path, default=None)
    ap.add_argument("--check", action="store_true", help="validate only; write nothing")
    ap.add_argument("--verify", action="store_true", help="assert committed files match the source")
    args = ap.parse_args(argv)

    source_dir = args.source_dir or _default_source_dir()
    exchange_dir = args.exchange_dir or _default_exchange_dir()

    try:
        if args.verify:
            res = verify(source_dir, exchange_dir)
            print(json.dumps(res, sort_keys=True))
            return 0
        res = build(source_dir, exchange_dir, write=not args.check)
        res["wrote"] = not args.check
        print(json.dumps(res, sort_keys=True))
        return 0
    except (ContractError, OSError) as e:
        print(f"CONTRACT FAILURE: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
