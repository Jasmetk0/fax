# STATUS: MSA Inventory
Generated: 2025-09-09T15:11:53+00:00 UTC
Script version: 1.0
Total Python files (excluding migrations): 54
Migrations count: 5
Packages: admin.py, apps.py, forms.py, models.py, services, tests, views.py

## Files Overview
| path | classes | functions | key decorators found |
| --- | --- | --- | --- |
| msa/__init__.py |  |  |  |
| msa/admin.py | CategoryAdmin, CategorySeasonAdmin, MatchAdmin, PlayerAdmin, PlayerLicenseAdmin, RankingAdjustmentAdmin, ScheduleAdmin, SeasonAdmin, SnapshotAdmin, TournamentAdmin, TournamentEntryAdmin |  |  |
| msa/apps.py | MsaConfig |  |  |
| msa/context_processors.py |  | msa_admin_mode |  |
| msa/forms.py |  |  |  |
| msa/migrations/__init__.py |  |  |  |
| msa/models.py | Category, CategorySeason, EntryStatus, EntryType, Match, MatchState, Phase, Player, PlayerLicense, RankingAdjustment, RankingScope, Schedule, Season, SeedingSource, Snapshot, Tournament, TournamentEntry, TournamentState |  |  |
| msa/services/_concurrency.py |  | _lock_tournament_row, atomic_tournament, lock_qs |  |
| msa/services/_legacy_draw.py |  |  |  |
| msa/services/admin_gate.py |  | require_admin_mode |  |
| msa/services/archiver.py |  | _serialize_entries, _serialize_matches, _serialize_schedule, archive, archive_tournament_state |  |
| msa/services/draw.py |  |  |  |
| msa/services/licenses.py | MissingLicense | _active_entries, _has_license, assert_all_licensed_or_raise, grant_license_for_tournament_season, missing_licenses | require_admin_mode |
| msa/services/ll_prefix.py | LLEntryView | _alt_queryset, _assigned_ll_queryset, _free_ll_queryset, _ll_queryset, _ll_queue_sorted, _md_slot_taken, enforce_ll_prefix_in_md, fill_vacant_slot_prefer_ll_then_alt, get_ll_queue, reinstate_original_player | atomic |
| msa/services/md_band_regen.py |  | _default_seeds_count, regenerate_md_band | atomic, require_admin_mode |
| msa/services/md_confirm.py | EntryView | _collect_active_entries, _default_seeds_count, _entry_map_by_id, _pick_seeds_and_unseeded, _slot_to_entry_id, _sort_key_for_unseeded, confirm_main_draw, hard_regenerate_unseeded_md | atomic, require_admin_mode |
| msa/services/md_embed.py |  | _opponent_slot, _seed_anchor_slots_in_order, effective_template_size_for_md, generate_md_mapping_with_byes, next_power_of_two, pairings_round1, r1_name_for_md |  |
| msa/services/md_generator.py |  | generate_main_draw_mapping |  |
| msa/services/md_placeholders.py | PlaceholderInfo | _ensure_placeholder_player, _existing_placeholder_entries, _final_winner_player_id_for_branch, confirm_md_with_placeholders, create_md_placeholders, replace_placeholders_with_qual_winners | atomic, require_admin_mode |
| msa/services/md_reopen.py |  | reopen_main_draw | atomic, require_admin_mode |
| msa/services/md_roster.py |  | _get_r1_match, _update_match_for_slot, ensure_vacancies_filled, remove_player_from_md, use_reserve_now | atomic, require_admin_mode |
| msa/services/md_soft_regen.py | EntryView | _collect_active_entries, _default_seeds_count, _seed_ids_by_wr, soft_regenerate_unseeded_md | atomic, require_admin_mode |
| msa/services/md_third_place.py |  | ensure_third_place_match | atomic |
| msa/services/ops.py |  | replace_slot | atomic_tournament |
| msa/services/planning.py | ScheduledItem | _compact_day, _ensure_not_scheduled_elsewhere, _list_all, _list_day, _restore_payload, _serialize_day_items, _snapshot_payload, clear_day, insert_match, list_day_order, move_match, normalize_day, restore_planning_snapshot, save_planning_snapshot, swap_matches | atomic, require_admin_mode |
| msa/services/qual_confirm.py | EntryView | _collect_qual_entries, _pairs_for_size, _round_name, _sort_by_wr, confirm_qualification, update_ll_after_qual_finals | atomic, require_admin_mode |
| msa/services/qual_edit.py | SwapResult | _fetch_r1_for_slot, _local_slot, _qual_size_and_anchors, _r1_name_for_size, _side_is_top, swap_slots_in_qualification | atomic, require_admin_mode |
| msa/services/qual_generator.py |  | bracket_anchor_tiers, generate_qualification_mapping, seeds_per_bracket |  |
| msa/services/qual_replace.py | ReplaceResult | _pick_best_alt_qs, _r1_qual_round_name, remove_and_replace_in_qualification | atomic, require_admin_mode |
| msa/services/recalculate.py | EntryState, Preview, Row | _current_layout, _default_md_seeds, _diff, _eff_draw_params, _eff_md_seeds, _eff_qwc_limit, _eff_wc_limit, _entries_active, _proposed_layout, _sort_by_wr, brutal_reset_to_registration, confirm_recalculate_registration, preview_recalculate_registration | atomic, require_admin_mode |
| msa/services/results.py | SetScore | _collect_downstream_matches_containing_player, _parent_pair_for_child, _propagate_winner_to_next_round, _round_size_from_name, _validate_sets, resolve_needs_review, set_result | atomic, require_admin_mode |
| msa/services/scoring.py | PointsBreakdown | _collect_player_md_matches, _is_round_fully_completed, _last_completed_md_round_size, _md_label_for_losing_round, _players_with_bye_in_r1, _round_size_from_name, _safe_get, compute_md_points, compute_q_wins_points, compute_tournament_points |  |
| msa/services/seed_anchors.py |  | band_sequence_for_S, md_anchor_map |  |
| msa/services/standings.py | RollingRow, RtFRow, SeasonRow | _activation_monday_for_tournament, _best_n_for_date, _final_winner_player_id, _intersects_weekly_window, _monday_of, _next_monday_strictly_after, _rolling_adjustments_map, _season_adjustments_map, _sorted_points_desc, _to_date, _tournament_total_points_map, _tournaments_in_season, _week_window, rolling_standings, rtf_standings, season_standings |  |
| msa/services/tx.py |  | atomic, locked |  |
| msa/services/wc.py | EntryView | _collect_entries, _cutline_D, _eff_qwc_slots, _eff_wc_slots, _rank_key, _sorted_registration_pool, _used_qwc_promotions, _used_wc_promotions, apply_qwc, apply_wc, remove_qwc, remove_wc, set_q_wc_slots, set_wc_slots | atomic |
| msa/tests/test_ll_prefix.py |  | test_enforce_ll_prefix_swaps_out_wrong_ll, test_fill_vacant_slot_prefers_ll_then_alt, test_ll_queue_ordering_nr_last, test_reinstate_original_pops_worst_ll_and_swaps_slots_if_needed | pytest.mark.django_db |
| msa/tests/test_md_band_regen.py |  | test_regenerate_seed_band_5_8_permutates_only_that_band, test_regenerate_unseeded_soft_does_not_touch_done_pairs | pytest.mark.django_db |
| msa/tests/test_md_confirm.py |  | test_confirm_main_draw_md16_s4_seeds_on_anchors_and_pairs_created, test_hard_regenerate_unseeded_changes_pool_keeps_seeds | pytest.mark.django_db |
| msa/tests/test_md_embed.py |  | test_confirm_main_draw_draw24_embeds_into_r32_with_byes_for_top8 | pytest.mark.django_db |
| msa/tests/test_md_generator.py |  | test_md16_s4_and_randomness_changes, test_md32_s8_seed_positions_deterministic, test_not_enough_unseeded_raises |  |
| msa/tests/test_md_placeholders.py |  | test_placeholders_lock_slots_and_later_swap_to_real_winners | pytest.mark.django_db |
| msa/tests/test_md_soft_regen.py |  | test_soft_regen_only_moves_unseeded_in_unfinished_r1 | pytest.mark.django_db |
| msa/tests/test_planning.py |  | test_insert_compacts_and_positions_correctly, test_save_and_restore_planning_snapshot, test_swap_across_days_and_normalize_and_clear | pytest.mark.django_db |
| msa/tests/test_qual_confirm.py |  | test_confirm_qualification_creates_full_tree_and_seeds_on_tiers, test_update_ll_after_qual_finals_promotes_final_losers | pytest.mark.django_db |
| msa/tests/test_qual_generator.py |  | test_R3_K2_tiers_top_bottom, test_R4_K3_four_tiers, test_seeds_per_bracket_formula, test_size_checks, test_unseeded_determinism_changes_with_rng |  |
| msa/tests/test_recalculate.py |  | test_brutal_reset_snapshots_and_clears_matches_and_slots, test_confirm_blocks_when_wc_or_qwc_limit_exceeded, test_preview_and_confirm_apply_groups_and_seeds_with_wc_respected | pytest.mark.django_db |
| msa/tests/test_results_needs_review.py |  | test_set_result_sets_validation_bo5_win_by_two, test_set_result_win_only_and_needs_review_propagation | pytest.mark.django_db |
| msa/tests/test_scoring.py |  | test_q_wins_accumulate_and_total_combines_with_md, test_q_wins_and_md_points_with_bye_rule_draw24 | pytest.mark.django_db |
| msa/tests/test_seed_anchors.py |  | test_anchor_counts, test_band_sequence_for_S_invalid, test_band_sequence_for_S_ok | pytest.mark.parametrize |
| msa/tests/test_standings.py |  | _mk_tournament, test_rolling_activation_and_expiry_61_weeks, test_rtf_pins_auto_top_winners, test_season_best_n_counts_top_results_only | pytest.mark.django_db |
| msa/tests/test_wc_qwc.py |  | test_qwc_promotes_alt_to_q_and_respects_limit_label_only_in_q, test_wc_above_cutline_is_label_only_does_not_consume, test_wc_below_cutline_promotes_and_demotes_last_DA_and_respects_limit | pytest.mark.django_db |
| msa/urls.py |  |  |  |
| msa/views.py |  |  |  |

