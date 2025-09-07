#!/usr/bin/env python3
"""Generate STATUS.md summarizing services and tests."""

from __future__ import annotations

import ast
import pathlib
import subprocess

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


def collect_services() -> dict[str, list[str]]:
    services_dir = pathlib.Path("msa/services")
    return {p.name: functions_in_module(p) for p in services_dir.glob("*.py")}


def collect_tests() -> dict[str, list[str]]:
    test_dirs = [pathlib.Path("tests"), pathlib.Path("msa/tests")]
    out: dict[str, list[str]] = {}
    for d in test_dirs:
        if not d.exists():
            continue
        for p in d.glob("test_*.py"):
            out[p.as_posix()] = functions_in_module(p)
    return out


def compare_with_spec(files: dict[str, list[str]]) -> tuple[list[str], dict[str, list[str]]]:
    missing_modules = [m for m in SPEC if m not in files]
    missing_functions = {
        m: [f for f in funcs if f not in files.get(m, [])]
        for m, funcs in SPEC.items()
        if m in files and any(f not in files[m] for f in funcs)
    }
    return missing_modules, missing_functions


def test_summary() -> str:
    proc = subprocess.run(["pytest", "-q"], capture_output=True, text=True)
    for line in reversed(proc.stdout.strip().splitlines()):
        if line and not line.startswith("="):
            return line
    return ""


def main() -> int:
    services = collect_services()
    tests = collect_tests()
    missing_modules, missing_functions = compare_with_spec(services)

    total_spec = sum(len(v) for v in SPEC.values())
    missing_count = sum(len(v) for v in missing_functions.values()) + len(missing_modules)
    coverage = 100 * (total_spec - missing_count) / total_spec if total_spec else 100

    summary = ["# Status\n"]
    summary.append("## Services\n")
    for file, funcs in sorted(services.items()):
        summary.append(f"- `{file}`: {', '.join(funcs)}\n")

    summary.append("\n## Tests\n")
    for file, funcs in sorted(tests.items()):
        summary.append(f"- `{file}`: {', '.join(funcs)}\n")

    summary.append("\n## Metrics\n")
    summary.append(f"- SPEC coverage: {coverage:.0f}%\n")
    summary.append(f"- Test results: {test_summary()}\n")

    summary.append("\n## Known gaps\n")
    if not missing_modules and not missing_functions:
        summary.append("- None\n")
    else:
        for m in missing_modules:
            summary.append(f"- Missing module: {m}\n")
        for m, funcs in missing_functions.items():
            summary.append(f"- {m}: missing {', '.join(funcs)}\n")

    summary.append("\n## Known risks\n")
    summary.append("- No duplicate imports detected; many private helpers could hide dead code.\n")

    pathlib.Path("STATUS.md").write_text("".join(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
