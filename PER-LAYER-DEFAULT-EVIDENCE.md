# Per-layer language default — evidence

**Task:** t_2449fe51 — *Per-layer language default: Nepali for the 5Ws form, English for Hub and Layer 3*
**Status:** DONE — REVIEW ARTIFACT
**Decision (Adib, 2026-09-20):** Layer 1 field forms default to Nepali; Layer 2 (Hub) and
Layer 3 (public site) default to English, with Nepali available as a one-tap toggle.

---

## 1. Which page defaults to which language

| Layer | Page | Default | How it is decided |
|---|---|---|---|
| 1 (field form) | `form/5ws-report.html` | **Nepali** | declares `<html lang="en" data-i18n-default="ne">` |
| 1 (other forms) | `form/index.html`, `contact/phq9/referral/selfreport.html`, `5ws-report-b2.html` | **English** | declare nothing |
| 1 (legacy entry) | `form/4ws-report.html` | n/a — **redirect** | a stub that redirects to the Nepali-default `5ws-report.html`, so it inherits whatever that page resolves to. It is not an English-default page. |
| 2 (Hub) | `hub/index.html`, `forms.html`, `access.html`, `inbox.html`, `coverage.html` | **English** | declare nothing |
| 3 (public site) | every page in `public-layer3/` | **English** | declare nothing; own engine copy keeps `DEFAULT = "en"` |

Only `5ws-report.html` gets a Nepali default, because it is the only trial form and the only
page that is 100 % translated (101 of 101 keys it uses are in the `ne` block).

## 2. The mechanism, and why it is per-layer

`hub/assets/i18n.js` is loaded by the forms, the Hub **and** Layer 3. A single global `DEFAULT`
cannot give three layers different defaults, and deciding from the URL path would break the first
time a page moved.

The default is therefore **declared in the page's own markup** and read by that one engine:

```html
<html lang="en" data-i18n-default="ne">
```

* The declaration belongs to one page, so there is nothing global for one layer's choice to
  overwrite — the leak the task asked to be proved impossible.
* `DEFAULT` stays `"en"`, so a page that declares nothing is English (Hub, Layer 3, other forms).
* The declared value is validated against the languages the dictionary offers, so a typo cannot
  strand a reader on a language that does not exist.

Resolution order is **unchanged**:

1. `?lang=` in the URL — still wins, so either language stays shareable/bookmarkable
2. `localStorage["mhpss-np-lang"]` — the reader's remembered choice
3. `navigator.language` starting `ne` — browser preference
4. **the page's declared default**, else `DEFAULT` (`"en"`)

A reader who picks English on the Nepali-default form stays in English: `pick()` only *reads* a
default, and nothing writes the declared default to the remembered key (proved by
`test_a_declared_default_is_not_written_back_or_leaked`).

## 3. Protected / `professionalOnly` behaviour — unchanged

`isProtected()` and the protected-substring list were not touched. Verified with 15 checks in
`tools/i18n-protection-and-marks-proof.py`, using a **fixture dictionary that deliberately gives
the protected keys a Nepali value** — so the property is proved by the engine refusing the Nepali,
not by the Nepali being absent:

* protected keys (`phq9.*`, `consent.`, `safeguard.`, …) render in **English on the Nepali page**
  (0 Devanagari characters in protected text), carry the `i18n-kept` class, and are explained;
* the honest reader notice still mounts on a Nepali page and **not** on an English one;
* `src="ne"` machine provenance is still labelled (`i18n-machine`);
* `?i18n=marks` still turns the translator marks on; a plain reader gets none.

The 5Ws page itself carries **no** protected keys (they live on `phq9.html` / `referral.html` /
`selfreport.html`), so the Nepali default cannot expose one there.

## 4. Feedback capture for the trial translation review

**Low-friction trigger:** a reviewer opens any page with `?i18n=report`, taps a string or a keyed
field, and picks one of four fixed reasons (`wrong`, `awkward`, `unclear`, `missing`). The mode is
remembered for the session (`?i18n=clean` turns it off), exactly like `?i18n=marks`.

**What can be reported — stated exactly, not "any string".** The engine declares the surface list
(`I18N.feedbackSurfaces`) and the picker wires each keyed surface the engine actually fills:

* `data-i18n` → `text` (the visible sentence)
* `data-i18n-ph` → `placeholder`
* `data-i18n-aria` → `aria-label`
* `data-i18n-alt` → `alt`
* `data-i18n-title` → `title`

A report names the surface (`"surface": "placeholder"`), so a translator knows whether the complaint
is about the sentence or the field's placeholder. A key is only reportable on the surface it
actually renders on that page (a placeholder-only key cannot be filed as text, and vice versa) —
four checks in the proof cover this.

