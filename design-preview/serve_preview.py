#!/usr/bin/env python3
"""Serve the review preview to a human over the tailnet and verify the links.

Bind the host's Tailscale address (never 0.0.0.0 — the project rule), serve the
REPOSITORY PARENT so the preview's own relative asset paths (`../hub/assets/...`)
resolve exactly as they do in the app, then fetch every URL that will be handed
over and assert the status code, byte count and that the served copy carries the
change (not a stale cache). Writes serve-report.json.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
PORT = int(os.environ.get("L2_PREVIEW_PORT", "8823"))


def tailscale_ip() -> str:
    out = subprocess.check_output(["tailscale", "ip", "-4"], text=True).strip().splitlines()
    return out[0].strip()


def dns_name() -> str:
    try:
        st = json.loads(subprocess.check_output(["tailscale", "status", "--json"], text=True))
        self_name = st.get("Self", {}).get("DNSName", "").rstrip(".")
        return self_name
    except Exception:
        return ""


def fetch(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            body = r.read()
            return {"url": url, "status": r.status, "bytes": len(body),
                    "head": body[:120].decode("utf-8", "replace")}
    except urllib.error.HTTPError as e:
        return {"url": url, "status": e.code, "bytes": 0, "head": ""}
    except Exception as e:  # pragma: no cover
        return {"url": url, "status": None, "bytes": 0, "head": str(e)}


def port_open(ip: str, port: int) -> bool:
    s = socket.socket()
    s.settimeout(1)
    try:
        return s.connect_ex((ip, port)) == 0
    finally:
        s.close()


def main() -> int:
    ip = tailscale_ip()
    dns = dns_name()
    log = Path("/tmp/l2preview-server.log")
    reused = port_open(ip, PORT)
    proc: subprocess.Popen | None = None
    if reused:
        pass                                   # a server is already up on this port
    else:
        proc = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(PORT), "--bind", ip],
            cwd=str(REPO), stdout=log.open("w"), stderr=subprocess.STDOUT,
        )
    # readiness: poll a real URL, never a blind sleep
    base = f"http://{ip}:{PORT}"
    ready = False
    for _ in range(40):
        r = fetch(base + "/design-preview/index.html")
        if r["status"] == 200 and r["bytes"] > 500:
            ready = True
            break
        time.sleep(0.25)
    if not ready:
        print(json.dumps({"ok": False, "error": "server did not become ready",
                          "log": log.read_text()[-800:] if log.exists() else ""}, indent=2))
        return 1

    targets = [
        "index.html",
        "concept-conservative.html",
        "concept-recommended.html",
        "concept-divergent.html",
        "preview.css",
        "preview.js",
        "REDUNDANCY-INVENTORY.md",
        "PRESERVATION-INVENTORY.md",
        "QA-REPORT.md",
        "screens/concept-recommended-375.png",
    ]
    checks = [fetch(f"{base}/design-preview/{t}") for t in targets]
    # confirm the served stylesheet really carries a rule we wrote
    sheet = fetch(f"{base}/design-preview/preview.css")
    with urllib.request.urlopen(f"{base}/design-preview/preview.css", timeout=8) as r:
        css = r.read().decode()
    carries = "--tap:44px" in css and "filter-panel:not([hidden])" in css
    # and that the served markup references the hashed asset (not a stale name)
    with urllib.request.urlopen(f"{base}/design-preview/concept-recommended.html", timeout=8) as r:
        page = r.read().decode()
    hashed = "preview.css?h=" in page and "preview.js?h=" in page

    report = {
        "ok": all(c["status"] == 200 and c["bytes"] > 0 for c in checks) and carries and hashed,
        "pid": proc.pid if proc else "reused existing listener",
        "reused_existing_listener": reused,
        "bind": ip,
        "port": PORT,
        "plain_http_base": base + "/design-preview/",
        "tailnet_dns": dns,
        "checks": checks,
        "served_css_carries_new_rules": carries,
        "served_markup_uses_hashed_assets": hashed,
        "still_running": (proc.poll() is None) if proc else port_open(ip, PORT),
    }
    (HERE / "serve-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "checks"}, indent=2))
    print("checks:", json.dumps(checks, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
