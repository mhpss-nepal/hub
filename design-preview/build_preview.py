#!/usr/bin/env python3
"""Build three deterministic, synthetic-only Layer 2 dashboard concepts.

Refinement of 21 Sep 2026 (Adib): the homepage is infographic-dominant and
understandable without long-form reading. The NDRRMA dashboard is the
interaction/content anchor, but this must beat it on source/date visibility,
filter clarity, non-additivity warnings, small-cell safety, correction status,
mobile readability and truthful loading/error/stale states.

Exploration boundary: no production/backend/schema/auth/rules changes, synthetic
fixtures only, and nothing outside design-preview/ is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from html import escape
from pathlib import Path

BASE = "42f308c33860987b56aadf0a5ab5e1a7be374633"
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent


def git_show(spec: str) -> str:
    return subprocess.check_output(["git", "show", spec], cwd=ROOT, text=True)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# --------------------------------------------------------------- contracts
CONTRACT_IDS = [
    "loader", "useLive", "file", "useLocal", "useDemo", "app", "srcNote", "liveStrip",
    "filters", "stats", "fClear", "p-ov", "p-who", "p-act", "p-raw", "p-pub", "rawFind",
    "expGap", "expMx", "expAll", "pubBasis", "pubFlood", "pubDir", "pubFull", "pubPreview", "pubGo"
]
GLOBAL_FILTER_IDS = ["fProv", "fDist", "fPal", "fOrg", "fDon", "fGrp", "fAct", "fMod", "fSta",
                     "fPeriod", "fBasis", "fFrom", "fTo"]
SECTION_HASHES = ["#overview", "#who-is-where", "#activities", "#reports", "#publish"]


def source_contract() -> dict:
    page = git_show(f"{BASE}:index.html")
    ids = re.findall(r'\bid="([^"]+)"', page)
    missing = sorted(set(CONTRACT_IDS) - set(ids))
    if missing:
        raise SystemExit(f"Base contract changed; missing expected ids: {missing}")
    controls = []
    for tag, attrs in re.findall(r'<(button|input|select|textarea)\b([^>]*)>', page, re.I):
        def attr(name: str) -> str:
            m = re.search(rf'\b{name}="([^"]*)"', attrs)
            return m.group(1) if m else ""
        controls.append({"tag": tag.lower(), "type": attr("type"), "id": attr("id"), "name": attr("name")})
    return {
        "base_commit": BASE,
        "source_path": "index.html",
        "source_sha256": sha(page),
        "source_loaded_scripts": re.findall(r'<script[^>]+src="([^"]+)"', page),
        "source_sections": SECTION_HASHES,
        "source_global_filter_controls": GLOBAL_FILTER_IDS,
        "source_controls": controls,
        "navigation_destinations": sorted(set(re.findall(r'<a[^>]+href="([^"]+)"', page))),
        "preserved_runtime_pairs": {
            "source_selection_buttons": ["useLive", "useLocal", "useDemo", "file", "file2"],
            "period_plus_basis": ["fPeriod", "fBasis", "fFrom", "fTo"],
            "cascading_filter_lists": GLOBAL_FILTER_IDS[:9],
            "csv_exports": ["expGap", "expMx", "expAll"],
            "publication": ["pubFlood", "pubDir", "pubFull", "pubBasis", "pubPreview", "pubGo"],
            "role_administration_destination": "access.html",
            "form_entries_destination": "forms.html",
        },
        "preview_policy": {
            "synthetic_only": True,
            "no_network_calls": True,
            "no_storage_reads_or_writes": True,
            "no_authentication": True,
            "no_publish_or_export_execution": True,
            "no_register_connection": True,
            "excluded_scope": ["GBV / child-protection case views", "referral-status expansion"],
        },
    }


# ------------------------------------------------------------------ shell
def head_links() -> str:
    return f'<link rel="stylesheet" href="preview.css?h={sha((OUT / "preview.css").read_text())[:10]}">'


def shell(title: str, body: str, body_class: str) -> str:
    js = f'preview.js?h={sha((OUT / "preview.js").read_text())[:10]}'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{escape(title)} — Layer 2 concept</title>{head_links()}</head><body class="{body_class}"><p class="demoband" role="note"><b>SYNTHETIC DESIGN PREVIEW</b> · not connected to the register · no save, export or publication</p>{body}<div class="modal" id="previewModal" hidden role="dialog" aria-modal="true" aria-labelledby="modalTitle"><div class="modal-card"><button class="modal-close quiet" type="button" aria-label="Close preview">×</button><span class="eyebrow">Publication preview</span><h2 id="modalTitle">Nothing will be published</h2><p>This shows placement and progressive disclosure only. The preview loads no database scripts, reads no register, holds no credential and has no write path.</p><button class="primary modal-close" type="button">Close</button></div></div><script src="{js}"></script></body></html>'''


# ------------------------------------------------------------ shared parts
def freshness_block() -> str:
    # A slim source line, not a panel: the first phone viewport must carry
    # figures, so source/date/status live on one row and the full explanation
    # sits behind a disclosure.
    return '<section class="freshness" id="freshness" role="status" aria-live="polite"></section>'


def state_demo() -> str:
    return '''<section class="statedemo" id="stateDemo" aria-label="Preview loading and freshness states"><span class="eyebrow">Truthful states — try them</span><div class="sg"><button type="button" data-state="fresh" class="on">Fresh</button><button type="button" data-state="stale">Stale (last good)</button><button type="button" data-state="failed">Refresh failed</button></div><p class="muted">Loading, error and stale states names what is known and never what is hoped. A failed refresh shows the last good snapshot with a warning instead of a blank page or a page of zeros.</p></section>'''


def filter_toggle() -> str:
    return '<button class="filter-toggle" type="button" id="filterToggle" aria-expanded="false" aria-controls="filterPanel">Filters <span class="count">0</span></button>'


def filter_panel() -> str:
    # Starts closed: on a phone it is a bottom sheet that must not cover the
    # first viewport, and on a desktop the page script opens it immediately so
    # the filter bar is still the prominent thing at the top.
    return '<div class="filter-panel" id="filterPanel" hidden aria-label="Filters"><div id="filterHost"></div></div>'


def status_strip() -> str:
    return '''<div class="status-strip" role="group" aria-label="Active filters and result count"><div class="chips" id="activeChips"></div><p class="count" id="resultCount" aria-live="polite"></p></div>'''


def empty_state() -> str:
    return '<section class="empty" id="emptyState" hidden role="status"></section>'


def kpi_row() -> str:
    return '<section class="kpis" id="kpiRow" aria-label="Response level at a glance"></section>'


def coverage_host() -> str:
    return '<div id="coverageHost"></div>'


def actors_hosts() -> str:
    return ('<div class="mix-grid">'
            '<section class="mix-card"><h3>Organisations reporting <span class="hint">click a bar to filter</span></h3><div id="orgHost" class="bars"></div></section>'
            '<section class="mix-card"><h3>IASC intervention layer <span class="hint">read from the activity code</span></h3><div id="layerHost" class="bars"></div></section>'
            '</div>')


def activity_host() -> str:
    return '<section class="mix-card"><h3>Activity mix <span class="hint">click a bar to filter</span></h3><div id="actHost" class="bars"></div><p class="muted">Report counts, not attendances; the two are separate measures and are never added. A report may carry more than one target group, so those rows are not additive.</p></section>'


def geo_hosts() -> str:
    return ('<div class="mix-grid">'
            '<section class="mix-card"><h3>Geographic concentration <span class="hint">click to filter</span></h3><div id="distHost" class="dist"></div></section>'
            '<section class="mix-card"><h3>Leading palikas</h3><ul class="plainlist" id="palikaList"></ul><p class="muted">Nothing smaller than a palika is shown, and a cell below 5 reports reads “fewer than 5”.</p></section>'
            '</div>')


def mix_hosts() -> str:
    return actors_hosts() + activity_host() + geo_hosts()


def quality_host() -> str:
    return '<div class="flags" id="qualityHost"></div>'


def method_notes() -> str:
    return '''<details class="method"><summary>Method, definitions and caveats (secondary — kept out of the first read)</summary><div><h4>What is counted</h4><p>One row is one activity report (5Ws): one session, at one place, on one day, with its attendance. Attendances are sessions, not unique people — one person at three sessions is three attendances, so attendances are never added to any count of people. No denominator is implied anywhere except coverage against the roster, which is stated as such.</p><h4>Non-additivity</h4><p>Activity families, target groups and IASC layers overlap and a record may appear in more than one, so their rows are not additive. Only the total report count is a sum.</p><h4>Small cells</h4><p>A count below 5 reads “fewer than 5”, and no figure smaller than a palika is shown, so no cell can point to an individual. The floor is printed on the page, not hidden in a note.</p><h4>Source, date and correction status</h4><p>Source, the data date and the capture state travel with every block. A record carrying a correction is flagged rather than silently rewritten. This fixture is synthetic and settles no institutional question.</p><h4>What this cannot show</h4><p>No trend, no target achievement, no coverage gap as a proportion of need: this data carries no MHPSS-specific denominator. Where a ratio would need one, the concept says it cannot be calculated instead of printing a number.</p></div></details>'''


# --------------------------------------------------------- concept A (A/B/C)
def concept_conservative() -> str:
    return f'''<div class="layout has-rail">
<nav class="side" aria-label="Concept navigation"><a class="brand" href="index.html"><span class="mark">M</span><b>MHPSS Nepal</b><small>Layer 2 · concept A</small></a>
<p class="side-label">Overview</p>
<a href="#response" aria-current="page">Response level</a>
<a href="#coverage">Coverage &amp; gaps</a>
<a href="#presence">Who is where</a>
<a href="#activity">Activity mix</a>
<a href="#quality">Data quality</a>
<p class="side-label">Secondary</p>
<a href="#method">Method &amp; definitions</a>
<a href="../index.html?source=choose">Current Hub ↗</a>
<a href="../forms.html">Form entries ↗</a>
<a href="../access.html">Access &amp; sign-in ↗</a>
</nav>
<main class="canvas">
<header class="pagehead"><div><span class="eyebrow">Concept A · Conservative</span><h1>Coordination dashboard</h1><p>Closest to the current Hub: the familiar five sections, shortened copy, global filters kept in one visible bar.</p></div>{filter_toggle()}</header>
{filter_panel()}{status_strip()}{freshness_block()}
<section id="response">{kpi_row()}</section>
<section id="coverage" class="block"><header class="blockhead"><div><span class="eyebrow">01</span><h2>Coverage &amp; gaps</h2><p>Which roster sites have a report, which are at zero, and which reports come from off-roster places.</p></div></header>{coverage_host()}{method_notes()}</section>
<section id="presence" class="block"><header class="blockhead"><div><span class="eyebrow">02</span><h2>Who is where</h2><p>Organisation and activity presence by district and palika. Service level only, no individual is named anywhere in it.</p></div></header>{mix_hosts()}</section>
<section id="activity" class="block"><header class="blockhead"><div><span class="eyebrow">03</span><h2>Activity mix</h2><p>The same code read twice: the plain label the worker chose and the IASC layer the backend reports.</p></div></header><p class="muted">Use the bars above; each row is a filter, so the page narrows as you read it.</p></section>
<section id="quality" class="block"><header class="blockhead"><div><span class="eyebrow">04</span><h2>Priority data-quality signals</h2><p>What a coordinator should look at before the numbers are quoted.</p></div></header>{quality_host()}</section>
<section class="block restricted"><header class="blockhead"><div><span class="eyebrow">05</span><h2>Restricted workflows</h2><p>Publication, export and access administration stay separate, role-gated and outside the homepage.</p></div><span class="status warn">Not exercised here</span></header><div class="links"><button type="button" class="secondary" data-preview>Publication preview</button><a href="../index.html?source=choose#publish">Current publish screen ↗</a><a href="../access.html">Access administration ↗</a></div></section>
{state_demo()}{empty_state()}
</main></div>'''


def concept_recommended() -> str:
    return f'''<div class="appbar"><a class="brand" href="index.html"><span class="mark">M</span><b>MHPSS Nepal</b><small>Layer 2 · response brief</small></a><div class="appbar-actions"><a class="quiet" href="../index.html?source=choose">Current Hub ↗</a><a class="quiet" href="../forms.html">Form entries ↗</a></div></div>
<main class="canvas wide">
<header class="brief-head"><div><span class="eyebrow">Concept B · Recommended</span><h1>Flood response — coordination brief</h1><p>One question per block, the priority first. Filter to any slice without leaving the page.</p></div>{filter_toggle()}</header>
{filter_panel()}{status_strip()}{freshness_block()}
<section id="response" class="hero">
<div class="hero-lead"><span class="eyebrow">Needs attention now</span><div class="heronum"><strong id="heroGap">6</strong><span>roster sites have no activity report</span></div><p id="heroSub">Coverage against the agreed roster is the headline, not the total: an aggregate can look healthy while a whole site has nobody reporting.</p><a class="primary" href="#coverage">See the sites</a></div>
<div class="hero-side">
<article><small>Actors reporting</small><b id="heroOrgs">—</b></article>
<article><small>Activity reports</small><b id="heroReports">—</b></article>
<article><small>Latest data date</small><b id="heroDate">—</b></article>
</div>
</section>
<section class="kpi-band">{kpi_row()}</section>
<section id="coverage" class="story"><header class="storyhead"><span class="step">01</span><div><span class="eyebrow">Where are the gaps?</span><h2>Coverage against the roster</h2><p>Six sites have no report; four more are held by a single organisation.</p></div><span class="meta">Synthetic fixture · data to 13 Sep 2026</span></header>{coverage_host()}<details class="method"><summary>How coverage is counted</summary><p>Only roster sites can appear as uncovered: a place nobody ever listed as a service point cannot be counted as one that was missed. Reports from off-roster places are listed separately and are neither covered sites nor gaps. If the roster itself is disputed, the denominator is disputed with it — this fixture does not settle that question.</p></details></section>
<section id="presence" class="story"><header class="storyhead"><span class="step">02</span><div><span class="eyebrow">Who is where, doing what?</span><h2>Actors and activity mix</h2><p>Organisation and geographic concentration first; each bar is a filter you can click.</p></div></header>{mix_hosts()}</section>
<section id="activity" class="story"><header class="storyhead"><span class="step">03</span><div><span class="eyebrow">What needs review?</span><h2>Priority data-quality signals</h2><p>Read these before quoting any figure on this page.</p></div></header>{quality_host()}</section>
<section class="story compact restricted"><header class="storyhead"><span class="step">04</span><div><span class="eyebrow">What can become public?</span><h2>Publication stays a separate, restricted decision</h2><p>The homepage never publishes. Source, basis and small-cell status stay visible; the publication path is unchanged and role-gated.</p></div><span class="status warn">Preview only</span></header><div class="links"><button type="button" class="secondary" data-preview>Preview publication screen</button><a href="../index.html?source=choose#publish">Current publish screen ↗</a><a href="../access.html">Access administration ↗</a><a href="../forms.html">Form entries ↗</a></div></section>
{method_notes()}{state_demo()}{empty_state()}
</main>'''


def concept_divergent() -> str:
    return f'''<div class="appbar"><a class="brand" href="index.html"><span class="mark">M</span><b>MHPSS Nepal</b><small>Layer 2 · concept C</small></a><div class="appbar-actions"><a class="quiet" href="../index.html?source=choose">Current Hub ↗</a></div></div>
<main class="canvas focus">
<header class="brief-head"><div><span class="eyebrow">Concept C · Divergent</span><h1>Choose the coordination question</h1><p>A task-first home: enter through the decision you need, then reveal only its evidence. The filter bar stays across every question.</p></div>{filter_toggle()}</header>
{filter_panel()}{status_strip()}{freshness_block()}
<section id="response" class="focus-intro"><h2>What do you need to decide?</h2><p>Four questions replace the long dashboard homepage. Each opens one evidence view, and every view keeps the same filters, source and freshness.</p>{kpi_row()}</section>
<nav class="question-grid" aria-label="Coordination questions">
<button type="button" data-focus="coverage"><span>01</span><b>Where are the gaps?</b><small>—</small></button>
<button type="button" data-focus="presence"><span>02</span><b>Who is where?</b><small>—</small></button>
<button type="button" data-focus="activity"><span>03</span><b>What was delivered?</b><small>—</small></button>
<button type="button" data-focus="records"><span>04</span><b>What needs review?</b><small>—</small></button>
</nav>
<section class="focus-panel" id="coverage" hidden><button class="back quiet" type="button" data-back>← All questions</button><header class="storyhead"><span class="step">01</span><div><span class="eyebrow">Where are the gaps?</span><h2 class="focus-summary">—</h2><p>Coverage is the first screen because an aggregate can look healthy while a whole site has nobody reporting.</p></div></header>{coverage_host()}</section>
<section class="focus-panel" id="presence" hidden><button class="back quiet" type="button" data-back>← All questions</button><header class="storyhead"><span class="step">02</span><div><span class="eyebrow">Who is where?</span><h2 class="focus-summary">—</h2><p>Organisation and service presence, never an individual case view.</p></div></header>{actors_hosts()}{geo_hosts()}</section>
<section class="focus-panel" id="activity" hidden><button class="back quiet" type="button" data-back>← All questions</button><header class="storyhead"><span class="step">03</span><div><span class="eyebrow">What was delivered?</span><h2 class="focus-summary">—</h2><p>Report count and attendance stay separate: they are not the same measure and are never added.</p></div></header>{activity_host()}</section>
<section class="focus-panel" id="records" hidden><button class="back quiet" type="button" data-back>← All questions</button><header class="storyhead"><span class="step">04</span><div><span class="eyebrow">What needs review?</span><h2 class="focus-summary">—</h2><p>Read these before quoting any figure. Each flag follows the current filters.</p></div></header>{quality_host()}</section>
<section class="focus-footer restricted"><p><b>Restricted workflows stay outside the task-first home.</b> Form entries, access administration, export and publication keep their current destinations and role boundaries.</p><div class="links"><a href="../forms.html">Form entries ↗</a><a href="../access.html">Access ↗</a><button type="button" class="secondary" data-preview>Publication preview</button></div></section>
{method_notes()}{state_demo()}{empty_state()}
</main>'''


def landing() -> str:
    cards = [
        ("A", "Conservative", "Closest to the current Hub",
         "Keeps the familiar five sections and a conventional left rail, shortens the copy, and moves all global filters into one visible bar with an active-filter strip.",
         "concept-conservative.html", False),
        ("B", "Recommended — infographic brief", "Strongest fit to the approved anchors",
         "A priority figure, a KPI band and truthful freshness in the first viewport; then one question per block with drill-down filters, geographic and actor concentration, and a data-quality signal block.",
         "concept-recommended.html", True),
        ("C", "Divergent — question router", "Genuinely different interaction model",
         "Replaces the long homepage with four coordination questions; each opens one evidence view behind progressive disclosure, under a persistent filter bar.",
         "concept-divergent.html", False),
    ]
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Layer 2 dashboard concepts</title>{head_links()}</head><body class="landing"><p class="demoband" role="note"><b>SYNTHETIC DESIGN PREVIEW</b> · no production data, no register read, no writes</p><main class="board">
<span class="eyebrow">MHPSS Nepal · Layer 2 coordination hub</span><h1>Consolidating the dashboard homepage</h1>
<p class="lead">Three interaction models built from Hub base <code>42f308c</code>, against the approved Layer 3 anchors and the 21 Sep refinement: infographic-dominant, filter-first, source and date always visible, methodology secondary. Every figure is synthetic; no concept connects to the register, reads storage, signs in, exports or publishes.</p>
<div class="concepts">''' + "".join(
        f'''<article{' class="pick"' if pick else ''}><span class="concept-no">{n}</span><h2>{escape(name)}</h2><b>{escape(tag)}</b><p>{escape(desc)}</p><a class="primary" href="{href}">Open concept {n}</a></article>'''
        for n, name, tag, desc, href, pick in cards) + '''</div>
<section class="decision"><h2>Recommended direction: B</h2><p>B is the strongest infographic-and-filter model and the best fit to the decisions already taken: one idea per block, the priority first, a filter bar that works on a phone, drill-down instead of more pages, and source/date/freshness/correction status visible at the top. It beats the NDRRMA anchor on filter clarity, non-additivity and small-cell warnings, and truthful loading/stale/failed states — while keeping methodology, definitions, export and administration secondary.</p><p class="muted">A is the low-risk fallback if the team prefers the current information architecture; C is kept to show a genuinely different model, not as a recommendation.</p></section>
<div class="board-links"><a href="REDUNDANCY-INVENTORY.md">Redundancy inventory</a><a href="PRESERVATION-INVENTORY.md">Preservation inventory</a><a href="QA-REPORT.md">QA report</a><a href="contract-inventory.json">Contract inventory (machine-readable)</a><a href="../index.html?source=choose">Current Hub</a></div>
</main></body></html>'''


# ---------------------------------------------------------------- validate
def validate_page(path: Path) -> None:
    page = path.read_text()
    ids = re.findall(r'\bid="([^"]+)"', page)
    dup = sorted({x for x in ids if ids.count(x) > 1})
    if dup:
        raise SystemExit(f"Duplicate ids in {path.name}: {dup}")
    forbidden = ["firebase", "firestore", "localstorage", "sessionstorage", "fetch(", "xmlhttprequest", "indexeddb"]
    hits = [x for x in forbidden if x in page.lower()]
    if hits:
        raise SystemExit(f"Forbidden runtime API in {path.name}: {hits}")
    for asset in re.findall(r'(?:src|href)="([^"]+)"', page):
        clean = asset.split("?")[0].split("#")[0]
        if not clean or clean.startswith(("http:", "https:", "../", "#", "mailto:")):
            continue
        if clean.endswith((".md", ".json")):
            continue                      # documentation links, not runtime assets
        if not (OUT / clean).exists():
            raise SystemExit(f"Missing runtime asset {clean} in {path.name}")


def build() -> None:
    contract = source_contract()
    (OUT / "contract-inventory.json").write_text(json.dumps(contract, indent=2) + "\n")
    pages = {
        "concept-conservative.html": shell("Conservative concept", concept_conservative(), "concept-page"),
        "concept-recommended.html": shell("Recommended concept", concept_recommended(), "concept-page"),
        "concept-divergent.html": shell("Divergent concept", concept_divergent(), "concept-page focus-page"),
        "index.html": landing(),
    }
    for name, content in pages.items():
        (OUT / name).write_text(content)
    for name in pages:
        validate_page(OUT / name)
    first = {name: sha((OUT / name).read_text()) for name in pages}
    for name, content in pages.items():
        (OUT / name).write_text(content)
    if first != {name: sha((OUT / name).read_text()) for name in pages}:
        raise SystemExit("Nondeterministic preview build")
    print(json.dumps({"built": sorted(pages), "base": BASE,
                      "source_sha256": contract["source_sha256"], "deterministic": True}, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE)
    a = ap.parse_args()
    if a.base != BASE:
        raise SystemExit(f"This review artifact is locked to {BASE}")
    build()
