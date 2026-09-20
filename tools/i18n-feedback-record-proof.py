#!/usr/bin/env python3
"""Prove the wording-feedback record is structured, scoped and unsent.

Adib's team reports wrong or awkward Nepali wording during the trial and a
human reviews it afterwards. The report must not open a privacy hole, so
`reportWording()` in assets/i18n.js:

  * carries a dictionary KEY and a fixed REASON, never free text (there is no
    field a beneficiary's name could end up in);
  * carries no query string or fragment from the address bar;
  * is refused for a key the page does not actually render;
  * is refused for a reason outside the fixed set;
  * is NOT SENT anywhere -- the engine has no transport, and the security
    rules deny any collection that is not the field records themselves.

Run from this repository root:
    python3 tools/i18n-feedback-record-proof.py
Exit 0 all properties hold / 1 a property is violated / 2 cannot run.
"""
from __future__ import annotations

import functools
import http.server
import json
import shutil
import socketserver
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PAGE = """<!DOCTYPE html>
<html lang="en" data-i18n-default="ne">
<head><meta charset="utf-8"><title>feedback fixture</title></head>
<body>
<h1 data-i18n="fx.title">t</h1>
<p data-i18n="fx.plain">p</p>
<script src="assets/i18n-strings.js"></script>
<script src="assets/i18n.js"></script>
</body></html>
"""

STRINGS = """window.I18N_STRINGS = {
  _meta: { langs: [{code:"en",label:"ENG",name:"English",html:"en"},
                   {code:"ne",label:"NEP",name:"नेपाली",html:"ne"}],
           revision: "fixture-1", professionalOnly: [],
           source: {machine:["fx.plain"], human:[]} },
  en: { "fx.title":"Title", "fx.plain":"Plain",
        "lang.select":"Select language", "mt.dismiss":"Dismiss",
        "mt.readEnglish":"Read in English", "mt.notice.en":"auto",
        "mt.authoritative.en":"auth", "i18n.todoTitle":"todo" },
  ne: { "fx.title":"शीर्षक", "fx.plain":"सरल" }
};
"""

PROBE = """() => {
  const I = window.I18N;
  const out = {reasons: I.feedbackReasons, cases: {}};
  out.cases.valid        = I.reportWording('fx.title', 'wrong');
  out.cases.absent_key   = I.reportWording('not.on.this.page', 'wrong');
  out.cases.bad_reason   = I.reportWording('fx.title', 'whatever I type');
  out.cases.no_reason    = I.reportWording('fx.title');
  out.cases.non_string   = I.reportWording({}, 'wrong');
  out.proto_methods      = Object.getOwnPropertyNames(I);
  out.has_transport      = ['fetch','XMLHttpRequest','sendBeacon','WebSocket']
                             .filter(k => typeof window[k] === 'function');
  return out;
}"""

# Drive the reviewer mode the way a person would: turn it on, tap a string,
# pick a reason from the popup, then read back what was recorded.
REVIEWER_TAP = """() => {
  const el = document.querySelector('[data-i18n="fx.title"]');
  el.click();
  const pick = document.getElementById('i18npick');
  if (!pick) return {picker: false};
  const reasons = [...pick.querySelectorAll('button')].map(b => b.textContent);
  pick.querySelector('button[data-reason="awkward"]').click();
  return {
    picker: true, reasons,
    picker_gone_after_pick: !document.getElementById('i18npick'),
    recorded: window.I18N.reports(),
    mode: document.documentElement.getAttribute('data-i18n-report'),
    chip: (document.getElementById('i18nrpt') || {}).textContent || null
  };
}"""

