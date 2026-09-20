#!/usr/bin/env python3
"""Adversarial rendered probe for the Hub trial-scope check.

Serves a throwaway copy of this worktree with one unapproved form link
(`../form/contact.html`) planted into the rendered DOM of `forms.html`, then
runs `tools/hub-trial-scope-render-check.py` against it.

Exit 0 means the checker REJECTED the planted link (probe passed).
Exit 1 means the checker ACCEPTED it (probe failed -- the checker is blind).

An optional second argument points at an alternative checker file, so the same
probe can be run against a candidate or a historical copy:

  python3 tools/render-check-adversarial-probe.py
  python3 tools/render-check-adversarial-probe.py /tmp/old-render-check.py
"""
import functools
import http.server
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "tools" / "hub-trial-scope-render-check.py"
PLANTED_HREF = "../form/contact.html"
PLANTED = '<a href="%s">planted unapproved link</a>' % PLANTED_HREF


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):  # keep the probe output readable
        pass


def main():
    with tempfile.TemporaryDirectory(prefix="hub-render-probe-") as temp:
        document_root = Path(temp)
        shutil.copytree(ROOT, document_root / "hub", ignore=shutil.ignore_patterns(".git"))
        forms = document_root / "hub" / "forms.html"
        forms.write_text(
            forms.read_text(encoding="utf-8").replace(
                "</body>", PLANTED + "</body>"
            ),
            encoding="utf-8",
        )
        handler = functools.partial(Quiet, directory=temp)
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as server:
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                result = subprocess.run(
                    [sys.executable, str(CHECKER), "http://127.0.0.1:%d" % port],
                    cwd=ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
            finally:
                server.shutdown()
                thread.join()
    print(result.stdout, end="")
    if result.returncode == 0:
        print("ACCEPTED planted rendered link %s -- checker is blind" % PLANTED_HREF)
        return 1
    print("REJECTED planted rendered link %s -- checker exit=%d"
          % (PLANTED_HREF, result.returncode))
    return 0


if __name__ == "__main__":
    sys.exit(main())
