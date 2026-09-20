/* Fixture dictionary for test_i18n_protection_intact.py — NOT shipped.

   It exists to exercise `_meta.professionalOnly` for real: unlike the shipped
   dictionaries, this one GIVES the protected keys a Nepali value, so the
   safety property "clinical wording renders in English even on the Nepali
   page" is proven by the engine refusing the Nepali, not by the Nepali being
   absent (which would prove nothing).

   `fx.plain` is a non-protected key with Nepali, to prove the page really is
   in Nepali at the same time, and `fx.machine` is marked machine-sourced so the
   machine provenance mark can be observed. */
window.I18N_STRINGS = {
  _meta: {
    langs: [
      { code: "en", label: "ENG", name: "English",  html: "en" },
      { code: "ne", label: "NEP", name: "नेपाली",   html: "ne" }
    ],
    revision: "fixture-1",
    professionalOnly: ["phq9.item", "consent.", "safeguard."],
    source: { machine: ["fx.machine"], human: [] }
  },
  en: {
    "fx.title":     "Protection fixture",
    "fx.plain":     "A plain, translatable sentence.",
    "fx.machine":   "A machine-drafted sentence.",
    "phq9.item1":   "Little interest or pleasure in doing things",
    "consent.label": "I agree to take part.",
    "safeguard.checkLabel": "No one is at immediate risk",
    "lang.select":  "Select language",
    "mt.notice.ne": "यो पृष्ठ स्वचालित रूपमा अनुवाद गरिएको हो।",
    "mt.authoritative.ne": "अंग्रेजी संस्करण आधिकारिक हो।",
    "mt.clinicalKept.ne": "चिकित्सकीय शब्दावली अंग्रेजीमै राखिएको छ।",
    "mt.notice.en": "This page was translated automatically.",
    "mt.authoritative.en": "The English version is the authoritative one.",
    "mt.clinicalKept.en": "Clinical wording is kept in English.",
    "mt.readEnglish": "Read in English",
    "mt.dismiss":   "Dismiss",
    "i18n.keptTitle": "Kept in English on purpose",
    "i18n.todoTitle": "Not yet translated"
  },
  ne: {
    "fx.title":     "संरक्षण नमुना",
    "fx.plain":     "साधारण, अनुवाद गर्न मिल्ने वाक्य।",
    /* A Nepali draft for every protected key. The engine must still hold these
       in English; if any of these three renders, the safety property is gone. */
    "fx.machine":   "मेसिनले मस्यौदा गरेको वाक्य।",
    "phq9.item1":   "काममा रुचि वा आनन्द कम हुनु",
    "consent.label": "म सहभागी हुन सहमत छु।",
    "safeguard.checkLabel": "कसैलाई तत्काल खतरा छैन"
  }
};
