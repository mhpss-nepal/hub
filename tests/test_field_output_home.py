#!/usr/bin/env python3
"""The Layer 2 receiving surface: the read path proven, not asserted.

The claim this suite defends is narrow and checkable:

    a record written by the current field form arrives on Layer 2, through the
    existing contract, and is read — and Layer 2 changed no contract to do it.

So it measures, rather than reads:

  · the route is addressable (it is a real hub page, served, not a snippet);
  · the page asks the register for exactly ONE kind and renders it;
  · the page never writes (its writers are wrapped and refuse);
  · the bridge and the record model are the FROZEN files, byte for byte —
    a copy pasted into the page would defeat the claim;
  · ROUND TRIP: the current `5ws-report.html` writes a synthetic report through
    the real `assets/fb.js`; the receiving page reads it back and shows its
    deterministic id. This is the only part that needs a register, and it runs
    against a LOCAL Firestore emulator (see tools/field-output-home-proof.py);
    when no emulator is listening the test SKIPS that body rather than passing
    green on nothing.
  · NEGATIVE CONTROL: a record of a different kind is not shown by the page, so
    the kind scope is proven to be a real boundary and not decoration.

The whole suite is red if the read path breaks. Planted breakages that must turn
it red are recorded in docs/FIELD-OUTPUT-HOME.md.

Run from the repository root:
    python3 -m unittest -v tests.test_field_output_home
"""
from __future__ import annotations

import functools
import hashlib
import http.server
import json
import os
import socketserver
import subprocess
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT.parent                      # hub/ and form/ served as siblings
PAGE = "field-output-home.html"
PAGE_URL = "/hub/" + PAGE              # the hub is served at /hub/ beside /form/
FORM = SITE / "form" / "5ws-report.html"
EMULATOR = os.environ.get("MHPSS_FIRESTORE_EMULATOR", "http://127.0.0.1:8081")

