#!/usr/bin/env python3
"""Verify every destination the concepts link to actually resolves, and that
no repository runtime file was touched (not part of the QA evidence record)."""
from __future__ import annotations

import json
import re
import subprocess
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
BASE_URL = f"http://100.98.168.123:8831"


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=6) as r:
            return r.status, len(r.read())
    except Exception as e:
        return None, str(e)


def main():
    links = {}
    for page in ("index.html", "concept-conservative.html",
                 "concept-recommended.html", "concept-divergent.html"):
        html = (HERE / page).read_text()
        links[page] = sorted(set(re.findall(r'(?:href|src)="([^"#?]+)', html)))
    resolved = {}
    for page, ls in links.items():
        for l in ls:
            if l.startswith(("http", "mailto")):
                continue
            resolved.setdefault(l, (HERE / l).resolve().exists())
    print(json.dumps({"relative_targets": {k: v for k, v in sorted(resolved.items())}}, indent=2))
    # Confirm the targets that leave the preview directory land on real Hub files.
    for l in sorted(resolved):
        if l.startswith(".."):
            print(f"  {l} -> {(HERE / l).resolve()} exists={(HERE / l).resolve().exists()}")
    # repository cleanliness outside the preview dir
    out = subprocess.check_output(
        ["git", "status", "--porcelain", "--", ".", ":(exclude)design-preview"],
        cwd=REPO, text=True).strip()
    print("runtime tree dirty outside design-preview:", repr(out))
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    print("HEAD:", head)


if __name__ == "__main__":
    main()
