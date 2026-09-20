#!/usr/bin/env python3
"""The optional `ward` field: accepted by Layer 2, exported by CSV, labelled, safe.

A field report may now carry an OPTIONAL `ward` (Layer 1 handoff,
`design-preview/HANDOFF-ward-field-to-hub.md`). Layer 2 must:

  1. not reject or silently drop it -- it reaches the CSV export;
  2. treat `""` as "not stated", matching the province/district/activity
     convention, not as missing or invalid;
  3. never treat a ward total as a denominator (it is an optional subset);
  4. keep the Ward control's labels out of the raw-key state, and keep the
     ward list built from the palika's own `wards` count in codes.js.

The defect this suite pins first is the silent one: `toCSV()` builds BOTH
the header and every row from `CSV_COLUMNS`, and `ward` was not in it, so a
reporter picked a ward, the record carried it, and the export lost it with
nothing looking wrong.

Run from the repository root:

    python3 -m unittest -v test_ward_field.py

The rendered checks drive a real browser over a served tree that holds this
repository as `/hub/` and the field-form build as `/form/` (set
$MHPSS_FORM_DIR to the form worktree; it defaults to the paired harness).
A source-text pass is NOT evidence the page works, so the label check is
rendered.
"""
from __future__ import annotations

import functools
import http.server
import json
import os
import shutil
import socketserver
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STORE = ROOT / "assets" / "store.js"
CODES = ROOT / "assets" / "codes.js"
DICT = ROOT / "assets" / "i18n-strings.js"
PROBE = ROOT / "tools" / "fixtures" / "store-probe.js"

# The form build is materialised from FORM_REF below, not served from a
# working tree -- see the note there.
# The form repository, and the commit whose 5Ws page carries the ward field the
# hub patches are for.
FORM_REPO = Path(os.environ.get("MHPSS_FORM_REPO", "/root/mhpss-nepal-work/form-frontend")).resolve()
FORM_REF = os.environ.get("MHPSS_FORM_REF", "24c7a2a")

# Keys that must render English on the Nepali page whatever the dictionary
# holds -- re-checked here because this change edits the dictionary.
PROTECTED_PREFIXES = [
    "phq9.item", "phq9.scale", "phq9.cutoff",
    "consent.", "safeguard.", "clinical.",
    "sr.p007", "sr.p001", "sr.clinicalNote",
]
PROTECTED_NAMED = [
    "phq9.item9", "phq9.item9Instruction", "phq9.scale1", "phq9.cutoff.interpretation",
    "consent.label", "consent.phq9",
    "safeguard.checkLabel", "safeguard.confirmation", "safeguard.consequence",
    "safeguard.referralExclusion", "sr.clinicalNote", "sr.p001", "sr.p007",
]

# The four palikas whose ward counts the hub patch adds, with the count that
# must appear. Aamachhodingmo is one NDRRMA names as affected.
WARD_COUNTS = {
    "NP0329401": ("Aamachhodingmo", 5),
    "NP0436408": ("Shahid Lakhan", 9),
    "NP0436409": ("Gandaki", 8),
    "NP0335401": ("Ichchhakamana", 7),
}

WARD_LABEL_KEYS = ["f4.wardLab", "f4.wardHelp", "f4.optional"]

A_RECORD_WITH_WARD = {
    "org": "X", "site": "PALIKA", "palika": "NP0328301", "ward": "4",
    "dateAD": "2026-09-18", "activity": "1.1", "modality": "HC",
    "reachedTotal": 5, "countBasis": "CONTACTS",
}
A_RECORD_WITHOUT_WARD = {
    "org": "Y", "site": "PALIKA", "palika": "NP0328302", "ward": "",
    "dateAD": "2026-09-18", "activity": "1.2", "modality": "COM",
    "reachedTotal": 3, "countBasis": "CONTACTS",
}


def _block(src, lang):
    import re
    m = re.search(r"\n  " + lang + r":\s*\{(.*?)\n  \}", src, re.S)
    if not m:
        return {}
    body = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)
    body = re.sub(r"^\s*//.*$", "", body, flags=re.M)
    return {mm.group(1): mm.group(2) for mm in
            re.finditer(r'"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"', body)}


