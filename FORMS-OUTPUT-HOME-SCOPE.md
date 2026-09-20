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
python3 -m unittest -v test_trial_scope.py          # 6 tests, 0 failures
python3 tools/rail.py                               # rail matches the generator
python3 tools/text-setting-check.py                 # 0
python3 tools/i18n-check.py                         # 0 (gate open)
python3 tools/contrast-check.py                     # 0

# rendered DOM, over the served workspace (both repos under one root):
python3 -m http.server 8791 --bind 127.0.0.1        # from a root with hub/ and form/
python3 tools/hub-trial-scope-render-check.py http://127.0.0.1:8791   # exit 0
```

The rendered check walks `/hub/`, `/hub/forms.html`, `/hub/access.html`,
`/hub/inbox.html` and `/hub/coverage.html` at 390 px and 1280 px and asserts the
rail group's hrefs are exactly `["./#reports", "forms.html", "../form/"]` and
that no rendered link resolves under `/form/` outside the approved two.

Failing-first: at base `ff2d4e2` the suite fails 3 of 6 (page link, rail group,
QR asset); at head it passes 6 of 6. Five adversarial probes (planted page link,
planted rail item, planted section hash, hand-edited rail block, restored
unapproved QR) each make the suite exit 1.
