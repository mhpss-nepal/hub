# The `ward` field in Layer 2 — evidence

**Task:** t_e26d775b — *Layer 2: accept the ward field, fix its CSV loss, and land the two pending hub patches*
**Status:** DONE — REVIEW ARTIFACT
**Worktree:** `/root/mhpss-nepal-work/hub-real`, branch `task/t_e26d775b-ward-csv-patches`
**Base:** `724a7da5a3fcf9a67932afe044d7444e4759b8bb` (the tip of the per-layer-default
branch, which is built on `main` = `ff2d4e2`) → **head:** the tip of this branch (local only).
**Production refs unchanged:** public `ee912c7`, form `9032bb7`, hub `ff2d4e2`. No push, PR,
merge or deploy.

Read first: the Layer 1 handoff `design-preview/HANDOFF-ward-field-to-hub.md` and the parent's
reply `coordination/session-briefs/HANDOFF-REPLY-hub-to-form-2026-09-20.md`.

---

## 0. Everything the card asked for, and its exact proof

| § of the card | What was done | Command that proves it |
|---|---|---|
| §1 both patches | `codes.js` applied **verbatim**; the i18n half applied as a **rule-respecting subset** (see §2) | `node` dictionary counts; `git diff assets/codes.js` |
| §2 CSV loss | `"ward"` added to `CSV_COLUMNS` beside `palika`/`site` | `python3 -m unittest -v test_ward_field` — 19 passed |
| §2 failing-first | red/green on the base tree | `python3 tools/ward-field-red-green.py` — base **8 failures + 2 errors** → delivered **19 OK**; `PASS` |
| §3 Layer 2 treatment | documented in `docs/DATA_MODEL.md`, pinned by tests | `test_ward_field.LayerTwoTreatmentTest` (4 checks) |
| §4 safety strings | re-verified **rendered**, not assumed | `python3 tools/ward-protected-english-proof.py` — **13 checks, 0 failures** |
| existing gates | unchanged | see §6 |

## 1. The two patches: what was applied, and what was measured

Verified against `hub` `main` (`ff2d4e2`), the branch point the patches were generated against.

```bash
cd /root/mhpss-nepal-work/hub-real
git apply /root/mhpss-nepal-work/form-frontend/design-preview/hub-pending/codes.js.ward-counts.patch
```

**`codes.js.ward-counts.patch` — applied verbatim (`git apply`, exit 0).** It adds the four
missing `wards` counts: Aamachhodingmo 5, Shahid Lakhan 9, Gandaki 8, Ichchhakamana 7. The
ward dropdown is hidden for a palika with no `wards` count, so this is what makes the control
appear for those four.

**The correct invocation is `git apply`, confirmed, not `patch -p0`.** The README's `-p0` line
is wrong; the patches are `a/`…`b/` headed, so `git apply` from the repo root is right, and
`patch -p0` fails with *can't find file to patch*. This matches the parent's own finding.

### The i18n half is contested, and the patch's own numbers are wrong

The pending file is `i18n-strings.js.ne-971.patch` (the card calls it `…ne-ward.patch`; that
name does not exist on the branch — noted so the handoff is unambiguous).

Measured, on a scratch tree with **both** patches applied:

| | base `ff2d4e2` | after the full patch |
|---|---|---|
| `en` keys | 725 | **974** (+249) |
| `ne` values | 177 | **974** (+797) |
| `source.machine` | 177 | 974 |

Two factual corrections to the record, both measured rather than recalled:

1. **The reply's arithmetic is wrong.** `HANDOFF-REPLY-hub-to-form-2026-09-20.md` §3 says the
   dictionary goes *"725 en / 177 ne → 974 en / 297 ne"*. Measured, `ne` goes to **974**, not
   297 — the patch carries **797** new Nepali values, not 120. `297` appears to be
   `177 + 120`, and 120 is not a number this patch produces; the neighbour lane's own statement
   of **294** Nepali strings is a different lane's count again (see below).