## Models
### Category
- fields:
  - name: CharField

### CategorySeason
- fields:
  - category: ForeignKey
  - draw_size: PositiveSmallIntegerField
  - md_seeds_count: PositiveSmallIntegerField
  - q_wc_slots_default: PositiveSmallIntegerField
  - qual_rounds: PositiveSmallIntegerField
  - qual_seeds_per_bracket: PositiveSmallIntegerField
  - qualifiers_count: PositiveSmallIntegerField
  - scoring_md: JSONField
  - scoring_qual_win: JSONField
  - season: ForeignKey
  - wc_slots_default: PositiveSmallIntegerField
- constraints:
  - UniqueConstraint(fields=['category', 'season', 'draw_size'], name=uniq_category_season_drawsize)

### Match
- fields:
  - best_of: PositiveSmallIntegerField
  - needs_review: BooleanField
  - phase: CharField
  - player1: ForeignKey
  - player2: ForeignKey
  - player_bottom: ForeignKey
  - player_top: ForeignKey
  - position: PositiveIntegerField
  - round: CharField
  - round_name: CharField
  - score: JSONField
  - slot_bottom: PositiveIntegerField
  - slot_top: PositiveIntegerField
  - state: CharField
  - tournament: ForeignKey
  - win_by_two: BooleanField
  - winner: ForeignKey
