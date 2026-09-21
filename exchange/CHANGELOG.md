# Changelog — MHPSS Nepal exchange feed

All notable changes to the exchange feed's **contract** are recorded here. The schema is
versioned in `schema.json` (`schema_version`); a breaking change increments it. Snapshots are
never overwritten — a refreshed snapshot lands as a new dated file and moves `latest`.

## schema_version 1 — 2026-09-19 (first published feed)

- First pull-only aggregate feed for OCHA/NDRRMA.
- Columns and HXL tags: `#activity`, `#sector`, `#org`, `#adm1(_+code)`, `#adm2(_+code)`,
  `#adm3(_+code)`, `#reached`, `#activity+count`, `#meta+basis`, `#date`, `#date+start`,
  `#date+end`, `#meta+version`.
- Join key: OCHA COD-AB P-code at adm1/adm2/adm3.
- Reach is **non-additive** (max per location); the basis string travels in every row.
- Small-cell floor: no row is published below a reach of 10 (`suppressed_below: 10`).
- Source: NDRRMA/OCHA public 5Ws Power BI dashboard, MHPSS sector, Rasuwa Flood Response,
  snapshot data date 2026-09-19, period 2026-08-26 … 2026-09-19.

### Not in this version

- No denominator (so no trend, coverage-gap or target-achievement claims are supported).
- No per-actor rows, no geography below adm3, no individual or case data.
- No `updated_since` delta field yet — consumers pull the whole (small) file each time.
