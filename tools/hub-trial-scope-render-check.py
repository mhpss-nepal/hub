#!/usr/bin/env python3
"""Rendered-browser trial-scope check, Hub side.

A source grep cannot see chrome that a shared asset injects at runtime, or a
link a script rewrites. This walks the real DOM of every Hub page at two
widths and asserts the trial scope holds where a reader actually is.

  python3 tools/hub-trial-scope-render-check.py http://127.0.0.1:8791

Serves the workspace root so the Hub's ../form/ and ../ links resolve, the
same way the sibling form repository's render check does.
"""
import sys
import posixpath
from urllib.parse import unquote, urljoin, urlparse

from playwright.sync_api import sync_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8791").rstrip("/")
PAGES = ["/hub/", "/hub/forms.html", "/hub/access.html", "/hub/inbox.html", "/hub/coverage.html"]
UNAPPROVED = ("contact", "phq9", "referral", "selfreport")
VIEWPORTS = [(390, 844, "mobile"), (1280, 900, "desktop")]

# The two addresses a Hub page may resolve to under /form/. Anything else that
# lands under /form/ fails. Compared after resolution and normalization, so a
# substring match cannot wave an unapproved instrument through.
# /form/all-forms.html is the review page: it opens every instrument through
# the review frame and carries no direct link to an unapproved one, so it is
# not a field entry point and the trial needs it reachable.
APPROVED_FORM_PATHS = ("/form", "/form/5ws-report.html", "/form/all-forms.html")
# The sibling form app's directory segment, normalized and case-folded.
FORMS_ROOT = "/form"


def resolved_path(href, page_url):
    """Absolute, normalized, case-folded path for a rendered href.

    Resolves relative, root-relative, protocol-relative and absolute URLs, then
    collapses dot segments, duplicate slashes and backslashes, percent-decodes,
    and strips the trailing-slash difference between /form and /form/.
    """
    raw = urljoin(page_url, href.strip())
    path = unquote(urlparse(raw).path).replace("\\", "/")
    path = posixpath.normpath(path) if path else "/"
    return path.lower()


def is_under_forms_root(path):
    return path == FORMS_ROOT or path.startswith(FORMS_ROOT + "/")


def is_unapproved_form_href(href, page_url):
    """True when a rendered href resolves to a form page outside the trial."""
    path = resolved_path(href, page_url)
    return is_under_forms_root(path) and path not in APPROVED_FORM_PATHS


def main():
    failures, lines = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width, height, label in VIEWPORTS:
            ctx = browser.new_context(viewport={"width": width, "height": height})
            page = ctx.new_page()
            for path in PAGES:
                page_url = BASE + path
                page.goto(page_url, wait_until="load")
                page.wait_for_timeout(300)
                hrefs = page.eval_on_selector_all(
                    "a[href]", "els => els.map(e => e.getAttribute('href'))"
                )
                form_targets, offenders, text_hits = [], [], []
                for href in hrefs:
                    if href is None:
                        continue
                    target_path = resolved_path(href, page_url)
                    if is_under_forms_root(target_path):
                        form_targets.append(href)
                        if is_unapproved_form_href(href, page_url):
                            offenders.append(href)
                body = page.inner_text("body")
                for name in UNAPPROVED:
                    if ("%s.html" % name) in body:
                        text_hits.append(name)
                lines.append(
                    "%-6s %-20s links=%2d form_links=%s offenders=%s text_mentions=%s"
                    % (label, path, len(hrefs), sorted(set(form_targets)),
                       offenders or "[]", text_hits or "[]")
                )
                if offenders:
                    failures.append("%s %s: link outside trial scope %s"
                                    % (label, path, offenders))
                # The rail group must expose exactly the three approved links.
                rail = page.eval_on_selector_all(
                    '[data-g="forms"] a[href]',
                    "els => els.map(e => e.getAttribute('href'))",
                )
                if rail != ["./#reports", "forms.html", "../form/"]:
                    failures.append("%s %s: Field forms rail group is %s"
                                    % (label, path, rail))
            ctx.close()
        browser.close()

    print("MHPSS Nepal hub -- trial scope, rendered DOM")
    for line in lines:
        print("  " + line)
    if failures:
        print("\n  OUT OF TRIAL SCOPE:")
        for f in failures:
            print("    " + f)
        return 1
    print("\n  True: no Hub page renders a link outside the trial scope, at either width.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