- constraints:
  - UniqueConstraint(fields=['tournament', 'phase', 'round_name', 'slot_top', 'slot_bottom'], name=uniq_match_slot_in_round)
  - UniqueConstraint(fields=['tournament', 'round', 'position'], name=uniq_match_tournament_round_position)

### Player
- fields:
  - country: CharField
  - name: CharField

### PlayerLicense
- fields:
  - player: ForeignKey
  - season: ForeignKey
- constraints:
  - UniqueConstraint(fields=['player', 'season'], name=uniq_player_season_license)

### RankingAdjustment
- fields:
  - best_n_penalty: SmallIntegerField
  - duration_weeks: PositiveSmallIntegerField
  - player: ForeignKey
  - points_delta: IntegerField
  - scope: CharField
  - start_monday: DateField

### Schedule
- fields:
  - match: OneToOneField
  - order: PositiveIntegerField
  - play_date: DateField
  - tournament: ForeignKey
- constraints:
  - UniqueConstraint(fields=['tournament', 'play_date', 'order'], name=uniq_tournament_day_order)

### Season
- fields:
  - best_n: PositiveSmallIntegerField
  - end_date: DateField
  - name: CharField
  - start_date: DateField

### Snapshot
- fields:
  - created_at: DateTimeField
  - payload: JSONField
  - tournament: ForeignKey
  - type: CharField

