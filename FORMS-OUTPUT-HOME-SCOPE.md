# Hub-side trial scope: which form pages the Hub may open

Status: the supervised trial exposes **exactly one** instrument.

| Approved for the field trial | Where |
| --- | --- |
| Activity report (5Ws) | `../form/5ws-report.html` |

The four other Layer-1 instruments — service contact, referral, PHQ-9 follow-up
and self-report — are **unapproved**. They exist as pages in the sibling `form`
repository and remain there for internal review, but no Hub navigation or link
may open one of them while the trial runs.

## What changed, and why

The trial-scope task `t_ceda8e3b` removed every path to the four unapproved
instruments from the field build. The Hub still advertised them:

- `forms.html` linked `../form/{contact,referral,phq9,selfreport}.html`
  ("Open the form →").
- `index.html` and `access.html` named Service contact, Referral, PHQ-9
  follow-up and Self-report, pointing at `forms.html#contact|#referral|#phq9|#selfreport`.

These are coordination surfaces rather than the field QR set, but they are
reachable by typing the Hub URL, so the exposure needed an explicit decision.
The Hub chose **remove for the trial**, keeping the one approved link.

- `tools/rail.py` — the four named rail items are gone; the "Field forms" group
  now holds the approved 5Ws link, a neutral **Form entries** link to the Hub's
  own `forms.html`, and one "Open the forms →" link.
- `forms.html` — the four "Open the form →" buttons are gone; each section keeps
  its import, its export and its read-only review tables. A trial note above the
  tabs states the scope.
- `inbox.html` — no longer names the four instruments and no longer defaults to
  `#contact`; it forwards to `forms.html` with no hash.
- `assets/qr.js` — the printable QR asset kept matrices for `contact`, `phq9`,
  `referral` and `self`, each encoding the absolute address of an unapproved
  page **inside the bit matrix**. They are removed. A QR is a physical path:
  once printed, its address is in the worker's hand and cannot be revoked in
  code. The two surviving entries, `master` and `5ws`, are byte-identical to the
  entries that were there before.

## What the Hub may still do

The Hub is a **review and import surface**, not a launcher. `forms.html` still
describes all four instruments, reads imported files for them, computes their
counts and flags, and exports their rows as CSV. That is deliberate and is
pinned by `test_hub_still_describes_and_imports_the_four_forms`.

`test_trial_scope.py` therefore enforces two rules, not one:

1. No default Hub navigation or link resolves to an unapproved form **page**
   (`../form/<name>.html`).
2. No Hub link is **named** for an unapproved instrument either
   (`forms.html#phq9` is as much a named path as `../form/phq9.html`).

`forms.html` itself is reachable as a neutral *Form entries* link; it opens a Hub
page, not an instrument.

## Not a permanent block

A static host still serves the four page files to anyone typing the exact URL.
That is a property of GitHub Pages and is recorded in the field build's
`TRIAL-SCOPE-EVIDENCE.md`; closing it needs a host rule or a service-worker
deny-list, which belongs to a deliberate decision, not to this task.

When an instrument is approved, restore it here: add its rail item back in
`tools/rail.py`, run `python3 tools/rail.py apply`, restore its
"Open the form →" button in `forms.html`, and add its QR matrix back to
`assets/qr.js` with `tools/qr-build.py` in the `form` repository. The test's
allowlists are the one place that has to change with it.

## Verification

```
python3 -m unittest -v test_trial_scope.py          # 8 tests, 0 failures
python3 tools/rail.py                               # rail matches the generator
python3 tools/text-setting-check.py                 # 0
python3 tools/i18n-check.py                         # 0 (gate open)
python3 tools/contrast-check.py                     # 0

# rendered DOM, over the served workspace (both repos under one root):
python3 -m http.server 8791 --bind 127.0.0.1        # from a root with hub/ and form/
python3 tools/hub-trial-scope-render-check.py http://127.0.0.1:8791   # exit 0

# adversarial: plants an unapproved rendered link and proves the checker
# exits non-zero against it (exit 0 here means the checker caught it):
python3 tools/render-check-adversarial-probe.py                        # exit 0

# red/green of the round-1 fix: the classifier test is red against the
# pre-fix checker (15d35b3) and green now; the probe is blind against the
# pre-fix checker and catches the planted link now:
python3 tools/round1-red-green-demo.py                                 # exit 0
```

The rendered check walks `/hub/`, `/hub/forms.html`, `/hub/access.html`,
`/hub/inbox.html` and `/hub/coverage.html` at 390 px and 1280 px and asserts the
rail group's hrefs are exactly `["./#reports", "forms.html", "../form/"]`, and
that no rendered link, once resolved to a URL and normalized, lands under
`/form/` outside the two approved form paths (`/form` and
`/form/5ws-report.html`). The rail group has three links: the 5Ws output, the
neutral Hub `forms.html` entries page, and the form landing page. Comparison is
exact equality on the normalized path, never a substring test, so
`../form//contact.html`, `../form/./phq9.html`, `../form/sub/../referral.html`,
`%2f`-encoded and backslash spellings, protocol-relative URLs and a `/FORM/`
case variant are all rejected (see the classifier table in
`test_rendered_link_check_uses_exact_normalized_form_paths`).

Failing-first: at base `ff2d4e2` the new suite fails 5 of 8 (page link, rail
group, rail generator, QR asset, and the absent pre-fix fixture); at head it
passes 8 of 8. The round-1 rendered-classifier defect is a property of the
checker, not the tree: the classifier test is **red** against the pre-fix
checker (`15d35b3`, kept verbatim at `tools/fixtures/render-check-prefix-15d35b3.py`
and pinned by SHA-256 in the suite) and **green** against the fixed one, and the
served-DOM probe `tools/render-check-adversarial-probe.py` plants
`../form/contact.html` into the rendered `forms.html` and proves the checker
exits non-zero -- against the pre-fix checker the same probe is accepted and
prints "checker is blind". `tools/round1-red-green-demo.py` runs both checks
against both checkers in one command and passes only when the change is
genuinely red-then-green, not green-only. Five static adversarial probes
(planted page link, planted rail item, planted section hash, hand-edited rail
block, restored unapproved QR) each make the suite exit 1.

## Worktree and the two unrelated files

The required clean worktree is met. Two untracked files that appeared during
the first attempt, `tools/i18n_apply.py` and `tools/terminology_lock.py`,
belong to the concurrent i18n lane and have been **relocated** -- not deleted,
not committed -- to `/root/mhpss-nepal-work/recovered/t_46e4cb25-collision/`
with their mtimes and SHA-256 preserved. They are recoverable in one move, and
the sibling `hub-translation` worktree keeps its own live copies. Nothing in
this change ever referenced them.
