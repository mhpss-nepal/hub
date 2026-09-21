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
| Coordination dashboard | `hub/` | `["activity"]` (`Q_KINDS`, `index.html:902`) | `tools/hub-live-read-scoping-check.py` |
| Per-form output homes | `hub/forms.html` | `["service_contact", "referral", "phq9", "self_report"]` (`LIVE_KINDS`, `forms.html:640`) | same guard, second surface |
| **The receiving surface added here** | `hub/field-output-home.html` | `["activity"]` | `tests/test_field_output_home.py` |

Two consequences, both of which were being carried silently:

* **Every one of the five instruments already has a working output home in Layer 2.** The
  supervised trial removed the *links* to the four unapproved instruments — rail items, page
  links, QR matrices — but it could not remove their homes, because `forms.html` must keep
  reading them for internal review. `FORMS-OUTPUT-HOME-SCOPE.md` says as much in its own closing
  section ("A static host still serves the four page files to anyone typing the exact URL"); the
  read half of that sentence was never written down. It is written down here.
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
form      : 5ws-report.html          report id (recordId)  R13ZH9PD
register  : submissions/activity_…   register doc id (FB.rid)
scheme    : 5ws-np-0.7.0             kind "activity"
values    : org CMC · site NUW-02 · palika NP0328301 · activity 1.1 · modality HC
            date 2026-09-21 · session 09:30 · attendance 3 · f04 3
stripped  : focalName, focalPhone, focalEmail  (fb.js NEVER_SENT — absent on read-back)
read at   : hub/field-output-home.html — kind-scoped read; queue drained to 0
```

**Negative control.** A synthetic record of a different kind is written into the same collection
and the page does not show it — the kind scope is a boundary, not decoration.

**Red is the point.** The suite fails if the read path breaks. Planted breakages that turn it red:

| planted defect | what must go red |
|---|---|
| the page asks for `kind == "activity"` but the form writes `activity` under another spelling | round trip finds no row |
| `watchKind` widened to `watch` (an unfiltered listen) | guard + browser test |
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
#    listening — they never pass green on nothing.
python3 -m unittest -v tests.test_field_output_home

# 3. the existing gates, unchanged
python3 tools/hub-live-read-scoping-check.py
python3 tools/hub-live-read-scoping-check.py --break     # self-test: the guard must go red
python3 tools/protected-strings-check.py
python3 tools/i18n-check.py
python3 tools/text-setting-check.py
python3 tools/contrast-check.py
python3 tools/rail.py
```

## 8. Known limitations

* **The emulator is a stand-in for the deployed register.** It is the same API and the same code
  path, but it is not the production Firestore and it does not apply the deployed security rules.
  What is proven here is the *client contract*, which is what this card is about. The rules' own
  behaviour is proven separately (`docs/OPERATIONAL-READINESS.md`, `test/store-data-path` family).
* **The proof runs locally, not on the deployed host,** so it is evidence about the code, not about
  production. This is deliberate: the card forbids any deployment beyond what is already live.
* **Two adjacent tasks on the hub tree leave before this one:**
  * `fix/store-backend-comment` (`326ffbb`) corrects the stale `assets/store.js` header, which
    currently claims the store has no backend while the same file implements `syncToRegister()`.
    `test_store_data_path_contract.py::test_header_describes_the_register_bridge_not_a_local_only_store`
    is red at the frozen head and green with that branch. Sharing the same file is what makes this
    a **merge-order** matter, not a defect in either change; the page here reads `store.js` and
    depends on neither wording.
  * `test_ward_field.py` is also red at the frozen head, for the same reason, on the same file
    (`assets/codes.js`), and is fixed by `task/t_e26d775b-ward-csv-patches`. Neither is touched by
    this change. They are named here so an independent reader is not surprised by a red suite that
    is not this card's.
