# Automatic private historical baseline candidate

Status: implemented and isolated-tested; not deployed, seeded in production, independently reviewed or publicly approved. No recurring private file import.

## Reader boundary

Default `/hub/` and `?source=historical` synchronously select `baseline-auth.js` BEFORE any legacy `fb.js` runs. This adapter imports only Firebase App/Auth 10.13.0, uses the same project/config and explicit `browserLocalPersistence`, supports existing password/email-link providers, and subscribes to `onIdTokenChanged`. It does not import Firestore, expose a legacy FB object, read/flush queues or register watchers. The private 12-key summary stays in page memory; Clear/sign-out/error/offline erase cards, hidden provenance and CSV state. Generation + abort + current-user checks fence delayed replies.

Refresh/open/auth change calls fixed `GET https://mhpss5ws-tdp3xtfnsq-as.a.run.app/admin/baseline`, with only bearer Authorization, omit credentials, no-store, redirect refusal and 30-second abort. Production access is enforced by the server, not this public JavaScript. Authentication alone is not entitlement: only the enabled exact primary admin binding qualifies. Backup/reporter/legacy roles do not. No token is put in DOM, application logs or custom storage. Firebase manages its own explicitly persistent session.

`?source=choose` and `?source=live` intentionally retain the original bridge and its legacy behavior. Switching from a historical-only session to live is a full explicit reload; switching from legacy to historical is also a reload to prevent retained writer/listener callbacks. The existing synthetic/local/export sources remain separate; no historical summary reaches inline ALL/DATA or publisher state. Legacy defects are not fixed or certified by this change.

## Backend/version boundary

`functions/baseline.py` dispatch is additive. Only `adapter.py` changes among the 43 deployed source files. All identity/admin/test/runtime/intake/backend/validator primitives and requirements remain byte-identical to active source revision `mhpss5ws-00004-zan`.

Server reads only admin control `mhpss5wsAdminControlV1/bootstrap`, current pointer `mhpssHistoricalBaselineControlV1/current`, and the version document under `mhpssHistoricalBaselineVersionsV1/<validated-version>`. It uses a read-only consistent transaction, rechecks live pointer/version/control and revocation-aware identity before response, never queries raw children or reports, and performs no GET audit/database writes. Missing/corrupt/unverified/provider failures return sanitized 503; missing bearer 401; refused authority/origin 403. CORS exact origin only, no-store/nosniff/no-referrer/Vary Origin. No IAM/Rules/grants/Auth/billing change.

The exact 12-key summary schema remains `mhpss-private-historical-summary-v1`; version grammar explicitly permits immutable maintained `historical-master-vN`. Source dates, read time and reporting period are distinct. Unit is service contacts, not unique people. Organisation/site/trend/joint-demographic dimensions remain unavailable, not fabricated charts/zeroes. Later unverified forms never contribute to historical contacts. Public aggregate publication remains separately gated.

## Operator maintenance and rollback

`backend/tools/seed_historical_baseline.py` defaults to dry-run and constructs no cloud client then. It verifies the immutable master against the source manifest, strict nullable typed counts/class/lineage and a separate scoped apply manifest, preserving `database_import_authorised:false` in the original. The payload stores an even smaller child projection: count/class/source digests/opaque source-identity hash and row lineage only; no raw date/count strings, IDs, contact values, narratives or clinical values. Historical and quarantined children are stored separately. Actual protobuf document sizes are measured; bounded maximum 400 writes, document 128KiB and 6MiB payload guard.

Apply is create-only immutable stage transaction → complete exact readback → transactional full readback and CAS current-pointer promotion → exact pointer readback. Identical replay is no-op; conflict/partial stage/stale pointer fails closed. Interrupted staging may leave a complete inactive immutable version, never a half-active version. Corrections require new version, predecessor, reason and reviewed source/apply manifest; old version remains intact.

Use a private rollback capsule containing the previous pointer plus exact previous version/children. `rollback_historical_baseline.py` checks capsule class counts and entries digest, explicit reviewed rollback decision and expected current CAS, then promotes only the previous verified pointer at a higher revision. Never delete either version. Initial activation has no previous baseline: rollback the Hub/Function to the pinned prior release (which has no baseline route), retain inactive data privately; do not invent a previous pointer or delete history.

## Evidence and release gates

See workspace `HANDOFF.md`, `RESULT.json`, `evidence/` and the AB01–AB16 ledger. Synthetic Chromium transport instrumentation and genuine local Auth/Firestore transactions are separate proofs, not production signed-session proof. This change does not certify operational report ingestion, all-device persistence, clinical approval or 13/13 backend readiness.
