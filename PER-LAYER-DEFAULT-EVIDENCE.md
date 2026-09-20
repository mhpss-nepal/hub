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
| 1 (derived preview) | `form/5ws-report-b2.html` | **Nepali** | *generated* from `5ws-report.html` by `design-preview/build_b2.py`, which copies the source `<head>` — so it declares the same `ne`. Regenerated with the builder, never hand-edited. |
| 1 (other forms) | `form/index.html`, `contact/phq9/referral/selfreport.html` | **English** | declare nothing |
| 1 (legacy entry) | `form/4ws-report.html` | n/a — **redirect** | a stub that redirects to the Nepali-default `5ws-report.html`, so it inherits whatever that page resolves to. It is not an English-default page. |
| 2 (Hub) | `hub/index.html`, `forms.html`, `access.html`, `inbox.html`, `coverage.html` | **English** | declare nothing |
| 3 (public site) | every page in `public-layer3/` | **English** | declare nothing; own engine copy keeps `DEFAULT = "en"` |

Only `5ws-report.html` gets a Nepali default, because it is the only trial form and the only
page that is 100 % translated (101 of 101 keys it uses are in the `ne` block; 91 of those carry
machine provenance). Measured live through the engine's own counter on the served page —
`I18N.coverage` = `total 101, translated 101, untranslated 0, missing 0, kept 0, machine 91`.

### Where the declaration physically lives — and how to confirm it, not trust this note

The form half of this change is **not in the hub repository** the card names as its workspace, and
it is **not in any of the six worktrees** the operator's scan covered (`form-frontend`,
`form-translation`, `form-interface`, `form-safety`, `form`, `hub-real`). It lives on a **seventh,
non-committed worktree of the form repository** that the pairing makes:

```
repository    /root/mhpss-nepal-audit-20260918/form        (branch main)
worktree      /root/mhpss-nepal-work/perlayer/form         branch task/t_2449fe51-form-default
base          9c3a41eeccc768fcef5d8f241430ba831e8ad9a8
head          e3abd1ae2a747bf718fcb5f81b94c3a73e5e4144
```