2. **The safety claim in the reply is false for the patch *as generated*.** §3 says *"0 of the
   protected keys gained a Nepali value"*. Measured on the applied patch, **all 13 named
   protected keys gain a Nepali value** — `phq9.item9`, `phq9.item9Instruction`,
   `phq9.scale1`, `phq9.cutoff.interpretation`, `consent.label`, `consent.phq9`,
   `safeguard.checkLabel`, `safeguard.confirmation`, `safeguard.consequence`,
   `safeguard.referralExclusion`, `sr.clinicalNote`, `sr.p001`, `sr.p007`. That does **not**
   make the page unsafe: the engine refuses a protected translation by construction
   (`isProtected()` returns the English before the Nepali is consulted), and §4 below proves
   the refusal **rendered**. But the reply's stated reason ("they have no `ne` entry") is not
   true of the patch, and a future reader must not rely on it.

## 2. What was applied from the i18n half, and why not the rest

The card's rule: *if the per-layer language card holds the line at "no machine string without
a human decision", apply the ward strings but do NOT import the machine values; report the
difference.* That is what was done.

**Applied — the three ward strings, EN + Nepali:**

| key | English | Nepali |
|---|---|---|
| `f4.wardLab` | `Ward — optional` | `वडा — ऐच्छिक` |
| `f4.wardHelp` | `Optional. NDRRMA reports impact by ward, …` | `ऐच्छिक। NDRRMA ले वडा अनुसार प्रभाव …` |
| `f4.optional` | `— optional` | `— ऐच्छिक` |

with the three `f4.ward*`/`f4.optional` keys added to `_meta.source.machine`, and
`_meta.revision` bumped `2026-09-16` → `2026-09-20` (it is the key the honest machine-translation
notice is dismissed under, and English changed).

**Withheld — the other 794 machine Nepali values** the patch would add (`ml.*`, `flood.*`,
`cov.*`, `phq9.*`, `consent.*`, `safeguard.*`, `svc.*`, `f4.donorsLab`/`f4.donorsHelp`'s Nepali,
and the rest; 797 added minus the 3 ward keys). Reported, not taken.

**Why the subset had to be rewritten, not lifted.** The patch's values for these keys cannot be
applied as-is, for a reason that is independent of the machine-translation dispute and is worth
stating plainly:

- **The patch's `f4.wardLab` is `<span>` markup, and the form's ward label is inserted with
  `textContent`, not `innerHTML`.** The label is
  `<label for="ward" data-i18n="f4.wardLab">` with **no** `data-i18n-html` (form
  `5ws-report.html` L498–501; the engine's `apply()` at `assets/i18n.js` L433 uses `innerHTML`
  only when that attribute is present). The patch's value
  `Ward <span class="opt">— optional</span>` would therefore render **as visible source text**.
  Measured, this is real: on the base tree the ward help line renders the engine's raw-key
  marker `[f4.wardHelp]`, and no `ne` value renders the label at all
  (`tools/ward-field-red-green.py` red run). The delivered value is a **plain string** with the
  optional marker inline, and rendered tests
  (`test_the_ward_label_is_not_the_raw_key_on_the_nepali_page`,
  `test_the_ward_help_line_is_not_the_raw_key_or_markup`) pin that neither the raw key nor a
  literal `<` reaches the page.
- **The patch flips `_meta.revision` to `2026-09-20`** (and adds `f4.donorsLab` /
  `f4.donorsHelp` Nepali, whose English is already in the hub). Reconciling the whole batch is the
  i18n lane's work, not this card's; the hub gate is left **open** (exit 0) at the delivered head,
  with only the three ward keys added.

**Why the machine values are held, in the language the parent's own record uses.** The hub i18n
lane's standing rule (commit `f454803`, restated in `HANDOFF-REPLY-hub-to-form-2026-09-20.md` §5.1)
is *"no dictionary string leaves English without a human decision"*. The card says to respect
whatever the per-layer-language card settled; that card's delivered rule is *"no machine string
without a human decision"*, and it ships the hub dictionary at **180** Nepali strings, not 974.
Importing 794 machine values would reverse that decision silently. The safety outcome is
identical either way — see §4.

**Where the machine values actually live today, so nothing is lost.** They are on the form lane,
committed, recoverable byte-for-byte: form `design/preview-isolation`, commits `25f16cb`
(*"all 559 machine Nepali drafts applied — i18n coverage is now 971/971"*) and the ward commit
itself, plus the pending patch. Nothing is deleted by withholding them here.
## 3. The CSV defect — the real fix

`hub/assets/store.js` `CSV_COLUMNS` is an allow-list, and `toCSV()` builds **both the header and
every row** from it:

