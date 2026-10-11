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
  import re
  for name in ['index.html','review-analytics-v48/index.html','review-current-v51/index.html']:
   current=(ROOT/name).read_text()
   baseline=subprocess.check_output(['git','show','e74e128:'+name],cwd=ROOT).decode()
   # Runtime scripts are immutable except removal of obsolete root nav controller
   scripts=lambda x:re.findall(r'<script(?: [^>]*)?>(.*?)</script>',x,re.S)
   old,new=scripts(baseline),scripts(current)
   old_nonempty=[x for x in old if x.strip()];new_nonempty=[x for x in new if x.strip()]
   self.assertEqual(old_nonempty[1:] if name=='index.html' else old_nonempty,new_nonempty)
   # Existing main contents (including auth hooks, hidden states, receipts) locked.
   def main(x):
    x=x[x.index('<main'):x.index('</main>')]
    x=re.sub(r'^<main[^>]*>','<main>',x)
    x=re.sub(r'<nav.*?</nav>','',x,flags=re.S)
    x=re.sub(r'<details class="source-options">.*?</details>','',x,flags=re.S)
    x=re.sub(r'<p class="source-note">.*?</p>','',x,flags=re.S)
    x=re.sub(r'<p class="l2-activation">.*?</p>','',x,flags=re.S)
    return re.sub(r'\s+',' ',x).strip()
   self.assertEqual(main(baseline),main(current),name)
   self.assertEqual(current.count('data-destination='),3)
   self.assertEqual(current.count('aria-disabled="true"'),4)
  current=(ROOT/'index.html').read_text()
  self.assertGreater(current.index(DEMO),current.index('$("expAll").addEventListener'))
if __name__=='__main__':unittest.main()