The declaration commit is `79e761c` (*"5Ws report declares its own Nepali default; trial-scope pin
narrowed to it"*), and the shipped blob is `ba35ab92b19523095c26d4aaa856c8d51922cb4e`. Confirm it
from any shell:

```
git -C /root/mhpss-nepal-work/perlayer/form rev-parse HEAD
git -C /root/mhpss-nepal-work/perlayer/form show HEAD:5ws-report.html | sed -n 2p
#   e3abd1ae2a747bf718fcb5f81b94c3a73e5e4144
#   <html lang="en" data-i18n-default="ne">
```

or, as a machine check over every worktree, from any directory one level above them:
`search_files(pattern="data-i18n-default", path="/root/mhpss-nepal-work")` returns exactly three
hits — `perlayer/form/5ws-report.html:2`, `perlayer/form/5ws-report-b2.html:2` (its derived preview)
and a non-worktree scratch copy. The other six worktrees correctly return **zero**: only the 5Ws
page is meant to declare a default. The worktree is clean (`git status --porcelain -uall` empty),
which `scripts/land.py` requires.

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
actually renders on that page (an aria-label-only key cannot be filed as text, and a text-only key
cannot be filed as a placeholder). The surface is part of a report's identity, so the same key
complained about on two different surfaces is **two** reports, while the same surface reported twice
is still one — otherwise a placeholder complaint would silently swallow a separate sentence
complaint. Six checks in the proof cover this (the fixture deliberately keys one string both as
visible text and as a placeholder).

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

**Privacy properties (35 checks in `tools/i18n-feedback-record-proof.py`):**

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
| `python3 tools/i18n-feedback-record-proof.py` (hub) | **35 checks, 0 failures** — durability, viewport, keyboard, surface and surface-identity |
| `python3 tools/i18n-feedback-red-green.py` (hub) | base `44bba2c` engine: **20 of 40** pickers overflow at 320 px and a report is **lost** on reopen → delivered engine: **0 overflow, 1 report kept**; `PASS` |
| `python3 tools/i18n-check.py` (hub) | exit 0 — Gate open |
| `python3 tools/rail.py` / `text-setting-check.py` / `contrast-check.py` (hub) | exit 0 / 0 / 0 |
| `python3 -m unittest -q test_trial_scope` (hub) | **9 passed** |
| `python3 -m unittest -q test_trial_scope` (form) | **8 passed** |
| `python3 tools/i18n-check.py` (form) | exit 0 — Gate open |
| `python3 tools/qr-check.py` (form) | exit 0 |
| `python3 tools/sw-precache-check.py` (form) | exit 0 |
| `python3 tools/precache-fingerprint.py` (form) | up to date (`23f39a54…`) |
| `python3 tools/5ws-still-works.py http://127.0.0.1:8799` (form) | exit 0 — `lang: ne`, ENG/NEP switch mounted, **24-name** contract match, **9** selects (`…palika, ward, modality…`) |
| `python3 tools/trial-scope-render-check.py http://127.0.0.1:8799` (form) | exit 0 — 390/1280 px |
| `python3 tools/hub-trial-scope-render-check.py http://127.0.0.1:8799` (hub) | exit 0 — 390/1280 px, `offenders=[]` |
| `python3 -m unittest discover -s design-preview -p 'test_*.py'` (form) | **48 passed** — includes the deterministic rebuild of the derived B2 page |
| `python3 tools/4ws-offline-redirect-check.py http://127.0.0.1:8799` (form) | exit 0 — distributed 4Ws address still reaches the 5Ws form offline, query/hash intact |
| `python3 tools/text-setting-check.py` (form) | **pre-existing red** at base `9c3a41e` as well — `design-preview/translation-review-index.html` bundles `th, td` on `text-align:left`; untouched by this task |

Rendered evidence for the decision itself (served site): the 5Ws form opens in **Nepali**
(`data-lang=ne`) with the bilingual notice and the ENG/NEP switch; `/hub/`, `/hub/forms.html`,
`/hub/access.html` and the Layer 3 fixtures open in **English**; `?lang=en` on the 5Ws page still
gives English; after pressing ENG the preference survives navigation back to the form.

## 6. Base / head / production refs

* Hub base `8273e9013b163549640d04b2ec86fa42c840a91b`; head is the tip of branch
  `task/t_2449fe51-i18n-per-layer-default` (local only). The latest **code** commit on it is
  `e14b2f63e40e10284b3dc0aebcec469598e6ec80` (the round-2 feedback-channel work); the commits above
  it are evidence-note edits and change no code, so the tip is not written as a literal that would
  go stale the moment this note is edited.
* Form base `9c3a41eeccc768fcef5d8f241430ba831e8ad9a8` (the tip of `design/form-frontend`); head
  `e3abd1ae2a747bf718fcb5f81b94c3a73e5e4144`, the tip of branch
  `task/t_2449fe51-form-default` — a worktree of the **form repository**
  (`/root/mhpss-nepal-audit-20260918/form`) branched from that base, **not** a worktree of
  `design/form-frontend`. The code commits on it are
  `79e761c` (the declared Nepali default), `311eb91`/`b449a59` (`sw.js` bumps for the engine
  changes), `8836f6e` (the regenerated derived B2 page) and `e3abd1a` (untracking the
  gitignore-covered `design-preview/__pycache__` bytecode the rebuild had re-dirtied, so the diff
  carries no `.pyc` churn and a future test run cannot re-dirty it).
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
5. **A parent finding that the form half was "missing" — investigated, refuted, and the note made
   self-verifying.** The finding held that no worktree contains `data-i18n-default` and that §1
   therefore overstated the delivery. It is true that six of the seven form worktrees contain none,
   and true that the form half is not on `hub-real` — but the declaration *is* committed and clean
   on the seventh, `perlayer/form` (branch `task/t_2449fe51-form-default`, head `e3abd1a`, commit
   `79e761c`, blob `ba35ab92…`), which that scan did not include. `search_files` over
   `/root/mhpss-nepal-work` returns exactly three hits and this is one of them. **No form change was
   needed or made**; §1 now states the exact worktree, base, head, commit and blob, with the two
   commands to confirm them, so the claim is checkable rather than asserted. (A seventh, orphaned
   `verify-perlayer/form` directory also carries the line but is not a registered worktree — its
   `.git` points at a deleted gitdir — so it is scratch, not a deliverable.)
6. **The declaration is not merely present, it is enforced — proved by falsifying it.** To answer
   "the form half is missing" the same way the language default itself is answered (failing-first),
   the one attribute was removed from the working tree and the form suite re-run: it goes **red** —
   `test_form_pages_and_unrelated_pwa_runtime_keep_byte_parity` fails (the page then differs from
   `base + the one authorized substitution`) and `test_precache_fingerprint_matches_current_form_and_hub_assets`
   fails (`23f39a54… != 485967a7…`). The file was restored byte-exact from git (`sha256 c63f9c2c…`,
   `git status --porcelain -uall` empty) and the suite is green again — form `test_trial_scope`
   **8 passed**, `design-preview` **48 passed**. So the single line the operator was told to hand to
   the form lane is already committed there and guarded by two tests; deleting it cannot pass CI.

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
2. **`sw.js` cache v41 → v42 → v43 → v44.** The engine is precached, so an installed phone would
   otherwise keep the old engine: v42 was required so the form opens in Nepali, v43 so a phone does
   not keep the engine that lost unexported feedback and overflowed the picker, and v44 so it does
   not keep the engine that merged a placeholder complaint with a sentence complaint on one key.
   Every engine edit needs its own bump; `tools/precache.sha` is now `23f39a54…`.
3. **`form/index.html` was not edited** (requirement from the sibling task).
4. **The two inaccurate shared strings** flagged by the sibling task (`ml.p036`, `ml.p011`) are
   dictionary text and were **not** touched — this task does not change dictionary content.
5. **`design-preview/translation-review-index.html` fails `tools/text-setting-check.py`** in the
   form repo — pre-existing (reproduced with my changes stashed), in a file this task does not visit.
6. **The form repo's own report of this change is limited to `sw.js`/`tools/precache.sha`.** The
   durable engine lives in the hub repository (`hub-real`), which is what the form pages load at
   `../hub/assets/i18n.js`; no dictionary text was edited in either repository.
7. **A round-1 regression, found while re-verifying for round 2: the derived B2 preview page.**
   `5ws-report-b2.html` is *generated* from `5ws-report.html` by `design-preview/build_b2.py`, and
   the builder copies the source `<head>` verbatim. Round 1 declared the language default on the
   source page and did not regenerate the derived page, so
   `test_build_script_reproduces_the_committed_page` passed at base `9c3a41e` and **failed** at the
   round-1 head. It went unnoticed because round 1 ran the form's `test_trial_scope` and the hub
   suites but not `design-preview`. Fixed by **running the builder** (hand-editing is exactly what
   the builder exists to prevent): one line changes — the `<html>` tag gains the same
   `data-i18n-default="ne"` the source declares — so the B2 preview of the 5Ws form matches the form
   it previews. `design-preview`: 48 passed. The form-side changed-file list is therefore
   `5ws-report-b2.html`, `sw.js`, `tools/precache.sha` (plus `5ws-report.html` itself,
   `test_trial_scope.py`, `tools/precache-fingerprint.py`, and the untracking of the two
   `design-preview/__pycache__/*.pyc`).
8. **A stale site server can make a rendered check report the opposite of the truth — check the
   port before believing a rendered run.** This round, the rendered checks were first pointed at
   `127.0.0.1:8791`; that port was already held by a **seven-hour-old** `python3 -m http.server`
   from an earlier session serving a *different* checkout of the form (one that still carries a
   runtime-injected `ward` field). The new server silently failed to bind, so
   `5ws-still-works.py` read that other tree and failed with *"name= contract drifted; extra
   `['ward']`"*, while `hub-trial-scope-render-check.py` read a hub tree whose rail group had
   moved. Both were **false**: the committed trees are unaffected, and the `ward` field belongs to
   a separate Layer 1→2 task, not this one. Re-run on a fresh port (`8799`) that nothing else held,
   every rendered check is green again (24-name contract match, 9 selects). Recorded because a
   passing rendered suite is only evidence if it was run against the tree being claimed: `ss -ltnp`
   the port first, or serve on a port nobody else can already own.
