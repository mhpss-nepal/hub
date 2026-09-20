#!/usr/bin/env python3
"""Prove the protected safety keys render ENGLISH, against a REAL dictionary.

The card requires the safety strings be re-verified AFTER the patches are
applied, not assumed. tools/i18n-protection-and-marks-proof.py does this with a
deliberately-hostile FIXTURE dictionary; this does it with the dictionaries
actually under discussion, so a claim about a real patch can be checked rather
than trusted.

It renders one page carrying every named protected key with the given
dictionary, at `?lang=ne`, and fails if any of them shows Devanagari.

    python3 tools/ward-protected-english-proof.py                # delivered dict
    python3 tools/ward-protected-english-proof.py path/to/i18n-strings.js

Exit 0 all protected keys render English / 1 a key rendered Nepali / 2 cannot run.
"""
from __future__ import annotations

import functools
import http.server
import json
import re
import shutil
import socketserver
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The protected keys the card names, plus the prefixes they belong to.
PREFIXES = ["phq9.item", "phq9.scale", "phq9.cutoff", "consent.",
            "safeguard.", "clinical.", "sr.p007", "sr.p001", "sr.clinicalNote"]
NAMED = [
    "phq9.item9", "phq9.item9Instruction", "phq9.scale1", "phq9.cutoff.interpretation",
    "consent.label", "consent.phq9",
    "safeguard.checkLabel", "safeguard.confirmation", "safeguard.consequence",
    "safeguard.referralExclusion", "sr.clinicalNote", "sr.p001", "sr.p007",
]

PAGE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>protected-key proof</title></head>
<body>
%s
<script src="assets/i18n-strings.js"></script>
<script src="assets/i18n.js"></script>
</body></html>
"""


def block(src, lang):
    m = re.search(r"\n  " + lang + r":\s*\{(.*?)\n  \}", src, re.S)
    if not m:
        return {}
    b = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)
    b = re.sub(r"^\s*//.*$", "", b, flags=re.M)
    return {mm.group(1): mm.group(2) for mm in
            re.finditer(r'"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"', b)}


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def has_devanagari(s):
    return any("\u0900" <= ch <= "\u097f" for ch in (s or ""))


def main(argv):
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        print("cannot run: playwright unavailable: %s" % exc)
        return 2

    label = "delivered dictionary"
    if len(argv) > 1:
        src = Path(argv[1]).read_text(encoding="utf-8")
        label = argv[1]
    else:
        src = (ROOT / "assets" / "i18n-strings.js").read_text(encoding="utf-8")

    ne = block(src, "ne")
    with_ne = [k for k in NAMED if ne.get(k, "").strip()]
    print("dictionary: %s" % label)
    print("  named protected keys carrying a Nepali value: %d" % len(with_ne))
    for k in with_ne:
        print("    %-32s ne=%s" % (k, ne[k][:50]))

    rows = "\n".join('<p data-i18n="%s">%s</p>' % (k, k) for k in NAMED)
    with tempfile.TemporaryDirectory(prefix="ward-protected-") as temp:
        root = Path(temp)
        (root / "assets").mkdir()
        shutil.copy(ROOT / "assets" / "i18n.js", root / "assets" / "i18n.js")
        (root / "assets" / "i18n-strings.js").write_text(src, encoding="utf-8")
        (root / "page.html").write_text(PAGE % rows, encoding="utf-8")

        handler = functools.partial(Quiet, directory=str(root))
        srv = socketserver.TCPServer(("127.0.0.1", 0), handler)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                ctx = browser.new_context(locale="en-US")
                page = ctx.new_page()
                page.goto("http://127.0.0.1:%d/page.html?lang=ne" % port,
                          wait_until="load")
                page.wait_for_timeout(300)
                got = page.evaluate(
                    "() => { const o = {lang: document.documentElement.getAttribute('data-lang'), t: {}};"
                    " document.querySelectorAll('[data-i18n]').forEach(e => {"
                    "   o.t[e.getAttribute('data-i18n')] = e.textContent; }); return o; }")
                ctx.close()
                browser.close()
        finally:
            srv.shutdown(); srv.server_close()

    failures = []
    print("  page resolved: data-lang=%s" % got["lang"])
    if got["lang"] != "ne":
        print("VERDICT: cannot verify — the page did not resolve to Nepali")
        return 2
    for k in NAMED:
        text = got["t"].get(k, "")
        bad = has_devanagari(text)
        if bad:
            failures.append(k)
        print("    %-32s %s  %s" % (k, "NEPALI!" if bad else "english",
                                    text[:56].replace("\n", " ")))
    print()
    print("checks: %d   failures: %d" % (len(NAMED), len(failures)))
    if failures:
        print("VERDICT: FAIL — %s rendered Nepali" % ", ".join(failures))
        return 1
    print("VERDICT: all protected keys render English on the Nepali page")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
