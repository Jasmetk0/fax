# Status
## Services
- `ll_prefix.py`: _ll_queryset, _assigned_ll_queryset, _free_ll_queryset, _alt_queryset, _md_slot_taken, _ll_queue_sorted, get_ll_queue, fill_vacant_slot_prefer_ll_then_alt, enforce_ll_prefix_in_md, reinstate_original_player
- `md_band_regen.py`: _default_seeds_count, _r1_name, regenerate_md_band
- `md_confirm.py`: _default_seeds_count, _collect_active_entries, _sort_key_for_unseeded, _pick_seeds_and_unseeded, _pairings_round1, _entry_map_by_id, _slot_to_entry_id, confirm_main_draw, hard_regenerate_unseeded_md
- `md_embed.py`: next_power_of_two, effective_template_size_for_md, r1_name_for_md, _seed_anchor_slots_in_order, _opponent_slot, generate_md_mapping_with_byes, pairings_round1
- `md_generator.py`: generate_main_draw_mapping
- `md_placeholders.py`: _ensure_placeholder_player, _existing_placeholder_entries, create_md_placeholders, confirm_md_with_placeholders, _final_winner_player_id_for_branch, replace_placeholders_with_qual_winners
- `md_soft_regen.py`: _collect_active_entries, _default_seeds_count, _seed_ids_by_wr, soft_regenerate_unseeded_md
- `planning.py`: _list_day, _list_all, _compact_day, _snapshot_payload, _restore_payload, _ensure_not_scheduled_elsewhere, _serialize_day_items, list_day_order, insert_match, swap_matches, normalize_day, clear_day, move_match, save_planning_snapshot, restore_planning_snapshot
- `qual_confirm.py`: _collect_qual_entries, _sort_by_wr, _round_name, _pairs_for_size, confirm_qualification, update_ll_after_qual_finals
- `qual_generator.py`: bracket_anchor_tiers, seeds_per_bracket, generate_qualification_mapping
- `recalculate.py`: _eff_draw_params, _default_md_seeds, _eff_md_seeds, _eff_wc_limit, _entries_active, _sort_by_wr, _current_layout, _proposed_layout, _diff, preview_recalculate_registration, confirm_recalculate_registration, brutal_reset_to_registration
- `results.py`: _round_size_from_name, _validate_sets, _collect_downstream_matches_containing_player, set_result, resolve_needs_review
- `scoring.py`: _round_size_from_name, _is_round_fully_completed, _last_completed_md_round_size, _md_label_for_losing_round, _safe_get, compute_q_wins_points, _players_with_bye_in_r1, _collect_player_md_matches, compute_md_points, compute_tournament_points
- `seed_anchors.py`: md_anchor_map, band_sequence_for_S
- `standings.py`: _to_date, _next_monday_strictly_after, _monday_of, _tournaments_in_season, _tournament_total_points_map, _sorted_points_desc, _best_n_for_date, season_standings, _activation_monday_for_tournament, rolling_standings, _final_winner_player_id, rtf_standings
- `tx.py`: atomic, locked
- `wc.py`: _eff_wc_slots, _eff_qwc_slots, _collect_entries, _rank_key, _sorted_registration_pool, _cutline_D, _used_wc_promotions, _used_qwc_promotions, set_wc_slots, set_q_wc_slots, apply_wc, remove_wc, apply_qwc, remove_qwc

## Tests
- `msa/tests/test_ll_prefix.py`: test_ll_queue_ordering_nr_last, test_fill_vacant_slot_prefers_ll_then_alt, test_enforce_ll_prefix_swaps_out_wrong_ll, test_reinstate_original_pops_worst_ll_and_swaps_slots_if_needed
- `msa/tests/test_md_band_regen.py`: test_regenerate_seed_band_5_8_permutates_only_that_band, test_regenerate_unseeded_soft_does_not_touch_done_pairs
- `msa/tests/test_md_confirm.py`: test_confirm_main_draw_md16_s4_seeds_on_anchors_and_pairs_created, test_hard_regenerate_unseeded_changes_pool_keeps_seeds
- `msa/tests/test_md_embed.py`: test_confirm_main_draw_draw24_embeds_into_r32_with_byes_for_top8
- `msa/tests/test_md_generator.py`: test_md32_s8_seed_positions_deterministic, test_md16_s4_and_randomness_changes, test_not_enough_unseeded_raises
- `msa/tests/test_md_placeholders.py`: test_placeholders_lock_slots_and_later_swap_to_real_winners
- `msa/tests/test_md_soft_regen.py`: test_soft_regen_only_moves_unseeded_in_unfinished_r1
- `msa/tests/test_planning.py`: test_insert_compacts_and_positions_correctly, test_swap_across_days_and_normalize_and_clear, test_save_and_restore_planning_snapshot
- `msa/tests/test_qual_confirm.py`: test_confirm_qualification_creates_full_tree_and_seeds_on_tiers, test_update_ll_after_qual_finals_promotes_final_losers
- `msa/tests/test_qual_generator.py`: test_seeds_per_bracket_formula, test_R3_K2_tiers_top_bottom, test_R4_K3_four_tiers, test_unseeded_determinism_changes_with_rng, test_size_checks
- `msa/tests/test_recalculate.py`: test_preview_and_confirm_apply_groups_and_seeds_with_wc_respected, test_brutal_reset_snapshots_and_clears_matches_and_slots
- `msa/tests/test_results_needs_review.py`: test_set_result_win_only_and_needs_review_propagation, test_set_result_sets_validation_bo5_win_by_two
- `msa/tests/test_scoring.py`: test_q_wins_and_md_points_with_bye_rule_draw24, test_q_wins_accumulate_and_total_combines_with_md
- `msa/tests/test_seed_anchors.py`: test_anchor_counts, test_band_sequence_for_S_ok, test_band_sequence_for_S_invalid
- `msa/tests/test_standings.py`: _mk_tournament, test_season_best_n_counts_top_results_only, test_rolling_activation_and_expiry_61_weeks, test_rtf_pins_auto_top_winners
- `msa/tests/test_wc_qwc.py`: test_wc_above_cutline_is_label_only_does_not_consume, test_wc_below_cutline_promotes_and_demotes_last_DA_and_respects_limit, test_qwc_promotes_alt_to_q_and_respects_limit_label_only_in_q
- `tests/test_app_labels_unique.py`: test_installed_apps_no_duplicates
- `tests/test_fax_calendar_from_storage.py`: test_from_storage_various_inputs
- `tests/test_fax_calendar_parsing.py`: test_parse_none, test_parse_empty_string, test_parse_iso_format, test_parse_dd_mm_yyyy, test_parse_with_dots, test_parse_bytes, test_invalid_input_raises_validation_error

## Metrics
- SPEC coverage: 100%
- Test results: 49 passed, 1 warning in 4.18s

## Known gaps
- None

## Known risks
- No duplicate imports detected; many private helpers could hide dead code.