### Tournament
- fields:
  - category: ForeignKey
  - category_season: ForeignKey
  - created_at: DateTimeField
  - draw_size: PositiveSmallIntegerField
  - end_date: DateField
  - md_best_of: PositiveSmallIntegerField
  - name: CharField
  - q_best_of: PositiveSmallIntegerField
  - q_wc_slots: PositiveSmallIntegerField
  - rng_seed_active: BigIntegerField
  - season: ForeignKey
  - seeding_source: CharField
  - slug: SlugField
  - snapshot_label: CharField
  - start_date: DateField
  - state: CharField
  - third_place_enabled: BooleanField
  - updated_at: DateTimeField
  - wc_slots: PositiveSmallIntegerField

### TournamentEntry
- fields:
  - entry_type: CharField
  - is_qwc: BooleanField
  - is_wc: BooleanField
  - player: ForeignKey
  - position: PositiveIntegerField
  - promoted_by_qwc: BooleanField
  - promoted_by_wc: BooleanField
  - seed: PositiveSmallIntegerField
  - status: CharField
  - tournament: ForeignKey
  - wr_snapshot: PositiveIntegerField
- constraints:
  - UniqueConstraint(fields=['tournament', 'player'], name=uniq_active_entry_per_player_tournament)
  - UniqueConstraint(fields=['tournament', 'position'], name=uniq_active_position_per_tournament)

## Services (public API)
- services/_concurrency.py
  - _lock_tournament_row
  - atomic_tournament
  - lock_qs
- services/_legacy_draw.py
- services/admin_gate.py
  - require_admin_mode
- services/archiver.py
  - _serialize_entries
  - _serialize_matches
  - _serialize_schedule
  - archive
  - archive_tournament_state
- services/draw.py
- services/licenses.py
  - _active_entries
  - _has_license
  - assert_all_licensed_or_raise
  - grant_license_for_tournament_season (require_admin_mode)
  - missing_licenses
- services/ll_prefix.py
  - _alt_queryset
  - _assigned_ll_queryset
  - _free_ll_queryset
  - _ll_queryset
  - _ll_queue_sorted
  - _md_slot_taken
  - enforce_ll_prefix_in_md (atomic)
  - fill_vacant_slot_prefer_ll_then_alt (atomic)
  - get_ll_queue
  - reinstate_original_player (atomic)
