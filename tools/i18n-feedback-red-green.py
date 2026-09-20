#!/usr/bin/env python3
"""Red/green demonstration for the trial wording-feedback channel.

The review asked for two corrections, both about the reviewer channel rather
than the per-layer default:

  1. feedback must be DURABLE on the device -- an unexported report must
     survive closing and reopening the page (it used to live in
     sessionStorage and vanished with the tab);
  2. the reason picker must FIT a small phone viewport and be operable by
     keyboard -- it used to clamp its left edge without accounting for its own
     width, so on a 320 px screen a picker opened near the right edge ran off
     the screen.

Both are demonstrated the same way the language default was: materialise the
engine as it stood at this task's base commit, run the real checks against it
(they must FAIL), then run the same checks against the delivered engine (they
must PASS). Nothing is read from a stored transcript.

    python3 tools/i18n-feedback-red-green.py

Exit 0 when base is red and head is green.
"""
from __future__ import annotations

import functools
import http.server
import importlib.util
import json
import socketserver
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The engine that first carried the reviewer channel (this task's first
# submission), i.e. the state the review found the two defects in.
FEEDBACK_BASE = "44bba2cd1440d9af9ca7769b80f8187466f93797"
PROOF = ROOT / "tools" / "i18n-feedback-record-proof.py"

# The fixture page and dictionary come from the proof tool, so the red run and
# the green run exercise exactly the same page.
_spec = importlib.util.spec_from_file_location("i18n_proof", PROOF)
proof = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(proof)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def engine_at(rev: str) -> str:
    return subprocess.run(["git", "show", "%s:assets/i18n.js" % rev],
                          cwd=ROOT, capture_output=True, text=True, check=True).stdout


# Report one string on the many-target page: click it, then pick a reason.
TAP_FIRST = """() => {
  const el = document.querySelector('[data-i18n]');
  el.click();
  const p = document.getElementById('i18npick');
  if (!p) return {picker: false};
  p.querySelector('button[data-reason="awkward"]').click();
  return {picker: true, recorded: window.I18N.reports().length};
}"""


def measure(engine_src: str) -> dict:
    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory(prefix="i18n-red-green-") as temp:
        root = Path(temp)
        (root / "assets").mkdir()
        (root / "assets" / "i18n.js").write_text(engine_src, encoding="utf-8")
        (root / "assets" / "i18n-strings-many.js").write_text(
            proof.MANY_STRINGS, encoding="utf-8")
        (root / "many.html").write_text(
            proof.MANY_PAGE.replace("assets/i18n-strings.js",
                                    "assets/i18n-strings-many.js"),
            encoding="utf-8")

        handler = functools.partial(Quiet, directory=str(root))
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
            port = srv.server_address[1]
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            base = "http://127.0.0.1:%d/many.html?i18n=report" % port
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                # narrow scan over many targets
                scans = {}
                for w, h in ((320, 640), (360, 740)):
                    ctx = browser.new_context(viewport={"width": w, "height": h})
                    page = ctx.new_page()
                    page.goto(base, wait_until="load")
                    page.wait_for_timeout(400)
                    scans["%dx%d" % (w, h)] = page.evaluate(proof.MANY_SCAN)
                    ctx.close()

                # durability: record, close, reopen in the same profile
                ctx = browser.new_context()
                page = ctx.new_page()
                page.goto(base, wait_until="load")
                page.wait_for_timeout(400)
                page.evaluate(TAP_FIRST)
                page.close()
                again = ctx.new_page()
                again.goto(base, wait_until="load")
                again.wait_for_timeout(400)
                survived = again.evaluate(
                    "() => (window.I18N.reports ? window.I18N.reports().length : -1)")
                scans["survived_reopen"] = survived
                ctx.close()
                browser.close()
            srv.shutdown()
    return scans


def main() -> int:
    try:
        import playwright  # noqa: F401
    except Exception as exc:  # pragma: no cover
        print("cannot run: playwright unavailable: %s" % exc)
        return 2

    base_result = measure(engine_at(FEEDBACK_BASE))
    head_result = measure((ROOT / "assets" / "i18n.js").read_text(encoding="utf-8"))

    print("=" * 74)
    print("BASE engine %s" % FEEDBACK_BASE[:7])
    print("=" * 74)
    print(json.dumps(base_result, indent=2))
    print()
    print("=" * 74)
    print("DELIVERED engine")
    print("=" * 74)
    print(json.dumps(head_result, indent=2))
    print()

    base_red = (any(v["overflowing"] for k, v in base_result.items()
                    if "x" in k) and base_result.get("survived_reopen") == 0)
    head_green = (all(v["overflowing"] == 0 for k, v in head_result.items()
                      if "x" in k) and head_result.get("survived_reopen") == 1)
    print("base red (overflow > 0 and report lost) :", base_red)
    print("delivered green (no overflow, report kept):", head_green)
    if base_red and head_green:
        print("red/green demonstration: PASS")
        return 0
    print("red/green demonstration: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
