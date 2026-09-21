# The Layer 2 home: where the forms' output lands and is read

**Status: structure only. No visual design is proposed here and none is approved.**
The appearance of the Layer 2 home — layout, typography, colour, card style, navigation shape —
waits for Adib. This document, and the page it describes, add a **reader** and nothing else.

Decided by Adib, 21 September 2026:

> "tutup update form as of now, jgn ada penimpaan lagi dr agen lain, km upate agen hub, make sure
> 'rumahnya di layer 2 dia siapkan' tapi desain tampilannya nunggu konfirmasiku"

Three instructions: the field forms are closed; prepare the Layer 2 home; the visual design of that
home is not approved yet.

---

## 1. The frozen base

Every branch was cut from `origin/main` **fresh**, after `git fetch` — a branch cut before a hotfix
and merged after it has silently reverted protected strings three times on this project, which is
why `tools/protected-strings-check.py` exists.

| | repository | commit |
|---|---|---|
| Hub (Layer 2) — the branch point | `mhpss-nepal/hub` `main` | `dfe660af880b96e2dfc9141c41eacc0ae3ff2869` |
| Form (Layer 1) — untouched, read only | `mhpss-nepal/form` `main` | `e011e379639e70bcfa9d607c106629c783d366c2` |

The form repository is **not** a branch point for this change: not one file of it is read at
runtime, referenced, or edited. Its head is quoted because the proof in §4 drives the real field
form and the reader must be able to say which form it drove.

## 2. What already existed, measured rather than assumed

The receiving surface is **not** a new idea in this project. `forms.html` already declares itself
the output home — *"One page, one section per Layer 1 form: the form's OUTPUT HOME"* — and
`tools/rail.py` builds the "Field forms — outputs" rail group from the same phrase. What did not
exist was a statement, from the code, of **which records each home can actually read**. That is
recorded here for the first time.

Measured on the frozen hub tree:

| Surface | Route | Register kinds it asks the server for | Contract that pins it |
|---|---|---|---|
| Coordination dashboard | `hub/` | `["activity"]` (`Q_KINDS`, `index.html:902`) | `tools/hub-live-read-scoping-check.py` (static) + `-browser-check.py` |
| Per-form output homes | `hub/forms.html` | `["service_contact", "referral", "phq9", "self_report"]` (`LIVE_KINDS`, `forms.html:640`) | `tools/hub-live-read-scoping-browser-check.py` (the four kinds, as a subset of the requests) |
| **The receiving surface added here** | `hub/field-output-home.html` | `["activity"]` (`KINDS`) | `tools/hub-live-read-scoping-check.py` (added to `SURFACES` by this change) + `tests/test_field_output_home.py` |

The static guard in the third column checks the *scope* of each read (kind-scoped, never an unfiltered `watch()`), and for `forms.html` it only requires that whatever `LIVE_KINDS` declares is also requested. The four instrument kinds are pinned by the **browser** check, which asserts them as a subset of what the page actually asks the server for.

**This change strengthens that guard; it does not weaken it.** The new page reads the register, so it
was added to the guard's explicit `SURFACES` map (`{"declared": "KINDS"}`) and to the `--break`
self-test. Measured on this head: the guard passes, the self-test still goes red, and two planted
defects on the *new* page each turn it red —

| planted on `field-output-home.html` | guard output |
|---|---|
| read widened to a literal kind the page does not declare | `watchKind asks for ['referral'] but KINDS does not declare them` |
| read made unfiltered (`FB.watch`) | `an UNFILTERED register listen (.watch() with no kind) is present` |

Two consequences, both of which were being carried silently:

* **Every one of the five instruments already has a working output home in Layer 2.** The
  supervised trial removed the *links* to the four unapproved instruments — rail items, page
  links, QR matrices — but it could not remove their homes, because `forms.html` must keep
  reading them for internal review. `FORMS-OUTPUT-HOME-SCOPE.md` says as much in its own closing
  section ("A static host still serves the four page files to anyone typing the exact URL"); the
  read half of that sentence was never written down. It is written down here.

  **Qualified by measurement.** What *pins* those four homes is **not** `tools/hub-live-read-scoping-check.py`,
  which this document first claimed. Measured on a copy of the frozen tree: shrinking
  `forms.html`'s `LIVE_KINDS` from four kinds to two — the read half of a link removal — leaves that
  guard **green** (exit 0). The guard only fails when the `watchKind` call itself is deleted, or when
  a read is widened (`watchKind` asking for a kind `LIVE_KINDS` does not declare). So the guard pins
  *scope*, not the four kinds. The thing that pins the four kinds is
  `tools/hub-live-read-scoping-browser-check.py` — it loads `forms.html` with a stub `fb.js` and
  fails unless `{service_contact, referral, phq9, self_report}` is a **subset** of the kinds actually
  requested — plus `test_trial_scope.py`, whose `APPROVED_FORM_TARGETS` admits `/form`, the 5Ws page
  and `all-forms.html`, and whose comment records that `forms.html` keeps its read-only review
  tables. A hub-side "consolidation" that trimmed those four homes would be caught by the browser
  check and the trial-scope suite, not by the static guard.