- services/md_band_regen.py
  - _default_seeds_count
  - regenerate_md_band (require_admin_mode, atomic)
- services/md_confirm.py
  - _collect_active_entries
  - _default_seeds_count
  - _entry_map_by_id
  - _pick_seeds_and_unseeded
  - _slot_to_entry_id
  - _sort_key_for_unseeded
  - confirm_main_draw (require_admin_mode, atomic)
  - hard_regenerate_unseeded_md (require_admin_mode, atomic)
- services/md_embed.py
  - _opponent_slot
  - _seed_anchor_slots_in_order
  - effective_template_size_for_md
  - generate_md_mapping_with_byes
  - next_power_of_two
  - pairings_round1
  - r1_name_for_md
- services/md_generator.py
  - generate_main_draw_mapping
- services/md_placeholders.py
  - _ensure_placeholder_player
  - _existing_placeholder_entries
  - _final_winner_player_id_for_branch
  - confirm_md_with_placeholders (require_admin_mode, atomic)
  - create_md_placeholders (require_admin_mode, atomic)
  - replace_placeholders_with_qual_winners (require_admin_mode, atomic)
- services/md_reopen.py
  - reopen_main_draw (require_admin_mode, atomic)
- services/md_roster.py
  - _get_r1_match
  - _update_match_for_slot
  - ensure_vacancies_filled (require_admin_mode, atomic)
  - remove_player_from_md (require_admin_mode, atomic)
  - use_reserve_now (require_admin_mode, atomic)
- services/md_soft_regen.py
  - _collect_active_entries
  - _default_seeds_count
  - _seed_ids_by_wr
  - soft_regenerate_unseeded_md (require_admin_mode, atomic)
- services/md_third_place.py
  - ensure_third_place_match (atomic)
- services/ops.py
  - replace_slot (atomic_tournament)
- services/planning.py
  - _compact_day
  - _ensure_not_scheduled_elsewhere
  - _list_all
  - _list_day
  - _restore_payload
  - _serialize_day_items
  - _snapshot_payload
  - clear_day (require_admin_mode, atomic)
  - insert_match (require_admin_mode, atomic)
  - list_day_order (atomic)
  - move_match (require_admin_mode, atomic)
  - normalize_day (require_admin_mode, atomic)
  - restore_planning_snapshot (require_admin_mode, atomic)
  - save_planning_snapshot (require_admin_mode, atomic)
  - swap_matches (require_admin_mode, atomic)
- services/qual_confirm.py
  - _collect_qual_entries
  - _pairs_for_size
  - _round_name
  - _sort_by_wr
  - confirm_qualification (require_admin_mode, atomic)
  - update_ll_after_qual_finals (require_admin_mode, atomic)
- services/qual_edit.py
  - _fetch_r1_for_slot
  - _local_slot
  - _qual_size_and_anchors
  - _r1_name_for_size
  - _side_is_top
  - swap_slots_in_qualification (require_admin_mode, atomic)
- services/qual_generator.py
  - bracket_anchor_tiers
  - generate_qualification_mapping
  - seeds_per_bracket
- services/qual_replace.py
  - _pick_best_alt_qs
  - _r1_qual_round_name
  - remove_and_replace_in_qualification (require_admin_mode, atomic)
- services/recalculate.py
  - _current_layout
  - _default_md_seeds
  - _diff
  - _eff_draw_params
  - _eff_md_seeds
  - _eff_qwc_limit
  - _eff_wc_limit
  - _entries_active
  - _proposed_layout
  - _sort_by_wr
  - brutal_reset_to_registration (require_admin_mode, atomic)
  - confirm_recalculate_registration (require_admin_mode, atomic)
  - preview_recalculate_registration (atomic)
- services/results.py
  - _collect_downstream_matches_containing_player
  - _parent_pair_for_child
  - _propagate_winner_to_next_round
  - _round_size_from_name
  - _validate_sets
  - resolve_needs_review (require_admin_mode, atomic)
  - set_result (require_admin_mode, atomic)
