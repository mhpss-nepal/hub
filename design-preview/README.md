# Lane C candidate — independent review pending

Executor and canonical output: Thar Lay/server. No Luna synchronization, cloud writes, account operations, GitHub push or publication.

Baseline: Hub main `1775af56d9be12e2f76d8d9a4e45631f6933cd58`, freshly cloned/fetched before branching. The served index and eleven runtime assets matched this baseline. See `live-pins.json` and the parent lane's evidence/live-index.html.

## Scope

Existing dashboard only: Overview, Reports, place/date/organisation filters and the original CSV export are primary. Existing Who/What/For whom, roster/duplicate/historical breakdown, other filters and publication panels are progressive disclosures. Three cards retain the existing report, attendance and organisation formulas and show source period; activity participations are not invented. Existing runtime modules, clinical dictionary, auth, persistence and publication/export handlers remain unchanged. `block-parity.json` pins seven exact inline blocks and ten unchanged modules/styles. Headline presentation and the day-table scroll-region attributes are the permitted inline-script markup changes.

`dashboard-preview.html` is a self-contained artifact derived from the actual candidate, with embedded assets, a rejecting Firebase stub, `connect-src 'none'` and a visible preview-only warning. Open it as a file; synthetic demonstrations and file import/export work. Do not import real records. Sign-in and publishing are disabled. This is not an operational deployment or confirmation of delivery.

## Evidence and bounded commands

Run from the candidate repository, using the server's existing Playwright environment:

    /usr/local/lib/hermes-agent/venv/bin/python tools/lane-c-tests/03-contract.py
    /usr/local/lib/hermes-agent/venv/bin/python tools/lane-c-tests/12-bounded-compare.py
    git diff --check

Previously executed rendered suites, not rearmed during the final freeze:

    /usr/local/lib/hermes-agent/venv/bin/python ../05-browser.py
    /usr/local/lib/hermes-agent/venv/bin/python ../10-preview-qa.py

Their portable copies are `tools/lane-c-tests/05-browser.py` and `10-preview-qa.py`. They require the existing Chromium binary `/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome`. All browser contexts are synthetic and route-blocked, service workers blocked, with transient exact-origin HTTP listeners shut down afterward. The packaged axe dependency avoids a network download during replay.

Executed evidence: source-contract 9/9, baseline/candidate browser 150/150 (42 scenarios), isolated preview 43/43, final bounded CSV comparator 9/9. Existing store/read-scoping unit tests 5/5; token parity nine declarations, read-scope guard and its intentionally broken self-test passed. Browser geometry, label/contrast axe and keyboard checks cover 320/390/1280 px. Browser artifacts and screenshots belong to the exact source SHA in `browser-report.json`; the preview hash is in `preview-qa.json`. These are implementer tests, not independent approval.

## CSV finding

Baseline and candidate CSV bytes match for the same initial synthetic state, and match again after the same export/reimport operation. Initial SHA-256: `f78f29e4ef9ebc99b810cfb624de839deae15ad49899a34de5754525aebd536e`. Reimported SHA-256: `f44869dabb779d9d4d3a7395ce225aaf7df4ef2f9189cbaa5916af5e62225340`.

Each version's own initial and reimported export differ identically: the legacy CSV path loses the fixture's donor tag and folded sex/age values when re-exporting. This is pre-existing behavior, not a cosmetic-branch regression. CSV is therefore not attested as a lossless archival roundtrip. No handler was changed to hide the finding. Earlier unfinished extra-contract work is excluded from passing totals and retained only in the parent lane's diagnostic evidence.

## Limitations and parent gates

No real Auth/backend access, operational write/readback, typed-v2/admin integration, public publishing or independent review. Nepali switch is functional but dashboard prose uses the existing explicitly disclosed English fallback. Existing legacy aggregate/age semantics remain unchanged and may require separately approved compatibility work. Role-based publishing capability remains the baseline's authority, behind Advanced; only the isolated preview forcibly refuses it. Review exact source and commit before any integration/publication. Parent owns all publication decisions.

Screenshots are named `head-{320,390,1280}-{overview,reports,analysis,roster,publish,empty}.png` plus baseline comparisons and Nepali preview captures. `manifest.json` pins evidence files; final absolute paths, commit/tree and changed-file inventory are in the lane-level HANDOFF.md and STATUS.json.
