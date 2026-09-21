#!/usr/bin/env python3
"""Print the remainder disclosure and the key first-viewport text of each
concept, so the claim 'ranking is disclosed' can be checked from the artifact."""
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    for name in ("concept-conservative", "concept-recommended", "concept-divergent"):
        pg = b.new_context(viewport={"width": 1280, "height": 900}).new_page()
        pg.goto((HERE / f"{name}.html").as_uri(), wait_until="load")
        pg.wait_for_timeout(250)
        print("=" * 70)
        print(name)
        print("  remainders:", pg.evaluate(
            "() => [...document.querySelectorAll('.remainder')].map(e => e.textContent.trim())"))
        print("  first viewport:", pg.evaluate(
            "() => document.querySelector('h1').textContent + ' | ' + "
            "(document.getElementById('freshness') ? document.getElementById('freshness').textContent.slice(0,70) : '')"))
        print("  filter count badge:", pg.evaluate(
            "() => { const c = document.querySelector('.filter-toggle .count'); return c ? c.textContent : null; }"))
        print("  panels visible:", pg.evaluate(
            "() => [...document.querySelectorAll('.focus-panel')].map(p => p.id + ':' + (p.hidden ? 'hidden' : 'shown'))"))
        b_ = pg.evaluate("() => document.body.scrollHeight")
        print("  page height:", b_)
    b.close()
