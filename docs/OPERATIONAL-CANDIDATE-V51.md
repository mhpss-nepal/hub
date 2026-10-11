# Operational bridge candidate v51 — NOT independently approved

Base: `24770e638c913a987855da2ee7e63da3e7bd718f`. One branch; no deployment, push, Rules, grants or native/historical migration.

## Runtime changes

- STORE correction merges unedited fields, keeps local revision history and saves a stable bridge `_rid`. New reports bind it to kind + source ID. Existing local reports retain explicit `_rid`, otherwise reconstruct their original legacy ID from the oldest retained local version. This does not reconcile already-forked remote duplicates or interpret old queued bodies.
- New outboxes are keyed and enveloped by captured origin/project/collection/scope before SDK initialization. Legacy key presence is detected through key names only. Old bytes are neither read, parsed, flushed, retired nor rewritten; the visible private-export action requires confirmation and downloads their exact bytes. Wrong-bound/malformed current envelopes are withheld unchanged. An existing explicit pending `_rid` is not recomputed.
- SDK dispatch is serialized; exact-entry acknowledgment cannot retire a newer correction; new correction queued in flight gets a following dispatch. Focal contact exclusions remain unchanged.
- Every actual kind reader enumerates server-only 500-row pages ordered by document ID, max 10000 rows per kind, twice. Unequal scans/cache/refusal/session drift/overflow block completion. No broad query fallback. Generic unscoped watch refuses. Root and field-output reader clear/hide incomplete outputs; root CSV/publication clicks are blocked. Forms withhold each incomplete kind and block that kind's CSV.
- Revalidation occurs every 60 seconds, not real-time snapshot listening. The page labels this honestly. Two matching enumerations are NOT an atomic snapshot, nor proof of a continuously stable collection; transient change/revert between reads can evade detection. If atomic point-in-time guarantees are a release criterion, this candidate does not satisfy it. Do not label it native snapshot protocol.

## Exact missing trusted new-report seam

Read-only inspection of `/48-historical-analytics/backend` at `785e3ec0ea439bb8f4540f442d5443dbc9a499f4` found a real GET `/current` API (`functions/adapter.py:29-59`, `backend.py:47-87`). It requires Bearer authentication + `X-Selected-Org`; existing V2 grant must authorize reporter's own organisation/current reports. Its `own-current-pages/1` cursor carries a fixed readTime and subject/org scope. Pages expose immutable lineage-verified native payloads, not the Hub's flat `mhpss-np-5ws/5ws-np-0.7.0` rows.

`contract_adapter.py:1-29` permits new writes only in exact approved joint 0.4 schema; historical 0.3 is immutable history, no coercion. Current actual root STORE saves the flat legacy schema directly to SDK `submissions`; no reviewed flat report -> joint payload/identity/grant/correction adapter exists here. `/admin/test/current` is separate TEST-only; `/admin/baseline[/analytics]` is separate historical aggregate data. Neither is a compatible new-report reader for this root report. This candidate therefore does NOT fabricate a report→trusted API→Hub journey, create grants, rebin age-sex/disability, or merge native/history into legacy output. Required seam: reviewed new-report producer and exact schema renderer/export adapter, authorized existing identity/org selection, current-page snapshot consumer, and end-to-end proof on the same permitted scope. Parent decides that work; do not widen access to make the legacy screen appear complete.

## Replay

```sh
cd /root/mhpss-nepal-final-forms/2026-10-06/45-automatic-baseline/hub
HUB_TEST_BASE=24770e638c913a987855da2ee7e63da3e7bd718f node --experimental-vm-modules tests/operational_bridge.cjs # expected RED, exit 1
node --experimental-vm-modules tests/operational_bridge.cjs
/root/mhpss-nepal-final-forms/2026-10-06/45-automatic-baseline/.venv/bin/python tests/operational_browser.py
/root/mhpss-nepal-final-forms/2026-10-06/45-automatic-baseline/.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

The old locked presentation/historical/navigation tests intentionally pin pre-candidate runtime bytes and fail where this authorized candidate changes them. They are not rewritten or waived by the child. Parent review must adjudicate intentional deltas and authorize a new preservation inventory; a passing targeted suite alone is not full regression clearance.

## Release gate / limitations

1. Independent review of exact candidate tree and any sibling Form patch. One writer only. Clinical text/design, private review v47/v48, navigation, public Layer3 remain byte-identical outside intentional operational changes.
2. New ID/queue compatibility with deployed Rules is NOT tested against cloud. Existing historical forks need separate human-reviewed reconciliation; no automatic rekey/delete/merge. Shared legacy queue stays quarantined until provenance review; private consent export is NOT migration authorization. Cached old fb.js can still flush old queues; publication must invalidate/version all consuming bridge assets and protect legacy devices before rollout.
3. Same-page write serialization is NOT cross-tab/device transaction control or native immutable revision compare-and-swap. A stale source retry from another context can overwrite a newer flat document; no server-side revision authorization is invented.
4. Double enumeration costs up to 20000 document reads per kind per successful 60-second refresh (plus terminal pages; root activity only, forms four separate kinds). No load, cost, offline field continuity, production authorization, clinical approval or sustained capacity claim. No new billing changes.
5. Current SDK enumeration is bounded by row count and a 30-second completion deadline; it is not atomic. A deadline blocks late results but does not cancel an already-running SDK request. Errors block outputs, not partial success. Raw root table deliberately displays first 400 with explicit count; all 2501 synthetic records are included in actual downloaded CSV and aggregate counts. Synthetic SDK/browser evidence is not signed operational acceptance.
6. Parent owns protected publication and ledger. No 13/13 completion promotion. No listeners started; fresh Chromium contexts close at test completion.
