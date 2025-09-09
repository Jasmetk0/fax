# MSA Compliance Report
Generated: 2025-09-09 16:57:10 UTC
Spec: C:/Users/Kluci/Projects/fax/docs/MSA_SPEC.yaml (version: 1.0)

## Summary
- Features: 10/11 PASS (90%)
- Models: 0 errors / 0 warns
- Tests: 9/9 present (100%)
- RNG hygiene: WARN
- Exit status: FAIL

## Features (per spec)
| Feature | Status | Evidence |
|---|---|---|
| admin_mode_gate | FAIL | md_confirm.py[1/1], md_soft_regen.py[0/0], md_reopen.py[1/1], md_placeholders.py[3/3], wc.py[0/6], qual_confirm.py[2/2], qual_edit.py[1/1], qual_replace.py[1/1], planning.py[6/6], results.py[2/2], recalculate.py[1/1] |
| deterministic_seeding | PASS | rng_for and tests |
| license_gate_required | PASS | licenses.py |
| ll_prefix_invariant | PASS | ll_prefix.py; test_ll_prefix.py |
| needs_review_flow | PASS | results.py; test_results_needs_review.py |
| no_bye_templates | PASS | md_embed.py; test_md_embed.py |
| planning_day | PASS | planning.py; test_planning.py |
| rankings_61w_monday | PASS | standings |
| recalculate_with_diff | PASS | recalculate.py |
| snapshots_archive | PASS | Snapshot model |
| wc_qwc_limits | PASS | wc.py; test_wc_qwc.py |

## Models & Constraints
### CategorySeason
| Constraint | Status |
|---|---|
| category, season, draw_size | PASS |
### Match
| Constraint | Status |
|---|---|
| tournament, phase, round_name, slot_top, slot_bottom | PASS |
| tournament, round, position | PASS |
### PlayerLicense
| Constraint | Status |
|---|---|
| player, season | PASS |
### Schedule
| Constraint | Status |
|---|---|
| tournament, play_date, order | PASS |
### Tournament
| Constraint | Status |
|---|---|
### TournamentEntry
| Constraint | Status |
|---|---|
| tournament, player | PASS |
| tournament, position | PASS |

## Admin-gating of mutators
| Module | Mutators | Gated OK | Gated Missing | Examples |
|---|---|---|---|---|
| msa/services/md_confirm.py | 1 | 1 | 0 |  |
| msa/services/md_placeholders.py | 3 | 3 | 0 |  |
| msa/services/md_reopen.py | 1 | 1 | 0 |  |
| msa/services/md_soft_regen.py | 0 | 0 | 0 |  |
| msa/services/planning.py | 6 | 6 | 0 |  |
| msa/services/qual_confirm.py | 2 | 2 | 0 |  |
| msa/services/qual_edit.py | 1 | 1 | 0 |  |
| msa/services/qual_replace.py | 1 | 1 | 0 |  |
| msa/services/recalculate.py | 1 | 1 | 0 |  |
| msa/services/results.py | 2 | 2 | 0 |  |
| msa/services/wc.py | 6 | 0 | 6 | set_wc_slots:98, set_q_wc_slots:112, apply_wc:126 |

## Central RNG hygiene
Offenders:
- msa/services/md_embed.py:92 -> random.Random(
- msa/services/md_reopen.py:84 -> random.Random(
Required rng_for modules:
- msa/services/md_band_regen.py: PASS
- msa/services/md_generator.py: PASS
- msa/services/md_soft_regen.py: PASS
- msa/services/qual_generator.py: PASS

## Tests coverage
Present:
- msa/tests/test_ll_prefix.py
- msa/tests/test_md_embed.py
- msa/tests/test_md_generator.py
- msa/tests/test_qual_generator.py
- msa/tests/test_wc_qwc.py
- msa/tests/test_recalculate.py
- msa/tests/test_planning.py
- msa/tests/test_results_needs_review.py
- msa/tests/test_standings.py
Missing:

## Risky patterns (informational)
### select_for_update / get_or_create / update_or_create counts per file
- msa/services/licenses.py: select_for_update=0, get_or_create=1, update_or_create=0
- msa/services/md_placeholders.py: select_for_update=0, get_or_create=1, update_or_create=0
- msa/services/tx.py: select_for_update=1, get_or_create=0, update_or_create=0
### Ungated mutators
- set_wc_slots:98
- set_q_wc_slots:112
- apply_wc:126
- remove_wc:184
- apply_qwc:213
- remove_qwc:242

## Top recommendations
- admin_mode_gate
- random module used