def probe(records):
    """Run assets/store.js in node and return what its export path produces."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(records, fh)
        name = fh.name
    try:
        out = subprocess.run(["node", str(PROBE), name],
                             capture_output=True, text=True, check=True).stdout
        return json.loads(out)
    finally:
        os.unlink(name)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):  # keep the output readable
        pass


class WardCsvExportTest(unittest.TestCase):
    """The silent loss, fixed first."""

    @classmethod
    def setUpClass(cls):
        try:
            subprocess.run(["node", "--version"], capture_output=True, check=True)
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest("node unavailable: %s" % exc)

    def test_a_record_carrying_a_ward_exports_it(self):
        """FAILING-FIRST: `ward` is in the allow-list, the header and the row."""
        got = probe([A_RECORD_WITH_WARD])
        self.assertIn("ward", got["columns"],
                      "ward is not in CSV_COLUMNS, so the export drops it silently")
        head = got["head"].split(",")
        self.assertIn("ward", head, "the CSV header does not carry a ward column")
        cells = got["rows"][0].split(",")
        self.assertEqual(len(head), len(cells),
                         "the export row does not have one cell per header column")
        self.assertEqual("4", cells[head.index("ward")],
                         "the ward the reporter chose did not reach its CSV column")
        # ...and it sits where a reader expects: next to the other geography
        self.assertEqual(head.index("palika") + 1, head.index("ward"))

    def test_a_record_without_a_ward_still_exports_cleanly(self):
        """`""` is "not stated", not a broken row: the column is present, empty."""
        got = probe([A_RECORD_WITHOUT_WARD])
        head = got["head"].split(",")
        cells = got["rows"][0].split(",")
        self.assertEqual(len(head), len(cells))
        self.assertEqual("", cells[head.index("ward")],
                         "a record that states no ward must export a blank cell")
        # the rest of the row is untouched -- the column is inserted, not swapped
        self.assertEqual("NP0328302", cells[head.index("palika")])
        self.assertEqual("3", cells[head.index("reachedTotal")])

    def test_ward_reaches_the_export_for_both_shapes_in_one_run(self):
        """One export, one with a ward and one without: both stay aligned."""
        got = probe([A_RECORD_WITH_WARD, A_RECORD_WITHOUT_WARD])
        head = got["head"].split(",")
        self.assertEqual(2, len(got["rows"]))
        wards = [r.split(",")[head.index("ward")] for r in got["rows"]]
        self.assertEqual(["4", ""], wards)

    def test_register_body_keeps_ward_and_treats_blank_as_not_stated(self):
        """Nothing may reject or silently drop the field; "" is dropped as empty.

        `registerBody` drops empty values by design (the register document has
        a key cap), so a stated ward is carried and a `""` one is omitted --
        the same treatment every other optional field gets.
        """
        bodies = probe([A_RECORD_WITH_WARD, A_RECORD_WITHOUT_WARD])["bodies"]
        self.assertEqual("4", bodies[0].get("ward"),
                         "registerBody dropped a stated ward")
        self.assertNotIn("ward", bodies[1],
                         "a blank ward should be omitted, like every empty field")


class WardCodesTest(unittest.TestCase):
    """The four ward counts the hub patch adds."""

    def test_the_four_palikas_carry_a_ward_count(self):
        src = CODES.read_text(encoding="utf-8")
        import re
        for pcode, (name, count) in WARD_COUNTS.items():
            m = re.search(r'\{ pcode: "%s".*?\}' % re.escape(pcode), src)
            self.assertIsNotNone(m, "%s (%s) is not in PALIKAS" % (pcode, name))
            self.assertRegex(m.group(0), r"\bwards:\s*%d\b" % count,
                             "%s should carry wards: %d" % (pcode, count))
            self.assertIn(name, m.group(0))

    def test_every_palika_still_carries_a_ward_count(self):
        """The ward control stays hidden where a count is unknown -- verify none
        regressed, since a missing count is what the patch exists to fix."""
        src = CODES.read_text(encoding="utf-8")
        import re
        block = re.search(r"const PALIKAS = \[(.*?)\n\];", src, re.S).group(1)
        entries = re.findall(r"\{[^{}]*\}", block)
        self.assertTrue(entries)
        for e in entries:
            self.assertRegex(e, r"\bwards:\s*\d+", "a palika carries no ward count: %s" % e[:80])


class WardDictionaryTest(unittest.TestCase):
    """The three ward strings reach the dictionary, and the safety keys do not move."""

    @classmethod
    def setUpClass(cls):
        cls.src = DICT.read_text(encoding="utf-8")
        cls.en = _block(cls.src, "en")
        cls.ne = _block(cls.src, "ne")

    def test_the_ward_label_strings_exist_in_both_languages(self):
        for k in WARD_LABEL_KEYS:
            self.assertIn(k, self.en, "%s has no English string" % k)
            self.assertTrue(self.ne.get(k, "").strip(),
                            "%s has no Nepali string" % k)

    def test_the_ward_label_is_a_plain_string_with_no_markup(self):
        """The form inserts this key with textContent, not innerHTML.

        A value carrying <span> would render as visible source text on the
        page -- the exact symptom this patch exists to remove.
        """
        for k in WARD_LABEL_KEYS:
            for lang, d in (("en", self.en), ("ne", self.ne)):
                self.assertNotRegex(
                    d.get(k, ""), r"<[a-zA-Z/][^>]*>",
                    "%s/%s carries markup but is rendered as plain text" % (lang, k))

    def test_no_protected_key_gained_a_nepali_value(self):
        """Safety, not translation: a machine-rendered PHQ-9 is not the PHQ-9."""
        leaked = [k for k in self.ne
                  if any(k.startswith(p) for p in PROTECTED_PREFIXES)]
        self.assertEqual([], leaked,
                         "a protected key carries a Nepali value, so it would "
                         "render translated on a Nepali page")
        for k in PROTECTED_NAMED:
            self.assertFalse(self.ne.get(k, "").strip(),
                             "%s must have no Nepali value" % k)

    def test_the_ward_strings_are_marked_machine(self):
        """Provenance: the page says the Nepali is a machine draft."""
        import re
        m = re.search(r"\n    source:\s*\{\s*machine:\s*\[(.*?)\]", self.src, re.S)
        self.assertIsNotNone(m)
        listed = set(re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1)))
        for k in WARD_LABEL_KEYS:
            self.assertIn(k, listed, "%s is not marked as a machine draft" % k)


class WardFieldRenderedTest(unittest.TestCase):
    """What the page SHOWS -- the label is not the raw key, the list is built."""

    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest("playwright unavailable: %s" % exc)

        cls._tmp = tempfile.TemporaryDirectory(prefix="ward-field-")
        root = Path(cls._tmp.name)
        shutil.copytree(ROOT, root / "hub",
                        ignore=shutil.ignore_patterns(".git", "__pycache__"))
        # The form build, materialised from its committed ref by `git archive`
        # (never a hand copy of a page). Read-only, and pinned so the check
        # cannot silently start testing a different page.
        form = root / "form"
        form.mkdir()
        tar = subprocess.run(["git", "archive", FORM_REF], cwd=FORM_REPO,
                             capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(form)], input=tar, check=True)
        page = (form / "5ws-report.html").read_text(encoding="utf-8")
        if "wardWrap" not in page:
            raise AssertionError(
                "the form build at %s %s has no ward control, so the rendered "
                "ward checks would pass vacuously -- point MHPSS_FORM_REPO/"
                "MHPSS_FORM_REF at a build that carries the ward field"
                % (FORM_REPO, FORM_REF))

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

    def _open(self, page, lang="ne"):
        # `?lang=ne` is explicit, so the label check does not depend on the
        # page's declared default (that is a separate task's property).
        page.goto(self.base + "/form/5ws-report.html?lang=" + lang, wait_until="load")
        page.wait_for_timeout(400)

    def test_the_ward_label_is_not_the_raw_key_on_the_nepali_page(self):
        """The symptom the hub patch removes: label renders as `f4.wardLab`."""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(locale="en-US")
            page = ctx.new_page()
            self._open(page)
            body = page.inner_text("body")
            for k in WARD_LABEL_KEYS:
                self.assertNotIn(k, body,
                                 "the page shows the raw key %s" % k)
            ctx.close()
            browser.close()

    def test_the_ward_control_appears_for_a_palika_with_a_ward_count(self):
        """Aamachhodingmo is one of the four the patch fixed; its list must build."""
        from playwright.sync_api import sync_playwright

        probe_js = """() => {
          const out = {};
          const site = document.getElementById('site');
          const pal = document.getElementById('palika');
          const ward = document.getElementById('ward');
          const wrap = document.getElementById('wardWrap');
          site.value = 'PALIKA';
          site.dispatchEvent(new Event('change', {bubbles:true}));
          pal.value = '%s';
          pal.dispatchEvent(new Event('change', {bubbles:true}));
          out.hidden = !!wrap.hidden;
          out.options = [...ward.options].map(o => o.value);
          out.label = document.querySelector('label[for=ward]').textContent.trim();
          return out;
        }""" % "NP0329401"

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(locale="en-US")
            page = ctx.new_page()
            self._open(page)
            got = page.evaluate(probe_js)
            self.assertFalse(got["hidden"], "the ward control stayed hidden")
            # a blank option plus one per ward
            self.assertEqual(6, len(got["options"]),
                             "Aamachhodingmo should offer 5 wards plus the blank")
            self.assertEqual("", got["options"][0])
            self.assertNotIn("f4.", got["label"])
            # the label is Nepali on the Nepali-default page, not the raw key
            self.assertTrue(any("\u0900" <= ch <= "\u097f" for ch in got["label"]),
                            "the ward label is not in Nepali: %r" % got["label"])
            # and it is TEXT, not literal markup: the label has no
            # data-i18n-html, so a value carrying <span> would be printed as
            # visible source. The pending patch's value does carry <span>; this
            # guards the delivered value against that.
            self.assertNotIn("<", got["label"],
                             "the ward label renders literal markup: %r" % got["label"])
            ctx.close()
            browser.close()

    def test_the_ward_help_line_is_not_the_raw_key_or_markup(self):
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(locale="en-US")
            page = ctx.new_page()
            self._open(page, lang="en")
            help_text = page.evaluate(
                "() => { const el = document.querySelector('#wardWrap .help');"
                " return el ? el.textContent : null; }")
            self.assertIsNotNone(help_text, "the ward help line is missing")
            self.assertNotIn("f4.", help_text)
            self.assertNotIn("<", help_text)
            self.assertIn("NDRRMA", help_text)
            ctx.close()
            browser.close()


class LayerTwoTreatmentTest(unittest.TestCase):
    """Layer 2's documented treatment of `ward`, pinned so it cannot drift.

    The requirement the parent accepted: `ward` is a new field nothing may
    reject; `""` means "not stated"; a ward total is a subset, never a
    denominator; and if a ward FILTER is added a record with no ward must be
    stated, not dropped.
    """

    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.model = (ROOT / "docs" / "DATA_MODEL.md").read_text(encoding="utf-8")

    def test_no_closed_field_list_rejects_an_unknown_field(self):
        """Nothing enumerates the record's fields as a validation allow-list.

        `validate()` returns problems; it never returns \"unknown field\". The
        only allow-lists in the codebase are for OUTPUT (what is exported, what
        is published), where a missing field drops a column rather than
        rejecting a record.
        """
        store = (ROOT / "assets" / "store.js").read_text(encoding="utf-8")
        validate = store.split("function validate(")[1].split("\n}")[0]
        for banned in ("unknown", "not allowed", "unexpected field", "Object.keys(r)"):
            self.assertNotIn(banned, validate,
                             "validate() rejects an unknown field: %r" % banned)

    def test_ward_is_declared_known_but_not_yet_a_dimension(self):
        """`ward` is NOT in DIMS: adding a ward filter changes what the
        dashboard shows, and no ward presentation has been reviewed."""
        import re
        m = re.search(r"var DIMS = \[(.*?)\];", self.index)
        self.assertIsNotNone(m, "the DIMS list moved")
        dims = re.findall(r'"([^"]+)"', m.group(1))
        self.assertNotIn("ward", dims,
                         "ward joined DIMS without a reviewed presentation")
        self.assertIn("palika", dims, "the DIMS scan read the wrong list")

    def test_the_dimensioning_decision_is_documented_with_the_adib_flag(self):
        """The card requires the choice be explicit and any presentation change
        flagged for Adib -- not left implicit."""
        for phrase in ("known-but-not-yet-dimensioned", "Flagged for Adib",
                       "never a denominator", "subset"):
            self.assertIn(phrase, self.model,
                          "DATA_MODEL.md does not record %r" % phrase)

    def test_the_trial_form_records_a_ward_field(self):
        """The whole reason this card exists: the form sends a `ward`."""
        page = subprocess.run(["git", "show", "%s:5ws-report.html" % FORM_REF],
                              cwd=FORM_REPO, capture_output=True, text=True,
                              check=True).stdout
        self.assertIn('id="ward"', page)
        self.assertRegex(page, r"ward:\s*[^,]*ward[^,]*\.value",
                         "the form does not put the ward control on the record")


class SafetyStringsRenderedTest(unittest.TestCase):
    """§4 of the card: after applying the patches, prove the protected keys still
    render ENGLISH on the Nepali page -- re-verified, not assumed.

    The dictionary half of this card adds Nepali values, so the risk it carries
    is that a protected key gained one. The proof is RENDERED: `?lang=ne` on the
    page that actually carries the protected keys (`selfreport.html`), reading
    the text the page shows. A source grep is not evidence the page works.

    Only `selfreport.html` uses a protected prefix in the current form build;
    the named PHQ-9 / consent / safeguard keys live on pages the trial build has
    removed, so for those the check is on the dictionary: they must hold no
    Nepali value at all.
    """

    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest("playwright unavailable: %s" % exc)

        cls._tmp = tempfile.TemporaryDirectory(prefix="ward-safety-")
        root = Path(cls._tmp.name)
        shutil.copytree(ROOT, root / "hub",
                        ignore=shutil.ignore_patterns(".git", "__pycache__"))
        form = root / "form"
        form.mkdir()
        tar = subprocess.run(["git", "archive", FORM_REF], cwd=FORM_REPO,
                             capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(form)], input=tar, check=True)

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

    @staticmethod
    def _has_devanagari(s):
        return any("\u0900" <= ch <= "\u097f" for ch in (s or ""))

    def test_protected_strings_are_english_on_the_nepali_self_report_page(self):
        from playwright.sync_api import sync_playwright

        probe_js = """() => {
          const out = {lang: document.documentElement.getAttribute('data-lang'), kept: {}};
          for (const k of ['sr.p007','sr.clinicalNote','sr.p001']) {
            const el = document.querySelector('[data-i18n="' + k + '"]');
            out.kept[k] = el ? el.textContent : null;
          }
          return out;
        }"""
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(locale="en-US")
            page = ctx.new_page()
            page.goto(self.base + "/form/selfreport.html?lang=ne", wait_until="load")
            page.wait_for_timeout(400)
            got = page.evaluate(probe_js)
            self.assertEqual("ne", got["lang"],
                             "the Nepali page did not resolve, so this proves nothing")
            for k, text in got["kept"].items():
                self.assertIsNotNone(text, "%s is not on the page" % k)
                self.assertTrue(text.strip(), "%s rendered empty" % k)
                self.assertFalse(self._has_devanagari(text),
                                 "%s rendered Nepali on the Nepali page: %r"
                                 % (k, text[:80]))
            ctx.close()
            browser.close()

    def test_every_named_protected_key_holds_no_nepali_value(self):
        """The named list in the card, checked against the dictionary itself.

        NOTE, recorded rather than assumed: in `hub` main, the named PHQ-9 /
        consent / safeguard keys carry NEITHER an English NOR a Nepali entry --
        they are simply absent, because the pages that would use them are not
        in this build. The safety property is therefore two-fold: (a) this
        change adds no Nepali for a protected key, and (b) where the hub does
        carry the key (sr.p001 / sr.p007 / sr.clinicalNote), the Nepali is
        absent too, so nothing renders translated on a Nepali page.
        """
        en = _block(DICT.read_text(encoding="utf-8"), "en")
        ne = _block(DICT.read_text(encoding="utf-8"), "ne")
        for k in PROTECTED_NAMED:
            self.assertFalse(ne.get(k, "").strip(),
                             "%s carries a Nepali value" % k)
        # every protected key the hub actually carries must have an English string
        present = [k for k in PROTECTED_NAMED if k in en]
        self.assertEqual(sorted(present), ["sr.clinicalNote", "sr.p001", "sr.p007"],
                         "the set of named protected keys in the dictionary moved")
        for k in present:
            self.assertTrue(en[k].strip(), "%s has an empty English string" % k)


if __name__ == "__main__":
    unittest.main(verbosity=2)
