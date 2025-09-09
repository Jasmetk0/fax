# Full Verification — MSA
Generated: 2025-09-09 17:54:01 UTC
Spec: /workspace/fax/docs/MSA_SPEC.yaml (version: 1.0)

## Scoreboard
- ARs: 14/16 PASS (87%)
- Models: 0 errors / 0 warns
- Tests: 9/9 present (100%)
- RNG hygiene: OK
- Reseed policy: N/A

## Results (all ARs)
| AR | Status | Evidence | Proposed fix |
|---|---|---|---|
| AR-CAL-001 | FAIL | no calendar sync code | add test msa/tests/test_calendar_sync.py |
| AR-LL-001 | PASS | ll_prefix.py & test_ll_prefix.py |  |
| AR-LL-002 | PASS | ll_prefix prefix enforcement |  |
| AR-MD-001 | PASS | seed_anchors.py & test_seed_anchors.py |  |
| AR-MD-004 | PASS | md_embed.py & test_md_embed.py |  |
| AR-PLN-001 | PASS | planning.py & test_planning.py |  |
| AR-QUAL-001 | PASS | qual_generator tier formula |  |
| AR-REC-001 | PASS | recalculate.py & test_recalculate.py |  |
| AR-REC-002 | PASS | brutal_reset_to_registration saves Snapshot |  |
| AR-REC-003 | PASS | rng_seed, anchors, unseeded, matches_changed |  |
| AR-REG-001 | PASS | recalculate.py:_sort_by_wr |  |
| AR-REG-002 | FAIL | no rank-bucket enforcement | add test msa/tests/test_registration_reorder.py |
| AR-REG-003 | PASS | power-of-two hint |  |
| AR-RES-001 | PASS | results.py & test_best_of_policy.py |  |
| AR-RES-004 | PASS | results.py & test_results_needs_review.py |  |
| AR-SCO-002 | PASS | scoring.py & test_scoring.py |  |

## Proposed Fixes
- AR-REG-002: add test msa/tests/test_registration_reorder.py
- AR-CAL-001: add test msa/tests/test_calendar_sync.py

## Open Questions
- none
