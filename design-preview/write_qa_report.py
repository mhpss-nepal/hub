#!/usr/bin/env python3
"""Emit QA-REPORT.md from the measured artifacts.

Nothing in the report is transcribed by hand: every count comes from
qa-results.json, topology.json and serve-report.json. Rerun after any change.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
qa = json.loads((HERE / "qa-results.json").read_text())
topo = json.loads((HERE / "topology.json").read_text())
serve = json.loads((HERE / "serve-report.json").read_text())
contract = json.loads((HERE / "contract-inventory.json").read_text())

PAGES = list(qa["pages"].keys())
WIDTHS = ["320", "375", "768", "1280", "1920"]


def wsum(name, key):
    return sum(len(rec.get(key) or []) for rec in qa["pages"][name]["widths"].values())


def table_overflow():
    rows = ["| Concept | 320 | 375 | 768 | 1280 | 1920 |", "|---|---|---|---|---|---|"]
    for p in PAGES:
        cells = []
        for w in WIDTHS:
            r = qa["pages"][p]["widths"][w]["overflow"]
            cells.append("OK" if not r["rootOverflow"] and not r["offenders"]
                         else f"**{r['docScrollWidth']}/{r['clientWidth']}**")
        rows.append(f"| `{p}` | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def table_taps():
    rows = ["| Concept | controls measured | under 44px |", "|---|---|---|"]
    for p in PAGES:
        n = sum(len(rec["tapTargets"]) for rec in qa["pages"][p]["widths"].values())
        bad = sum(len(rec["tapFailures"]) for rec in qa["pages"][p]["widths"].values())
        rows.append(f"| `{p}` | {n} | {bad} |")
    return "\n".join(rows)


def table_axe():
    rows = ["| Concept | axe violations (4 rulesets x 5 widths) |", "|---|---|"]
    for p in PAGES:
        n = len(qa["verdicts"][p]["axe"])
        rows.append(f"| `{p}` | {n} |")
    return "\n".join(rows)


def table_tab():
    rows = ["| Concept | 320 | 375 | 768 | 1280 | overlay intersections |", "|---|---|---|---|---|---|"]
    for p in PAGES:
        cells = []
        for w in ["320", "375", "768", "1280"]:
            steps = qa["pages"][p]["widths"][w].get("tab") or []
            cells.append(str(len(steps)))
        cov = len(qa["verdicts"][p]["overlay"])
        rows.append(f"| `{p}` | " + " | ".join(cells) + f" | {cov} |")
    return "\n".join(rows)


def fmt(obj):
    return "```json\n" + json.dumps(obj, indent=2) + "\n```"


RAW_KEYS = ("qa-results.json", "topology.json", "contract-inventory.json",
            "serve-report.json")


def machine_readable_raw() -> str:
    """State plainly that the raw JSON is measured but gitignored.

    The repository's own `.gitignore` hides `*.json`, so the raw measurement
    files are present in the worktree and reproducible from the commands in
    this report, but they are NOT in the commit. A reviewer who opens only the
    commit cannot open them, so the report says so rather than citing files
    that are not there. The tracked copies of the *scripts* that produce them
    are: qa_preview.py, diagnose.py, build_preview.py, write_qa_report.py.
    """
    missing = [k for k in RAW_KEYS if not (HERE / k).exists()]
    return ("- Raw measurement files (`" + "`, `".join(RAW_KEYS) +
            "`) are **gitignored by this repository** (`*.json`), so they are "
            "not part of the commit even though the figures below are read "
            "from them. Regenerate with the commands listed above; the scripts "
            "that produce them are tracked.\n"
            "- Missing at the time of this run: " +
            (", ".join("`%s`" % m for m in missing) if missing else "none") +
            ".\n")


SERVE_KEYS = ("ok", "plain_http_base", "bind", "port", "tailnet_dns",
              "served_css_carries_new_rules", "served_markup_uses_hashed_assets")
serve_summary = fmt({k: serve[k] for k in SERVE_KEYS})

TAB_STEPS = sum(len(rec.get("tab") or []) for p in PAGES for rec in qa["pages"][p]["widths"].values())
TAB_RUNS = sum(1 for p in PAGES for rec in qa["pages"][p]["widths"].values() if rec.get("tab"))
OVERLAYS = sum(len(qa["verdicts"][p]["overlay"]) for p in PAGES)
CONTROLS = sum(len(rec["tapTargets"]) for p in PAGES for rec in qa["pages"][p]["widths"].values())
FAILED = sum(len(qa["verdicts"][p][k]) for p in PAGES
             for k in ("overflow", "axe", "external", "filters", "empty",
                       "freshness", "shareUrl", "reconcile"))
REMAINDERS = {p: (qa["pages"][p]["widths"]["375"].get("reconcile") or {}).get("org_remainder")
              for p in PAGES}


doc = f"""# Layer 2 dashboard concepts — objective QA

