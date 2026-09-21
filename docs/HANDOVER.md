# Handover to WHO — start here

This repository (`mhpss-nepal/hub`) is the coordination layer and the home of **every asset every
other layer shares**. It is one of three published surfaces:

| Layer | Repository | URL |
|---|---|---|
| **Layer 1** — field forms | `mhpss-nepal/form` | https://mhpss-nepal.github.io/form/ |
| **Layer 2** — coordination hub (this repo) | `mhpss-nepal/hub` | https://mhpss-nepal.github.io/hub/ |
| **Layer 3** — public site | `mhpss-nepal/mhpss-nepal.github.io` | https://mhpss-nepal.github.io/ |

## What this system is

**Coordination, not case management.** It does not hold individual-level information. No names, no
NIK, no phone, no diagnosis, no individual score, no photo. The register is counts and coordination
facts; a client name may never sit in the same document as an aggregate number.

## Read, in this order

1. **`docs/OPERATOR-GUIDE-WHO.md`** — how to read the dashboard, how to publish, how to add a user,
   and **what must never be published**.
2. **`docs/RUNBOOK.md`** — where every job runs, its cadence, how to refresh data, and how to roll
   back. Everything here is **AI-free and runs on GitHub**, so it outlives any one contract.
3. **`docs/DATA_MODEL.md`** — the record model and its mapping to the IASC 4Ws.
4. **`exchange/README.md`** — the pull-only data feed for OCHA/NDRRMA (HXL CSV, P-code join key).

## Status at handover (honest)

- **Live and verified:** all three layers HTTP 200; the exchange feed live and content-verified.
- **AI-free operations:** the exchange build and the NDRRMA capture are scheduled GitHub Actions
  running the Python standard library only — no model, no agent, no person at a keyboard.
- **Security floor:** the role- and kind-scoped Firestore rules (v4) are **written and
  emulator-verified (38/38, guards proven by mutation)**; they are **applied in the Firebase
  console** and that application is an operator action.
- **Not yet published, deliberately:** the Layer 3 small-cell redaction fix. **Do not publish real
  data to `public_stats` until it is live.**
- **Deliberately not built:** HMIS/DHIS2. It is a considered seam, not a component.

## Ownership

Ownership (system owner, data controller, the Firebase/GCP project owner, the billing owner, the
indicator approver, and the OCHA acceptance owner) is an **institutional decision**, recorded in the
project's decision ledger. Nothing here depends on one person's laptop or one person's server.
