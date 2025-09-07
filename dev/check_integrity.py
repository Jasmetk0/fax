#!/usr/bin/env python3
"""Verify msa/services modules expose expected public functions."""

from __future__ import annotations

import ast
import pathlib

SPEC = {
    "seed_anchors.py": ["md_anchor_map", "band_sequence_for_S"],
    "md_generator.py": ["generate_main_draw_mapping"],
    "md_embed.py": [
        "effective_template_size_for_md",
        "r1_name_for_md",
        "generate_md_mapping_with_byes",
        "pairings_round1",
    ],
    "md_confirm.py": ["confirm_main_draw", "hard_regenerate_unseeded_md"],
    "md_soft_regen.py": ["soft_regenerate_unseeded_md"],
    "md_band_regen.py": ["regenerate_md_band"],
    "qual_generator.py": [
        "bracket_anchor_tiers",
        "seeds_per_bracket",
        "generate_qualification_mapping",
    ],
    "qual_confirm.py": ["confirm_qualification", "update_ll_after_qual_finals"],
    "md_placeholders.py": [
        "create_md_placeholders",
        "confirm_md_with_placeholders",
        "replace_placeholders_with_qual_winners",
    ],
    "ll_prefix.py": [
        "get_ll_queue",
        "fill_vacant_slot_prefer_ll_then_alt",
        "enforce_ll_prefix_in_md",
        "reinstate_original_player",
    ],
    "results.py": ["set_result", "resolve_needs_review"],
    "planning.py": [
        "insert_match",
        "swap_matches",
        "normalize_day",
        "clear_day",
        "list_day_order",
        "move_match",
        "save_planning_snapshot",
        "restore_planning_snapshot",
    ],
    "recalculate.py": [
        "preview_recalculate_registration",
        "confirm_recalculate_registration",
        "brutal_reset_to_registration",
    ],
    "wc.py": [
        "set_wc_slots",
        "set_q_wc_slots",
        "apply_wc",
        "remove_wc",
        "apply_qwc",
        "remove_qwc",
    ],
    "scoring.py": [
        "compute_q_wins_points",
        "compute_md_points",
        "compute_tournament_points",
    ],
    "standings.py": [
        "season_standings",
        "rolling_standings",
        "rtf_standings",
    ],
    "tx.py": ["atomic", "locked"],
}


def functions_in_module(path: pathlib.Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    return [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]


def main() -> int:
    services_dir = pathlib.Path(__file__).resolve().parents[1] / "msa" / "services"
    files = {p.name: functions_in_module(p) for p in services_dir.glob("*.py")}

    missing_modules = [m for m in SPEC if m not in files]
    missing_functions = {
        m: [f for f in funcs if f not in files.get(m, [])]
        for m, funcs in SPEC.items()
        if m in files and any(f not in files[m] for f in funcs)
    }
    extra_functions = {m: [f for f in files[m] if f not in SPEC.get(m, [])] for m in files}

    print("Missing modules:", missing_modules)
    print("Missing functions:", missing_functions)
    print("Extra functions:", extra_functions)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
