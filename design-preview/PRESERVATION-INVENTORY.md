# Layer 2 homepage — preservation inventory

**Base commit:** `42f308c` · **Method:** `design-preview/diagnose.py` (source
facts) and `design-preview/build_preview.py` (what the concepts must therefore
carry). The concepts are **presentation artifacts**: they change no runtime file,
so the primary claim of this document is that nothing in the Hub's runtime
surface is touched or forked. Where a concept *reuses* a surface, it links to the
existing destination rather than reimplementing it.

## 1. Contract preservation — the claim, stated precisely

| Contract | Status in the concepts |
|---|---|
| DOM/runtime contracts of `index.html` | **Untouched.** No concept is `index.html`; each is a new file under `design-preview/`. |
| `assets/fb.js` (bridge) | **Not loaded, not modified.** Its 21 globals stay the only read/write path. |
| `assets/store.js` (record shape, ids, CSV) | **Not loaded, not modified.** |
| `assets/codes.js` (P-codes, activity/IASC maps) | **Not loaded, not modified.** |
| Role/access semantics (`admin`, `coordinator`, `im_officer`, `viewer`, + the blocked GBV role) | **Unchanged, not exercised.** No concept signs in, reads a role document, or renders a role-gated control as enabled. |
| Selectors and element ids in the app | **Unchanged.** The concepts use their own ids in their own files (builder asserts no duplicate ids). |
| Navigation destinations | **All preserved and linked**: `#overview`, `#who-is-where`, `#activities`, `#reports`, `#publish`, `forms.html`, `access.html`, `../form/`. |
| Data collectors (the forms) | **Untouched.** No concept collects a record. |
| Publication hooks (`FB.publish`, `public_stats`, `basis`, `computed_at`, 40-field cap) | **Untouched.** The publication block is a link and an inert dialog; there is no write path in any concept. |
| Bilingual keys (`i18n-strings.js`, `i18n.js`, `mark.js`) | **Untouched.** The concepts are English-only exploration artifacts and deliberately do **not** fork the key set; see §5. |
| Small-cell safeguard (below-floor redaction) | **Not weakened.** Exploration fixture floor is 5; the production floor is **not** changed (see `topology.json → small_cell_floor_source: 10`). |
| Export allow-list (`CSV_COLUMNS`, 71 columns, includes `ward`) | **Untouched and not exposed.** No concept offers an export control that reaches the Hub's exporter. |

## 2. Runtime surfaces the current page owns (must keep working)

From `topology.json`:

- **Source selection**: `useLive`, `useLocal`, `useDemo`, `file`, `file2` — the
  four ways a coordinator points the dashboard at a source. *Not present in the
  concepts* because a concept reads its own synthetic fixture; the current Hub
  remains the only page that connects to the register.
- **Cascading filters**: `fProv fDist fPal fOrg fDon fGrp fAct fMod fSta`
  selected from the values that survive the other eight, plus `fPeriod`,
  `fBasis`, `fFrom`, `fTo`, `fClear`. *Modelled, not replaced* — see §4.
- **CSV exports**: `expGap`, `expMx`, `expAll`. *Deliberately absent* from every
  concept, and listed as a safeguard in §6.
- **Publication**: `pubBasis`, `pubFlood`, `pubDir`, `pubFull`, `pubPreview`,
  `pubGo`. *Present as a disabled/preview-only affordance*, never as a call.
- **Role administration**: `access.html` — linked from every concept.
- **Per-form homes**: `forms.html` — linked from every concept.
- **The field inbox path**: `inbox.html` → `forms.html` — untouched.
- **Compatibility shims**: `coverage.html`, `inbox.html` — untouched.
- **Twelve legacy hash aliases** (`#gaps #duplication #matrix #activity #records
  #publish #coverage #who #what #when #people #helpline`) — the concepts
  namespace their own filter fragment as `#flt=…` precisely so this alias space
  is never collided with.

## 3. The concepts' own contracts (built and asserted)

`build_preview.py` refuses to write a bad page: it re-reads each written file and
asserts

- **no duplicate element ids** anywhere in the document;
- **no forbidden runtime API** — `firebase`, `firestore`, `localStorage`,
  `sessionStorage`, `fetch(`, `XMLHttpRequest`, `indexedDB` are scanned for and
  their absence asserted;
