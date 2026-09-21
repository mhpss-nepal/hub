#!/usr/bin/env python3
"""Detector B: merges that took the branch's older version of a file.

Signature of the silent revert: a line exists in M^1 (main just before the
merge) and in neither M (the merge result) nor M^2 (the branch tip). The merge
therefore resolved that region to the branch's copy, and whatever main had
gained in that region since the branch was cut is gone.

Graph-based detector A (lines absent at merge-base) misses the case where the
branch's own parent already carried the change and the author still rewrote it
from a stale copy; detector B catches it, because it compares trees, not
ancestry.
"""
import subprocess, sys, json
from pathlib import Path

REPO = str(Path(__file__).resolve().parents[2])
SINCE = sys.argv[1] if len(sys.argv) > 1 else "2026-09-19T00:00:00+00:00"
SHIPPED = ("assets/", "tools/", "tests/", "exchange/", "docs/")


def g(*a):
    return subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True).stdout


def blob(rev, path):
    r = subprocess.run(["git", "-C", REPO, "show", f"{rev}:{path}"], capture_output=True, text=True)
    return r.stdout.splitlines() if r.returncode == 0 else None


merges = g("rev-list", "--merges", f"--since={SINCE}", "origin/main").split()
out = []
for m in merges:
    parts = g("rev-list", "--parents", "-n1", m).split()
    if len(parts) < 3:
        continue
    p1, p2 = parts[1], parts[2]
    files = g("diff", "--name-only", p1, m).split()
    hits = []
    for f in files:
        if not f.endswith((".js", ".py", ".html", ".json", ".css", ".csv", ".md")):
            continue
        a, b, c = blob(p1, f), blob(m, f), blob(p2, f)
        if a is None or b is None or c is None:
            continue
        sb, sc = set(b), set(c)
        lost = [l for l in a if l not in sb and l not in sc and l.strip() and len(l.strip()) > 3]
        if len(lost) >= 2:
            hits.append({"file": f, "lines": len(lost), "samples": [l.strip()[:110] for l in lost[:5]]})
    if hits:
        out.append({
            "merge": m[:7],
            "subject": g("log", "-1", "--format=%h %ad %s", "--date=short", m).strip(),
            "branch_tip": g("log", "-1", "--format=%h %s", p2).strip(),
            "hits": hits,
        })

print(json.dumps(out, indent=1, ensure_ascii=False))
print("merges scanned:", len(merges), "| merges with a branch-took-over hit:", len(out))