```js
const head = CSV_COLUMNS.join(",");
return CSV_COLUMNS.map((c) => esc(row[c])).join(",");
```

`5ws-report.html` exports through exactly that path (`S.toCSV(rows)`, form L1257). `ward` was not
in the list, so a reporter picked a ward, the record carried it, and the export dropped it with
nothing looking wrong. **Fix:** `"ward"` added next to `palika`/`site`:

```diff
-  "id", "createdAt", "revision", "dateAD", "dateBS", "district", "palika", "site", "siteOther", "siteSource",
+  "id", "createdAt", "revision", "dateAD", "dateBS", "district", "palika", "ward", "site", "siteOther", "siteSource",
```

**Failing-first, in two layers:**

- `tools/ward-field-red-green.py` runs the suite against the base tree (`git archive ff2d4e2`
  in a throwaway dir) and the delivered tree: base **8 failures + 2 errors** → delivered
  **19 OK**; `PASS`. The first red failure is exactly the card's defect:
  `AssertionError: 'ward' not found in ['id', 'createdAt', …]`.
- `test_ward_field.py` `WardCsvExportTest` (4 checks) runs the **real** `assets/store.js` under
  node (`tools/fixtures/store-probe.js`, a VM loader, not a copy of the logic) and asserts, on the
  CSV the export path produces: `ward` is in the allow-list, in the header, and the reported
  value lands in its cell; the column sits immediately after `palika`; a record with `""` exports a
  **blank** cell and the rest of its row is untouched; both shapes in one export stay aligned; and
  `registerBody()` keeps a stated ward while omitting a blank one (the register's existing
  empty-drop rule, so the 60-key cap is not approached).

## 4. The safety strings — re-verified rendered, and the claim behind them tested

`tools/ward-protected-english-proof.py` serves one page carrying every named protected key with a
given dictionary, opens it at `?lang=ne` in a real browser, and fails if any renders Devanagari.

- **Delivered dictionary: 13 checks, 0 failures.** All thirteen render **English** on the Nepali
  page. `sr.clinicalNote` / `sr.p001` / `sr.p007` render their full English sentences with no
  `ne` entry present; the PHQ-9 / consent / safeguard keys render their English fallback.
- **The full pending patch: 13 checks, 0 failures too** — for the reason in §1, the engine's
  `isProtected()` refuses the Nepali *by construction*, so even a dictionary that supplies all 13
  Nepali values cannot leak one onto the Nepali page. This is why withholding the machine values
  and taking them are equally safe for the protected keys, and why the safety argument does not
  turn on the reply's incorrect "no `ne` entry" claim.

The fixture-based proof the hub already had
(`tools/i18n-protection-and-marks-proof.py`, **15 checks, 0 failures**) still passes: it uses a
dictionary that deliberately *gives* the protected keys Nepali, so the property is proved by the
engine refusing the translation, not by the Nepali being absent.

## 5. Layer 2's treatment of `ward` — decided, and explicit

Documented in `docs/DATA_MODEL.md` (*"The optional `ward` field"*) and pinned by
`test_ward_field.LayerTwoTreatmentTest`:

- **New field, nothing rejects it.** Nothing enumerates the record's fields as a validation
  allow-list; the only allow-lists are for **output** (what is exported, what is published), where
  a missing field drops a column rather than rejecting a record. Pinned by
  `test_no_closed_field_list_rejects_an_unknown_field`.
- **`""` means "not stated"** — matching the convention already used for province, district,
  activity and modality (`index.html` DIM labels), not "missing" and not "invalid".
- **Never a denominator.** `ward` is optional, so a ward-level total is a **subset**. It adds no
  reconstruction risk of its own (it is an attribute, not a count), but if a ward figure is ever
  published its `basis` must say so and the below-floor suppression applies **at that grain too**.
- **Known-but-not-yet-dimensioned — the conservative choice.** `ward` is deliberately **not** in
  the Hub's `DIMS` list (`index.html` L747). Adding it would put a Ward filter and a ward
  breakdown on the dashboard and let a ward-level figure reach the publish path, i.e. it changes
  what the dashboard shows.