* **The read is the boundary, not the filter.** Firestore evaluates a query against its whole
  potential result set: the rules are not filters. A page must therefore *ask for* exactly the
  kinds it renders. That is why `watchKind` exists and why the guard forbids `watch()`.

## 3. The receiving surface

`hub/field-output-home.html` — one page, no new design.

* **Addressable.** A real hub page at a real URL, not a snippet: `…/hub/field-output-home.html`.
* **Reads through the frozen files.** It loads `assets/fb.js` and `assets/store.js` exactly as the
  other hub pages do and reimplements neither. A pasted-in copy of either contract fails the test.
* **Asks for one kind.** `var KINDS = ["activity"]` — the instrument approved for the trial.
* **Never writes.** `FB.submit()` and `FB.publish()` are wrapped on this page: an attempt is
  counted and refused with a rejected promise, and the count is shown on the page.
* **Documents the shapes it expects.** The page carries a table of the contracts it depends on —
  `kind`, the schema stamp, `recordId()`, `FB.rid()`, `_rid`, the two device storage keys
  (`mhpss-np-4ws-v1`, `mhpss-np-queue-v1`), the `NEVER_SENT` list and the 85-column export
  allow-list — each with the frozen file that defines it and the point at which it is read.
* **Not in the navigation.** No hub page links to it and `tools/rail.py` does not offer it.
  Putting it in the rail is a visible change and is Adib's call (§6, question 1).

### What it deliberately is not

It is not a dashboard, it has no filters, no export, no charts, and it copies no styling that
could be mistaken for a design. It is the minimum surface that makes the read path testable, so
that the *plumbing* can be proven now while the *look* waits.

## 4. The read path, proven with a synthetic record

**The journey.** A synthetic 5Ws activity report is entered on the current frozen field form
(`form/5ws-report.html`); the form saves the device copy and hands the register copy to
`FB.submit()`, which stamps a `_rid` and queues it; the bridge retries with `setDoc` against the
deterministic document id until the register acknowledges and the queue drains; the receiving
surface asks the register for `kind == "activity"` and reads the row back.

**The transport.** The proof runs against a **local Firestore emulator** (`firebase emulators:start
--only firestore`), reached by proxying the page's Firestore traffic in the browser. Nothing in the
served tree is altered to make this possible: `assets/fb-config.js` keeps the project's own
`projectId` and `assets/fb.js` keeps the SDK URL and its `setDoc`/`watchKind` calls. Only the HTTP
hop is redirected — so what is exercised is **the real bridge against a real Firestore API
implementation**, not a stub of either. `tools/hub-live-read-scoping-browser-check.py` already
establishes the pattern of replacing the bridge; this goes one step further and replaces nothing.

**Synthetic values only**, and no person-level, clinical, contact or identifiable data. The one
field the model calls personal — the focal point — is a fixed placeholder and is stripped by
`NEVER_SENT` before the write, which the round trip reads back as absent:

```
form      : 5ws-report.html          report id (recordId)  R13GIWOU
register  : submissions/…            register doc id (FB.rid, starting with the record id)
scheme    : 5ws-np-0.7.0             kind "activity"
values    : org CMC · cadre HW · district NUW · site NUW-02 · activity 1.1
            modality HC · status ONG · date 2026-09-21 · session 09:30
            attendance 3 · f04 3
basis     : CMC||NUW-02|||2026-09-21|1.1|HC|09:30   (store.js recordId: FNV-1a over
            org, orgOther, site, siteOther, palika, dateAD, activity, modality, sessionTime)
stripped  : focalName, focalPhone, focalEmail  (fb.js NEVER_SENT — absent on read-back)
read at   : hub/field-output-home.html — kind-scoped read; queue drained to 0
```

The id is not transcribed: it is what `recordId()` returns for that exact basis, computed from the
frozen `assets/store.js` (the test asserts the row the page shows carries the id the form wrote, so
a drift in either the basis or the renderer turns the round trip red).

**Negative control.** A synthetic record of a different kind is written into the same collection
and the page does not show it — the kind scope is a boundary, not decoration.

**Red is the point.** The suite fails if the read path breaks. Planted breakages that turn it red:

| planted defect | what must go red |
|---|---|
| the page asks for `kind == "activity"` but the form writes `activity` under another spelling | round trip finds no row |
| `watchKind` widened to `watch` (an unfiltered listen) | guard (all three surfaces) + browser test |
| the page's read pointed at a literal kind `KINDS` does not declare | guard (the new page is in `SURFACES`) |
| the page's row renderer looks for a different id field | round trip can no longer show the record's id |
| the bridge's `_rid` basis changed | the deterministic vector changes |
| a second kind added to the page's `KINDS` | "asks for one kind" + negative control |

