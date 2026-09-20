#!/usr/bin/env python3
"""Apply the 7 review-settled Nepali strings to the canonical dictionary.

Reuses the project's own append logic (`tools/i18n_apply.py`) so the rules it
enforces still hold: append-only, no existing line touched, under
`_meta.source.machine` (this is machine drafting; `_meta.source.human` stays
empty), and a key under a professionalOnly prefix gets no Nepali whatever the
input says.

Run from the hub repository root:  python3 tools/i18n_apply_review.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import i18n_apply

FORM = Path("/root/mhpss-nepal-work/form-translation")
ROOT = Path(__file__).resolve().parents[1]
STRINGS = ROOT / "assets" / "i18n-strings.js"

COMMENT = ("    /* ---- referral, PHQ-9 and service contact forms: 7 more keys\n"
           "       20 Sep 2026, settled by comparing the two machine lanes against the\n"
           "       project's OWN published vocabulary (assets/codes.js `np` fields, the\n"
           "       terminology lock, the dictionary's placeholders) -- never by a vote.\n"
           "       Each settled key differed on exactly one term the project has already\n"
           "       fixed, e.g. अनुगमन over फलोअप, स्थान over स्थल. Where the difference was\n"
           "       not fixed by that material it was LEFT IN ENGLISH and reported; see\n"
           "       tools/i18n-ne-authority-held.json in the form repo. Machine drafts,\n"
           "       NOT checked by a Nepali speaker. -- */")


def main():
    settled = json.loads((FORM / "tools" / "i18n-ne-authority-resolved.json").read_text(
        encoding="utf-8"))
    drafts = {k: v["np"] for k, v in settled.items()}

    source = STRINGS.read_text(encoding="utf-8")
    protected = [k for k in drafts if k.startswith(tuple(i18n_apply.PROTECTED))]
    if protected:
        raise SystemExit("refusing: %s sit under a professionalOnly prefix" % protected)
    conflicts = sorted(k for k in drafts if k not in i18n_apply.keys_in(source, "en"))
    if conflicts:
        raise SystemExit("refusing: these keys have no English string: %s" % conflicts)

    additions = [(k, v) for k, v in sorted(drafts.items()) if v.strip()]
    source, added = i18n_apply.append_to_block(source, "ne", additions, COMMENT)
    print("ne: +%d machine drafts (%s)" % (len(added), ", ".join(added)))

    machine = sorted(k for k, v in i18n_apply.keys_in(source, "ne").items() if v.strip())
    source, added_machine = i18n_apply.append_to_meta_list(source, "machine", machine)
    print("_meta.source.machine: +%d keys, %d listed in total"
          % (len(added_machine), len(machine)))

    STRINGS.write_text(source, encoding="utf-8")
    print("wrote %s" % STRINGS)


if __name__ == "__main__":
    main()