- services/scoring.py
  - _collect_player_md_matches
  - _is_round_fully_completed
  - _last_completed_md_round_size
  - _md_label_for_losing_round
  - _players_with_bye_in_r1
  - _round_size_from_name
  - _safe_get
  - compute_md_points
  - compute_q_wins_points
  - compute_tournament_points
- services/seed_anchors.py
  - band_sequence_for_S
  - md_anchor_map
- services/standings.py
  - _activation_monday_for_tournament
  - _best_n_for_date
  - _final_winner_player_id
  - _intersects_weekly_window
  - _monday_of
  - _next_monday_strictly_after
  - _rolling_adjustments_map
  - _season_adjustments_map
  - _sorted_points_desc
  - _to_date
  - _tournament_total_points_map
  - _tournaments_in_season
  - _week_window
  - rolling_standings
  - rtf_standings
  - season_standings
- services/tx.py
  - atomic
  - locked
- services/wc.py
  - _collect_entries
  - _cutline_D
  - _eff_qwc_slots
  - _eff_wc_slots
  - _rank_key
  - _sorted_registration_pool
  - _used_qwc_promotions
  - _used_wc_promotions
  - apply_qwc (atomic)
  - apply_wc (atomic)
  - remove_qwc (atomic)
  - remove_wc (atomic)
  - set_q_wc_slots (atomic)
  - set_wc_slots (atomic)

## Tests discovered
- msa/tests/test_ll_prefix.py
  - test_enforce_ll_prefix_swaps_out_wrong_ll
  - test_fill_vacant_slot_prefers_ll_then_alt
  - test_ll_queue_ordering_nr_last
  - test_reinstate_original_pops_worst_ll_and_swaps_slots_if_needed
- msa/tests/test_md_band_regen.py
  - test_regenerate_seed_band_5_8_permutates_only_that_band
  - test_regenerate_unseeded_soft_does_not_touch_done_pairs
- msa/tests/test_md_confirm.py
  - test_confirm_main_draw_md16_s4_seeds_on_anchors_and_pairs_created
  - test_hard_regenerate_unseeded_changes_pool_keeps_seeds
- msa/tests/test_md_embed.py
  - test_confirm_main_draw_draw24_embeds_into_r32_with_byes_for_top8
- msa/tests/test_md_generator.py
  - test_md16_s4_and_randomness_changes
  - test_md32_s8_seed_positions_deterministic
  - test_not_enough_unseeded_raises
- msa/tests/test_md_placeholders.py
  - test_placeholders_lock_slots_and_later_swap_to_real_winners
- msa/tests/test_md_soft_regen.py
  - test_soft_regen_only_moves_unseeded_in_unfinished_r1
- msa/tests/test_planning.py
  - test_insert_compacts_and_positions_correctly
  - test_save_and_restore_planning_snapshot
  - test_swap_across_days_and_normalize_and_clear
- msa/tests/test_qual_confirm.py
  - test_confirm_qualification_creates_full_tree_and_seeds_on_tiers
  - test_update_ll_after_qual_finals_promotes_final_losers
- msa/tests/test_qual_generator.py
  - test_R3_K2_tiers_top_bottom
  - test_R4_K3_four_tiers
  - test_seeds_per_bracket_formula
  - test_size_checks
  - test_unseeded_determinism_changes_with_rng
- msa/tests/test_recalculate.py
  - test_brutal_reset_snapshots_and_clears_matches_and_slots
  - test_confirm_blocks_when_wc_or_qwc_limit_exceeded
  - test_preview_and_confirm_apply_groups_and_seeds_with_wc_respected
- msa/tests/test_results_needs_review.py
  - test_set_result_sets_validation_bo5_win_by_two
  - test_set_result_win_only_and_needs_review_propagation