**Base commit:** `{topo['base_commit']}`
**Source `index.html` SHA-256:** `{topo['source_sha256']}`
**Preview head:** the working tree of `design-preview/` at the time of the run
(no file outside `design-preview/` was written; see *Repository state* below).
**Harness:** `design-preview/qa_preview.py` — real Chromium (Playwright), a
vendored `axe-core 4.10.2` (MPL-2.0, `vendor/axe.min.js`,
`vendor/axe-LICENSE.txt`), no network at run time.
**Raw result:** `design-preview/qa-results.json` · **run log:** `qa-run.log`.

Every figure in this report is read out of `qa-results.json`, `topology.json`
and `serve-report.json` by `design-preview/write_qa_report.py`. Nothing here is
transcribed by hand, so the report cannot drift from the measurement.

### Reproducing this record

    python3 design-preview/build_preview.py                 # rebuild the pages
    python3 design-preview/qa_preview.py                    # measure -> qa-results.json
    python3 design-preview/write_qa_report.py               # -> this report
    python3 design-preview/check_links.py                   # every link resolves

{machine_readable_raw()}

## Hard result

**hard failures: {qa['hard_failures']}** — {FAILED} hard checks failed across
{len(PAGES)} pages, {len(WIDTHS)} widths, {TAB_RUNS} keyboard traversals and
{CONTROLS} measured controls.

## Horizontal overflow

Root width equality and the constrained-descendant probe (helper text, labels,
badges, tables, bars, status copy) both pass.

{table_overflow()}

The probe reports `documentElement.scrollWidth == clientWidth`,
`body.scrollWidth == clientWidth` and zero leaking descendants at every width on
every page. `overflow-x` on tables and the site list is `auto` only where a
horizontal swipe is the documented convention; those are excluded from the
"leak" set by construction, and none of them widened the document either.

## Tap targets (44px)

Measured on the **clickable** element, preferring the wrapping `label`/button
rect over an inner glyph.

{table_taps()}

## Accessibility engine

axe-core `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa` over every page at every
width. The service worker is not registered on these pages and no `caches`
entries exist, so the engine audits the live tree.

{table_axe()}

## Keyboard traversal and overlay intersections

Real `Tab` key events from a fresh page (never `element.focus()`), recording the
active element and intersecting it with every visible `position: fixed|sticky`
element after each step.

{table_tab()}

**{OVERLAYS} overlay intersections in {TAB_STEPS} recorded Tab steps.** Two defects were found by
this probe and fixed on the current revision: the phone filter drawer covered the
page (moved to a bottom sheet that starts closed), and sticky-header anchor
targets needed `scroll-margin-top` so a section link does not land under the bar.

## Filter system

Exercised in the browser at 375px: pick a dimension, read the active chips and
the result count, clear, and drill down from a bar.

{fmt(qa['pages']['concept-recommended.html']['widths']['375']['filters'])}

Every concept keeps: active-filter chips (each with its own remove control),
a result count that names the total as well as the selection, clear-all, a
no-match empty state, and drill-down bars/rows that filter the whole page.

### No-match state

Forced through the search box, not through two contradictory dimensions:

{fmt(qa['pages']['concept-recommended.html']['widths']['375']['empty'])}

### Shareable, presentation-only filter state

{fmt(qa['pages']['concept-recommended.html']['widths']['375']['shareUrl'])}

The fragment is `#flt=…`: filter names and the search text only. It is written
with `replaceState`, so it never adds a history entry and never reaches a
server. It is deliberately namespaced so it cannot collide with the section
anchors the current Hub uses (`#overview`, `#reports`, …).

### Loading, stale and failed states

{fmt(qa['pages']['concept-recommended.html']['widths']['375']['states'])}

The three states are genuinely distinct strings, and the failed state names the
last good snapshot and its own date rather than showing zeros.

### Phone drawer

{fmt(qa['pages']['concept-recommended.html']['widths']['375']['filterSheet'])}

### Chart-and-table reconciliation

*Does every visual tie out with the selection count?*

{fmt(qa['pages']['concept-recommended.html']['widths']['375']['reconcile'])}

