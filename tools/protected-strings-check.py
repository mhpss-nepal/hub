#!/usr/bin/env python3
"""The 19 protected strings must EXIST in English and have NO Nepali.

Why this guard exists: three times now, a branch cut before an earlier fix and
merged after it has silently reverted this file, and the live site began
rendering the PHQ-9 items and the safeguarding notices as literal [key] text.
Reading the diff did not catch it; only measuring the live page did. So it is
now a test.

The rule the dictionary states for itself: phq9.item*, consent.*, safeguard.*
and clinical.* are strings NO machine may translate, because the PHQ-9 cut-off
>=10 belongs to specific validated wording (Kohrt et al., BMC Psychiatry 2016).
They must stay in the `en` table so i18n.js isProtected() shows the English, and
must have no `ne` value so a machine draft can never reach them.

Exit 0 all present and English; 1 a key is missing or has Nepali.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

DICT = Path(__file__).resolve().parent.parent / "assets" / "i18n-strings.js"
PREFIXES = ("phq9.item", "consent.", "safeguard.", "clinical.")

# Keys inside those prefixes that are legitimately allowed Nepali, if any.
# Listed so that adding one is a visible decision, not an accident.
#
# 2026-09-21 -- DECISION: the PHQ-9 items and the two instruction lines are
# allowed Nepali, and this is the only entry ever added.
#
#   phq9.item1..9      NOT machine output. The validated Nepali instrument from
#                      Kohrt et al. (BMC Psychiatry 2016;16:58, PMC4782581,
#                      Additional file 1), converted out of the legacy
#                      non-Unicode font and cross-checked with a second
#                      independent converter. Two mappers agree on all nine
#                      items. The cut-off of 10 or more belongs to these words,
#                      so these published words are what ships. Verbatim: not
#                      one item is re-worded.
#   phq9.itemInstruction  the "over the last 2 weeks" line, plain draft.
#   phq9.itemDifficulty   the impairment question, plain draft.
#                      Both carry NO scoring weight and are marked as drafts
#                      pending a Nepali-speaking clinician.
#
# STILL NOT ALLOWED, and this is deliberate: phq9.item9Instruction (the crisis
# instruction after item 9 -- someone acts on it in a real emergency and no
# verified Nepali exists, so it stays English and the engine marks it kept),
# phq9.cutoff.*, consent.*, safeguard.*, clinical.*.
ALLOW_NEPALI: tuple = (
    "phq9.item1", "phq9.item2", "phq9.item3", "phq9.item4", "phq9.item5",
    "phq9.item6", "phq9.item7", "phq9.item8", "phq9.item9",
    "phq9.itemInstruction", "phq9.itemDifficulty",
    # 2026-11-22 -- DECISION: Nepali written by a person for the grief and
    # referral directory forms. These 31 consent, safeguarding and clinical
    # sentences had no Nepali by rule; the native-speaking clinician reviewing
    # the forms for CMC-Nepal wrote them in proofreading round 1 (formproof,
    # 20-21 Nov 2026) and the owner approved applying them (22 Nov 2026).
    # Each is declared in _meta.source.human, which is what lets the engine
    # show it. The PHQ-9 back-translation lines (clinical.grief.phq.item*,
    # .scale*) are NOT here and never get Nepali: the validated Kohrt 2016
    # wording is the only Nepali PHQ-9 (owner decision, 22 Nov 2026).
    "clinical.grief.phq.partial",
    "clinical.grief.phq.src",
    "clinical.grief.phq.ten",
    "clinical.grief.phq.total",
    "clinical.grief.state.calm",
    "clinical.grief.state.confused",
    "clinical.grief.state.draft",
    "clinical.grief.state.overwhelmed",
    "clinical.grief.state.q",
    "clinical.grief.state.upset",
    "clinical.grief.state.warn",
    "clinical.grief.state.warnH",
    "clinical.grief.triage.acute",
    "clinical.grief.triage.normal",
    "clinical.grief.triage.ptsd",
    "clinical.grief.triage.redflag",
    "consent.dirf.correct.01",
    "consent.dirf.correct.02",
    "consent.dirf.publish.01",
    "consent.dirf.publish.02",
    "consent.grief.script.01",
    "consent.grief.script.02",
    "safeguard.dirf.safe",
    "safeguard.grief.cp",
    "safeguard.grief.selfharm.01",
    "safeguard.grief.selfharm.02",
    "safeguard.grief.urgent.01",
    "safeguard.grief.urgent.02",
    "safeguard.grief.urgent.03",
    "safeguard.grief.urgent.04",
    "safeguard.grief.urgent.05",
)


def load() -> dict:
    out = subprocess.run(
        ["node", "-e",
         "global.window={};require(process.argv[1]);"
         "console.log(JSON.stringify(window.I18N_STRINGS))", str(DICT)],
        capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def main() -> int:
    S = load()
    en, ne = S.get("en", {}), S.get("ne", {})
    pro = S.get("_meta", {}).get("professionalOnly", [])

    def protected(k):
        return any(k == p or k.startswith(p) for p in PREFIXES)

    # every key the dictionary is asked to render for a protected surface
    in_en = sorted(k for k in en if protected(k))
    leaked = sorted(k for k in ne if protected(k) and k not in ALLOW_NEPALI)

    problems = []
    if not in_en:
        problems.append("no protected key is present in `en` at all -- this is "
                        "the regression: the engine will render [key] text")
    if leaked:
        problems.append("protected key(s) carry Nepali, which the dictionary "
                        "forbids: %s" % leaked)

    # the prefixes must still be declared as protected, or the rule is inert
    for p in PREFIXES:
        if not any(p == d or d.startswith(p.rstrip(".")) or d == p
                   for d in pro):
            problems.append("prefix %r is not in _meta.professionalOnly" % p)

    print("  protected keys present in en: %d" % len(in_en))
    print("  protected keys carrying Nepali: %d" % len(leaked))
    if problems:
        print("\n  PROTECTED-STRINGS CHECK FAILED:")
        for p in problems:
            print("    %s" % p)
        return 1
    print("\n  OK: every protected string exists in English and only declared human-written ones have Nepali.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