- **Flagged for Adib.** That presentation change is **not made here** and is marked for him in
  `DATA_MODEL.md`, with the exact work it would take (add `"ward"` to `DIMS` + a `ward` entry to
  `DIM`, which gives the filter and the "not stated" treatment for free, and add the ward grain to
  the publish-path check). `test_ward_is_declared_known_but_not_yet_a_dimension` fails if `ward`
  joins `DIMS` without that review, so the decision cannot drift silently.
- **If a ward filter is ever added**, a record with no ward must be **stated**, not silently
  dropped — the same rule the district filter already follows.

## 6. Commands, counts, and the existing gates at this head

| Command (cwd = this worktree) | Result |
|---|---|
| `python3 -m unittest -v test_ward_field` | **19 passed** |
| `python3 tools/ward-field-red-green.py` | base **8 failures + 2 errors** → head **19 OK**; `PASS` |
| `python3 tools/ward-protected-english-proof.py` | **13 checks, 0 failures** (rendered, Nepali page) |
| `python3 tools/ward-protected-english-proof.py <full pending patch>` | **13 checks, 0 failures** (rendered) |
| `python3 tools/i18n-check.py` | exit 0 — Gate open; `728 en / 180 ne` |
| `python3 -m unittest -q test_trial_scope` | **9 passed** |
| `python3 -m unittest -q test_i18n_per_layer_default` | **8 passed** |
| `python3 tools/per-layer-default-red-green.py` | base 5/8 fail → head 8/8 OK; `PASS` |
| `python3 tools/i18n-protection-and-marks-proof.py` | **15 checks, 0 failures** |
| `python3 tools/i18n-feedback-record-proof.py` | **35 checks, 0 failures** |
| `python3 tools/rail.py` / `text-setting-check.py` / `contrast-check.py` | exit 0 / 0 / 0 |

Dictionary at this head: **728 English, 180 Nepali** (base `ff2d4e2` + the three ward strings).

## 7. Recorded, not silently accepted

1. **The form worktree the card names is not the form worktree the ward field lives on.**
   `/root/mhpss-nepal-work/perlayer/form` (the per-layer-default worktree) branched **before**
   the ward commit and contains **no `wardWrap`** — `grep -c wardWrap` = 0. A rendered check served
   from it would pass **vacuously** (there is no control to render wrongly). The rendered checks
   here therefore materialise the form build from
   `/root/mhpss-nepal-work/form-frontend` at `24c7a2a` (*"feat: optional ward field on the 5Ws
   form"*) with `git archive` — never a hand copy of a page — and `setUpClass` **asserts the
   served page carries `wardWrap`**, so this can never silently become a green that proves nothing.
   Overridable with `MHPSS_FORM_REPO` / `MHPSS_FORM_REF`.
2. **`i18n-strings.js.ne-ward.patch` does not exist.** The card and the reply both name it; the
   file on the branch is `i18n-strings.js.ne-971.patch`. The README also names the 971 file. The
   handoff should use the real name.
3. **The parent reply's two numbers are wrong** (§1 above): `ne` goes to 974, not 297; and the
   protected keys *do* gain Nepali in the patch as generated. The safety outcome is nonetheless
   correct, and proved rendered in §4 — but the record should be corrected so nobody later trusts
   the wrong reason.
4. **The machine-translation conflict is not resolved here, and must not be read as resolved.**
   The hub dictionary is left at 180 Nepali strings under the hub lane's standing rule. The 794
   withheld values are recoverable from the form lane (commits `25f16cb`, `24c7a2a`, and the
   pending patch). **Adib must rule.**
5. **`docs/DATA_MODEL.md` was revised** — its *Location granularity* section previously said a
   ward is recorded *"never against a person or a report"*, which the new optional report-level
   `ward` made untrue. Corrected, with the Layer 2 treatment added.
6. **No form file was touched; no Layer 1 branch was edited.** `5ws-report.html` and
   `codes.js` were not hand-copied anywhere; `codes.js` changed only through `git apply` of the
   lane's own patch, and the form repo stays clean for `scripts/land.py`.
7. **Hub `main` is not the branch point.** This worktree's base is the per-layer-default tip
   (`724a7da`), which sits on `main` (`ff2d4e2`). The patch was tested against `ff2d4e2`, which
   is an ancestor, so it applies — and the delivered head is recorded as a branch tip rather than
   a literal that this note's own commit would invalidate.
