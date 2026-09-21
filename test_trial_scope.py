#!/usr/bin/env python3
"""Trial scope, Hub side.

The supervised trial exposes exactly one instrument: the 5Ws activity report
(`../form/5ws-report.html`, whose home is the dashboard's "Reports received").
The Hub may describe or import the four unapproved forms (`contact`,
`phq9`, `referral`, `selfreport`), but no default Hub navigation or link may
resolve to one of their pages while the trial runs.

Run from the repository root:  python3 -m unittest -v test_trial_scope.py
"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
import hashlib
import importlib.util
import posixpath
import re
import unittest

ROOT = Path(__file__).resolve().parent
UNAPPROVED = ("contact", "phq9", "referral", "selfreport")
# The layer-1 forms are a sibling repository, served at /form/ beside /hub/.
FORMS_DIR_PREFIX = "/form/"
# The two form addresses a Hub page may resolve to, as normalized absolute site
# paths. Compared after resolution, never as raw substrings: `/form/` alone
# would wave `/form/phq9.html` through (the round-1 defect).
# The addresses a hub page may open.
#
#   /form/               the form landing page
#   /form/5ws-report.html  the one instrument approved for field use
#   /form/all-forms.html   the REVIEW page Adib asked for: it lists every
#                          instrument and opens each through the review frame
#
# all-forms.html is on this list because it is not a field entry point. It
# carries no direct link to an unapproved instrument -- it routes every open
# through preview.html?preview_form=<file>, which is the review surface the
# repository already keeps out of the field app. Forbidding it here would
# forbid the very review listing the trial needs.
APPROVED_FORM_TARGETS = ("/form", "/form/5ws-report.html", "/form/all-forms.html")
# Hub pages are served under /hub/, so a link resolves against that base.
SITE_DIR = "/hub"
# The pre-fix rendered checker, kept verbatim so the round-1 red/green demo is
# reproducible. Pinned by SHA-256 below: editing this fixture to make the demo
# pass would itself fail the suite. This is the file at commit 15d35b3, the
# version review round 1 probed at head 435a2c3.
PRE_FIX_CHECKER = "tools/fixtures/render-check-prefix-15d35b3.py"
PRE_FIX_CHECKER_SHA256 = "ebdcd25b5a54ad89afb0311fa2c2e53b55f593d15e53eaecc1684dea86f6f7dd"
# Page keys of the hub pages that carry a generated rail.
RAIL_PAGES = ("index.html", "forms.html", "access.html")
# The one allowed "Field forms" rail group (the row that could regress).
APPROVED_FORMS_GROUP = ["./#reports", "forms.html", "../form/"]
# Sections of the Hub's own review surface that name an unapproved instrument.
# forms.html itself is a neutral "form entries" link; a rail item that lands on
# one of these four hashes is a named path back to an unapproved form.
UNAPPROVED_SECTION_HASHES = tuple("#%s" % name for name in UNAPPROVED)
# assets/qr.js is a printable payload: the address is inside the bit matrix,
# so a QR printed from this file is a physical path to whatever it encodes.
# Only the trial's own two addresses may stay in it.
QRJS_ENTRY = re.compile(
    r'"([A-Za-z0-9_-]+)":\s*\{\s*"n":\s*\d+\s*,\s*"url":\s*"([^"]+)"'
)
APPROVED_QR_URLS = {
    "master": "/form/",
    "5ws": "/form/5ws-report.html",
}
QR_BASE = "https://mhpss-nepal.github.io"


def pages():
    return sorted(p for p in ROOT.glob("*.html") if p.is_file())


def anchors(html):
    out = []

    class A(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == "a":
                href = dict(attrs).get("href")
                if href:
                    out.append(href)

    A(convert_charrefs=True).feed(html)
    return out


def rail_group_hrefs(html, group):
    """The hrefs of the anchors in the rail group `data-g="<group>"`."""
    out = []
    state = {"in": False, "depth": 0}

    class R(HTMLParser):
        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if tag == "div":
                if not state["in"] and a.get("data-g") == group:
                    state["in"], state["depth"] = True, 1
                    return
                if state["in"]:
                    state["depth"] += 1
            if tag == "a" and state["in"] and a.get("href"):
                out.append(a["href"])

        def handle_endtag(self, tag):
            if state["in"] and tag == "div":
                state["depth"] -= 1
                if state["depth"] == 0:
                    state["in"] = False

    R(convert_charrefs=True).feed(html)
    return out


def form_links(page_relpath, html):
    """In-repo hrefs of a page that resolve under the sibling /form/ app.

    A hub page lives at `/hub/<page>`, so a link resolves against `/hub/`.
    Relative (`../form/...`), root-relative (`/form/...`), protocol-relative,
    dot-segment, backslash, percent-encoded and case-variant spellings all
    reduce to the same normalized site path, mirroring the rendered checker's
    `resolved_path`. `unapproved_form_targets` applies the approved-address
    filter. `page_relpath` is accepted for callers but the base is fixed,
    because the hub is served at a known address.
    """
    out = []
    for href in anchors(html):
        unapproved = False
        target = resolved_form_target(href)
        if target == "/form" or target.startswith(FORMS_DIR_PREFIX):
            unapproved = True
        if unapproved:
            out.append(href)
    return out


def resolved_form_target(href):
    """Normalized site path an href resolves to from a page served at /hub/.

    Mirrors tools/hub-trial-scope-render-check.py: percent-decode, treat
    backslashes as separators, resolve relative roots, collapse dot segments,
    strip the /form vs /form/ difference, lowercase.
    """
    href = href.strip()
    if not href or href.startswith("#"):
        return ""
    if "://" in href or href.startswith("//"):
        path = urlparse(href).path
    else:
        path = href
    path = unquote(path.split("#", 1)[0].split("?", 1)[0]).replace("\\", "/")
    if not path:
        return ""
    if path.startswith("/"):
        return posixpath.normpath(path).lower()
    return posixpath.normpath(posixpath.join(SITE_DIR, path)).lower()


def unapproved_form_targets(page_relpath, html):
    """Resolved form links that are not one of the two approved addresses."""
    return [
        href
        for href in form_links(page_relpath, html)
        if resolved_form_target(href) not in APPROVED_FORM_TARGETS
    ]


def unapproved_nav_targets(html):
    """In-page hrefs that name or open an unapproved instrument."""
    return [
        href for href in anchors(html)
        if any(href.endswith(h) for h in UNAPPROVED_SECTION_HASHES)
    ]


def rail_module():
    spec = importlib.util.spec_from_file_location("hub_rail", ROOT / "tools" / "rail.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render_check_module():
    spec = importlib.util.spec_from_file_location(
        "hub_trial_scope_render_check",
        ROOT / "tools" / "hub-trial-scope-render-check.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HubTrialScopeTest(unittest.TestCase):
    def test_rendered_link_check_uses_exact_normalized_form_paths(self):
        check = render_check_module()
        page_url = "http://127.0.0.1:8791/hub/forms.html"
        cases = {
            "../form/": False,
            "../form": False,
            "../form/5ws-report.html?source=hub#top": False,
            "https://mhpss-nepal.github.io/FORM/5ws-report.html": False,
            "../form/contact.html": True,
            "/form/phq9.html": True,
            "https://mhpss-nepal.github.io/form/referral.html": True,
            "../form/selfreport.html?source=hub": True,
            "forms.html#contact": False,
            # adversarial spellings that a substring match would wave through
            "../form//contact.html": True,
            "../form/./contact.html": True,
            "../form/sub/../phq9.html": True,
            "../form%2fcontact.html": True,
            "../form/contact.html".replace("/", "\\"): True,
            "//mhpss-nepal.github.io/form/referral.html": True,
            "/FORM/Phq9.html": True,
        }
        self.assertEqual(
            cases,
            {href: check.is_unapproved_form_href(href, page_url) for href in cases},
        )

    def test_pre_fix_checker_fixture_is_unmodified(self):
        """The round-1 red/green demo must not be neutered by editing the fixture.

        The pre-fix checker has no `is_unapproved_form_href` at all: its scope
        rule lived inline in `main()` as a substring membership test
        (`any(p in href ...)`), which is exactly the round-1 defect. The fixture
        is pinned both by hash and by that substring signature, and the fixed
        checker must no longer carry the signature.
        """
        raw = (ROOT / PRE_FIX_CHECKER).read_text(encoding="utf-8")
        self.assertEqual(
            PRE_FIX_CHECKER_SHA256,
            hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "%s was edited; it must stay the pre-fix checker verbatim" % PRE_FIX_CHECKER,
        )
        self.assertIn(
            "any(p in href", raw,
            "the fixture no longer carries the pre-fix substring scope test",
        )
        fixed = (ROOT / "tools" / "hub-trial-scope-render-check.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(
            "any(p in href", fixed,
            "the fixed checker still uses the substring scope test",
        )

    def test_the_review_page_is_allowed_and_a_field_instrument_is_not(self):
        """The list is the decision, so the decision is pinned against real strings.

        A reviewer needs all-forms.html reachable. An unapproved instrument must
        never be reachable directly. Both must hold, or the trial scope is wrong
        in one direction or the other.
        """
        allowed = {
            '<a href="../form/all-forms.html"></a>': True,
            '<a href="../form/5ws-report.html"></a>': True,
            '<a href="../form/"></a>': True,
        }
        refused = {
            '<a href="../form/contact.html"></a>': False,
            '<a href="../form/referral.html"></a>': False,
            '<a href="../form/phq9.html"></a>': False,
            '<a href="../form/selfreport.html"></a>': False,
        }
        for html, must_pass in {**allowed, **refused}.items():
            found = unapproved_form_targets("forms.html", html)
            if must_pass:
                self.assertEqual([], found,
                                 f"a permitted address was refused: {html}")
            else:
                self.assertTrue(found,
                                f"an unapproved instrument was permitted: {html}")

    def test_no_hub_page_links_to_an_unapproved_form_page(self):
        offenders = {}
        for page in pages():
            found = sorted(set(unapproved_form_targets(
                page.name, page.read_text(encoding="utf-8"))))
            if found:
                offenders[page.name] = found
        self.assertEqual(
            {}, offenders,
            "a hub page offers a link that opens a form page outside the trial scope",
        )

    def test_static_form_link_rule_matches_the_rendered_rule(self):
        """The static scan must flag the same spellings the browser check does."""
        cases = {
            '<a href="../form/contact.html"></a>': True,
            '<a href="/form/phq9.html"></a>': True,
            '<a href="../form/sub/../referral.html"></a>': True,
            '<a href="../form/./selfreport.html"></a>': True,
            '<a href="../form//contact.html"></a>': True,
            '<a href="/FORM/Phq9.html"></a>': True,
            '<a href="//mhpss-nepal.github.io/form/referral.html"></a>': True,
            '<a href="../form%2fcontact.html"></a>': True,
            '<a href="../form/5ws-report.html"></a>': False,
            '<a href="../form/"></a>': False,
            '<a href="/form/"></a>': False,
            '<a href="/form"></a>': False,
            '<a href="./#reports"></a>': False,
            '<a href="forms.html#phq9"></a>': False,
        }
        for html, must_flag in cases.items():
            self.assertEqual(
                must_flag,
                bool(unapproved_form_targets("forms.html", html)),
                "static rule disagrees with the rendered rule for %s" % html,
            )

    def test_rail_generator_cannot_reintroduce_an_unapproved_form_link(self):
        rail = rail_module()
        offenders = sorted({
            href
            for _key, _label, _layer, _em, items in rail.GROUPS
            for _k, _l, href in items
            if unapproved_form_targets("index.html", '<a href="%s"></a>' % href)
        } | {
            href
            for _key, _label, _layer, _em, items in rail.GROUPS
            for _k, _l, href in items
            if unapproved_nav_targets('<a href="%s"></a>' % href)
        })
        self.assertEqual(
            [], offenders,
            "tools/rail.py offers a form page outside the trial scope as a rail item",
        )

    def test_default_rail_offers_only_the_approved_5ws_form(self):
        for page in RAIL_PAGES:
            html = (ROOT / page).read_text(encoding="utf-8")
            self.assertEqual(
                APPROVED_FORMS_GROUP, rail_group_hrefs(html, "forms"),
                "%s: the Field forms rail group is not the trial scope" % page,
            )
            self.assertIsNotNone(
                rail_module().MARK.search(html), "%s carries no rail marker" % page
            )

    def test_generated_rail_is_the_committed_rail(self):
        """A hand-edit of a rail block would otherwise pass the href checks."""
        rail = rail_module()
        for page in RAIL_PAGES:
            html = (ROOT / page).read_text(encoding="utf-8")
            rebuilt = rail.MARK.sub(
                lambda m: "<!--NAV:rail %s-->\n%s\n<!--/NAV-->"
                % (m.group(2), rail.rail_block(m.group(2))),
                html,
            )
            self.assertEqual(html, rebuilt,
                             "%s: run `python3 tools/rail.py apply`" % page)

    def test_hub_still_describes_and_imports_the_four_forms(self):
        """The trial rule removes the link, not the Hub's own review surface."""
        html = (ROOT / "forms.html").read_text(encoding="utf-8")
        for name in UNAPPROVED:
            self.assertIn('id="p-%s"' % name, html)
        self.assertEqual(4, html.count("Import a file"))
        self.assertEqual(4, html.count("Export these as CSV"))

    def test_hub_qr_asset_encodes_only_the_trial_addresses(self):
        """A printed QR is a physical path; none may encode an unapproved page."""
        src = (ROOT / "assets" / "qr.js").read_text(encoding="utf-8")
        found = {
            key: url[len(QR_BASE):] if url.startswith(QR_BASE) else url
            for key, url in QRJS_ENTRY.findall(src)
        }
        self.assertEqual(APPROVED_QR_URLS, found,
                         "assets/qr.js encodes an address outside the trial scope")


if __name__ == "__main__":
    unittest.main()
