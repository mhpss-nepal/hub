from pathlib import Path
R=Path(__file__).parents[1]
def test_owner_review_wired_no_public_or_automated_metrics():
 js=(R/'assets/selfreport-surface.js').read_text();homes=(R/'assets/instrument-homes.js').read_text();page=(R/'index.html').read_text()
 assert 'SelfreportSurface.mount' in homes and 'assets/selfreport-surface.js' in page
 assert "BASE+'/selfreport/current'" in js and "Authorization:'Bearer '+token" in js
 assert 'pending privacy' not in js # held, not fabricated metrics
 assert 'Public aggregates held' in js and 'paint(d)' in js and 'await read()' in js
 assert 'rows.replaceChildren()' in js and 'BaselineAuth.onChange' in js and "credentials:'omit'" in js
