#!/usr/bin/env python3
"""Measure the C1 fix in a REAL browser (rule 9: a passing suite is not evidence).

Two proofs:
  1. With a STUB fb.js, load hub/index.html and hub/forms.html from the local
     worktree and assert the page asks the register for a KIND-SCOPED read
     (watchKind), not an unfiltered one (watch) -- measured from the page's own
     calls, not from the source text.
  2. Zero page errors on load.

This never reaches the network or a real register: fb.js is replaced by a stub
that records the calls the page makes.
"""
import http.server
import socketserver
import threading
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

HUB = Path("/root/mhpss-nepal-work/exchange-t_9cec2b39")

STUB_FB = """
window.__CALLS = [];
window.FB = {
  status: function(){ return {configured:true, ready:true, user:{email:'probe@example.invalid'}}; },
  onStatus: function(cb){ setTimeout(function(){cb(window.FB.status());},0); return function(){}; },
  watch: function(cb, err){ window.__CALLS.push({fn:'watch'}); },
  watchKind: function(kind, cb, err){ window.__CALLS.push({fn:'watchKind', kind:kind}); },
  signIn: function(){ return Promise.resolve(); },
  signOut: function(){},
};
"""


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(HUB), **k)

    def log_message(self, *a):
        pass

    def do_GET(self):
        # serve a stub fb.js so the page records calls instead of hitting Firebase
        if self.path.endswith("/assets/fb.js") or self.path == "/assets/fb.js":
            body = STUB_FB.encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()


def main():
    httpd = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    base = f"http://127.0.0.1:{port}"
    ok = True
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, after in (("index.html", "useLive"), ("forms.html", None)):
            ctx = b.new_context()
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(f"{base}/{name}", wait_until="load")
            if after:
                try:
                    pg.click(f"#{after}", timeout=2000)
                except Exception:
                    pass
            pg.wait_for_timeout(800)
            calls = pg.evaluate("window.__CALLS || []")
            kinds = [c.get("kind") for c in calls if c["fn"] == "watchKind"]
            unfiltered = [c for c in calls if c["fn"] == "watch"]
            print(f"[{name}] calls={calls}")
            print(f"[{name}] page errors={len(errs)} :: {errs[:3]}")
            if unfiltered:
                print(f"[{name}] FAIL: page made {len(unfiltered)} UNFILTERED watch() call(s)")
                ok = False
            if name == "index.html" and "activity" not in kinds:
                print(f"[{name}] FAIL: no watchKind('activity') observed")
                ok = False
            if name == "forms.html":
                want = {"service_contact", "referral", "phq9", "self_report"}
                if not want.issubset(set(kinds)):
                    print(f"[{name}] FAIL: kind-scoped reads incomplete, got {kinds}")
                    ok = False
            if errs:
                print(f"[{name}] FAIL: page errors present")
                ok = False
            pg.screenshot(path=f"/tmp/c1-{name}.png", full_page=False)
            ctx.close()
        b.close()
    httpd.shutdown()
    print("BROWSER CHECK:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
