#!/usr/bin/env python3
"""Detector C: for every merge into main since a date, list the lines main had
before the merge that the merge dropped, and classify each:

  STILL_GONE  the line is not on origin/main today
  RESTORED    the line is back on origin/main today (someone noticed and put it
              back — the signature of the silent-revert/restore cycle)

Files whose content is a dictionary of translated values (assets/i18n-strings.js)
are excluded here and reviewed separately: their values change by design.
"""
import subprocess, sys, collections, json
from pathlib import Path

REPO = str(Path(__file__).resolve().parents[2])
SINCE = sys.argv[1] if len(sys.argv) > 1 else "2026-09-19T00:00:00+00:00"
EXCLUDE = {"assets/i18n-strings.js"}


def g(*a):
    return subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True).stdout


def blob(rev, path):
    r = subprocess.run(["git", "-C", REPO, "show", f"{rev}:{path}"], capture_output=True, text=True)
    return r.stdout.splitlines() if r.returncode == 0 else None


def lines_at(rev, path):
    key = (rev, path)
    if key not in _cache:
        b = blob(rev, path)
        _cache[key] = set(b) if b is not None else set()
    return _cache[key]


_cache = {}
merges = g("rev-list", "--merges", f"--since={SINCE}", "origin/main").split()
rows = []
for m in merges:
    parts = g("rev-list", "--parents", "-n1", m).split()
    if len(parts) < 3:
        continue
    p1, p2 = parts[1], parts[2]
    for f in g("diff", "--name-only", p1, m).split():
        if f in EXCLUDE:
            continue
        if not f.endswith((".js", ".py", ".html", ".json", ".css", ".csv")):
            continue
        a, b = blob(p1, f), blob(m, f)
        if a is None or b is None:
            continue
        sb = set(b)
        dropped = [l for l in a if l not in sb and l.strip() and len(l.strip()) > 4]
        if not dropped:
            continue
        today = lines_at("origin/main", f)
        gone = [l for l in dropped if l not in today]
        back = [l for l in dropped if l in today]
        rows.append({
            "merge": m[:7],
            "subject": g("log", "-1", "--format=%h %ad %s", "--date=short", m).strip(),
            "file": f,
            "dropped": len(dropped),
            "still_gone": len(gone),
            "restored": len(back),
            "restored_samples": [l.strip()[:100] for l in back[:3]],
            "gone_samples": [l.strip()[:100] for l in gone[:3]],
        })

json.dump(rows, open(Path(__file__).resolve().parent / "sweep-classified.json", "w"),
          indent=1, ensure_ascii=False)
for r in rows:
    print(f"{r['merge']} {r['file']:<34} dropped={r['dropped']:<4} still_gone={r['still_gone']:<4} restored={r['restored']:<4} | {r['subject'][:70]}")
print("merges scanned:", len(merges), "| rows:", len(rows))
