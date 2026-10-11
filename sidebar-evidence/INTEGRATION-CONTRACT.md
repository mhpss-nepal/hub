# Layer 2 navigation and Claude-authored form integration contract

Owner instructions, 11 October 2026. Implementation authority is limited to the existing Hub navigation candidate; this document does not activate forms, grant access, or publish clinical data.

## Three first-class destinations now

| Label | Existing destination | Source and boundary |
|---|---|---|
| 5Ws Reports | `/hub/review-current-v51/` | Automatic authenticated own-reporter/own-organisation API read after discovery; empty is a valid complete snapshot. Real submission activation remains false. Named reporter/org authority and scoped private backup custody/restore decision remain held. Admin/WHO identity alone is not a reporter grant. |
| Historical Baseline | `/hub/review-analytics-v48/?source=historical` | Fixed retained historical v2 source, private automatic authorised API read; not a manual upload, embedded public JSON, operational reporting, or reseeding action. Owner describes 300+ retained records; current baseline proof uses 300 historical entries with separate quarantined later forms. Preserve source version, dates, gaps, units and CSV. |
| Sample Data | `/hub/?source=demo` | Existing fixed-seed deterministic synthetic sample, fixed September 2026 dates. Reload reproduces identical values and membership. Not operational totals; do not remove until real-data acceptance is separately confirmed. |

Root arrival resolves to existing 5Ws Reports; historical root alias resolves to the existing historical reader. Auth action query parameters and hash are preserved. No new preview pages. Website Layer 3 keeps its top navigation, untouched.

Future menu items are explicitly unavailable, without placeholder routes: Individual Contacts; Referrals; PHQ-9 Follow-up; Admin Audit. Referrals require restricted case-management origin, destination, reason and status, with reviewed mapping/merge requirements. Admin Audit requires backend-enforced Adib-only entry history (actor, form, date/time); known WHO/Gmail administrator bindings do not establish this new entitlement. No public clinical/referral details or API grants are authorised.

## Claude form handoff: yes, adaptable, not automatic activation

Existing engine can adapt GitHub-published forms when the released package has:

- Stable form/instrument ID, record ID semantics and kind; explicit schema and payload version.
- Typed payload mapping, required/optional/null/unknown semantics, code-list versions and units.
- Authenticated transport author identity supplied and verified by the server, never trusted from an HTML field or inferred from email domain.
- Common entry adapter plus instrument-specific mapping and authorised dashboard renderer; reuse server validation, immutable retry identity, content-bound revision receipts and access checks.
- Tested correction lineage, account/organisation isolation, pending-device recovery, receipt/readback and CSV parity for the changed instrument.

Preserve native reviewed form content, bilingual provenance and anonymous respondent model. Labels/layout-only changes do not require a backend rebuild when stable schema and security semantics are unchanged. Schema/security changes require only the affected validation, access, receipt/retry and projection checks, not an automatic whole-platform rebuild. No claim that every new form instantly synchronises.

Current joint age-by-sex implementation is authoritative: **0–4, 5–9, 10–17, 18–59, 60+**; Female/Male and distinct Other/Not recorded semantics. Do not restore older draft bands, invent ages, or infer historical joint cells. Preserve historical age definitions and flag unknown/missing values. Current candidate changes no form content, ages, referral merge or backend; later content/referral changes need exact reviewed package/mapping handoff and affected checks only.

## Release boundary

One Hub writer in `51/publication/current-hub`, fresh main containing PR42. Candidate commit, loopback browser evidence and hash reuse are preparation for parent independent delta/visual review and protected landing. No self-release, deployment, PR, cloud mutation, credential action, Luna write or additional worker is authorised by this contract.
