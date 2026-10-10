"""V50 approved links/styles and exact-demo entry; all remaining HTML is pinned."""
import unittest, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='36da1798a04010e79050d45f6c98e77daf081d06'
STYLE='/* V50 source navigation: links only; no source or account state. */\n  body.hub.dashboard-selected .source-nav{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}\n  body.hub.dashboard-selected .source-nav a{display:inline-flex;align-items:center;min-height:44px;min-width:44px;padding:8px 12px;border:1px solid var(--line);border-radius:var(--r);background:#fff;color:var(--who-d);font-size:13px;font-weight:700;white-space:normal;max-width:100%;box-sizing:border-box;overflow-wrap:break-word}\n  body.hub.dashboard-selected .source-nav a:focus-visible{outline:3px solid var(--who-d);outline-offset:2px}\n  body.hub.dashboard-selected .source-note{font-size:12px;color:var(--slate);margin:0 0 14px}\n'
DEMO='  // Explicit demo URL reuses the existing registered handler; normal arrival is unchanged.\n  if (new URLSearchParams(location.search).get("source") === "demo") $("useDemo").click();\n'
NAV_MAIN='  <nav class="source-nav" aria-label="Dashboard data sources">\n    <a href="?source=choose">Dashboard home</a>\n    <a href="review-analytics-v48/?source=historical">Historical data (real retained records)</a>\n    <a href="?source=demo">Synthetic demo (generated examples, not real service figures)</a>\n  </nav>\n  <p class="source-note">Historical data retains source gaps. The demo is synthetic and never fills missing historical fields; its figures and units are not a performance comparison.</p>\n'
NAV_REAL='  <nav class="source-nav" aria-label="Dashboard data sources">\n    <a href="../?source=choose">Dashboard home</a>\n    <a aria-current="page" href="?source=historical">Historical data (real retained records)</a>\n    <a href="../?source=demo">Synthetic demo (generated examples, not real service figures)</a>\n  </nav>\n  <p class="source-note">Historical data retains source gaps. The demo is synthetic and never fills missing historical fields; its figures and units are not a performance comparison.</p>\n'

class SourceNavigation(unittest.TestCase):
 def test_exact_approved_html_delta(self):
  for name,nav in [('index.html',NAV_MAIN),('review-analytics-v48/index.html',NAV_REAL)]:
   current=(ROOT/name).read_text()
   self.assertEqual(current.count(STYLE),1)
   self.assertEqual(current.count(nav),1)
   restored=current.replace(STYLE,'').replace(nav,'')
   if name=='index.html':
    self.assertEqual(restored.count(DEMO),1)
    # Execute only after the full runtime initializes, not immediately after listener registration.
    self.assertGreater(current.index(DEMO), current.index('$("expAll").addEventListener'))
    restored=restored.replace(DEMO,'')
   self.assertEqual(restored,subprocess.check_output(['git','show',BASE+':'+name],cwd=ROOT).decode())
if __name__=='__main__':unittest.main()
