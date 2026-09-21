# MHPSS Nepal — exchange feed (pull-only)

**This folder is a pull target for our humanitarian partners. You fetch it; we never push
into your systems, and we hold no credential for anywhere else.**

It carries **aggregates only** — the figures already published on the NDRRMA/OCHA public 5Ws
dashboard, MHPSS sector, Rasuwa Flood Response. **No individual, case or identity data ever
passes through this feed.**

## The URL is the contract

| File | What it is |
|---|---|
| `mhpss_np_5w_latest.csv` | the newest snapshot, stable name — **pull this** |
| `mhpss_np_5w_<YYYY-MM-DD>.csv` | the same snapshot under its data date; dated files are never overwritten |
| `schema.json` | the column contract (names, types, HXL tags, version) |
| `CHANGELOG.md` | what changed between schema versions |

Base URL: `https://mhpss-nepal.github.io/hub/exchange/`

## The file

- **CSV with an HXL hashtag row** (row 2), so tooling can merge and validate without a human
  explanation of the columns.
- **One row per reporting unit** (adm3 palika).
- **The join key is the OCHA COD-AB P-code**, at all three levels (`#adm1+code`, `#adm2+code`,
  `#adm3+code`). **Join on the P-code, never on a place name.** Three name traps would silently
  break a name join: `Chitwan`/`Chitawan`, `Tanahun`/`Tanahu`, and `Nawalparasi`, which is **two**
  districts (we report the **East** unit, `NP0447`).

## Read this before you sum anything

- The reach measure is **non-additive** — counted once per location (max per location), as the
  source computes it. **Cross-dimension sums disagree by design.** Do not sum rows to a total.
- The source is a **snapshot, not a live feed**. Always quote the `#date` with any figure.
- It supports **reach, geography, actors, status and modality only**. It carries **no denominator**,
  so it cannot support trend, coverage-gap or target-achievement claims.
- Small cells are **suppressed**: no row is published below a reach of 10. A below-floor value is
  never emitted, so a published total minus published parts cannot reconstruct one.

## How it is produced

`tools/exchange/build_exchange.py` — **Python standard library only. No network, no credentials,
no account, no AI, no model.** It reads the frozen, public-safe source in `exchange/source/` and
emits the files above. A machine check refuses to build if the export ever breaks its own contract
(a missing P-code, a missing metadata field, an additive claim on a non-additive measure, a
below-floor value, or any identity key in the source). `--verify` re-reads the committed files and
asserts they match a deterministic rebuild.

Regenerate, never hand-edit:

```bash
python3 tools/exchange/build_exchange.py          # rebuild
python3 tools/exchange/build_exchange.py --verify  # assert committed files match the source
python3 -m unittest tests.test_exchange_contract   # the contract tests
```

## Update cadence and acceptance

- Cadence: see the handover note / `CHANGELOG.md`. (Interim: refreshed when the source snapshot moves.)
- Acceptance owner (interim): **Chandra Rana, UN OCHA** — pending confirmation.
- The one real acceptance test is **yours**: please confirm the file loads in your tooling.
