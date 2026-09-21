#!/usr/bin/env python3
"""Sweep hub history for silently reverted content.

A silent revert is: a merge M into main whose result drops lines that were added
to main AFTER the branch was cut — i.e. lines present in M^1 (main before the
merge) and absent from merge-base(M^1, M^2) (the branch's own base). The branch
never saw them, so it could not have deleted them on purpose.
"""
import subprocess, sys, json
from pathlib import Path

REPO = str(Path(__file__).resolve().parents[2])


def g(*args):
    return subprocess.run(["git", "-C", REPO] + list(args),
                          capture_output=True, text=True, check=True).stdout


merges = g("rev-list", "--merges", "origin/main").split()
report = []
for m in merges:
    parts = g("rev-list", "--parents", "-n1", m).split()
    if len(parts) < 3:
        continue
    p1, p2 = parts[1], parts[2]
    base = g("merge-base", p1, p2).strip()
    subject = g("log", "-1", "--format=%h %s", m).strip()
    files = g("diff", "--name-only", p1, m).split()
    hits = []
    for f in files:
        def blob(rev):
            r = subprocess.run(["git", "-C", REPO, "show", f"{rev}:{f}"],
                               capture_output=True, text=True)
            return set(r.stdout.splitlines()) if r.returncode == 0 else set()
        b_base, b_p1, b_m = blob(base), blob(p1), blob(m)
        # lines the merge removed from main
        lost = b_p1 - b_m
        # of those, ones that main gained AFTER the branch was cut
        silent = {l for l in lost if l not in b_base and l.strip()}
        if len(silent) > 2:
            hits.append({"file": f, "lost_lines": len(lost), "silent_lines": len(silent),
                         "samples": sorted(silent)[:6]})
    if hits:
        report.append({"merge": m[:7], "subject": subject, "base": base[:7],
                       "p1": p1[:7], "p2": p2[:7], "hits": hits})

print(json.dumps(report, indent=1, ensure_ascii=False))
print("merges scanned:", len(merges))
