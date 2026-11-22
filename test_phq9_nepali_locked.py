"""The Nepali PHQ-9 is final (owner decision, 22 Nov 2026).

The forms use the validated Nepal PHQ-9 (Kohrt et al., BMC Psychiatry 2016):
phq9.item1-9 and phq9.scale0-3 in the `ne` table. No proofreading round,
reviewer correction or agent may change those words: the cut-off of 10 or
more belongs to them. This test pins their exact bytes.
"""
import hashlib, json, pathlib, subprocess, unittest

HERE = pathlib.Path(__file__).resolve().parent
STRINGS = HERE / "assets" / "i18n-strings.js"
ENGINE = HERE / "assets" / "i18n.js"
KOHRT_SHA256 = "17eef17b6b5e441f3922ff4d9cec330d6560555cc908ced469cecab08a2d5f12"
KEYS = ["phq9.item%d" % i for i in range(1, 10)] + ["phq9.scale%d" % i for i in range(4)]


def load():
    js = "global.window={};require(%s);process.stdout.write(JSON.stringify(window.I18N_STRINGS))" % json.dumps(str(STRINGS))
    return json.loads(subprocess.check_output(["node", "-e", js]))


class Phq9NepaliLocked(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.S = load()

    def test_kohrt_wording_is_byte_identical(self):
        ne = self.S["ne"]
        blob = "\n".join(k + "=" + ne[k] for k in KEYS)
        self.assertEqual(hashlib.sha256(blob.encode("utf-8")).hexdigest(), KOHRT_SHA256,
                         "The validated Nepal PHQ-9 wording changed. It is final: restore the Kohrt 2016 text.")

    def test_kohrt_wording_is_declared_human(self):
        human = set(self.S["_meta"]["source"]["human"])
        self.assertTrue(set(KEYS) <= human)

    def test_back_translation_lines_have_no_nepali(self):
        bad = [k for k in self.S["ne"] if k.startswith("clinical.grief.phq.item") or k.startswith("clinical.grief.phq.scale")]
        self.assertEqual(bad, [], "A re-translated PHQ-9 line would sit beside the validated one; keep these English-only.")

    def test_no_key_is_both_machine_and_human(self):
        src = self.S["_meta"]["source"]
        both = sorted(set(src["machine"]) & set(src["human"]))
        self.assertEqual(both, [], "A protected line would show a machine draft as if a person wrote it")

    def test_engine_shows_protected_text_only_when_human(self):
        src = ENGINE.read_text(encoding="utf-8")
        self.assertIn('if (isProtected(key) && provenance(key) !== "human")', src)

    def test_reviewed_pages_do_not_claim_machine_translation(self):
        src = ENGINE.read_text(encoding="utf-8")
        self.assertIn('if (keyed && cov.human && cov.human > (cov.machine || 0)) kind = "reviewed";', src)
        self.assertIn("mt.reviewed.en", self.S["en"])


if __name__ == "__main__":
    unittest.main()