## 5. Contracts: unchanged, and checked

This change adds a reader and **changes no contract**. Specifically, all of the following are
exactly as they were at `dfe660a`, and the suite asserts that the page neither redefines nor
bypasses any of them: field `name`/`id`, the schema, the storage keys, `_rid`, event identity,
de-duplication, revision, the queue/retry/ack behaviour, the Firestore behaviour, the submit
handlers, and the success/error contracts.

No **Interface Change Request** is required, because preparing the home did not need one. If a
later step does — for instance if a coordinator wants the receiving surface to *write* a
reconciliation note — that is an interface change and must be filed as one, not made here.

## 6. Waiting for Adib

Nothing below is decided. **No visual-design change has been shipped**: the receiving page reuses
the hub's existing tokens and stylesheets and introduces no new layout, typography, colour, card
style or navigation shape. The design-preview work that proposes a homepage consolidation remains
in `design-preview/` on the `design/layer2-dashboard` branch, clearly labelled as a proposal
awaiting confirmation, and is not merged by this change.

The questions he is being asked:

1. **Does this become a fixed Layer 2 destination with its own address, and should it appear in the
   side rail?** Today it is reachable by URL only; adding it to the navigation is a visible change.
2. **One home or two?** The activity report already has a home inside the dashboard ("Reports
   received"). Should the register read-through live there, here, or both?
3. **Should the four unapproved instruments' output homes be visible during the trial,** or stay
   reachable-but-unlisted as they are now?
4. **What should a coordinator see first?** The five existing dashboard sections are unchanged; if
   the home is to be reorganised, its shape is his decision.
5. **Typography, colour, cards and layout** — not proposed here, deliberately. No look ships until
   he confirms one.

## 7. How to reproduce

```bash
# 1. the local register (a real Firestore API implementation; no account, no cloud project)
firebase emulators:start --only firestore --project mhpss-nepal-hub   # listens on 127.0.0.1:8081

# 2. the suite. The round-trip and negative-control bodies SKIP when no emulator is
#    listening — they never pass green on nothing. 26 tests, OK, ~193 s.
python3 -m unittest discover -s tests -p 'test_*.py' -v

#    …and the whole-suite form, which is where the four pre-existing reds (§8) appear.
python3 -m unittest discover -p 'test_*.py'

# 3. the existing gates, unchanged
python3 tools/hub-live-read-scoping-check.py
python3 tools/hub-live-read-scoping-check.py --break     # self-test: the guard must go red
python3 tools/protected-strings-check.py
python3 tools/i18n-check.py
python3 tools/text-setting-check.py
python3 tools/contrast-check.py
python3 tools/rail.py
```

### Measured on this head (all exit 0)

| command | result |
|---|---|
| `python3 -m unittest discover -s tests -p 'test_*.py'` | **Ran 26 tests … OK** (~193 s), incl. the emulator round trip |
| `python3 tools/hub-live-read-scoping-check.py` | `PASS (every register read is kind-scoped)` |
| `python3 tools/hub-live-read-scoping-check.py --break` | `SELF-TEST OK: the guard went red exactly as it must.` |
| `python3 tools/protected-strings-check.py` | `OK` — 19 protected keys in `en`, 0 carrying Nepali |
| `python3 tools/i18n-check.py` | `Gate open` — the new page is listed under "NOT YET MIGRATED" (929 words), the same class as `index.html`/`forms.html`; the gate is not weakened |
| `python3 tools/text-setting-check.py` | `True: running text is set justified…` |
| `python3 tools/contrast-check.py` | `True: every declared token clears AA…` (25 pairs) |
| `python3 tools/rail.py` | `True: every page's rail is the one written in tools/rail.py` |

### The suite bites when the read path breaks (mutation check)

A copy of this tree with one character changed — the page's `KINDS` set from `["activity"]` to
`["referral"]`, i.e. the read pointed at a kind the form does not write — turns **three** tests red:

```
FAIL test_round_trip_a_record_written_by_the_current_form_is_read_on_layer_two
     AssertionError: 'read succeeded' != 'refused: no answer from the register within 20s'
FAIL test_the_page_asks_for_one_kind_and_never_writes
     AssertionError: Lists differ: ['activity'] != ['referral']
FAIL test_it_asks_for_exactly_one_kind_and_it_is_the_trial_instrument
     AssertionError: 'var KINDS = ["activity"];' not found
Ran 11 tests … FAILED (failures=3)
```

So the round trip is a real read, not a tautology: point it at the wrong kind and it goes red.

### Re-measured live site (cache-busted, read-only fetch)

Measured **before** the merge that landed this change, and again **after** it, from the live host:

| what | before | after |
|---|---|---|
| `https://mhpss-nepal.github.io/hub/field-output-home.html` | **404** | **200**, 18 121 B, `sha256 7fd5d52b145c496636e5d5aa91191cedd00de0d3bf4106be356e47f29ce661dc` |
| `.../hub/index.html` | 200, `sha256 5493ce92…` | unchanged, same digest |
| `.../hub/forms.html` | 200, `sha256 2a299d18…` | unchanged, same digest |
| `.../hub/assets/i18n-strings.js` | 200, 314 445 B | unchanged, same size |
| live `LIVE_KINDS` / `Q_KINDS` | four instruments / `activity` | unchanged |

So the recent work the card protects (validated Nepali PHQ-9, skip link, MoFAGA 753 palikas) is
untouched on the live host, and the only live difference is the one added page.

**The live page, rendered in a fresh headless browser** (`locale=en-US`, no session, no account):

| measurement | value |
|---|---|
| page errors on load | **0** |
| `#kinds` / `#rOther` / `#rWrite` before the read | `activity` / `—` / `0` |
| bridge | `assets/fb.js loaded; ready` |
| `#colCount` (read from the frozen `CSV_COLUMNS`) | `85` |
| any rail link to the page | **none** |
| after pressing "Read the register now" | `Outcome: read succeeded` · `Rows: 312` · `Other kinds asked for: none` · `Writes attempted: 0` |

The 312 is the same figure, the same kind and the same deliberate window that the live dashboard
already shows — `index.html` renders *"Open demonstration window — activity reports only, readable
without an account until 30 September 2026 · 312 activity report(s)"*. This page adds a **second
reader of the same kind**, not a new data class, and it asks for no kind the dashboard does not
already ask for.

**The preview link:** <https://mhpss-nepal.github.io/hub/field-output-home.html> — reachable by URL
only; no hub page links to it and `tools/rail.py` does not offer it, because adding it to the
navigation is a visible change and that is Adib's call (§6, question 1).

## 8. Known limitations

* **The emulator is a stand-in for the deployed register.** It is the same API and the same code
  path, but it is not the production Firestore and it does not apply the deployed security rules.
  What is proven here is the *client contract*, which is what this card is about. The rules' own
  behaviour is proven separately (`docs/OPERATIONAL-READINESS.md`, `test/store-data-path` family).
* **The proof runs locally, not on the deployed host,** so it is evidence about the code, not about
  production. This is deliberate: the card forbids any deployment beyond what is already live.
* **Four tests are already red at the frozen hub head, and none of them is this card's.** Measured
  twice: on the frozen commit itself (`git worktree add --detach /tmp/basehub-dfe660a dfe660a`) and on
  this branch, `python3 -m unittest discover -p 'test_*.py'` from the repository root reports the
  **same four** failures — `test_store_data_path_contract` ×1 and `test_ward_field` ×3 — and the same
  single skip. This branch adds no failure and removes none.

  Two earlier explanations for them were wrong and are corrected here:

  * **`assets/store.js`'s header is a silent revert, not an unmerged branch.** An earlier draft of
    this document said `fix/store-backend-comment` (`326ffbb`) was "ahead of `main` and unmerged".
    That is false: `326ffbb` **is** merged (`e231549`, hub#3) and **is** an ancestor of `origin/main`.
    It was then silently undone — `e479582` (hub#14, the Ministry age bands, merged as `dab6329`)
    carries the header **back** to the stale "Deliberately has NO backend" text, even though its own
    parent `e34018c` already contained the fix. So the same failure mode the card names for protected
    strings ("a branch cut before a hotfix and merged after it has silently reverted…") has now
    happened a fourth time, on a **comment**, and the guard that would have caught it
    (`test_store_data_path_contract.py`) is red on `main` because of it. Merging that branch again
    would do nothing; the header has to be re-applied. It is **not** this card's file — `assets/store.js`
    is a shared hotspot — so it is reported, not repaired here.
  * **`test_ward_field.py` is stale relative to the validated Nepali PHQ-9.** Two of its three
    failures are its own `PROTECTED_PREFIXES` copy of the no-Nepali rule, which still lists
    `phq9.item`/`phq9.scale`; hub#21 deliberately shipped the validated Nepali for exactly those keys
    and updated `tools/protected-strings-check.py` (`ALLOW_NEPALI`) — but did **not** update this test.
    The third failure is `test_every_palika_still_carries_a_ward_count`, which expects `wards:` on every
    palika entry; hub#19 replaced the 20 OCHA pcodes with the official 753-palika MoFAGA list, whose
    entries carry no ward count. Both are real regressions at the frozen head, both belong to the lanes
    that made them, and neither is touched by this change.

  Filed as a follow-up card rather than fixed here (this card adds a reader; it repairs nothing else).
