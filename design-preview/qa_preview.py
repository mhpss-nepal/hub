#!/usr/bin/env python3
"""Objective QA for the Layer 2 dashboard concepts.

Runs a real browser (Chromium via Playwright), over the exact preview pages,
with a vendored axe-core. Records, for each concept and each supported width:

  * horizontal overflow: documentElement and body scrollWidth vs clientWidth,
    plus any constrained descendant that leaks past its own box or the viewport;
  * tap targets: every clickable control's clickable rect, measured;
  * axe-core WCAG 2.0/2.1 A + AA violations;
  * real Tab traversal (not element.focus()) with fixed/sticky overlay
    intersection recorded after every Tab;
  * filter behaviour: active state, result count, clear, empty state;
  * the loading/stale/failed state switch;
  * a block network log proving no request leaves the local origin.

Usage: python3 design-preview/qa_preview.py [--base-url http://127.0.0.1:PORT/]
Exit code is non-zero if any hard check fails.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
AXE = (HERE / "vendor" / "axe.min.js").read_text()
CONCEPTS = ["index.html", "concept-conservative.html", "concept-recommended.html", "concept-divergent.html"]
WIDTHS = [320, 375, 768, 1280, 1920]
ALLOWED_PREFIXES = ("http://127.0.0.1", "http://localhost", "file://", "data:", "blob:")
TAP_MIN = 44

OVERFLOW_PROBE = """
() => {
  const de = document.documentElement, b = document.body;
  const vw = de.clientWidth;
  const wide = [];
  document.querySelectorAll('body *').forEach(el => {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || !el.offsetParent && s.position !== 'fixed') return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    const leaksSelf = el.scrollWidth > el.clientWidth + 1 &&
      ['visible', 'clip'].indexOf(s.overflowX) < 0;
    const leaksView = r.right > vw + 1 || r.left < -1;
    const scrollable = ['auto', 'scroll'].indexOf(s.overflowX) >= 0;
    if ((leaksSelf || leaksView) && !scrollable) {
      wide.push({ tag: el.tagName, id: el.id, cls: (el.className || '').toString().slice(0, 60),
                  left: Math.round(r.left), right: Math.round(r.right),
                  sw: el.scrollWidth, cw: el.clientWidth, overflowX: s.overflowX });
    }
  });
  return {
    clientWidth: vw,
    docScrollWidth: de.scrollWidth,
    bodyScrollWidth: b.scrollWidth,
    rootOverflow: de.scrollWidth > vw + 1 || b.scrollWidth > vw + 1,
    offenders: wide.slice(0, 12)
  };
}
"""

TAP_PROBE = """
() => {
  const out = [];
  const sel = 'a[href], button, select, input, summary, [role="button"], [data-focus], [data-set-dim], [data-clear], [data-preview], [data-back], [data-clear-dim]';
  document.querySelectorAll(sel).forEach(el => {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    if (el.disabled) return;
    /* the clickable target is the element itself; for a control inside a
       full-width label the label rect is what a finger hits, so prefer it */
    const label = el.closest('label') || el;
    const lr = label.getBoundingClientRect();
    out.push({
      tag: el.tagName, id: el.id || '',
      text: (el.textContent || '').trim().slice(0, 40),
      w: Math.round(r.width), h: Math.round(r.height),
      labelW: Math.round(lr.width), labelH: Math.round(lr.height),
      ok: Math.min(r.height, lr.height) >= 44 || (label !== el && Math.min(lr.height) >= 44)
    });
  });
  return out;
}
"""

AXE_PROBE = """
async (tags) => {
  const r = await window.axe.run(document, { resultTypes: ['violations'],
    runOnly: { type: 'tag', values: tags } });
  return r.violations.map(v => ({ id: v.id, impact: v.impact, n: v.nodes.length,
    where: (v.nodes[0] && (v.nodes[0].target || []).join(' ')) || '' }));
}
"""


def tab_walk(page, limit=60):
    """Real Tab key traversal from the top of the document."""
    page.evaluate("() => { document.body.focus(); window.scrollTo(0,0); }")
    seen = []
    for _ in range(limit):
        page.keyboard.press("Tab")
        rec = page.evaluate("""() => {
          const a = document.activeElement;
          if (!a || a === document.body) return null;
          const r = a.getBoundingClientRect();
          const overlays = [...document.querySelectorAll('*')].filter(el => {
            const s = getComputedStyle(el);
            return s.display !== 'none' && (s.position === 'fixed' || s.position === 'sticky');
          });
          const covered = overlays.filter(el => el !== a && !el.contains(a) && !a.contains(el)).filter(el => {
            const q = el.getBoundingClientRect();
            return r.bottom > q.top && r.top < q.bottom && r.right > q.left && r.left < q.right;
          }).map(el => el.id || el.className.toString().slice(0, 30));
          return { tag: a.tagName, id: a.id || '', text: (a.textContent||'').trim().slice(0,32),
                   w: Math.round(r.width), h: Math.round(r.height),
                   focusVisible: a.matches(':focus-visible'), coveredBy: covered };
        }""")
        if rec is None:
            break
        key = (rec["tag"], rec["id"], rec["text"])
        seen.append(rec)
        if len(seen) > 3 and key == (seen[0]["tag"], seen[0]["id"], seen[0]["text"]):
            break
    return seen


def panel_state(page):
    return page.evaluate("() => !document.getElementById('filterPanel').hidden")


def open_panel(page):
    if not panel_state(page):
        page.click("#filterToggle")
        page.wait_for_timeout(80)


def close_panel(page):
    if panel_state(page):
        page.evaluate("""() => {
          const p = document.getElementById('filterPanel');
          const t = document.getElementById('filterToggle');
          if (p) p.hidden = true;
          if (t) { t.setAttribute('aria-expanded','false'); }
        }""")
        page.wait_for_timeout(80)


def filter_probe(page):
    """Exercise the filter system: set one, read the count, clear, drill down."""
    out = {}
    open_panel(page)
    clear_filters(page)
    before = page.evaluate("() => document.getElementById('resultCount').textContent")
    page.select_option('select[data-dim="district"]', index=1)
    after = page.evaluate("() => document.getElementById('resultCount').textContent")
    chips = page.evaluate("() => [...document.querySelectorAll('#activeChips .chip')].map(c => c.textContent.trim())")
    out["count_before"] = before
    out["count_after_district"] = after
    out["chips_after"] = chips
    out["changed"] = before != after
    clear_filters(page)
    out["count_after_clear"] = page.evaluate("() => document.getElementById('resultCount').textContent")
    out["chips_after_clear"] = page.evaluate("() => document.querySelectorAll('#activeChips .chip').length")
    # Drill-down: a bar click must filter. In the task-first concept the bars
    # live behind a question, so open the first question the way a coordinator
    # would before looking for one.
    page.evaluate("""() => {
      const prefer = document.querySelector('[data-focus="presence"]') || document.querySelector('[data-focus]');
      if (prefer) prefer.click();
    }""")
    page.wait_for_timeout(120)
    clicked = page.evaluate("""() => {
      const b = [...document.querySelectorAll('.bar-row')].find(x => x.getBoundingClientRect().height > 0);
      if (!b) return false; b.click(); return true;
    }""")
    if clicked:
        out["count_after_bar"] = page.evaluate("() => document.getElementById('resultCount').textContent")
        out["bar_filter_changed"] = out["count_after_bar"] != out["count_after_clear"]
        clear_filters(page)
    else:
        out["count_after_bar"] = None
    return out


def clear_filters(page):
    page.evaluate("""() => {
      const b = document.querySelector('#filterHost [data-clear]');
      if (b) b.click();
    }""")
    page.wait_for_timeout(80)


def forced_empty(page):
    """Force a no-match state through the search box and read the empty state."""
    open_panel(page)
    page.fill("#filterSearch", "zzz-no-such-record")
    page.wait_for_timeout(320)
    state = page.evaluate("""() => {
      const e=document.getElementById('emptyState');
      return { hidden: e ? e.hidden : null,
               text: e ? e.textContent.trim().slice(0,140) : null,
               count: document.getElementById('resultCount').textContent,
               chips: [...document.querySelectorAll('#activeChips .chip')].map(c => c.textContent.trim()) };
    }""")
    page.fill("#filterSearch", "")
    page.wait_for_timeout(320)
    state["after_clear"] = page.evaluate("() => document.getElementById('resultCount').textContent")
    return state


def state_switch(page):
    close_panel(page)
    page.evaluate("() => document.getElementById('stateDemo').scrollIntoView({ block: 'center' })")
    page.wait_for_timeout(150)
    page.click('button[data-state="stale"]')
    stale = page.evaluate("() => document.getElementById('freshness').textContent.trim().slice(0,90)")
    page.click('button[data-state="failed"]')
    failed = page.evaluate("() => document.getElementById('freshness').textContent.trim().slice(0,90)")
    page.click('button[data-state="fresh"]')
    fresh = page.evaluate("() => document.getElementById('freshness').textContent.trim().slice(0,90)")
    page.evaluate("() => window.scrollTo(0,0)")
    return {"stale": stale, "failed": failed, "fresh": fresh,
            "distinct": len({stale, failed, fresh}) == 3}


def share_url_probe(page):
    """Choose a filter, read the fragment, reload, and confirm it re-applies."""
    open_panel(page)
    page.select_option('select[data-dim="district"]', index=1)
    frag = page.evaluate("() => location.hash")
    count = page.evaluate("() => document.getElementById('resultCount').textContent")
    page.reload(wait_until="load")
    page.wait_for_timeout(250)
    after = page.evaluate("() => document.getElementById('resultCount').textContent")
    carried = page.evaluate("() => location.hash")
    selected = page.evaluate("""() => {
      const s=document.querySelector('select[data-dim="district"]');
      return s ? s.value : null; }""")
    clear_filters(page)
    return {"fragment": frag, "count_before_reload": count, "count_after_reload": after,
            "fragment_after_reload": carried, "district_after_reload": selected,
            "presentation_only": frag.startswith("#flt=") and "Rasuwa" in frag,
            "survives_reload": count == after and selected == "Rasuwa"}


def sheet_probe(page):
    """Measure the phone filter drawer: is it on screen, does it overflow?"""
    return page.evaluate("""() => {
      const p = document.getElementById('filterPanel');
      const r = p.getBoundingClientRect();
      const s = getComputedStyle(p);
      return { hidden: p.hidden, position: s.position, top: Math.round(r.top),
               height: Math.round(r.height),
               viewportH: window.innerHeight,
               coversFirstViewport: !p.hidden && r.top <= 1,
               overflowsX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1 };
    }""")


def reconcile_probe(page):
    """Every chart must reconcile with the selection, or disclose its remainder.

    Charts and tables are all rendered from one filtered row set, so the figures
    have to tie out. A top-N ranking does not sum to the whole, which is fine —
    but only if the remainder is stated on the page. This asserts the tie-out
    where the bars are complete, and the disclosure where they are not.
    """
    open_panel(page)
    clear_filters(page)
    return page.evaluate("""() => {
      const count = parseInt(document.getElementById('resultCount').querySelector('b').textContent
                     .replace(/[^0-9]/g, ''), 10);
      const vals = sel => [...document.querySelectorAll(sel)]
        .map(b => parseInt((b.querySelector('.bar-value') || b.querySelector('.dist-val') || {}).textContent || '', 10))
        .filter(n => !isNaN(n));
      const sum = a => a.reduce((x, y) => x + y, 0);
      const remainder = host => {
        const p = document.querySelector(host + ' .remainder');
        if (!p) return null;
        const m = p.textContent.match(/remaining ([\\d,]+) reports/);
        return m ? parseInt(m[1].replace(/,/g, ''), 10) : null;
      };
      const org = vals('#orgHost .bar-row'), act = vals('#actHost .bar-row'), dist = vals('#distHost .dist-row');
      const orgRest = remainder('#orgHost'), actRest = remainder('#actHost');
      const pcts = [...document.querySelectorAll('#distHost .dist-val')]
        .map(e => parseInt((e.textContent.match(/(\\d+)%/) || [0, 0])[1], 10));
      const kpiText = document.getElementById('kpiRow') ? document.getElementById('kpiRow').textContent : '';
      const sourceLine = document.getElementById('freshness') ? document.getElementById('freshness').textContent : '';
      const ties = (bars, rest) => (rest === null ? sum(bars) === count : sum(bars) + rest === count);
      return {
        result_count: count,
        org_rows: org.length, org_sum: sum(org), org_remainder: orgRest,
        act_rows: act.length, act_sum: sum(act), act_remainder: actRest,
        dist_rows: dist.length, dist_sum: sum(dist),
        org_reconciles: org.length ? ties(org, orgRest) : null,
        act_reconciles: act.length ? ties(act, actRest) : null,
        dist_reconciles: dist.length ? sum(dist) === count : null,
        district_pct_total_100: pcts.length ? Math.abs(sum(pcts) - 100) <= 1 : null,
        remainder_disclosed: orgRest !== null || actRest !== null ||
                            (org.length && sum(org) === count),
        kpi_names_selection: kpiText.indexOf(String(count).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ',')) >= 0,
        metric_basis_stated: /not unique people/i.test(document.body.textContent),
        source_and_date_visible: /source/i.test(sourceLine) && /data date/i.test(sourceLine)
      };
    }""")


def run(base_url: str | None) -> dict:
    report = {"pages": {}, "network": [], "ok": True}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for page_name in CONCEPTS:
            url = urljoin(base_url + "/", page_name) if base_url else (HERE / page_name).as_uri()
            entry = {"url": url, "widths": {}}
            for width in WIDTHS:
                ctx = browser.new_context(viewport={"width": width, "height": 900},
                                          device_scale_factor=1,
                                          reduced_motion="reduce")
                pg = ctx.new_page()
                reqs = []
                pg.on("request", lambda r: reqs.append(r.url))
                pg.goto(url, wait_until="load")
                pg.wait_for_timeout(150)
                try:
                    pg.add_script_tag(content=AXE)
                    axe = pg.evaluate(AXE_PROBE, ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
                except Exception as e:  # pragma: no cover
                    axe = [{"id": "axe-error", "impact": "error", "n": 1, "where": str(e)}]
                rec = {
                    "overflow": pg.evaluate(OVERFLOW_PROBE),
                    "tapTargets": pg.evaluate(TAP_PROBE),
                    "axe": axe,
                }
                rec["tapFailures"] = [t for t in rec["tapTargets"] if not t["ok"]]
                if width in (320, 375, 768, 1280):
                    rec["tab"] = tab_walk(pg)
                if width == 375:
                    has_filters = pg.query_selector("#resultCount") is not None
                    if has_filters:
                        rec["filters"] = filter_probe(pg)
                        rec["empty"] = forced_empty(pg)
                        rec["states"] = state_switch(pg)
                        rec["shareUrl"] = share_url_probe(pg)
                        rec["reconcile"] = reconcile_probe(pg)
                        shot = HERE / "screens" / f"{page_name.replace('.html','')}-{width}.png"
                        pg.screenshot(path=str(shot), full_page=True)
                        rec["screenshot"] = str(shot)
                        pg.evaluate("() => { const p=document.getElementById('filterPanel'); if(p) p.hidden=false; }")
                        rec["filterSheet"] = sheet_probe(pg)
                if width == 1280:
                    shot = HERE / "screens" / f"{page_name.replace('.html','')}-wide.png"
                    pg.screenshot(path=str(shot), full_page=True)
                    rec["screenshot_wide"] = str(shot)
                rec["externalRequests"] = [u for u in reqs if not u.startswith(ALLOWED_PREFIXES)]
                report["network"].extend(rec["externalRequests"])
                entry["widths"][str(width)] = rec
                ctx.close()
            report["pages"][page_name] = entry
        browser.close()

    # ---- verdicts -------------------------------------------------------
    verdicts = {}
    for page_name, entry in report["pages"].items():
        pv = {"overflow": [], "tap": [], "axe": [], "overlay": [], "external": [],
              "filters": [], "empty": [], "freshness": [], "shareUrl": [], "sheet": [],
              "reconcile": []}
        for width, rec in entry["widths"].items():
            if rec["overflow"]["rootOverflow"]:
                pv["overflow"].append({"width": width, "detail": rec["overflow"]})
            elif rec["overflow"]["offenders"]:
                pv["overflow"].append({"width": width, "offscreen_offenders": rec["overflow"]["offenders"]})
            if rec["tapFailures"]:
                pv["tap"].append({"width": width, "count": len(rec["tapFailures"]),
                                  "sample": rec["tapFailures"][:6]})
            for v in rec["axe"]:
                pv["axe"].append({"width": width, **v})
            for step in rec.get("tab", []):
                if step["coveredBy"]:
                    pv["overlay"].append({"width": width, "step": step})
            if rec["externalRequests"]:
                pv["external"].append({"width": width, "urls": rec["externalRequests"]})
            f = rec.get("filters")
            if f is not None:
                problems = []
                if not f.get("changed"):
                    problems.append("district filter did not change the result count")
                if not f.get("chips_after"):
                    problems.append("no active-filter chip after filtering")
                if not f.get("bar_filter_changed"):
                    problems.append("drill-down bar did not filter")
                if f.get("count_after_clear") != f.get("count_before"):
                    problems.append("clear-all did not restore the full count")
                if problems:
                    pv["filters"].append({"width": width, "problems": problems, "detail": f})
            e = rec.get("empty")
            if e is not None:
                restored = e.get("after_clear") or ""
                if not (e.get("hidden") is False and e.get("count", "").startswith("0 of")
                        and "filters active" in restored and restored.split()[0] != "0"):
                    pv["empty"].append({"width": width, "detail": e})
            s = rec.get("states")
            if s is not None and not s.get("distinct"):
                pv["freshness"].append({"width": width, "detail": s})
            u = rec.get("shareUrl")
            if u is not None and not (u.get("presentation_only") and u.get("survives_reload")):
                pv["shareUrl"].append({"width": width, "detail": u})
            rc = rec.get("reconcile")
            if rc is not None:
                problems = []
                if rc.get("org_reconciles") is False:
                    problems.append("organisation bars do not reconcile with the selection")
                if rc.get("act_reconciles") is False:
                    problems.append("activity bars do not reconcile with the selection")
                if rc.get("dist_reconciles") is False:
                    problems.append("district bars do not reconcile with the selection")
                if rc.get("district_pct_total_100") is False:
                    problems.append("district percentages do not total 100")
                if not rc.get("remainder_disclosed"):
                    problems.append("a top-N ranking is not disclosed as a ranking")
                if not rc.get("metric_basis_stated"):
                    problems.append("attendance metric basis is not stated")
                if not rc.get("source_and_date_visible"):
                    problems.append("source/data-date not visible")
                if problems:
                    pv["reconcile"].append({"width": width, "problems": problems, "detail": rc})
            sh = rec.get("filterSheet")
            if sh is not None and sh.get("coversFirstViewport") and width == "375":
                pv["sheet"].append({"width": width, "detail": sh})
        verdicts[page_name] = pv
    report["verdicts"] = verdicts
    hard = 0
    for page_name, pv in verdicts.items():
        hard += len([x for x in pv["overflow"] if "detail" in x])
        hard += len(pv["axe"])
        hard += len(pv["external"])
        hard += len(pv["filters"]) + len(pv["empty"]) + len(pv["freshness"]) + len(pv["shareUrl"]) + len(pv["reconcile"])
    report["hard_failures"] = hard
    report["ok"] = hard == 0
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=None,
                    help="e.g. http://127.0.0.1:8811/ ; omit to load from file://")
    ap.add_argument("--out", default=str(HERE / "qa-results.json"))
    a = ap.parse_args()
    rep = run(a.base_url)
    Path(a.out).write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps({
        "hard_failures": rep["hard_failures"],
        "pages": {k: {kk: (len(vv) if isinstance(vv, list) else vv) for kk, vv in v.items()}
                  for k, v in rep["verdicts"].items()},
        "external_requests": sorted(set(rep["network"])),
    }, indent=2))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
