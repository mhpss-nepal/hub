#!/usr/bin/env python3
"""Failing-first proof: the language default is per page, from one engine.

Adib's decision (2026-09-20) is that the field form (Layer 1) opens in Nepali
while the Hub (Layer 2) and the public site (Layer 3) open in English. The
engine `assets/i18n.js` is shared by all of them, so a single global default
cannot express that -- and a default guessed from the URL path breaks the first
time a page moves.

The mechanism under test here is a per-page declaration read by that one
engine:

    <html lang="en" data-i18n-default="ne">

These tests drive a real browser over a served root that holds this repository
as `/hub/` and the field-form build as `/form/`, so the engine and the pages
are the real files, not stand-ins. They assert the six properties the decision
depends on:

  1. a page declaring `ne` opens in Nepali        (the 5Ws report)
  2. a page declaring nothing opens in English    (Hub, Layer 3, all other
                                                   form pages)
  3. `?lang=` still wins, either way              (shareable/bookmarkable)
  4. a remembered choice survives navigation      (pick English, stay English)
  5. browser preference still works where no explicit default applies
  6. one page's default does not leak into another -- proved on a SINGLE
     origin, so the proof does not rest on isolation between origins

Run from this repository root:

    python3 -m unittest -v test_i18n_per_layer_default.py

The field-form build is read from $MHPSS_FORM_DIR, defaulting to the sibling
worktree this task created. Both repositories must be checked out; the test
skips (does not pass) if the form build is missing, so a false green is not
possible.
"""
from __future__ import annotations

import functools
import http.server
import os
import re
import shutil
import socketserver
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# The paired verification harness: `perlayer/form` sits beside a `hub` symlink
# to `hub-real`, which is how the two repositories are served to a reader
# (../hub/assets/... resolves for the form pages). See EVIDENCE-per-layer-default.md.
DEFAULT_HARNESS = "/root/mhpss-nepal-work/perlayer/form"
FORM_DIR = Path(os.environ.get("MHPSS_FORM_DIR", DEFAULT_HARNESS)).resolve()
ENGINE = ROOT / "assets" / "i18n.js"

# One origin for everything, so "does not leak" is about the mechanism and not
# about browser origin isolation.
FIXTURE_DECLARED_NE = """<!DOCTYPE html>
<html lang="en" data-i18n-default="ne">
<head><meta charset="utf-8"><title>declared ne</title></head>
<body>
<h1 data-i18n="f4.h1">fallback</h1>
<script src="../../assets/i18n-strings.js"></script>
<script src="../../assets/i18n.js"></script>
</body></html>
"""

