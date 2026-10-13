# Unified dashboard houses — candidate handoff

## Result and boundary

Implemented in the existing `index.html` dashboard and its single sidebar, retaining the six-card Home and existing 5Ws iframe/reader. Eight source instruments (5Ws plus seven siblings) map to eleven visible destinations including separate GBV, Historical Baseline and Sample Data. PHQ-9 and anonymous Self-report remain distinct. Provider register and service points are distinct review homes. Parked clinical/directory forms are not linked or activated; old deleted contact/referral links were replaced with safe homes.

Training is an integrated dashboard: event/participation/partner-held cards, event table, date/organisation/event-district filters and actual structured English CSV. Uses existing `TRAINING_API` complete paging, metadata/schema validation and content hashes for own history. Unknown/denied/loading/failed values are dashes; partner-held participation counts are unknown. No synthetic figures ship in application assets. `training.html?view=own` is polished separate personal history; old `?view=current` resolves to the main training house.

## Authority contract

Apply with backend candidate `3fd05578f8588786410ca42c6a0275bb0ac2cfe9` and `51-operational-closure/all-homes/ADMIN-CONTRACT-NOTE.md`.

`staff-account/1` top-level shape unchanged. Exact accepted ordered sections: `5ws, contacts, referrals, phq9, selfreport, training, providers, servicepoints, gbv, baseline, sample`. The strict decoder's only delta is those four canonical keys; it creates no grant. Server-validated administrator role opens all homes even during the older profile transition with omitted sections. No client email allowlist grants access. Ordinary role scopes and backend enforcement remain unchanged.

Administrator processed training uses `/dashboard/training` across organisations; ordinary approved training readers retain `/training/current`; personal history remains `/training/entries`. Administrator raw view remains existing 5Ws `/admin/entries`, not an all-form raw reader. Unsupported clinical/Self-report/directory destinations say authorised but not connected, never zero or another approval request. Backup administrator baseline is a precise current-reader implementation limitation, not a new grant requirement; primary continues its existing direct reader. No clinical data is read or activation inferred.

Frontend-first publication is required before the backend starts returning new keys. Parent alone owns publication, merging and deployment.

## Preservation

No edits to `assets/store.js`, `assets/codes.js`, `assets/i18n-strings.js`, 5Ws schema/form/collector, current auth, service workers, queues or legacy records. Tests pin bytes to fresh `b330e73018908b8330d4b287265f3b6cc6fb5929`. Training transport changes only optional admin processed-reader route selection; enqueue/send/hash/validation/CSV remain byte-preserved after subtracting that exact delta.

## Executed evidence

- `uv run --with playwright python tests/all-homes-browser.py`: actual Chromium, 390 and 1280, eleven destinations, preserved six-card Home, EN→NE→EN switching, current route/Back, separately approved baseline/sample direct destinations, two-page training listing, actual CSV download and structured participant cells, filter selection, read refusal, account switch, sign-out, integrated/standalone history, old and expanded administrator profiles, admin `/dashboard/training` selection. Explicit synthetic Auth/HTTP fixtures ONLY, never provider proof. No outbound POSTs.
- `python tests/test_all_homes_scope.py`: 5 preservation/scope tests pass.
- `node tests/landing-contract.cjs`, `node tests/landing-correction.cjs`, `node tests/training-journey.cjs`, `node tests/training-cr1.cjs`: pass.
- Root capable discovery: 35 tests, pass, 1 missing external field-build skip.
- Module-only axe WCAG A/AA/2.1: zero violations and zero incomplete at both widths after fixing keyboard-scrollable table region. New module interactive targets measured ≥44×44; no document horizontal overflow. These are not a whole-application accessibility certificate.
- Full-page screenshots for instrument homes, plus ordinary training viewport and own-history screenshots in `all-homes-evidence/`. First metric now fits the ordinary phone viewport. Visual review led to compacted duplicate chrome; final owner visual acceptance and combined independent review remain parent gates.
- `git diff --check`: pass.

## Known inherited/general-suite limitations

Nested discovery has inherited `test_dashboard_visual_contract.test_controls_and_assets_exact` failure (old expected hub-shell stylesheet vs already-published hashed stylesheet + home-nav); reproduced against archived exact fresh base with repository Git metadata. No changed file causes it. Capable nested field-output browser tests also reference an absent legacy path (404 / missing #read) and two Firestore-emulator cases skip without :8081. Those unchanged pages/tests are outside this lane. Initial plain Python lacked Playwright; capable root/new browser suites were rerun via uv rather than counted as passes.

## Remaining gates

Parent must merge the parallel Hub three-file lane, run independent combined frontend/backend review, publish frontend before backend, and verify genuine administrator and ordinary scoped accounts. This candidate does not claim seven operational sibling receivers, new all-form personal history, real provider/API data verification, clinical activation, all-form raw export or complete Nepali translation. Existing language engine/toggles are preserved; new home-specific explanatory copy is explicitly English pending review. Provider/service-point registrations require review, not automatic public publication. No legacy auto-upload.