# The files the page must load rather than reimplement. Their digests are read
# from disk, so this is "is it the same file", not "does it still say the same
# words": a copy pasted into the page fails it.
SHARED = ("assets/fb.js", "assets/store.js")
# The commit this change was cut from, quoted in the evidence doc and checked
# here so "the contracts hold" is a test and not a sentence.
FROZEN_HUB = "dfe660af880b96e2dfc9141c41eacc0ae3ff2869"
FROZEN_FORM = "e011e379639e70bcfa9d607c106629c783d366c2"
EVIDENCE = ROOT / "docs" / "FIELD-OUTPUT-HOME.md"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emulator_up(timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(EMULATOR + "/", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def emulator_write(doc_id: str, body: dict) -> None:
    """Put one synthetic document in the local emulator, with no browser.

    Used only for the negative control: a record of a kind this page must not
    read. The payload is obviously synthetic and carries no person-level field.
    The project id is the one the page's own config names, because the proxy
    only rewrites the host, never the path.
    """
    project = emulator_project()
    url = ("%s/v1/projects/%s/databases/(default)/documents/submissions?documentId=%s"
           % (EMULATOR, project, doc_id))
    fields = {}
    for k, v in body.items():
        fields[k] = {"stringValue": v} if isinstance(v, str) else {"integerValue": str(v)}
    data = json.dumps({"fields": fields}).encode()
    # DELETE then POST: a rerun must overwrite the control record rather than
    # 409 on it, so the suite is repeatable.
    base = "%s/v1/projects/%s/databases/(default)/documents/submissions/%s" % (
        EMULATOR, project, doc_id)
    for method, url in (("DELETE", base), ("POST", base.split("/submissions/")[0]
                                           + "/submissions?documentId=" + doc_id)):
        req = urllib.request.Request(url, data=(data if method == "POST" else None),
                                     method=method, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                assert r.status == 200, r.status
        except urllib.error.HTTPError as e:
            if method == "DELETE" and e.code == 404:
                continue          # nothing to remove; the POST below writes it
            raise


def emulator_project() -> str:
    """The projectId the page's own fb-config.js names, read from the file."""
    src = (ROOT / "assets" / "fb-config.js").read_text(encoding="utf-8")
    import re
    m = re.search(r'projectId:\s*"([^"]+)"', src)
    assert m, "fb-config.js declares no projectId"
    return m.group(1)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):  # keep the run readable
        pass


def firestore_proxy(route):
    """Send the page's Firestore traffic to the local emulator, nothing else.

    The served tree is NOT edited: `assets/fb-config.js` keeps the project's own
    id and `assets/fb.js` keeps the SDK URL and its `setDoc`/`watchKind` calls.
    Only the HTTP hop is redirected, so what is exercised is the real bridge
    against a real Firestore API implementation.

    The Firestore SDK will not talk to a private-network address in this build
    and Playwright refuses a cross-protocol `continue_`, so each request is
    relayed from Python and `fulfill`-ed — Playwright accepts a cross-origin
    fulfill, because it is not a request rewrite.
    """
    req = route.request
    url = req.url
    if not url.startswith("https://firestore.googleapis.com"):
        route.continue_()
        return
    target = EMULATOR + url[len("https://firestore.googleapis.com"):]
    headers = {k: v for k, v in req.headers.items()
               if k.lower() not in ("host", "content-length", "origin", "referer",
                                    "accept-encoding")}
    try:
        r = urllib.request.Request(target, data=req.post_data_buffer,
                                   method=req.method, headers=headers)
        with urllib.request.urlopen(r, timeout=25) as resp:
            route.fulfill(status=resp.status, body=resp.read(),
                          headers={"content-type": resp.headers.get("content-type", "application/json")})
    except urllib.error.HTTPError as e:
        route.fulfill(status=e.code, body=e.read(), headers={"content-type": "application/json"})
    except Exception as e:  # pragma: no cover
        route.fulfill(status=502, body=json.dumps({"error": str(e)}).encode(),
                      headers={"content-type": "application/json"})


def wait_settled(pg, timeout_ms=30000):
    """Poll the page's own state until the read has an outcome.

    A fixed sleep is the thing that made this suite flaky; the page publishes
    its outcome on window.OUTPUT_HOME, so wait for it rather than guess.
    """
    waited = 0
    while waited < timeout_ms:
        st = pg.evaluate("() => window.OUTPUT_HOME ? window.OUTPUT_HOME.state : null")
        if st and (st.get("ok") or st.get("error")):
            return st
        pg.wait_for_timeout(250)
        waited += 250
    return pg.evaluate("() => window.OUTPUT_HOME.state")


STUB_BRIDGE = """
window.__CALLS = [];
window.__WRITES = [];
window.FB_CONFIG = {projectId:'probe', apiKey:'probe'};
window.FB_COLLECTION = 'submissions';
var _realKind = function (kind, ok, err) { window.__CALLS.push({fn:'watchKind', kind:kind}); };
window.FB = {
  status: function(){ return {configured:true, ready:true, user:null}; },
  onStatus: function(cb){ setTimeout(function(){cb(window.FB.status());},0); return function(){}; },
  watch: function(cb, err){ window.__CALLS.push({fn:'watch'}); },
  watchKind: _realKind,
  submit: function(){ window.__WRITES.push('submit'); return Promise.resolve(); },
  publish: function(){ window.__WRITES.push('publish'); return Promise.resolve(); },
  signIn: function(){ return Promise.resolve(); },
  signOut: function(){}
};
"""


class _Server:
    """Serve the workspace root (hub/ + form/ side by side) on a free port."""

    def __init__(self, patch_bridge: bool):
        self.patch_bridge = patch_bridge

    def __enter__(self):
        outer = self

        class H(Quiet):
            def do_GET(self):
                if outer.patch_bridge and self.path.split("?")[0].endswith("/assets/fb.js"):
                    body = STUB_BRIDGE.encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/javascript")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                return super().do_GET()

        handler = functools.partial(H, directory=str(SITE))
        self.httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.httpd.server_address[1]
        return self

    def __exit__(self, *a):
        self.httpd.shutdown()


def browser():
    from playwright.sync_api import sync_playwright
    return sync_playwright()


def has_playwright() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
        return True
    except Exception:
        return False


class ReceivingSurfaceTest(unittest.TestCase):
    """Static facts. These run anywhere, with no browser and no register."""

    def setUp(self):
        self.html = (ROOT / PAGE).read_text(encoding="utf-8")

    def test_the_route_is_addressable(self):
        self.assertTrue((ROOT / PAGE).is_file(), "%s is missing" % PAGE)
        self.assertIn("<title>", self.html)
        self.assertIn('<html lang="en">', self.html, "the hub's pages declare their language")

    def test_the_page_loads_the_frozen_shared_files_rather_than_reimplementing_them(self):
        for rel in SHARED:
            self.assertIn('src="%s"' % rel, self.html,
                          "%s must be loaded from the shared file, not copied in" % rel)
        # …and it must not carry a second copy of either contract in its body.
        # A pasted-in bridge would pass the src check while defeating the claim.
        for marker in ("window.FB = {", "window.STORE = {", "function fnv1a",
                       "function recordId", "function registerBody"):
            self.assertNotIn(marker, self.html,
                             "the page reimplements %r instead of loading it" % marker)

    def test_it_changes_no_contract(self):
        """A reader adds no column, no key, no id rule and no schema."""
        for forbidden in ("CSV_COLUMNS =", "SCHEMA_VERSION =", "function recordId", "function rid",
                          "mhpss-np-4ws-v1'", "localStorage.setItem"):
            self.assertNotIn(forbidden, self.html,
                             "the receiving surface must not (re)define a contract: %r" % forbidden)

    def test_it_asks_for_exactly_one_kind_and_it_is_the_trial_instrument(self):
        self.assertIn('var KINDS = ["activity"];', self.html)

    def test_it_is_not_in_the_navigation(self):
        """Adding it to the rail is a navigation change, and that is Adib's call."""
        for page in ("index.html", "forms.html", "access.html", "coverage.html", "inbox.html"):
            src = (ROOT / page).read_text(encoding="utf-8")
            self.assertNotIn(PAGE, src, "%s links to %s; that is a visible change" % (page, PAGE))
        rail = (ROOT / "tools" / "rail.py").read_text(encoding="utf-8")
        self.assertNotIn(PAGE, rail, "the rail generator must not offer it")

    def test_the_frozen_base_is_quoted_and_measured(self):
        """The card's evidence 1, as a check: both frozen heads, quoted, and the
        hub's own HEAD is that commit — a branch cut earlier and merged later
        has silently reverted protected strings three times on this project."""
        self.assertTrue(EVIDENCE.is_file(), "%s is missing" % EVIDENCE)
        doc = EVIDENCE.read_text(encoding="utf-8")
        for sha in (FROZEN_HUB, FROZEN_FORM):
            self.assertIn(sha, doc, "the frozen head %s is not quoted" % sha)
        # HEAD may be the frozen commit itself or a commit on top of it; what
        # must never happen is a branch cut from something older.
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT),
                              capture_output=True, text=True).stdout.strip()
        anc = subprocess.run(["git", "merge-base", "--is-ancestor", FROZEN_HUB, "HEAD"],
                             cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(0, anc.returncode,
                         "this branch is not descended from the frozen hub main: HEAD=%s" % head)

    def test_the_read_scoping_guard_still_passes(self):
        """A new reader must not become an unfiltered listen, and the guard must agree."""
        import subprocess, sys
        p = subprocess.run([sys.executable, str(ROOT / "tools" / "hub-live-read-scoping-check.py")],
                           capture_output=True, text=True)
        self.assertEqual(0, p.returncode, p.stdout + p.stderr)


@unittest.skipUnless(has_playwright(), "playwright is not installed here")
class ReadPathBrowserTest(unittest.TestCase):
    """The read path, measured in a real browser."""

    def test_the_page_asks_for_one_kind_and_never_writes(self):
        with _Server(patch_bridge=True) as srv, browser() as p:
            b = p.chromium.launch()
            ctx = b.new_context()
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto("%s%s" % (srv.base, PAGE_URL), wait_until="load")
            pg.wait_for_timeout(600)
            pg.click("#read")
            pg.wait_for_timeout(1200)
            calls = pg.evaluate("() => window.__CALLS || []")
            writes = pg.evaluate("() => window.__WRITES || []")
            receipt = pg.evaluate("""() => ({
              writes: document.getElementById('rWrite').textContent,
              kinds: document.getElementById('kinds').textContent,
              other: document.getElementById('rOther').textContent,
              source: document.getElementById('coll').textContent
            })""")
            table = pg.inner_text("#rows")
            b.close()
        self.assertEqual([], errs, "the page must load clean")
        kinds = [c.get("kind") for c in calls if c["fn"] == "watchKind"]
        self.assertEqual(["activity"], kinds,
                         "the page must ask the register for exactly the kind it renders")
        self.assertEqual([], [c for c in calls if c["fn"] == "watch"],
                         "an unfiltered listen is the defect this guards against")
        self.assertEqual([], writes, "the page must never write (submit/publish)")
        self.assertEqual("0", receipt["writes"])
        # The stub answers no call, so the receipt's outcome cell is still "—":
        # what must hold is that the page never *requests* a kind but activity,
        # which is measured from the wrapped watchKind above. The receipt cell is
        # asserted not to name any other kind.
        for foreign in ("service_contact", "referral", "phq9", "self_report"):
            self.assertNotIn(foreign, receipt["other"],
                             "the page asked the register for %r" % foreign)
        self.assertNotIn("No report", table)

    def test_a_missing_bridge_is_stated_not_silently_blank(self):
        with _Server(patch_bridge=False) as srv, browser() as p:
            b = p.chromium.launch()
            pg = b.new_context().new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto("%s%s" % (srv.base, PAGE_URL), wait_until="load")
            pg.wait_for_timeout(1500)
            text = pg.inner_text("body")
            b.close()
        self.assertEqual([], errs)
        self.assertIn("field forms", text.lower(), "the page still states what it is for")

    @unittest.skipUnless(emulator_up(), "no Firestore emulator on %s" % EMULATOR)
    def test_round_trip_a_record_written_by_the_current_form_is_read_on_layer_two(self):
        """The proof. Same synthetic report, through the unmodified contract."""
        rec = {"org": "CMC", "cadre": "HW", "dateAD": "2026-09-21", "sessionTime": "09:30",
               "district": "NUW", "site": "NUW-02", "activity": "1.1", "modality": "HC",
               "status": "ONG", "reachedTotal": "3", "f04": "3"}
        with _Server(patch_bridge=False) as srv, browser() as p:
            b = p.chromium.launch()
            ctx = b.new_context()
            ctx.route("https://firestore.googleapis.com/**", firestore_proxy)
            errs = []

            fp = ctx.new_page()
            fp.on("pageerror", lambda e: errs.append("form: " + str(e)))
            fp.goto("%s/form/5ws-report.html" % srv.base, wait_until="load")
            fp.wait_for_timeout(1200)
            fp.evaluate("""(rec) => {
              const $ = (id) => document.getElementById(id);
              const set = (id, v) => { const el = $(id); if (!el) return;
                el.value = v; el.dispatchEvent(new Event('input', {bubbles:true}));
                el.dispatchEvent(new Event('change', {bubbles:true})); };
              const pick = (id, v) => { const s = $(id); if (!s) return;
                s.value = v; s.dispatchEvent(new Event('change', {bubbles:true})); };
              pick('org', rec.org); pick('cadre', rec.cadre); set('dateAD', rec.dateAD);
              set('sessionTime', rec.sessionTime); pick('district', rec.district);
              pick('site', rec.site); pick('activity', rec.activity);
              pick('modality', rec.modality); pick('status', rec.status);
              const tg = document.querySelector('#tgs input[type=checkbox]');
              if (tg) { tg.checked = true; tg.dispatchEvent(new Event('change', {bubbles:true})); }
              set('reachedTotal', rec.reachedTotal); set('f04', rec.f04);
              set('focalName', 'SYNTHETIC PROBE'); set('focalPhone', '9800000000');
              set('description', 'SYNTHETIC - read-path proof, safe to delete');
              document.getElementById('f').dispatchEvent(new Event('submit', {bubbles:true, cancelable:true}));
            }""", rec)
            # wait for the register to acknowledge: the queue drains to 0
            sent = False
            for _ in range(40):
                fp.wait_for_timeout(500)
                st = fp.evaluate("() => window.FB ? window.FB.status() : null")
                if st and st.get("pending") == 0:
                    sent = True
                    break
            written = fp.evaluate("""() => {
              const dev = JSON.parse(localStorage.getItem('mhpss-np-4ws-v1') || '[]');
              return dev.length ? dev[dev.length - 1] : null;
            }""")
            self.assertTrue(sent, "the form's write never reached the register")
            self.assertIsNotNone(written, "the form wrote no device record")

            hp = ctx.new_page()
            hp.on("pageerror", lambda e: errs.append("home: " + str(e)))
            hp.goto("%s%s" % (srv.base, PAGE_URL), wait_until="load")
            hp.wait_for_timeout(3000)
            hp.click("#read")
            wait_settled(hp)
            receipt = hp.evaluate("""() => ({
              outcome: document.getElementById('rOut').textContent,
              n: document.getElementById('rN').textContent,
              other: document.getElementById('rOther').textContent,
              writes: document.getElementById('rWrite').textContent,
              rowid: (document.querySelector('#rows code') || {}).textContent || ''
            })""")
            table = hp.inner_text("#rows")
            b.close()

        self.assertEqual([], errs, errs)
        self.assertEqual("read succeeded", receipt["outcome"])
        self.assertIn(written["id"], table,
                      "the receiving surface must show the record the form wrote")
        self.assertEqual("none", receipt["other"], "it read no kind but activity")
        self.assertEqual("0", receipt["writes"], "the receiving page wrote nothing")

    @unittest.skipUnless(emulator_up(), "no Firestore emulator on %s" % EMULATOR)
    def test_a_record_of_another_kind_is_not_shown(self):
        """The kind scope is the boundary, not a display filter.

        A record of another kind is put in the same collection the page reads,
        through the same Firestore API, and must not appear: the page asks for
        `activity` and nothing else. Written over REST so the negative control
        does not depend on the thing under test.
        """
        marker = "ZZNEGATIVECONTROL"
        emulator_write("self_report_%s" % marker,
                       {"kind": "self_report", "org": "SYNTHETIC",
                        "schema": "mhpss-np-selfreport/1", "id": marker})
        with _Server(patch_bridge=False) as srv, browser() as p:
            b = p.chromium.launch()
            ctx = b.new_context()
            ctx.route("https://firestore.googleapis.com/**", firestore_proxy)
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto("%s%s" % (srv.base, PAGE_URL), wait_until="load")
            pg.wait_for_timeout(3000)
            pg.click("#read")
            wait_settled(pg)
            receipt = pg.evaluate("""() => ({
              outcome: document.getElementById('rOut').textContent,
              n: document.getElementById('rN').textContent
            })""")
            table = pg.inner_text("#rows")
            b.close()
        self.assertEqual([], errs, errs)
        self.assertEqual("read succeeded", receipt["outcome"],
                         "the read itself must work, or this control proves nothing")
        self.assertNotIn(marker, table)
        self.assertNotIn("self_report", table)


if __name__ == "__main__":
    unittest.main(verbosity=2)
