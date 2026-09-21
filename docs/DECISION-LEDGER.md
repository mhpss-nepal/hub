# Decision ledger — the institution's memory

**Frozen.** Each line is a **settled decision**, not a proposal. Reopening one requires the
operator (Adib), explicitly. This file is handed over with the system so that the *reasons* survive
the people who made them; the repository, not a chat thread, is where the record lives.

Copied from the master roadmap §9 at handover. If the two ever disagree, the roadmap copy is the
authority and this one must be re-copied — never edited independently.

---

## Scope and safety

1. The system is **coordination, not case management**. It does not hold individual-level information.
2. The iron rule: **a client name may never sit in the same document as an aggregate number.**
3. **Read access is the real boundary** — if data must not be seen by someone, it must not be sent to their device.
4. Safeguarding must **block**, not warn. *"Peringatan bukan pengaman."*
5. For risk to life: **act first**. Referral is by **number**, not by pathway — about 60% of district pathways are non-functional. 1145 (GBV/NWC, 24/7, free, includes under-18), 1098 (CWIN, child, 24/7), 100 (police), 102 (ambulance), 16600102005 (TPO Nepal MHPSS, 08:00–18:00), OCMC for clinical services.
6. A referral record **never** structurally reaches `public_stats`; the whole referral collection is a restricted class.
7. IN/OUT matching is allowed; **one record = one person only when the code is identical**. "Probably matches" is flagged for a human.
8. Raising the small-cell floor is **not** the fix for reconstruction; computing redaction **per document** is.
9. `public_stats` must refuse non-production mode, any declared floor below 10, and `referral_directory`.

## Language and assets

10. Per-layer default, **declared on the page itself** (`data-i18n-default`), never from the URL path: **Nepali for Layer 1 field surfaces; English for Layer 2 and Layer 3.**
11. External assets (WHO, cluster, guideline) are written **in English**. Internal discussion files may be Indonesian.
12. Machine translation is **authorised** for the field forms, with the human team reviewing Nepali on the live pages afterwards. **Nothing is labelled "human" that a machine produced.**

## Design

13. Layer 2 is **one dashboard with tiers inside it**: T0 public aggregates · T1 TWG/MoH EDCD/WHO/cluster leads · T2 admin + GBV/CP focal points · T3 admin only (names, codes, audit, export).
14. **Export is its own restricted item.** One download button defeats the whole ladder.
15. A **data-quality page must never be public** — a pattern like *"3 records without a date in region X"* already discloses the existence of cases.
16. The `description` field is **not** removed — the Hub uses it for IASC classification; it moves to a coordination-only collection.
17. `ward` is **optional by design**: *"a geographic guess is worse than an empty geography, because it looks usable."*
18. Ekspor ke OCHA = **they pull, we never push.** The URL is the contract. No login, no portal, no request, no credentials of another organisation.

## Operations and handover

19. The system must run **automatically after the contract ends — with no AI**, no dependency on the operator's laptop or one person's server; the critical path on institutional infrastructure.
20. Production changes go through a **PR** and are verified against the **live site**, never the branch.
21. **Never write a credential value.** Access is granted by email address, one person at a time, and every grant is recorded.

---

## Decisions added at handover (2026-09-21)

22. The **Firestore rules' read scoping is by role AND kind** (`canReadKind`). A `viewer` reads no register kind; a coordinator reads activity counts only; the GBV/CP focal-point roles read referral only. **Emulator-verified** (38/38, with mutation proofs) before it is applied.
23. The **hub must read the register kind-scoped** (`watchKind`), never with an unfiltered listener — the read the client is *allowed* to make is the boundary, and rules are not filters.
24. The **OCHA/NDRRMA exchange feed rides the existing publishing** (repository + GitHub Actions), is **stdlib-only and AI-free**, and its refresh commits **only when the frozen source actually moves**.
25. **The exchange feed and (once enabled) the NDRRMA capture are the AI-free core**; any job that still runs on the project server is a **named handover gap**, not an accepted end state.
