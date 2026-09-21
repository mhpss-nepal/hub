#!/usr/bin/env python3
"""What is actually inside the first viewport on a phone? Report the elements
whose top is above the fold, so 'at a glance' is measured, not asserted."""
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    for name in ("concept-conservative", "concept-recommended", "concept-divergent"):
        pg = b.new_context(viewport={"width": 375, "height": 812}).new_page()
        pg.goto((HERE / f"{name}.html").as_uri(), wait_until="load")
        pg.wait_for_timeout(250)
        out = pg.evaluate("""() => {
          const fold = window.innerHeight;
          const rows = [];
          document.querySelectorAll('main > *').forEach(el => {
            const r = el.getBoundingClientRect();
            if (r.top < fold) rows.push({ tag: el.tagName, id: el.id,
              cls: (el.className || '').toString().slice(0,30),
              top: Math.round(r.top), h: Math.round(r.height),
              text: el.textContent.trim().replace(/\\s+/g,' ').slice(0, 90) });
          });
          return { fold, rows, height: document.body.scrollHeight };
        }""")
        print("=" * 72)
        print(name, "viewport 375x812  page height", out["height"])
        for r in out["rows"]:
            print(f"  top={r['top']:>5} h={r['h']:>5} {r['tag']}#{r['id']}.{r['cls']}")
            print(f"        {r['text']}")
    b.close()
