# Evidence: the four pre-existing reds in the hub suite

**Task** `t_22c34977`. **Where this branch was cut from:** `origin/main` at
`68b2ce40590ff49a7216c60c9c5533d2a78677c6` (*"Merge pull request #24 from
mhpss-nepal/task/t_4a73eb05-guard-and-evidence"*). The four failures were also
reproduced on the frozen head named in the card, `dfe660a` (*"Merge pull request
#22 from mhpss-nepal/fix/mt-notice-validated"*), with a detached worktree at
`dfe660a`: identical four failures, 32 tests, 1 skipped.

    python3 -m unittest discover -p 'test_*.py'      # from the repository root

| | at `dfe660a` | at `68b2ce4` (branch point) | after this branch |
|---|---|---|---|
| result | FAILED (failures=4, skipped=1) | FAILED (failures=4, skipped=1) | **OK (skipped=1)** |

---

## 1. `assets/store.js` — the header, reverted by `e479582` (fourth occurrence)

**What it asserts.** `test_store_data_path_contract.py` reads the comment block
above `const KEY` and requires it to name `syncToRegister()` and `submissions`,
and forbids the two phrases of the local-only story ("Deliberately has NO
backend", "leave it only when a person exports them").

**Why it was red.** `fix/store-backend-comment` (`326ffbb`, merged as `e231549`,
hub#3) *is* an ancestor of `origin/main` and *did* land: it rewrote the header to
describe the device → register → export path, `syncToRegister()`, the
`submissions` register, and the focal point never crossing the network.
`e479582` (hub#14, the Ministry age bands, merged as `dab6329`) then carried the
header **back** to the stale text.

```
$ git rev-list --parents -n1 e479582
e479582… e34018c…                       # its own parent already had the fix
$ git show e34018c:assets/store.js | sed -n '4,7p'
   The device copy is the first durable copy. `save()` writes it to
   localStorage, then `syncToRegister()` hands a stripped copy to the loaded
   Firebase bridge (`fb.js`) for the `submissions` register; failed delivery
   stays queued for retry. The Hub reads that register.

$ git show e479582 -- assets/store.js | grep -E '^index'
index 0e73242..d2e02ff 100644           # 0e73242 = the fixed header
$ git rev-parse 0e73242                # == the post-326ffbb blob
$ git merge-base --is-ancestor 326ffbb origin/main && echo YES
YES
```

The five-line stale paragraph is byte-identical to the pre-`326ffbb` text
(`d2e02ff` differs from `14216cf`, the pre-fix blob, only in the
`SCHEMA_VERSION` line), so the branch was cut before the fix and merged after
it — the failure mode the card for `t_4a73eb05` names.

**Why merging the branch again does nothing.** `326ffbb` is already in `main`;
the revert is committed on top of it. The header has to be re-applied, which is
what this branch does — verbatim the reviewed text from `326ffbb`.

**Sibling sweep — did `e479582` (or its siblings) revert anything else?**

* The branch is a single commit and touches exactly two files:
  `assets/i18n-strings.js`, `assets/store.js` (`git show --stat e479582`).
* `assets/store.js`: hunk-by-hunk, the only loss is the header. The other 45
  changed lines are the deliberate schema/age-band work of that commit
  (`SCHEMA_VERSION` 0.5.0 → 0.6.0, `BANDS_V04`, `FOLD_BOUNDARY` 20, the new
  `CSV_COLUMNS` ids) and are all present on `main` today.
* `assets/i18n-strings.js`: the same commit dropped the 19 protected English
  strings. That is the regression the project already hit and repaired
  (hub#15 / hub#17); on current `main` all 19 are present and the guard passes —
  `tools/protected-strings-check.py`: *"protected keys present in en: 19 ·
  protected keys carrying Nepali: 0 · OK"*. Nothing new to fix; guarded already.
* Repository-wide sweeps, committed with this branch so they can be re-run
  rather than believed — `tools/evidence/sweep_reverts.py` (graph detector),
  `tools/evidence/sweep_branch_takeover.py` (tree detector),
  `tools/evidence/sweep_classified.py` (line-by-line, with the still-gone /
  restored classification) and `tools/evidence/red_green_probe.py` (the
  adversarial probes below). All are read-only: they read `git` and copy trees
  into throwaway directories.
  * graph detector — merges whose result drops lines main gained after the
    branch was cut: **24 merges scanned, 0 hits**. It cannot see this case,
    because the branch's parent carried the fix and the author rewrote the
    region by hand, which git records as an ordinary edit.
  * tree detector — merges whose result drops lines that main had *and the
    branch also lacked*: 13 merges, all of them deliberate supersession
    (old geography rows replaced by the MoFAGA list, regenerated QR assets, the
    nav restructure, the skip-link rewritten as `keepSkipFirst()` with a
    `MutationObserver`, `APPROVED_FORM_TARGETS` widened to the four approved
    forms). Each still-gone line in a shipped file was inspected one by one; the
    only unexplained loss in the window is the `store.js` header.

---

## 2. `test_ward_field.py` — two stale assertions, not a merge-order artefact

### 2a. `test_no_protected_key_gained_a_nepali_value` and
### `test_every_named_protected_key_holds_no_nepali_value`

**What they assert.** That no key in a protected family carries a Nepali value,
and that a named list of PHQ-9 / consent / safeguard keys holds none.

**Why they were red.** Each carried its **own copy** of the rule —
`PROTECTED_PREFIXES = ["phq9.item", "phq9.scale", …]` — frozen before hub#21
shipped the validated Nepali PHQ-9 (Kohrt et al. 2016, Additional file 1: the
nine items and the four-level scale) for exactly those keys, and before
`_meta.professionalOnly` was narrowed to `phq9.item9Instruction` +
`phq9.cutoff.*`. The shipped rule lives in `tools/protected-strings-check.py`
(`PREFIXES`, `ALLOW_NEPALI`); the test contradicted the file it was checking.

**What changed (no assertion deleted, none weakened).**

* The prefix list and the exception list are now **read from the shipped guard**
  (`_shipped_rule()`), so the two cannot drift apart again.
* `PROTECTED_NAMED` is the card's named set **minus** the published exception —
  which is precisely `phq9.item9` and `phq9.scale1`.
* New, still stronger properties: every named protected key must carry a
  non-empty **English** string (that is what stops a page rendering literal
  `[key]`); every key allowed Nepali inside a protected family must be declared
  in `_meta.source.human` or be one of the guard's two named instruction lines;
  and the render-forced keys (`sr.p001/p007/clinicalNote`,
  `phq9.item9Instruction`, `phq9.cutoff.*`) must stay in
  `_meta.professionalOnly`, because that declaration — not the absence of a
  value — is what keeps them English on the page.
* The released instrument is now pinned both ways: `phq9.item1..9` and
  `phq9.scale0..3` must be in `_meta.source.human` **and** keep their Nepali
  value, so a merge-order revert cannot take the Nepali PHQ-9 away quietly.

### 2b. `test_every_palika_still_carries_a_ward_count`

**What it asserted.** `wards:` on *every* entry of `PALIKAS`.

**Why it was red.** hub#19 replaced the affected-area p-codes with the official
753-palika MoFAGA list, whose entries carry no ward count (the list publishes
none). Measured on this branch: `PALIKAS` holds **753 entries — 20 carrying a
ward count, 733 not**, and every one of the 733 is a `MF…` MoFAGA entry naming
its source.

**What it asserts now.** The property the original defect violated, and the two
lists so it cannot pass on a shrunken file: a palika that carries a count
carries a whole number in Nepal's 5–35 range; a palika without one names its
MoFAGA source, so the absence is declared rather than silent; at least the 20
affected-area counts remain; at least 753 palikas are present.

---

## Measurement

* **Guards still pass** (they were passing before this branch, and are green
  after it): `tools/protected-strings-check.py`,
  `tools/i18n-check.py`, `tools/hub-live-read-scoping-check.py`.
* **Six adversarial probes** (`python3 tools/evidence/red_green_probe.py`; each
  guarded defect planted back into a throwaway tree, one at a time, and the
  suite must go red): the reverted header, a Nepali value added to a protected
  key, the validated Nepali PHQ-9 removed, the instrument struck from
  `source.human`, the render-forced declaration removed, a ward count emptied
  without a MoFAGA source. **6 of 6 caught.**

---

## Live site

* **Before this branch.** The reverts were being served:
  `https://mhpss-nepal.github.io/hub/assets/store.js` — HTTP 200, 27 357 B,
  sha256 `663230653cd732b5…`, stale header present, `syncToRegister` absent.
* **After the merge.** Measured from a fresh cache-busted fetch and re-checked
  in the browser — see the closing note at the end of this file.