FIXTURE_NO_DECLARATION = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>no declaration</title></head>
<body>
<h1 data-i18n="f4.h1">fallback</h1>
<script src="../../assets/i18n-strings.js"></script>
<script src="../../assets/i18n.js"></script>
</body></html>
"""

# A declaration naming a language the dictionary does not offer. It must fall
# back to English rather than stranding the reader.
FIXTURE_DECLARED_TYPO = """<!DOCTYPE html>
<html lang="en" data-i18n-default="zz">
<head><meta charset="utf-8"><title>declared typo</title></head>
<body>
<h1 data-i18n="f4.h1">fallback</h1>
<script src="../../assets/i18n-strings.js"></script>
<script src="../../assets/i18n.js"></script>
</body></html>
"""

FIXTURE_DIR = "tools/fixtures"
FIXTURES = {
    "declared-ne.html": FIXTURE_DECLARED_NE,
    "no-declaration.html": FIXTURE_NO_DECLARATION,
    "declared-typo.html": FIXTURE_DECLARED_TYPO,
}

LANG_PROBE = "() => document.documentElement.getAttribute('data-lang')"


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):  # keep the output readable
        pass


def _unit_test_source_checks():
    """Static properties, checked without a browser (still failing-first)."""
    src = ENGINE.read_text(encoding="utf-8")


class PerLayerDefaultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not FORM_DIR.is_dir():
            raise unittest.SkipTest(
                "field-form build not found at %s (set MHPSS_FORM_DIR)" % FORM_DIR)
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest("playwright unavailable: %s" % exc)

        import tempfile
        cls._tmp = tempfile.TemporaryDirectory(prefix="i18n-per-layer-")
        root = Path(cls._tmp.name)
        shutil.copytree(ROOT, root / "hub",
                        ignore=shutil.ignore_patterns(".git", "__pycache__"))
        shutil.copytree(FORM_DIR, root / "form",
                        ignore=shutil.ignore_patterns(".git", "__pycache__"))
        fix = root / "hub" / FIXTURE_DIR
        fix.mkdir(parents=True, exist_ok=True)
        for name, body in FIXTURES.items():
            (fix / name).write_text(body, encoding="utf-8")

        handler = functools.partial(Quiet, directory=str(root))
        cls._server = socketserver.TCPServer(("127.0.0.1", 0), handler)
        cls._port = cls._server.server_address[1]
        cls._thread = threading.Thread(target=cls._server.serve_forever, daemon=True)
        cls._thread.start()
        cls.base = "http://127.0.0.1:%d" % cls._port

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "_server", None):
            cls._server.shutdown()
            cls._server.server_close()
            cls._thread.join()
        if getattr(cls, "_tmp", None):
            cls._tmp.cleanup()

    # -- helpers ---------------------------------------------------------
    def _lang(self, page, url, context=None, wait=350):
        page.goto(url, wait_until="load")
        page.wait_for_timeout(wait)
        return page.evaluate(LANG_PROBE)

    def test_engine_declares_the_hook_and_keeps_english_as_the_floor(self):
        src = ENGINE.read_text(encoding="utf-8")
        self.assertIn('data-i18n-default', src,
                      "engine does not read a per-page language default")
        # The constant stays English: a page that declares nothing must be
        # English, and no page may be handed Nepali by a global switch.
        self.assertIn('var DEFAULT = "en"', src,
                      "the global default was changed; the Hub and Layer 3 "
                      "would now open in Nepali")
        self.assertNotIn('var DEFAULT = "ne"', src)
        # The declared value must be validated against the offered languages.
        self.assertRegex(src, r"codes\.indexOf\(DECLARED\)\s*>\s*-1")

    def test_layers_get_their_own_default_in_one_browser(self):
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            # A fresh context: no remembered choice, and an English browser, so
            # only the page's own default can decide.
            ctx = browser.new_context(locale="en-US")
            page = ctx.new_page()

            # 1. the 5Ws report declares Nepali and opens in Nepali
            self.assertEqual(
                self._lang(page, self.base + "/form/5ws-report.html"), "ne",
                "the 5Ws report did not open in Nepali")

            # 2. the Hub and Layer 3-style pages declare nothing and stay English
            for path in ("/hub/index.html", "/hub/forms.html", "/hub/access.html",
                         "/hub/tools/fixtures/no-declaration.html"):
                self.assertEqual(
                    self._lang(page, self.base + path), "en",
                    "%s did not open in English" % path)

            # 6. the leak test, on one origin: Hub is English while the form
            #    page on the same origin is Nepali
            self.assertEqual(self._lang(page, self.base + "/form/5ws-report.html"), "ne")
            self.assertEqual(self._lang(page, self.base + "/hub/index.html"), "en")

            # a declaration naming an unavailable language must not strand anyone
            self.assertEqual(
                self._lang(page, self.base + "/hub/tools/fixtures/declared-typo.html"),
                "en")

            # a fixture declaring Nepali must genuinely resolve to Nepali, so
            # the mechanism (not the page) is what decides
            self.assertEqual(
                self._lang(page, self.base + "/hub/tools/fixtures/declared-ne.html"),
                "ne")

            ctx.close()
            browser.close()

    def test_url_still_wins_on_the_nepali_default_page(self):
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(locale="en-US")
            page = ctx.new_page()
            self.assertEqual(
                self._lang(page, self.base + "/form/5ws-report.html?lang=en"), "en",
                "?lang=en did not override the Nepali default")
            self.assertEqual(
                self._lang(page, self.base + "/form/5ws-report.html?lang=ne"), "ne")
            # and the URL wins on an English-default page too, so both
            # languages stay shareable everywhere
            self.assertEqual(
                self._lang(page, self.base + "/hub/index.html?lang=ne"), "ne")
            ctx.close()
            browser.close()

    def test_remembered_choice_survives_navigation(self):
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(locale="en-US")
            page = ctx.new_page()

            # A reader on the Nepali-default form picks English...
            self.assertEqual(self._lang(page, self.base + "/form/5ws-report.html"), "ne")
            page.eval_on_selector(
                "#i18nbar button[data-lang='en']", "b => b.click()")
            page.wait_for_timeout(200)
            self.assertEqual(
                page.evaluate(LANG_PROBE), "en",
                "the ENG button did not switch the page to English")

            # ...and stays in English afterwards, on the plain URL and on a
            # different page of the same origin.
            self.assertEqual(
                self._lang(page, self.base + "/form/5ws-report.html"), "en",
                "the remembered English choice was lost on the Nepali-default form")
            self.assertEqual(
                self._lang(page, self.base + "/hub/forms.html"), "en")
            ctx.close()
            browser.close()

    def test_browser_preference_still_works_with_no_explicit_default(self):
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            # A phone set to Nepali, on a page that declares no default: the
            # browser preference is still honoured.
            ctx = browser.new_context(locale="ne-NP")
            page = ctx.new_page()
            self.assertEqual(
                self._lang(page, self.base + "/hub/index.html"), "ne",
                "browser preference was ignored where no default was declared")
            # and on the form page it agrees with the declaration
            self.assertEqual(
                self._lang(page, self.base + "/form/5ws-report.html"), "ne")
            ctx.close()
            browser.close()

    def test_a_declared_default_is_not_written_back_or_leaked(self):
        """The default must not become a remembered choice.

        pick() may READ a default, but only an explicit reader action may WRITE
        the remembered key. If the default were written on first load it would
        become sticky: a reader landing on the Nepali form would then be shown
        Nepali everywhere, including the English-default Hub -- which is exactly
        the leak the per-layer design exists to prevent.
        """
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(locale="en-US")
            page = ctx.new_page()
            self.assertEqual(self._lang(page, self.base + "/form/5ws-report.html"), "ne")
            self.assertIsNone(
                page.evaluate("() => localStorage.getItem('mhpss-np-lang')"),
                "a declared default was written to the remembered-choice key; "
                "it would leak into every other page")
            # and simply accepting the default on an English page writes nothing
            self.assertEqual(self._lang(page, self.base + "/hub/index.html"), "en")
            self.assertIsNone(
                page.evaluate("() => localStorage.getItem('mhpss-np-lang')"))
            ctx.close()
            browser.close()

    def test_layer_3_public_site_declares_no_default_and_stays_english(self):
        """The public site is its own engine copy and must stay English.

        Layer 3 (the public site) is a separate repository with its own copy of
        this engine. It declares no per-page default, so it keeps whatever that
        copy's DEFAULT is -- which must remain English. Checked statically so it
        runs without the Layer 3 checkout being served.
        """
        layer3 = Path(os.environ.get(
            "MHPSS_LAYER3_DIR", "/root/mhpss-nepal-work/public-layer3")).resolve()
        if not layer3.is_dir():
            self.skipTest("Layer 3 checkout not present at %s" % layer3)
        engine = layer3 / "assets" / "i18n.js"
        self.assertTrue(engine.is_file(), "Layer 3 engine missing")
        src = engine.read_text(encoding="utf-8")
        self.assertIn('var DEFAULT = "en"', src,
                      "Layer 3's engine no longer defaults to English")
        for page in sorted(layer3.glob("*.html")):
            html = page.read_text(encoding="utf-8")
            self.assertNotIn("data-i18n-default", html,
                             "%s declares a per-page default; the public site "
                             "must stay English by default" % page.name)


    def test_field_worker_never_sees_the_reviewer_chrome(self):
        """Reviewer mode (?i18n=report) must be invisible to a field worker.

        It is off unless the address asks for it, so a worker opening the 5Ws
        form on a phone sees no report chip and no dashed outlines.
        """
        from playwright.sync_api import sync_playwright

        CHROME = """() => ({
          mode: document.documentElement.getAttribute('data-i18n-report'),
          chip: !!document.getElementById('i18nrpt'),
          lang: document.documentElement.getAttribute('data-lang')
        })"""
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(locale="en-US")
            page = ctx.new_page()
            self._lang(page, self.base + "/form/5ws-report.html")
            plain = page.evaluate(CHROME)
            self.assertIsNone(plain["mode"], "reviewer mode was on by default")
            self.assertFalse(plain["chip"], "the report chip was shown by default")
            self.assertEqual(plain["lang"], "ne")

            # and it does mount when a reviewer asks for it
            self._lang(page, self.base + "/form/5ws-report.html?i18n=report")
            review = page.evaluate(CHROME)
            self.assertEqual(review["mode"], "on")
            self.assertTrue(review["chip"])
            ctx.close()
            browser.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