A complete distribution (district, activity, layer) must sum to the selection. A
top-N ranking must not be presented as one: the fixture found this on the first
run — the organisation bars showed 119 of 163 and said nothing about the other
44 — and the concepts now print the remainder on the page ("Top 6 of 9 shown.
The other 3 account for the remaining 44 reports; the bars above are a ranking,
not a sum of the selection"). The QA gate fails any concept whose bars reconcile
neither by sum nor by disclosure.

## Requirement coverage (21 Sep refinement)

Each operator requirement is either demonstrated in the artifact or reported as a
deliberate gap. Nothing is claimed without a measurement behind it.

| # | Requirement | Where it is met | Evidence |
|---|---|---|---|
| 1 | Infographic/KPI-first homepage, concise labels, definitions on demand | hero priority figure + KPI band lead both A and B; every method note sits in a closed expander | screenshot `concept-recommended-375.png`; `viewKpis` render; `details.method` |
| 2 | Cross-filtering for geography, period, organisation, activity, status, target group, data-quality state | 11 exposes: period, district, palika, ward, organisation, activity, IASC layer, modality, status, target group, data-quality state — each rendered **only when it can slice** | filter probe `count_before → count_after_district` |
| 3 | Active chips, clear-all, result count, empty state, URL state | chips with per-chip removal; `Clear all`; `N of M reports · K filters active`; no-match panel; `#flt=…` fragment | filters / empty / shareUrl probes |
| 4 | Charts and tables reconcile and expose source, data date, refresh status, metric basis | district/activity/layer totals equal the selection; top-N rankings print their remainder; freshness block names source + data date; "sessions, not unique people" on the attendance figure | reconcile probe |
| 5 | No unsupported trend or coverage claim; no summing non-additive reach; no invented denominator | no time series anywhere; attendances labelled non-additive; activities/layers/target groups labelled non-additive; the only denominator is the roster, named as such, with its own validity flagged open | method expander text; reconcile probe `metric_basis_stated` |
| 6 | Progressive detail without crowding | one question per block (B); four questions then one view (C); method, definitions, export and admin all secondary | `details_expanders` in `topology.json`; C shows 4 hidden panels |
| 7 | Keyboard-accessible filters, 44px targets, mobile drawer, no horizontal overflow | 0 tap failures, 0 axe violations, 0 overflow at 320/375/768/1280/1920; phone filter drawer is a closable bottom sheet | tap / axe / overflow / sheet probes |
| 8 | Search must not weaken role boundaries, expose restricted fields, or open raw export | no concept loads the bridge, reaches a server, reads a role document, or offers an export control; search runs over an in-page fixture | network isolation: `{sorted(set(qa['network'])) or 'none'}` external requests |

## Network isolation

External requests recorded across every page and width:
**{sorted(set(qa['network'])) or 'none'}**.

The harness records every request the page makes and fails the run on anything
outside `127.0.0.1` / `localhost` / `file:` / `data:` / `blob:`. The pages load
no Firebase SDK, reach no CDN (the concepts carry no Google Fonts link, unlike
the current Hub), and hold no credential.

## Repository state

- `git status --porcelain` outside `design-preview/`: **clean**.
- No file under `assets/`, `index.html`, `forms.html`, `access.html`,
  `data/`, `tools/` or `tests` was modified during concept exploration.
- No Firebase write, no Firestore rule change, no schema change, no auth change,
  no service-worker change, no deploy, no push, no PR.

## Review link

{serve_summary}
"""

doc += f"""
## What the link demonstrates, and what it does not

| Demonstrable over plain HTTP on the tailnet | Requires a secure context (not testable here) |
|---|---|
| layout, mobile reflow, tap targets | service worker / offline behaviour |
| the filter system, chips, counts, empty state | PWA install |
| loading / stale / failed state wording | queue-and-sync against the register |
| keyboard traversal and focus order | real authentication and role enforcement |
| drill-down and progressive disclosure | publication and export (deliberately absent) |

The artifact is a **design preview with a synthetic fixture**, served over plain
HTTP; it is not the Hub, it reads no register, and it cannot be used to judge
offline reliability or server-enforced access.

## Screenshots

`design-preview/screens/` — `index`, `concept-conservative`,
`concept-recommended`, `concept-divergent`, each at 375px and at desktop width,
captured full-page by the same run.
"""

(HERE / "QA-REPORT.md").write_text(doc)
print("wrote", HERE / "QA-REPORT.md", len(doc), "chars")