**Where the reports land:** on the device, in **durable** storage —
`localStorage["mhpss-np-i18n-reports"]` — downloadable as `i18n-reports.json` from the ⚑ chip. This
was `sessionStorage` in the first submission and a review found the defect: an unexported report
disappeared when the tab closed. It is `localStorage` now, and the proof records a report, **closes
the page, reopens it in the same profile, and downloads the file** to show the report survived and
is still exportable. A person then hands that file to the translation review by whatever channel is
already approved (the same way a private export is handed over today).

**Keyboard operability (a review finding):** the reason picker was pointer-only and overflowed a
320 px screen (an independent scan found 29 of 77 visible targets placed a picker past the right
edge, because the left clamp ignored the picker's own width). Now:

* the picker clamps **both** edges against its measured width and height and wraps its buttons, so
  it fits narrow phones; the proof scans **every** keyed target on a 40-target fixture (and on the
  real served 5Ws page, 80 targets) at 320×640 / 360×740 / 390×844 and requires **0** overflowing
  pickers;
* in report mode every keyed element becomes focusable, Enter/Space opens the picker, focus moves to
  the first reason button, and Escape dismisses it and returns focus to the element. A field worker
  who is **not** in report mode gets no tab stops added.

**Privacy properties (30 checks in `tools/i18n-feedback-record-proof.py`):**

* the record is **structured, not typed** — `{kind, schema, key, surface, lang, revision, reason, page, src}`;
  there is **no free-text field**, so there is nowhere for a beneficiary's name to go;
* it carries **no query string or fragment** from the address bar (a shared link may carry anything);
* a key the page does not render, or a reason outside the fixed set, is refused;
* the engine contains **no transport** (`fetch`/`XMLHttpRequest`/`sendBeacon`/`WebSocket`) — it is
  a static public asset, so a URL written in it would be readable by anyone.

**Dependency (not invented here):** a **server-side sink needs an approved rules change.** The
Firestore rules' catch-all (`match /{document=**} { allow read, write: if false; }`) denies any new
collection; the only unauthenticated write today is a field record in `submissions`. Until
`/i18n_feedback` (or an equivalent approved destination) is added to the rules *and* published, the
reports stay on the device. That is the safe failure: the page never silently posts somewhere
unapproved.

## 5. Commands and counts

Verified trees: **Hub `/root/mhpss-nepal-work/hub-real`**, branch
`task/t_2449fe51-i18n-per-layer-default`; **form `/root/mhpss-nepal-work/perlayer/form`**, branch
`task/t_2449fe51-form-default` (worktree of `design/form-frontend`, whose tip `9c3a41e` contains
the trial build). The two are checked out side by side — `perlayer/form` with a `hub` symlink to
`hub-real` — so the form pages resolve `../hub/assets/*` to the durable repo, which is how the app
is served.

| Command (cwd) | Result |
|---|---|
| `python3 -m unittest -v test_i18n_per_layer_default` (hub) | **8 passed** |
| `python3 tools/per-layer-default-red-green.py` (hub) | base **5 of 8 FAIL** → delivered **8/8 OK**; `red/green demonstration: PASS` |
| `python3 tools/i18n-protection-and-marks-proof.py` (hub) | **15 checks, 0 failures** — safety properties unchanged |
| `python3 tools/i18n-feedback-record-proof.py` (hub) | **33 checks, 0 failures** — durability, viewport, keyboard, surface |
| `python3 tools/i18n-feedback-red-green.py` (hub) | base `44bba2c` engine: **20 of 40** pickers overflow at 320 px and a report is **lost** on reopen → delivered engine: **0 overflow, 1 report kept**; `PASS` |
| `python3 tools/i18n-check.py` (hub) | exit 0 — Gate open |
| `python3 tools/rail.py` / `text-setting-check.py` / `contrast-check.py` (hub) | exit 0 / 0 / 0 |
| `python3 -m unittest -q test_trial_scope` (hub) | **9 passed** |
| `python3 -m unittest -q test_trial_scope` (form) | **8 passed** |
| `python3 tools/i18n-check.py` (form) | exit 0 — Gate open |
| `python3 tools/qr-check.py` (form) | exit 0 |
| `python3 tools/sw-precache-check.py` (form) | exit 0 |
| `python3 tools/precache-fingerprint.py` (form) | up to date (`d9a844b4…`) |
| `python3 tools/5ws-still-works.py http://127.0.0.1:8899` (form) | exit 0 — `lang: ne`, switch mounted, 24-name contract match, 8 pickers |
| `python3 tools/trial-scope-render-check.py http://127.0.0.1:8899` (form) | exit 0 — 390/1280 px |
| `python3 tools/hub-trial-scope-render-check.py http://127.0.0.1:8899` (hub) | exit 0 — 390/1280 px, `offenders=[]` |

Rendered evidence for the decision itself (served site): the 5Ws form opens in **Nepali**
(`data-lang=ne`) with the bilingual notice and the ENG/NEP switch; `/hub/`, `/hub/forms.html`,
`/hub/access.html` and the Layer 3 fixtures open in **English**; `?lang=en` on the 5Ws page still
gives English; after pressing ENG the preference survives navigation back to the form.

## 6. Base / head / production refs

* Hub base `8273e9013b163549640d04b2ec86fa42c840a91b`; head is the tip of branch
  `task/t_2449fe51-i18n-per-layer-default` (local only). The latest **code** commit on it is
  `670763a662b0c04e3ad4b681a0353c7ea36e1919` (the round-1 feedback-channel fix); the commits above
  it are evidence-note edits and change no code, so the tip is not written as a literal that would
  go stale the moment this note is edited.
* Form base `9c3a41eeccc768fcef5d8f241430ba831e8ad9a8`; head is the tip of branch
  `task/t_2449fe51-form-default` (a worktree of `design/form-frontend`), latest code commit
  `79e761c` (the declared Nepali default).
* Production refs **unchanged**: public `68bf197`, form `9032bb7`, hub `ff2d4e2`
* No push, PR, merge or deploy. Both worktrees clean (`git status --porcelain -uall` empty).

## 7. Review-round corrections (round 1 → 2)

The first submission was returned with four points; all four are addressed, and the two execution
ones have their own red/green proof (`tools/i18n-feedback-red-green.py`):

1. **Durable feedback.** `sessionStorage` → `localStorage` for the report store, so an unexported
   report survives the tab closing. The proof records a report, closes the page, reopens it in the
   same profile and **downloads** the file to show it is still exportable. Red at `44bba2c`
   (`survived_reopen: 0`), green at head (`1`).
2. **Picker fits a phone and is keyboard-operable.** The picker now measures itself and clamps both
   edges (and wraps), and report mode makes keyed elements focusable with Enter/Space to open,
   focus into the first reason button, and Escape to dismiss. Red at `44bba2c`: **20 of 40** pickers
   overflow a 320×640 viewport; green at head: **0 of 40**. Rendered against the **real served 5Ws
   page**: 80 keyed targets, 0 overflowing, at 320×640 / 360×740 / 390×844.
3. **Evidence-note corrections.** The red/green count is **5 of 8** failing (not 4/8); the Hub head
   was written as `44bba2c` when the reviewed artifact was actually the evidence commit
   `a11466832c6dc743adef4ab942d79dccf5bc0f82` on top of it (and section 6 now names the branch tip
   rather than a literal that changes with every note edit); `4ws-report.html` is described as a
   **redirect/legacy entry**, not an English-default page.
4. **The reporting surface is stated, not implied.** It is no longer "any string": the engine
   declares `feedbackSurfaces` (`text`, `placeholder`, `aria-label`, `alt`, `title`) and the record
   carries `surface`. A key is reportable only on the surface it renders on that page.

The engine change to support this is in `assets/i18n.js`; the form side of the same change is the
`sw.js` cache bump (below).

## 8. Recorded, not silently accepted

1. **The form repo's precache fingerprint was already red before this change.** It hashes
   `../hub/assets/i18n.js` and friends through a *sibling path*, and the sibling
   `/root/mhpss-nepal-work/hub/` is a **stale staging copy** that diverges from the durable repo in
   `codes.js`, `i18n.js` and `i18n-strings.js`. At the form base `9c3a41e` the test already failed
   (`recorded 34b515c7… != computed 24bfe53c…`) — before any edit of mine, and the parent task's own
   tree fails it the same way. `tools/precache-fingerprint.py` was added so this is regenerated
   rather than hand-computed, and it now records the digest against the **durable** hub repo
   (`e9d8c501…`). **Caveat stated plainly:** that value is correct only in a layout where the form
   repo's sibling `hub/` is the durable hub repository — as in this verification harness. In the
   `form-frontend` checkout the sibling is the stale copy and the test still fails; reconciling that
   copy is a separate task, not this one.
2. **`sw.js` cache v41 → v42 → v43.** The engine is precached, so an installed phone would otherwise
   keep the old engine: v42 was required so the form opens in Nepali, and v43 so a phone does not
   keep the engine that lost unexported feedback and overflowed the picker. Both bumps are required
   by this task; `tools/precache.sha` regenerated to `d9a844b4…`.
3. **`form/index.html` was not edited** (requirement from the sibling task).
4. **The two inaccurate shared strings** flagged by the sibling task (`ml.p036`, `ml.p011`) are
   dictionary text and were **not** touched — this task does not change dictionary content.
5. **`design-preview/translation-review-index.html` fails `tools/text-setting-check.py`** in the
   form repo — pre-existing (reproduced with my changes stashed), in a file this task does not visit.
6. **The form repo's own report of this change is limited to `sw.js`/`tools/precache.sha`.** The
   durable engine lives in the hub repository (`hub-real`), which is what the form pages load at
   `../hub/assets/i18n.js`; no dictionary text was edited in either repository.
