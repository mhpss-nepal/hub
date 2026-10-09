# Owner-selected dashboard candidate

Executor and canonical artifacts: Thar Lay/server. No Luna mirror.

Baseline: 180a64e8ccb077e26d0905adffa320e107ffb45f. Reference: owner-selected 27 September image, SHA256 b2f9cd2f73dd6caad0ee20a51b20c7d20f7d7d5b31e327d1c5f7d2cebc191b9b. Reference figures and historical category labels are not approved metric definitions.

Original delivered candidate preserved in commit 842677b (unverified checkpoint). Continuation fixes: trailing whitespace; a missing closing div causing secondary sections to remain inside the overview grid; pre-existing matrix-header contrast reproduced against the exact baseline, corrected in presentation CSS to meet the requested zero-violation gate. No inline JavaScript or shared asset changes.

Fresh QA checks 13 canonical baseline/candidate output comparisons at each of 320/390/1280: stats, coverage, duplication flags, organisation-place matrix, activities, demographic table, daily table, report membership/body, filtered stats, filter summary, CSV, report search and matrix CSV. All use the same synthetic fixture, period and timezone. These are 39 isolated presentation comparisons, NOT the owner 13 backend indicators. Six rendered states per viewport are axe A/AA checked. Language test is initial English then click NEP, not a cold Nepali load; translation is incomplete. Only the existing language-preference key changes.

Reproduction: arrange a clean clone as <working-directory>/hub; copy source/{qa.py,verify_final.py,baseline.html,axe.min.js} to its parent and run /usr/local/lib/hermes-agent/venv/bin/python qa.py followed by verify_final.py. Contract tests: python -m unittest discover -s hub/tests -p test_dashboard_visual_contract.py -v. No installs or production data needed. qa.py serves only bounded static routes on a dynamic loopback port, stubs fb.js, blocks other origins, closes owned browser/listener. Sources prepare/implement/refine are provenance only: DO NOT replay them over the delivered candidate.

Limitations: not production backend–frontend parity; existing cloud reader/auth/publisher unchanged and not activated or certified. No real operational read/write. No all-13 readiness claim. Existing source terminology remains historical; no unique-person inference, denominator invention, new fields or relabelled historical age cells. No root service-worker/manifest call site; installed-client migration not claimed. Final visual owner acceptance is pending.
