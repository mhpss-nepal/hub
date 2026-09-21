#!/usr/bin/env python3
"""Small reader for qa-results.json — prints the parts a human needs to judge."""
import json
import sys
from pathlib import Path

rep = json.loads((Path(__file__).resolve().parent / "qa-results.json").read_text())
only = sys.argv[1] if len(sys.argv) > 1 else None

for pg, entry in rep["pages"].items():
    if only and only not in pg:
        continue
    print("=" * 70)
    print(pg)
    for w, rec in entry["widths"].items():
        ov = rec["overflow"]
        taps = rec.get("tapFailures") or []
        print(f"  {w}px  rootOverflow={ov['rootOverflow']} "
              f"doc={ov['docScrollWidth']}/{ov['clientWidth']} "
              f"offenders={len(ov['offenders'])} axe={len(rec['axe'])} "
              f"tapFailures={len(taps)}")
        for t in taps[:6]:
            print("      TAP", t["tag"], t["id"], repr(t["text"]), t["w"], "x", t["h"],
                  "label", t["labelW"], "x", t["labelH"])
        for o in ov["offenders"][:4]:
            print("      OFLOW", o)
        for v in rec["axe"][:6]:
            print("      AXE", v)
        if rec.get("tab"):
            print("      tab steps:", len(rec["tab"]), "covered:", sum(1 for s in rec["tab"] if s["coveredBy"]))
        if rec.get("filters"):
            print("      FILTERS", json.dumps(rec["filters"]))
        if rec.get("empty") is not None:
            print("      EMPTY", json.dumps(rec["empty"]))
        if rec.get("states"):
            print("      STATES", json.dumps(rec["states"]))
print("=" * 70)
print("hard_failures:", rep["hard_failures"], "ok:", rep["ok"])
print("external requests:", sorted(set(rep["network"])))
