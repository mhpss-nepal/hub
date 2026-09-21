# Runbook — what runs, where, and what to do when it breaks

Last updated at handover, 2026-09-21. **Everything here is AI-free**: no job in the running loop
needs a model, an agent, or a person at a keyboard.

---

## 1. The three published layers

| Layer | Repository | URL | Language |
|---|---|---|---|
| Layer 1 — field forms | `mhpss-nepal/form` | https://mhpss-nepal.github.io/form/ | **Nepali** on the field surface |
| Layer 2 — coordination hub | `mhpss-nepal/hub` | https://mhpss-nepal.github.io/hub/ | English |
| Layer 3 — public site | `mhpss-nepal/mhpss-nepal.github.io` | https://mhpss-nepal.github.io/ | English |

**Publication:** `main` is protected; a change lands through a pull request and is verified against
the **live site**, never the branch. GitHub Pages re-publishes automatically (allow ~30–60 s).

**Cache:** `sw.js` carries a version (`mhpss-np-field-v43`). **Any change to a precached file must
bump the cache name** — `form/tools/precache-fingerprint.py` regenerates the fingerprint and the
`sw-precache-check` gate fails if you forget.

## 2. The recurring jobs — where each one actually runs

### 2a. On GitHub (outlives the contract) — the handover target

| Job | Where | Cadence | What it does |
|---|---|---|---|
| Exchange feed build | `hub/.github/workflows/exchange-weekly.yml` | weekly (Mon 03:30 UTC) + manual | rebuilds `/exchange/` from the frozen snapshot; commits **only** if the snapshot moved |
| NDRRMA weekly capture | `mhpss-nepal.github.io/.github/workflows/ndrrma-weekly.yml` **— written, reviewed, NOT YET ENABLED** | weekly (Mon 02:15 UTC) | captures the public NDRRMA 5Ws aggregates |

The exchange job has been **run green on GitHub's runners** (run `35555460537`): contract tests pass,
the rebuild and `--verify` succeed, and an unchanged week logs *"no commit required."*

### 2b. Still on the project server (Hermes cron) — **a known handover gap**

These are `no-agent` (script-only, no model) but they run on the development server, which **does
not outlive the contract**. They must move to institution-owned infrastructure before handover:

| Job | Cadence | Must move to |
|---|---|---|
| Firestore logical backup | daily 13:00 | an institutional target (the GCP project owner's choice) |
| Nightly backup to the operator's laptop | daily 14:00 | an institutional target, or drop |
| Weekly NDRRMA 5Ws snapshot | Mon 09:00 | the reviewed GitHub Action above (needs a go-ahead to push) |

### 2c. Agent-lane jobs — these simply go away

`pending work reminder`, `morning readiness brief`, `provider-error watch`, `Codex quota alert`,
`efficiency evaluation`. They serve the *development* lanes, not the system. Nothing depends on them.

> **The honest statement:** the exchange feed and (once enabled) the NDRRMA capture are AI-free and
> institution-owned. The **backups still run on the server that ends with the contract** — moving
> them is an ownership decision, not a coding task, and it is recorded as open. **Nothing in the
> running system needs a person until that is resolved; the failure mode is a missing backup, not a
> missing dashboard.**

## 3. How to refresh the exchange feed

1. Capture the new public aggregate snapshot and update `exchange/source/baseline.json` (and
   `pcode-map.json` if geography changed) — **regenerate, never hand-edit a figure**.
2. Run `python3 tools/exchange/build_exchange.py` and commit the result, or let the weekly Action do
   it. `python3 tools/exchange/build_exchange.py --verify` asserts the committed files match.
3. The build **refuses** (exit 2, no traceback) if the contract breaks: a missing P-code, a missing
   metadata field, an additive claim on a non-additive measure, a below-floor value, or any identity
   key in the source.

## 4. What to do when something breaks

| Symptom | First check | Then |
|---|---|---|
| A live page is 404 or stale | the repository's **Actions → pages-build-deployment** run | re-run the deployment; confirm the commit landed on `main` |
| The dashboard shows *"The register refused the read"* | the signed-in account's **role** | an admin adds the address on the Access page. This is the server protecting the data, not a bug |
| The exchange feed is stale | `hub` Actions → *Exchange feed build* | trigger it manually (`workflow_dispatch`). If it fails, read the log — a contract failure names the field |
| A form's figures look inflated | the record's `kind` | the hub reads per-kind; a wrong `kind` on a record is a data entry issue, not a display one |
| Storage warning on a phone (*"Saved for this page only"*) | the phone's browser privacy mode | ask the officer to export, then record normally — nothing is lost until they close the page |

## 5. Rollback

- **A published change:** revert the merge commit on `main`; Pages re-publishes. Nothing is destructive.
- **A scheduled job:** *Disable workflow* in the repository's Actions tab, or delete the workflow in a
  reviewed commit. The last committed artifacts are inert and can stay.
- **A bad data snapshot:** the dated exchange files are never overwritten, so the prior version is still
  fetchable; restore `exchange/source/baseline.json` and rebuild.

## 6. The rules that do not bend

- **Never write a credential value anywhere** — not in a file, not in a chat, not in a commit.
- **Never publish real data to Layer 3** until the small-cell redaction fix is live (see the operator guide §3).
- **Never store raw submissions, exports, backups, or credentials in GitHub.**
- **Read access is the boundary:** if data must not be seen by someone, it must not be sent to them.
- **A client name may never sit in the same document as an aggregate number.**
