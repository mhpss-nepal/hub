#!/usr/bin/env python3
"""Focused debug of the phone filter sheet state (not part of the QA record)."""
from pathlib import Path
from playwright.sync_api import sync_playwright

url = (Path(__file__).resolve().parent / "concept-recommended.html").as_uri()
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 375, "height": 900}).new_page()
    pg.goto(url, wait_until="load")
    pg.wait_for_timeout(200)
    print("initial hidden:", pg.evaluate("() => document.getElementById('filterPanel').hidden"))
    pg.click("#filterToggle")
    pg.wait_for_timeout(120)
    print("after toggle hidden:", pg.evaluate("() => document.getElementById('filterPanel').hidden"),
          "display:", pg.evaluate("() => getComputedStyle(document.getElementById('filterPanel')).display"),
          "position:", pg.evaluate("() => getComputedStyle(document.getElementById('filterPanel')).position"))
    pg.evaluate("() => { document.getElementById('filterPanel').hidden = true; }")
    pg.wait_for_timeout(120)
    print("after direct hide:", pg.evaluate("() => document.getElementById('filterPanel').hidden"),
          "display:", pg.evaluate("() => getComputedStyle(document.getElementById('filterPanel')).display"))
    pg.evaluate("() => document.getElementById('stateDemo').scrollIntoView({block:'center'})")
    pg.wait_for_timeout(200)
    el = pg.evaluate("""() => {
      const b=document.querySelector('button[data-state="stale"]');
      const r=b.getBoundingClientRect();
      const top=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2);
      return { y: Math.round(r.top), tag: top&&top.tagName, id: top&&top.id,
               cls: top&&top.className, panelHidden: document.getElementById('filterPanel').hidden,
               panelDisplay: getComputedStyle(document.getElementById('filterPanel')).display }; }""")
    print("hit test:", el)
    b.close()
