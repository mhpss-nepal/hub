# Layer 2 dashboard concepts — objective QA

**Base commit:** `42f308c33860987b56aadf0a5ab5e1a7be374633`
**Source `index.html` SHA-256:** `8ce3ebfc77ed851161dacf20621c03cc0598a60a8b3478b9e72f7f71c84e1979`
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

- Raw measurement files (`qa-results.json`, `topology.json`, `contract-inventory.json`, `serve-report.json`) are **gitignored by this repository** (`*.json`), so they are not part of the commit even though the figures below are read from them. Regenerate with the commands listed above; the scripts that produce them are tracked.
- Missing at the time of this run: none.


## Hard result

**hard failures: 0** — 0 hard checks failed across
4 pages, 5 widths, 16 keyboard traversals and
812 measured controls.

## Horizontal overflow

Root width equality and the constrained-descendant probe (helper text, labels,
badges, tables, bars, status copy) both pass.

| Concept | 320 | 375 | 768 | 1280 | 1920 |
|---|---|---|---|---|---|
| `index.html` | OK | OK | OK | OK | OK |
| `concept-conservative.html` | OK | OK | OK | OK | OK |
| `concept-recommended.html` | OK | OK | OK | OK | OK |
| `concept-divergent.html` | OK | OK | OK | OK | OK |

The probe reports `documentElement.scrollWidth == clientWidth`,
`body.scrollWidth == clientWidth` and zero leaking descendants at every width on
every page. `overflow-x` on tables and the site list is `auto` only where a
horizontal swipe is the documented convention; those are excluded from the
"leak" set by construction, and none of them widened the document either.

## Tap targets (44px)

Measured on the **clickable** element, preferring the wrapping `label`/button
rect over an inner glyph.

| Concept | controls measured | under 44px |
|---|---|---|
| `index.html` | 40 | 0 |
| `concept-conservative.html` | 339 | 0 |
| `concept-recommended.html` | 319 | 0 |
| `concept-divergent.html` | 114 | 0 |

## Accessibility engine

axe-core `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa` over every page at every
width. The service worker is not registered on these pages and no `caches`
entries exist, so the engine audits the live tree.

| Concept | axe violations (4 rulesets x 5 widths) |
|---|---|
| `index.html` | 0 |
| `concept-conservative.html` | 0 |
| `concept-recommended.html` | 0 |
| `concept-divergent.html` | 0 |

## Keyboard traversal and overlay intersections

Real `Tab` key events from a fresh page (never `element.focus()`), recording the
active element and intersecting it with every visible `position: fixed|sticky`
element after each step.

| Concept | 320 | 375 | 768 | 1280 | overlay intersections |
|---|---|---|---|---|---|
| `index.html` | 8 | 8 | 8 | 8 | 0 |
| `concept-conservative.html` | 60 | 60 | 60 | 60 | 0 |
| `concept-recommended.html` | 56 | 56 | 60 | 60 | 0 |
| `concept-divergent.html` | 15 | 15 | 28 | 28 | 0 |

**0 overlay intersections in 590 recorded Tab steps.** Two defects were found by
this probe and fixed on the current revision: the phone filter drawer covered the
page (moved to a bottom sheet that starts closed), and sticky-header anchor
targets needed `scroll-margin-top` so a section link does not land under the bar.

## Filter system

Exercised in the browser at 375px: pick a dimension, read the active chips and
the result count, clear, and drill down from a bar.

```json
{
  "count_before": "163 of 163 reports \u00b7 0 filters active",
  "count_after_district": "92 of 163 reports \u00b7 1 filter active",
  "chips_after": [
    "District: Rasuwa \u00d7Remove this filter"
  ],
  "changed": true,
  "count_after_clear": "163 of 163 reports \u00b7 0 filters active",
  "chips_after_clear": 1,
  "count_after_bar": "21 of 163 reports \u00b7 1 filter active",
  "bar_filter_changed": true
}
```

Every concept keeps: active-filter chips (each with its own remove control),
a result count that names the total as well as the selection, clear-all, a
no-match empty state, and drill-down bars/rows that filter the whole page.

### No-match state

Forced through the search box, not through two contradictory dimensions:

```json
{
  "hidden": false,
  "text": "No report matches these filtersThe selection is empty. That is a true state, not an error, and not a page of zeros dressed up as figures \u2014 t",
  "count": "0 of 163 reports \u00b7 1 filter active",
  "chips": [
    "Search: zzz-no-such-record \u00d7Remove this filter"
  ],
  "after_clear": "163 of 163 reports \u00b7 0 filters active"
}
```

### Shareable, presentation-only filter state

```json
{
  "fragment": "#flt=district=Rasuwa",
  "count_before_reload": "92 of 163 reports \u00b7 1 filter active",
  "count_after_reload": "92 of 163 reports \u00b7 1 filter active",
  "fragment_after_reload": "#flt=district=Rasuwa",
  "district_after_reload": "Rasuwa",
  "presentation_only": true,
  "survives_reload": true
}
```

The fragment is `#flt=…`: filter names and the search text only. It is written
with `replaceState`, so it never adds a history entry and never reaches a
server. It is deliberately namespaced so it cannot collide with the section
anchors the current Hub uses (`#overview`, `#reports`, …).

### Loading, stale and failed states

```json
{
  "stale": "Showing the last successful refresh\u00b7data date 13 Sep 2026\u00b7refresh 14:20\u00b7source: synthetic ",
  "failed": "This view could not be refreshed\u00b7data date 13 Sep 2026\u00b7refresh 14:20\u00b7source: synthetic rev",
  "fresh": "Synthetic fixture loaded\u00b7data date 13 Sep 2026\u00b7refresh 14:20\u00b7source: synthetic review fixt",
  "distinct": true
}
```

The three states are genuinely distinct strings, and the failed state names the
last good snapshot and its own date rather than showing zeros.

### Phone drawer

```json
{
  "hidden": false,
  "position": "fixed",
  "top": 162,
  "height": 738,
  "viewportH": 900,
  "coversFirstViewport": false,
  "overflowsX": false
}
```

### Chart-and-table reconciliation

*Does every visual tie out with the selection count?*

```json
{
  "result_count": 163,
  "org_rows": 6,
  "org_sum": 119,
  "org_remainder": 44,
  "act_rows": 7,
  "act_sum": 163,
  "act_remainder": null,
  "dist_rows": 2,
  "dist_sum": 163,
  "org_reconciles": true,
  "act_reconciles": true,
  "dist_reconciles": true,
  "district_pct_total_100": true,
  "remainder_disclosed": true,
  "kpi_names_selection": true,
  "metric_basis_stated": true,
  "source_and_date_visible": true
}
```

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
| 8 | Search must not weaken role boundaries, expose restricted fields, or open raw export | no concept loads the bridge, reaches a server, reads a role document, or offers an export control; search runs over an in-page fixture | network isolation: `none` external requests |

## Network isolation

External requests recorded across every page and width:
**none**.

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

```json
{
  "ok": true,
  "plain_http_base": "http://100.98.168.123:8823/design-preview/",
  "bind": "100.98.168.123",
  "port": 8823,
  "tailnet_dns": "srv1989703.tail766325.ts.net",
  "served_css_carries_new_rules": true,
  "served_markup_uses_hashed_assets": true
}
```

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