QUIET_READER = """() => ({
  mode: document.documentElement.getAttribute('data-i18n-report'),
  chip: !!document.getElementById('i18nrpt'),
  picker: !!document.getElementById('i18npick')
})"""


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def main():
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        print("cannot run: playwright unavailable: %s" % exc)
        return 2

    checks = []
    with tempfile.TemporaryDirectory(prefix="i18n-feedback-") as temp:
        root = Path(temp)
        (root / "assets").mkdir()
        shutil.copy(ROOT / "assets" / "i18n.js", root / "assets" / "i18n.js")
        (root / "assets" / "i18n-strings.js").write_text(STRINGS, encoding="utf-8")
        (root / "page.html").write_text(PAGE, encoding="utf-8")

        handler = functools.partial(Quiet, directory=str(root))
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as server:
            port = server.server_address[1]
            threading.Thread(target=server.serve_forever, daemon=True).start()
            # A query string and fragment that must NOT reach the record.
            url = ("http://127.0.0.1:%d/page.html?lang=ne&secret=NAME#frag" % port)

            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                page = browser.new_page()
                page.goto(url, wait_until="load")
                page.wait_for_timeout(400)
                res = page.evaluate(PROBE)

                # A quiet reader: no reviewer mode, nothing on screen.
                quiet = browser.new_page()
                quiet.goto("http://127.0.0.1:%d/page.html" % port, wait_until="load")
                quiet.wait_for_timeout(400)
                quiet_state = quiet.evaluate(QUIET_READER)

                # The reviewer: ?i18n=report, tap, pick, read back.
                page.goto("http://127.0.0.1:%d/page.html?i18n=report" % port,
                          wait_until="load")
                page.wait_for_timeout(400)
                tap = page.evaluate(REVIEWER_TAP)
                browser.close()
            server.shutdown()

    cases = res["cases"]
    print("fixed reasons:", res["reasons"])
    print("I18N members :", res["proto_methods"])
    print("window transports present:", res["has_transport"])
    for name, val in cases.items():
        print("  %-14s %s" % (name, json.dumps(val, ensure_ascii=False)))

    valid = cases["valid"] or {}
    checks.append(("a_valid_report_is_produced", bool(valid), str(valid)))
    checks.append(("report_is_structured_to_a_key_and_reason",
                   valid.get("key") == "fx.title" and valid.get("reason") == "wrong"
                   and valid.get("kind") == "i18n_feedback",
                   str(valid)))
    checks.append(("reason_set_is_fixed", res["reasons"] == ["wrong", "awkward", "unclear", "missing"],
                   str(res["reasons"])))
    # The critical one: nothing typed reaches the record.
    flat = json.dumps(valid, ensure_ascii=False)
    checks.append(("no_free_text_field_in_the_record",
                   not any(k in valid for k in ("text", "comment", "note", "message", "free_text")),
                   str(sorted(valid.keys()))))
    checks.append(("no_query_string_or_fragment_in_the_record",
                   "secret" not in flat and "NAME" not in flat and "frag" not in flat,
                   flat))
    checks.append(("a_key_not_rendered_here_is_refused",
                   cases["absent_key"] is None, str(cases["absent_key"])))
    checks.append(("an_unlisted_reason_is_refused",
                   cases["bad_reason"] is None, str(cases["bad_reason"])))
    checks.append(("a_missing_reason_is_refused",
                   cases["no_reason"] is None, str(cases["no_reason"])))
    checks.append(("a_non_string_key_is_refused",
                   cases["non_string"] is None, str(cases["non_string"])))
    # The engine itself must have no transport: the sink is a dependency.
    engine = (ROOT / "assets" / "i18n.js").read_text(encoding="utf-8")
    checks.append(("engine_has_no_transport",
                   not any(t in engine for t in ("fetch(", "XMLHttpRequest",
                                                 "sendBeacon", "WebSocket")),
                   "engine contains no network call"))
    checks.append(("record_declares_its_schema_and_language",
                   valid.get("schema") == "i18n-feedback/1" and valid.get("lang") == "ne",
                   str({k: valid.get(k) for k in ("schema", "lang")})))

    # ---- the reviewer mode, driven as a person would ----------------------
    print()
    print("quiet reader      :", json.dumps(quiet_state))
    print("reviewer tap      :", json.dumps(tap, ensure_ascii=False))
    checks.append(("quiet_reader_sees_no_reviewer_chrome",
                   quiet_state["mode"] is None and not quiet_state["chip"]
                   and not quiet_state["picker"],
                   str(quiet_state)))
    checks.append(("reviewer_mode_marks_the_document",
                   tap.get("mode") == "on", str(tap.get("mode"))))
    checks.append(("tapping_a_string_opens_a_fixed_reason_picker",
                   tap.get("picker") and tap.get("reasons") ==
                   ["wrong", "awkward", "unclear", "missing"],
                   str(tap.get("reasons"))))
    recorded = tap.get("recorded") or []
    checks.append(("picking_a_reason_records_a_structured_report",
                   len(recorded) == 1 and recorded[0]["key"] == "fx.title"
                   and recorded[0]["reason"] == "awkward",
                   json.dumps(recorded, ensure_ascii=False)))
    checks.append(("picker_closes_after_picking", bool(tap.get("picker_gone_after_pick")),
                   str(tap.get("picker_gone_after_pick"))))
    checks.append(("a_recorded_report_carries_no_free_text",
                   not any(k in (recorded[0] if recorded else {})
                           for k in ("text", "comment", "note", "message")),
                   str(sorted(recorded[0].keys())) if recorded else "no report"))

    print()
    bad = [c for c in checks if not c[1]]
    print("checks: %d   failures: %d" % (len(checks), len(bad)))
    for name, ok, detail in bad:
        print("  FAIL %s  (%s)" % (name, detail))
    print("VERDICT:", "feedback record is structured, scoped and unsent" if not bad
          else "FEEDBACK PROPERTY VIOLATED")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