- msa/tests/test_scoring.py
  - test_q_wins_accumulate_and_total_combines_with_md
  - test_q_wins_and_md_points_with_bye_rule_draw24
- msa/tests/test_seed_anchors.py
  - test_anchor_counts
  - test_band_sequence_for_S_invalid
  - test_band_sequence_for_S_ok
- msa/tests/test_standings.py
  - test_rolling_activation_and_expiry_61_weeks
  - test_rtf_pins_auto_top_winners
  - test_season_best_n_counts_top_results_only
- msa/tests/test_wc_qwc.py
  - test_qwc_promotes_alt_to_q_and_respects_limit_label_only_in_q
  - test_wc_above_cutline_is_label_only_does_not_consume
  - test_wc_below_cutline_promotes_and_demotes_last_DA_and_respects_limit

## Keyword scan (per file)
| path | select_for_update( | @transaction.atomic | UniqueConstraint( | get_or_create( | update_or_create( | q_best_of | md_best_of | rng_seed | needs_review | LL | ALT | BYE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| msa/__init__.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/admin.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 |
| msa/apps.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/context_processors.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/forms.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/migrations/__init__.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/models.py | 0 | 0 | 7 | 0 | 0 | 1 | 1 | 1 | 1 | 2 | 2 | 0 |
| msa/services/_concurrency.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/services/_legacy_draw.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/services/admin_gate.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/services/archiver.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 |
| msa/services/draw.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/services/licenses.py | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/services/ll_prefix.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 34 | 4 | 0 |
| msa/services/md_band_regen.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 |
| msa/services/md_confirm.py | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 20 | 0 | 3 | 3 | 7 |
| msa/services/md_embed.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 3 |
| msa/services/md_generator.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 1 | 0 | 0 |
| msa/services/md_placeholders.py | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 |
| msa/services/md_reopen.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 |
| msa/services/md_roster.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 3 | 0 |
| msa/services/md_soft_regen.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| msa/services/md_third_place.py | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| msa/services/ops.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/services/planning.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/services/qual_confirm.py | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 9 | 0 | 5 | 0 | 0 |
| msa/services/qual_edit.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/services/qual_generator.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 |
| msa/services/qual_replace.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 |
| msa/services/recalculate.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 1 | 3 | 0 |
| msa/services/results.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 12 | 0 | 0 | 0 |
| msa/services/scoring.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 |
| msa/services/seed_anchors.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/services/standings.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/services/tx.py | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/services/wc.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 |
| msa/tests/test_ll_prefix.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 20 | 6 | 0 |
| msa/tests/test_md_band_regen.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 |
| msa/tests/test_md_confirm.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 |
| msa/tests/test_md_embed.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 4 |
| msa/tests/test_md_generator.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 |
| msa/tests/test_md_placeholders.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| msa/tests/test_md_soft_regen.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| msa/tests/test_planning.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/tests/test_qual_confirm.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 |
| msa/tests/test_qual_generator.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 |
| msa/tests/test_recalculate.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| msa/tests/test_results_needs_review.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 |
| msa/tests/test_scoring.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 4 |
| msa/tests/test_seed_anchors.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/tests/test_standings.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/tests/test_wc_qwc.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 11 | 0 |
| msa/urls.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| msa/views.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Gaps vs "MSA 1.0 – kompletní specifikace"
- [ ] Deterministic seeding (rng_seed + generate_draw)
- [x] No-BYE templates (embed non-power-of-two)
- [x] LL queue + prefix invariant, ALT flow
- [ ] WC/QWC capacity validation
- [ ] Snapshots (Confirm/Generate/Regenerate/Reopen/Manual) + audit
- [ ] Planning day (swap/insert) with locks + preview
- [ ] Recalculate with diff preview
- [ ] Rankings (61-week rolling, Monday activation/expiry, Season/RtF, best-N penalty, adjustments)
- [ ] License gate (season license required)
- [x] needs_review propagation on results