- **every referenced runtime asset exists** (`preview.css?h=…`, `preview.js?h=…`);
- **the output is deterministic** — the builder runs twice and the two SHA-256
  sets must match.

Asset URLs are hashed by content (`?h=<sha256[:10]>`), never by a hand-bumped
version number, so a stale stylesheet cannot masquerade as a CSS bug.

## 4. What the redesign replaces conceptually, and what it must therefore carry

The current Hub's nine-dimension cascading filter is why its filter panel reads
as a form. The concepts keep the *capability* and change the *presentation*:

| Current control | Concept equivalent | Evidence |
|---|---|---|
| province / district / palika | District, Palika, Ward selects | 375px filter probe |
| org / donor | Organisation select | same |
| group / activity | Activity, IASC layer selects | same |
| modality / status | Modality, Status selects | same |
| — | **Target group** select (new to the homepage) | same |
| — | **Data-quality state** select (new; the Layer 2 record's item 6) | same |
| period + basis + from/to | Reporting period select | same |
| free-text search | `#filterSearch` across org, site, activity, palika | forced-empty probe |
| nine controls, always expanded | one bar, collapsed on a phone, chips for each active filter | sheet probe |

**Dimensions are exposed only when the data supports them**: a list with fewer
than two distinct values is not rendered at all, so no concept offers a control
that cannot slice. The cascading rule is preserved in the same direction (a
list offers only values that survive the *other* filters).

## 5. Bilingual keys

The Hub is a bilingual surface: `index.html` declares `lang="en"` and the i18n
engine carries an `ne` dictionary; the per-page default for the Hub is English
and for the forms is Nepali (decision of 20 Sep 2026, `PER-LAYER-DEFAULT-EVIDENCE.md`).

The concepts are **English-only review artifacts** and do **not** fork the key
dictionary. That is deliberate: adding keys for a design that may be discarded
would create a second place where page text lives, which is exactly the failure
mode the i18n workstream exists to prevent. **If a concept is adopted, its text
must be keyed into `assets/i18n-strings.js` and the Nepali column filled before it
ships** — recorded here as a condition of adoption, not as a gap in exploration.

## 6. Safeguards that must not be weakened (explicitly out of scope)

Recorded so a reviewer can check that exploration did not relax them:

- **No GBV / child-protection case view** in any concept.
- **No referral-status expansion** in any concept.
- **No export surface** in any concept: a single export button would defeat every
  display-side restriction (the Layer 2 access record's item 9).
- **No publication path**: the public shelf is described, never written, and the
  dialog that opens says so in the first sentence.
- **Small cells**: the fixture prints "fewer than 5" and never prints a figure
  below the floor; no concept prints a place smaller than a palika.
- **Non-additivity**: attendances are labelled "not unique people — never added
  to people"; activity/layer/target-group rows are labelled non-additive; no
  concept prints a coverage *ratio* it cannot support.
- **No invented denominator**: the only denominator on any concept is the roster,
  named as the roster, with a visible statement that its own validity is an open
  question.
- **Search and filtering do not cross a role boundary**: the concepts filter a
  synthetic in-page fixture, so no query reaches a server and no restricted field
  is fetched, filtered, revealed or exported.

## 7. Files written

Everything is inside `design-preview/`; `git status --porcelain` outside it is
clean.

```
design-preview/
├── index.html                  landing / concept chooser
├── concept-conservative.html   A
├── concept-recommended.html    B
├── concept-divergent.html      C
├── preview.css  preview.js     shared, hashed-by-content assets
├── build_preview.py            deterministic builder (refuses a bad page)
├── diagnose.py                 reads the base commit → topology.json
├── qa_preview.py               browser QA → qa-results.json
├── qa_read.py                  human-readable QA dump
├── write_qa_report.py          generates QA-REPORT.md from the measurements
├── serve_preview.py            tailnet server + link verification
├── contract-inventory.json     preserved contracts, machine-readable
├── topology.json               source facts, machine-readable
├── qa-results.json  qa-run.log  serve-report.json  screens/
├── vendor/axe.min.js  vendor/axe-LICENSE.txt
└── REDUNDANCY-INVENTORY.md  PRESERVATION-INVENTORY.md  QA-REPORT.md
```
