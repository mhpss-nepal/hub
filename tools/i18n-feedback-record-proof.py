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
<input id="field" data-i18n-ph="fx.ph" placeholder="old">
<a id="navlink" href="#x" data-i18n-aria="fx.aria">link</a>
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
        "fx.ph":"Your name", "fx.aria":"Open the report",
        "lang.select":"Select language", "mt.dismiss":"Dismiss",
        "mt.readEnglish":"Read in English", "mt.notice.en":"auto",
        "mt.authoritative.en":"auth", "i18n.todoTitle":"todo" },
  ne: { "fx.title":"शीर्षक", "fx.plain":"सरल",
        "fx.ph":"तपाईंको नाम", "fx.aria":"प्रतिवेदन खोल्नुहोस्" }
};
"""

PROBE = """() => {
  const I = window.I18N;
  const out = {reasons: I.feedbackReasons, cases: {}};
  out.surfaces           = I.feedbackSurfaces;
  out.cases.valid        = I.reportWording('fx.title', 'wrong');
  out.cases.absent_key   = I.reportWording('not.on.this.page', 'wrong');
  out.cases.bad_reason   = I.reportWording('fx.title', 'whatever I type');
  out.cases.no_reason    = I.reportWording('fx.title');
  out.cases.non_string   = I.reportWording({}, 'wrong');
  // keyed ATTRIBUTES, not only text: a wrong placeholder is reportable, and
  // the record says which surface the complaint is about.
  out.cases.attr_placeholder = I.reportWording('fx.ph', 'wrong', 'placeholder');
  out.cases.attr_aria        = I.reportWording('fx.aria', 'unclear', 'aria-label');
  // a key that only exists as a placeholder cannot be reported as text, and
  // vice versa
  out.cases.attr_key_as_text = I.reportWording('fx.ph', 'wrong', 'text');
  out.cases.text_key_as_ph   = I.reportWording('fx.title', 'wrong', 'placeholder');
  out.cases.bad_surface      = I.reportWording('fx.ph', 'wrong', 'nowhere');
  out.keyed_focusable        = document.querySelector('[data-i18n="fx.title"]').tabIndex;
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
    chip: (document.getElementById('i18nrpt') || {}).textContent || null,
    keyed_focusable: document.querySelector('[data-i18n="fx.title"]').tabIndex
  };
}"""

QUIET_READER = """() => ({
  mode: document.documentElement.getAttribute('data-i18n-report'),
  chip: !!document.getElementById('i18nrpt'),
  picker: !!document.getElementById('i18npick'),
  keyed_focusable: document.querySelector('[data-i18n="fx.title"]').tabIndex
})"""

# Report a KEYED ATTRIBUTE the way a reviewer would: click the field whose
# placeholder is wrong (not its visible text), pick a reason, read the record.
ATTR_TAP = """() => {
  const field = document.getElementById('field');
  field.click();
  const pick = document.getElementById('i18npick');
  if (!pick) return {picker: false};
  pick.querySelector('button[data-reason="wrong"]').click();
  return {picker: true, recorded: window.I18N.reports()};
}"""

# A page with many keyed targets spread across the width and down the page --
# the shape of a real form, and the shape that exposed the overflow. Every
# visible target is clicked and the picker measured, the way an independent
# 320x640 scan found 29 of 77 targets overflow the right edge.
MANY = ["f4.a%d" % i for i in range(40)]
_rows = []
for _i, _k in enumerate(MANY):
    _cls = '' if _i % 2 == 0 else ' class="right"'
    _rows.append('<div%s><span data-i18n="%s">%s</span></div>' % (_cls, _k, _k))
MANY_PAGE = """<!DOCTYPE html>
<html lang="en" data-i18n-default="ne">
<head><meta charset="utf-8"><title>many targets</title>
<style>body{margin:0}div{padding:14px 4px;border-bottom:1px solid #eee}
.right{margin-left:auto;width:max-content}span{display:inline-block}</style>
</head><body>
%s
<script src="assets/i18n-strings.js"></script>
<script src="assets/i18n.js"></script>
</body></html>
""" % "\n".join(_rows)

MANY_STRINGS = "window.I18N_STRINGS = {\n" \
    '  _meta: { langs: [{code:"en",label:"ENG",name:"English",html:"en"},' \
    '{code:"ne",label:"NEP",name:"\u0928\u0947\u092a\u093e\u0932\u0940",html:"ne"}],' \
    ' revision: "fixture-many", professionalOnly: [], source: {machine:[], human:[]} },\n' \
    "  en: {" + ",".join('"%s":"%s"' % (k, k) for k in MANY) + \
    ', "lang.select":"Select language","mt.dismiss":"Dismiss",' \
    '"mt.readEnglish":"Read in English","mt.notice.en":"auto",' \
    '"mt.authoritative.en":"auth","i18n.todoTitle":"todo"},\n' \
    "  ne: {" + ",".join('"%s":"\u0936\u0940\u0930\u094d\u0937\u0915"' % k for k in MANY) + "}\n};\n"

# Click every keyed target, measure the picker, then dismiss with Escape. A
# picker that overflows is a report a reviewer cannot make.
MANY_SCAN = """() => {
  const bad = [];
  const seen = [];
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    seen.push(el.getAttribute('data-i18n'));
    el.click();
    const p = document.getElementById('i18npick');
    if (!p) { bad.push({key: el.getAttribute('data-i18n'), why: 'no_picker'}); return; }
    const b = p.getBoundingClientRect();
    if (b.left < 0 || b.right > innerWidth || b.top < 0 || b.bottom > innerHeight) {
      bad.push({key: el.getAttribute('data-i18n'), left: b.left, right: b.right,
                top: b.top, bottom: b.bottom, w: innerWidth, h: innerHeight});
    }
    document.dispatchEvent(new KeyboardEvent('keydown',
      {key: 'Escape', bubbles: true, cancelable: true}));
  });
  return {targets: seen.length, overflowing: bad.length, bad: bad.slice(0, 5)};
}"""


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
        (root / "assets" / "i18n-strings-many.js").write_text(
            MANY_STRINGS, encoding="utf-8")
        # The many-target page loads the same engine but its own dictionary.
        (root / "many.html").write_text(
            MANY_PAGE.replace("assets/i18n-strings.js",
                              "assets/i18n-strings-many.js"),
            encoding="utf-8")

        handler = functools.partial(Quiet, directory=str(root))
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as server:
            port = server.server_address[1]
            threading.Thread(target=server.serve_forever, daemon=True).start()
            # A query string and fragment that must NOT reach the record.
            url = ("http://127.0.0.1:%d/page.html?lang=ne&secret=NAME#frag" % port)

            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                context = browser.new_context(accept_downloads=True)
                page = context.new_page()
                page.goto(url, wait_until="load")
                page.wait_for_timeout(400)
                res = page.evaluate(PROBE)

                # A quiet reader: no reviewer mode, nothing on screen.
                quiet = context.new_page()
                quiet.goto("http://127.0.0.1:%d/page.html" % port, wait_until="load")
                quiet.wait_for_timeout(400)
                quiet_state = quiet.evaluate(QUIET_READER)

                # The reviewer: ?i18n=report, tap, pick, read back.
                page.goto("http://127.0.0.1:%d/page.html?i18n=report" % port,
                          wait_until="load")
                page.wait_for_timeout(400)
                tap = page.evaluate(REVIEWER_TAP)

                # Closing the page must not discard unexported feedback. Open a
                # fresh page in the same browser profile, then exercise the real
                # download control rather than trusting an in-memory API read.
                page.close()
                reopened = context.new_page()
                reopened.goto("http://127.0.0.1:%d/page.html?i18n=report" % port,
                              wait_until="load")
                reopened.wait_for_timeout(400)
                reopened_reports = reopened.evaluate("() => window.I18N.reports()")
                with reopened.expect_download() as download_info:
                    reopened.click("#i18nrpt")
                downloaded = json.loads(
                    Path(download_info.value.path()).read_text(encoding="utf-8"))

                # A common small phone viewport: the picker must remain wholly
                # visible, move focus into its controls, and close on Escape.
                narrow = context.new_page()
                narrow.set_viewport_size({"width": 320, "height": 640})
                narrow.goto("http://127.0.0.1:%d/page.html?i18n=report" % port,
                            wait_until="load")
                narrow.wait_for_timeout(400)
                narrow.focus('[data-i18n="fx.title"]')
                narrow.press('[data-i18n="fx.title"]', "Enter")
                narrow_state = narrow.evaluate("""() => {
                  const p = document.getElementById('i18npick');
                  const r = p && p.getBoundingClientRect();
                  return {
                    picker: !!p,
                    left: r && r.left, right: r && r.right,
                    top: r && r.top, bottom: r && r.bottom,
                    width: innerWidth, height: innerHeight,
                    focused_reason: !!(document.activeElement &&
                      document.activeElement.matches('#i18npick button'))
                  };
                }""")
                narrow.keyboard.press("Escape")
                narrow_state["closed_on_escape"] = not narrow.locator("#i18npick").count()

                # A reviewer reporting a KEYED ATTRIBUTE: the field's
                # placeholder is wrong, so they click the field, not a
                # sentence. Start from an empty store so the count is exact.
                attr_page = context.new_page()
                attr_page.goto("http://127.0.0.1:%d/page.html?i18n=report" % port,
                               wait_until="load")
                attr_page.wait_for_timeout(400)
                attr_page.evaluate("() => window.I18N.clearReports()")
                attr_tap = attr_page.evaluate(ATTR_TAP)

                # A narrow-viewport scan over MANY targets: every picker must
                # fit on screen. This is the check an independent 320x640 scan
                # used to find 29 of 77 targets overflowing.
                scans = {}
                for w, h in ((320, 640), (360, 740), (390, 844)):
                    sctx = browser.new_context(viewport={"width": w, "height": h})
                    sp = sctx.new_page()
                    sp.goto("http://127.0.0.1:%d/many.html?i18n=report" % port,
                            wait_until="load")
                    sp.wait_for_timeout(400)
                    scans["%dx%d" % (w, h)] = sp.evaluate(MANY_SCAN)
                    sctx.close()
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
    print("attribute tap     :", json.dumps(attr_tap, ensure_ascii=False))
    print("surfaces          :", json.dumps(res["surfaces"]))
    print("narrow scan       :", json.dumps(scans))
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
    checks.append(("an_unexported_report_survives_page_close_and_reopen",
                   reopened_reports == recorded,
                   json.dumps(reopened_reports, ensure_ascii=False)))
    checks.append(("a_reopened_report_remains_exportable",
                   downloaded == recorded,
                   json.dumps(downloaded, ensure_ascii=False)))
    checks.append(("picker_fits_a_320_by_640_viewport",
                   narrow_state.get("picker")
                   and narrow_state.get("left", -1) >= 0
                   and narrow_state.get("right", 321) <= narrow_state.get("width", 320)
                   and narrow_state.get("top", -1) >= 0
                   and narrow_state.get("bottom", 641) <= narrow_state.get("height", 640),
                   json.dumps(narrow_state)))
    checks.append(("keyboard_activation_focuses_a_reason",
                   bool(narrow_state.get("focused_reason")),
                   json.dumps(narrow_state)))
    checks.append(("escape_dismisses_the_picker",
                   bool(narrow_state.get("closed_on_escape")),
                   json.dumps(narrow_state)))

    # ---- the supported surface, stated exactly ----------------------------
    checks.append(("the_supported_surface_is_declared_by_the_engine",
                   res["surfaces"] == ["text", "placeholder", "aria-label",
                                       "alt", "title"],
                   json.dumps(res["surfaces"])))
    checks.append(("a_keyed_placeholder_is_reportable",
                   (cases["attr_placeholder"] or {}).get("key") == "fx.ph"
                   and (cases["attr_placeholder"] or {}).get("surface") == "placeholder",
                   str(cases["attr_placeholder"])))
    checks.append(("a_keyed_aria_label_is_reportable",
                   (cases["attr_aria"] or {}).get("key") == "fx.aria"
                   and (cases["attr_aria"] or {}).get("surface") == "aria-label",
                   str(cases["attr_aria"])))
    checks.append(("a_key_is_only_reportable_on_the_surface_it_renders",
                   cases["attr_key_as_text"] is None
                   and cases["text_key_as_ph"] is None,
                   json.dumps({k: cases[k] for k in
                               ("attr_key_as_text", "text_key_as_ph")},
                              ensure_ascii=False)))
    checks.append(("an_unknown_surface_is_refused",
                   cases["bad_surface"] is None, str(cases["bad_surface"])))
    checks.append(("clicking_a_keyed_attribute_records_that_surface",
                   len(attr_tap.get("recorded") or []) == 1
                   and (attr_tap["recorded"][0].get("key") == "fx.ph")
                   and (attr_tap["recorded"][0].get("surface") == "placeholder"),
                   json.dumps(attr_tap, ensure_ascii=False)))
    checks.append(("report_mode_makes_keyed_text_keyboard_reachable",
                   isinstance(tap.get("keyed_focusable"), int)
                   and tap["keyed_focusable"] >= 0,
                   str(tap.get("keyed_focusable"))))
    checks.append(("a_plain_reader_gets_no_keyboard_tab_stops",
                   quiet_state.get("keyed_focusable") in (-1, None),
                   str(quiet_state.get("keyed_focusable"))))

    # ---- no picker may leave the viewport on a phone ----------------------
    for label, scan in scans.items():
        checks.append(("every_picker_fits_%s" % label,
                       scan["targets"] > 30 and scan["overflowing"] == 0,
                       json.dumps(scan)))

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
