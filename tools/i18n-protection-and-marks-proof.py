#!/usr/bin/env python3
"""Prove the safety properties still hold after the per-layer default change.

This task moved the language DEFAULT out of the engine and onto the page. Four
properties must be unchanged by that, and none of them may be taken on trust:

  1. `professionalOnly` keys render in ENGLISH even on a Nepali page -- the
     clinical-consent rule. A machine-rendered PHQ-9 is not the PHQ-9.
  2. The honest reader notice still appears on a Nepali page (translated
     automatically; English authoritative) and not on an English one.
  3. `src="ne"` machine provenance is still labelled (i18n-machine class).
  4. `?i18n=marks` still turns the translator marks on, and the marks are off
     for a plain reader.

It runs against the FIXTURE dictionary (tools/fixtures/i18n-protection-strings.js),
which deliberately GIVES the protected keys a Nepali value -- otherwise the
property would pass for the wrong reason, because there was no Nepali to refuse.

Run from this repository root:
    python3 tools/i18n-protection-and-marks-proof.py
Exit 0 all properties hold / 1 a property is violated / 2 cannot run.
"""
from __future__ import annotations

import functools
import http.server
import shutil
import socketserver
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PAGE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>protection fixture</title></head>
<body>
<h1 data-i18n="fx.title">t</h1>
<p data-i18n="fx.plain">p</p>
<p data-i18n="fx.machine">m</p>
<p data-i18n="phq9.item1">i</p>
<p data-i18n="consent.label">c</p>
<p data-i18n="safeguard.checkLabel">s</p>
<script src="assets/i18n-strings.js"></script>
<script src="assets/i18n.js"></script>
</body></html>
"""

PROBE = """() => {
  const rd = (k) => { const e = document.querySelector('[data-i18n="' + k + '"]');
    return e ? {text: e.textContent.trim(), cls: e.className,
                title: e.getAttribute('title') || ''} : null; };
  const dev = (s) => (String(s).match(/[\\u0900-\\u097f]/g) || []).length;
  const note = document.getElementById('mtnote');
  return {
    lang: document.documentElement.getAttribute('data-lang'),
    marks: document.documentElement.getAttribute('data-i18n-marks'),
    protected: {phq9: rd('phq9.item1'), consent: rd('consent.label'),
                safeguard: rd('safeguard.checkLabel')},
    devanagari_in_protected: ['phq9.item1', 'consent.label', 'safeguard.checkLabel']
        .map(k => dev(rd(k) ? rd(k).text : '')).reduce((a, b) => a + b, 0),
    plain: rd('fx.plain'),
    machine: rd('fx.machine'),
    notice: note ? {kind: note.getAttribute('data-mt'),
                    text: note.innerText} : null,
    kept_count: document.querySelectorAll('.i18n-kept').length,
    todo_count: document.querySelectorAll('.i18n-todo').length,
    machine_count: document.querySelectorAll('.i18n-machine').length
  };
}"""


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def has_devanagari(text):
    return any("\u0900" <= ch <= "\u097f" for ch in text)


def main():
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        print("cannot run: playwright unavailable: %s" % exc)
        return 2

    checks = []
    with tempfile.TemporaryDirectory(prefix="i18n-protection-") as temp:
        root = Path(temp)
        (root / "assets").mkdir()
        shutil.copy(ROOT / "assets" / "i18n.js", root / "assets" / "i18n.js")
        shutil.copy(ROOT / "tools" / "fixtures" / "i18n-protection-strings.js",
                    root / "assets" / "i18n-strings.js")
        (root / "page.html").write_text(PAGE, encoding="utf-8")

        handler = functools.partial(Quiet, directory=str(root))
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as server:
            port = server.server_address[1]
            threading.Thread(target=server.serve_forever, daemon=True).start()
            base = "http://127.0.0.1:%d" % port

            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                page = browser.new_page()

                # ---- a plain reader, Nepali page -------------------------
                page.goto(base + "/page.html?lang=ne", wait_until="load")
                page.wait_for_timeout(400)
                ne = page.evaluate(PROBE)

                print("reader view (?lang=ne):")
                print("  data-lang=%s  marks=%s  kept=%d machine=%d todo=%d"
                      % (ne["lang"], ne["marks"], ne["kept_count"],
                         ne["machine_count"], ne["todo_count"]))
                for k, v in ne["protected"].items():
                    print("  protected %-10s %s" % (k, (v or {}).get("text", "-")[:60]))
                print("  plain     %s" % (ne["plain"] or {}).get("text", "-"))
                print("  notice    %s" % (ne["notice"] or {}).get("kind", "NONE"))

                checks.append(("page_really_nepali",
                               ne["lang"] == "ne" and has_devanagari(ne["plain"]["text"]),
                               (ne["plain"] or {}).get("text", "")))
                checks.append(("protected_keys_stay_english",
                               ne["devanagari_in_protected"] == 0,
                               "devanagari chars in protected text: %d"
                               % ne["devanagari_in_protected"]))
                for k in ("phq9", "consent", "safeguard"):
                    el = ne["protected"][k]
                    checks.append(("protected/%s_english_and_kept" % k,
                                   bool(el) and not has_devanagari(el["text"])
                                   and "i18n-kept" in el["cls"],
                                   (el or {}).get("text", "MISSING")))
                checks.append(("reader_notice_present_on_nepali",
                               bool(ne["notice"]) and ne["notice"]["kind"] == "full"
                               and has_devanagari(ne["notice"]["text"]),
                               str(ne["notice"])[:80]))
                checks.append(("marks_off_for_a_plain_reader", ne["marks"] is None,
                               "data-i18n-marks=%s" % ne["marks"]))
                checks.append(("machine_provenance_labelled",
                               "i18n-machine" in ne["machine"]["cls"],
                               ne["machine"]["cls"]))

                # ---- the translator view (?i18n=marks) -------------------
                page.goto(base + "/page.html?lang=ne&i18n=marks", wait_until="load")
                page.wait_for_timeout(400)
                mk = page.evaluate(PROBE)
                print("translator view (?i18n=marks):")
                print("  marks=%s  kept=%d machine=%d todo=%d"
                      % (mk["marks"], mk["kept_count"], mk["machine_count"],
                         mk["todo_count"]))
                print("  kept title: %s"
                      % (mk["protected"]["phq9"] or {}).get("title", "-"))
                checks.append(("marks_on_when_asked", mk["marks"] == "on",
                               "data-i18n-marks=%s" % mk["marks"]))
                checks.append(("kept_mark_still_explained_in_marks_view",
                               "Kept in English" in (mk["protected"]["phq9"] or {}).get("title", ""),
                               (mk["protected"]["phq9"] or {}).get("title", "")))
                checks.append(("protected_still_english_in_marks_view",
                               mk["devanagari_in_protected"] == 0,
                               "devanagari in protected: %d" % mk["devanagari_in_protected"]))

                # ---- English page: no notice, no marks --------------------
                page.goto(base + "/page.html?lang=en", wait_until="load")
                page.wait_for_timeout(300)
                en = page.evaluate(PROBE)
                checks.append(("no_reader_notice_on_english",
                               en["notice"] is None,
                               str(en["notice"])[:60]))
                checks.append(("english_page_shows_english_text",
                               not has_devanagari(en["plain"]["text"]),
                               en["plain"]["text"]))

                # ---- a SECOND context: a Nepali reader who lands on a page
                # that declares no default still gets the notice + protection
                ctx = browser.new_context(locale="ne-NP")
                p2 = ctx.new_page()
                p2.goto(base + "/page.html", wait_until="load")
                p2.wait_for_timeout(400)
                nn = p2.evaluate(PROBE)
                checks.append(("nepali_browser_without_declaration_is_nepali",
                               nn["lang"] == "ne", "data-lang=%s" % nn["lang"]))
                checks.append(("nepali_browser_protected_still_english",
                               nn["devanagari_in_protected"] == 0,
                               "devanagari in protected: %d" % nn["devanagari_in_protected"]))
                ctx.close()
                browser.close()
            server.shutdown()

    print()
    bad = [c for c in checks if not c[1]]
    print("checks: %d   failures: %d" % (len(checks), len(bad)))
    for name, ok, detail in bad:
        print("  FAIL %s  (%s)" % (name, detail))
    print("VERDICT:", "safety properties unchanged" if not bad
          else "SAFETY PROPERTY VIOLATED")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
