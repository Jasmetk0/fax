#!/usr/bin/env python3
"""Generate MSA compliance report based on docs/MSA_SPEC.yaml."""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator  # noqa: UP035

# ---------------------------------------------------------------------------
# YAML parsing (minimal)


def _parse_scalar(token: str) -> Any:
    token = token.strip()
    if token.startswith("[") and token.endswith("]"):
        inner = token[1:-1].strip()
        if not inner:
            return []
        return [part.strip().strip("\"'") for part in inner.split(",")]
    if token.startswith("'") and token.endswith("'"):
        return token[1:-1]
    if token.startswith('"') and token.endswith('"'):
        return token[1:-1]
    if token.isdigit():
        return int(token)
    if token.lower() in {"true", "false"}:
        return token.lower() == "true"
    return token


def _parse_yaml_lines(lines: list[str], indent: int, start: int) -> tuple[Any, int]:
    items: list[Any] = []
    mapping: dict[str, Any] = {}
    i = start
    is_list = False
    while i < len(lines):
        raw = lines[i]
        if "#" in raw:
            raw = raw.split("#", 1)[0]
        if not raw.strip():
            i += 1
            continue
        cur_indent = len(raw) - len(raw.lstrip(" "))
        if cur_indent < indent:
            break
        stripped = raw.strip()
        if stripped.startswith("- "):
            is_list = True
            item = stripped[2:]
            if item and not item.endswith(":"):
                items.append(_parse_scalar(item))
                i += 1
            else:
                key = item[:-1].strip() if item.endswith(":") else None
                sub, j = _parse_yaml_lines(lines, indent + 2, i + 1)
                if key is None:
                    items.append(sub)
                else:
                    items.append({key: sub})
                i = j
        else:
            if is_list:
                break
            key, _, rest = stripped.partition(":")
            key = key.strip()
            rest = rest.strip()
            if rest:
                mapping[key] = _parse_scalar(rest)
                i += 1
            else:
                sub, j = _parse_yaml_lines(lines, indent + 2, i + 1)
                mapping[key] = sub
                i = j
    return (items if is_list else mapping), i


def load_spec(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    data, _ = _parse_yaml_lines(lines, 0, 0)
    assert isinstance(data, dict)
    return data


def load_answers(path: Path) -> dict[str, Any]:
    """Return mapping with clarifications for AR checks."""
    if not path.exists():
        return {}
    data = load_spec(path)
    ans = data.get("answers")
    return ans if isinstance(ans, dict) else {}


# ---------------------------------------------------------------------------
# Data collection

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class FileData:
    path: Path
    text: str
    tree: ast.AST | None


def iter_py_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*.py")):
        if "migrations" in path.parts and path.name != "__init__.py":
            continue
        yield path


def read_repo(msa_dir: Path) -> tuple[dict[str, FileData], dict[str, list[str]]]:
    files: dict[str, FileData] = {}
    tests: dict[str, list[str]] = {}
    for path in iter_py_files(ROOT):
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            tree = None
        files[rel] = FileData(path=path, text=text, tree=tree)
        if rel.startswith(f"{msa_dir.as_posix()}/tests"):
            names: list[str] = []
            if tree:
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
                        names.append(node.name)
                    if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                        names.append(node.name)
            tests[rel] = names
    return files, tests


def dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{dotted(node.value)}.{node.attr}"
    if isinstance(node, ast.Call):
        return dotted(node.func)
    return ""


# ---------------------------------------------------------------------------
# Feature checks

MUTATOR_PREFIXES = (
    "confirm",
    "apply",
    "regenerate",
    "reopen",
    "insert",
    "move",
    "swap",
    "clear",
    "remove",
    "set_",
    "use_",
    "resolve",
    "save",
    "restore",
    "create",
    "replace",
    "update",
)


@dataclass
class GatingInfo:
    total: int = 0
    ok: int = 0
    missing: list[str] = field(default_factory=list)


def analyze_admin_gating(
    mods: list[str], files: dict[str, FileData]
) -> tuple[dict[str, GatingInfo], list[str]]:
    ungated: list[str] = []
    res: dict[str, GatingInfo] = {}
    for mod in mods:
        info = GatingInfo()
        fd = files.get(mod)
        if not fd or not fd.tree:
            res[mod] = info
            continue
        for node in fd.tree.body:
            if isinstance(node, ast.FunctionDef) and any(
                node.name.startswith(p) for p in MUTATOR_PREFIXES
            ):
                info.total += 1
                decos = {dotted(d) for d in node.decorator_list}
                has_admin = any("require_admin_mode" in d for d in decos)
                has_atomic = any(d.split(".")[-1] == "atomic" for d in decos)
                if has_admin and has_atomic:
                    info.ok += 1
                else:
                    info.missing.append(f"{node.name}:{node.lineno}")
                    ungated.append(f"{mod}:{node.lineno}:{node.name}")
        res[mod] = info
    return res, ungated


def feature_checks(
    spec: dict[str, Any],
    files: dict[str, FileData],
    tests: dict[str, list[str]],
    models: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    features: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    warns: list[str] = []

    def has_module(path: str) -> bool:
        return path in files

    def has_test(path: str) -> bool:
        return path in tests

    def test_name_contains(substr: str) -> bool:
        return any(substr in n for names in tests.values() for n in names)

    def module_contains(path: str, substr: str) -> bool:
        fd = files.get(path)
        return bool(fd and substr in fd.text)

    gating_mods = spec.get("services", {}).get("must_be_admin_gated", [])
    gating_res, _ = analyze_admin_gating(gating_mods, files)
    ok = all(info.total == info.ok for info in gating_res.values())
    evidence = ", ".join(f"{Path(m).name}[{g.ok}/{g.total}]" for m, g in gating_res.items())
    features["admin_mode_gate"] = {"pass": ok, "evidence": evidence}
    if not ok:
        errors.append("admin_mode_gate")

    rng_mods = spec.get("services", {}).get("use_central_rng", [])
    rng_missing = []
    for mod in rng_mods:
        fd = files.get(mod)
        text = fd.text if fd else ""
        if "rng_for" not in text or "rng_for(" not in text or "randoms" not in text:
            rng_missing.append(mod)
    determinism_test = (
        has_test("msa/tests/test_md_generator.py")
        or has_test("msa/tests/test_qual_generator.py")
        or test_name_contains("seed_positions_deterministic")
        or test_name_contains("unseeded_determinism")
    )
    ok = not rng_missing and determinism_test
    if ok:
        features["deterministic_seeding"] = {"pass": True, "evidence": "rng_for and tests"}
    else:
        ev = []
        if rng_missing:
            ev.append("missing rng_for: " + ", ".join(Path(m).name for m in rng_missing))
        if not determinism_test:
            ev.append("no determinism test")
        features["deterministic_seeding"] = {"pass": False, "evidence": "; ".join(ev)}
        errors.append("deterministic_seeding")

    def feature_file_test(module: str, test_path: str, name: str) -> None:
        ok = has_module(module) and has_test(test_path)
        features[name] = {
            "pass": ok,
            "evidence": f"{Path(module).name if has_module(module) else 'missing module'}; "
            f"{Path(test_path).name if has_test(test_path) else 'missing test'}",
        }
        if not ok:
            errors.append(name)

    feature_file_test("msa/services/md_embed.py", "msa/tests/test_md_embed.py", "no_bye_templates")
    feature_file_test(
        "msa/services/ll_prefix.py", "msa/tests/test_ll_prefix.py", "ll_prefix_invariant"
    )
    feature_file_test("msa/services/wc.py", "msa/tests/test_wc_qwc.py", "wc_qwc_limits")
    feature_file_test("msa/services/planning.py", "msa/tests/test_planning.py", "planning_day")
    feature_file_test(
        "msa/services/results.py", "msa/tests/test_results_needs_review.py", "needs_review_flow"
    )

    snapshot_model = "Snapshot" in models
    archive_ok = (snapshot_model or has_module("msa/services/archiver.py")) and has_test(
        "msa/tests/test_recalculate.py"
    )
    features["snapshots_archive"] = {
        "pass": archive_ok,
        "evidence": "Snapshot model" if snapshot_model else "archiver.py",
    }
    if not archive_ok:
        errors.append("snapshots_archive")

    recalc_mod = "msa/services/recalculate.py"
    recalc_ok = (
        has_module(recalc_mod)
        and (
            module_contains(recalc_mod, "_diff")
            or test_name_contains("preview")
            or test_name_contains("recalculate")
        )
        and has_test("msa/tests/test_recalculate.py")
    )
    features["recalculate_with_diff"] = {
        "pass": recalc_ok,
        "evidence": "recalculate.py" if has_module(recalc_mod) else "missing module",
    }
    if not recalc_ok:
        errors.append("recalculate_with_diff")

    standings_mod = "msa/services/standings.py"
    standings_ok = (
        has_module(standings_mod)
        and has_test("msa/tests/test_standings.py")
        and (module_contains(standings_mod, "61") or test_name_contains("61_week"))
    )
    features["rankings_61w_monday"] = {
        "pass": standings_ok,
        "evidence": "standings" if standings_ok else "missing",
    }
    if not standings_ok:
        errors.append("rankings_61w_monday")

    lic_mod = "msa/services/licenses.py"
    license_ok = has_module(lic_mod) and (
        module_contains("msa/services/md_confirm.py", "assert_all_licensed_or_raise")
        or module_contains("msa/services/qual_confirm.py", "assert_all_licensed_or_raise")
    )
    features["license_gate_required"] = {
        "pass": license_ok,
        "evidence": "licenses.py" if has_module(lic_mod) else "missing module",
    }
    if not license_ok:
        errors.append("license_gate_required")

    return features, errors, warns


# ---------------------------------------------------------------------------
# Model parsing and checks


def collect_models(files: dict[str, FileData]) -> dict[str, dict[str, Any]]:
    models: dict[str, dict[str, Any]] = {}
    for rel, fd in files.items():
        if not rel.startswith("msa/") or not fd.tree:
            continue
        for node in fd.tree.body:
            if isinstance(node, ast.ClassDef) and node.name not in models:
                fields: set[str] = set()
                uniques: set[tuple[str, ...]] = set()
                meta: ast.ClassDef | None = None
                for stmt in node.body:
                    if isinstance(stmt, ast.Assign | ast.AnnAssign):
                        target = stmt.targets[0] if isinstance(stmt, ast.Assign) else stmt.target
                        if isinstance(target, ast.Name):
                            fields.add(target.id)
                    if isinstance(stmt, ast.ClassDef) and stmt.name == "Meta":
                        meta = stmt
                if meta:
                    for m in meta.body:
                        if isinstance(m, ast.Assign) and isinstance(m.targets[0], ast.Name):
                            if m.targets[0].id == "constraints" and isinstance(m.value, ast.List):
                                for el in m.value.elts:
                                    if isinstance(el, ast.Call) and dotted(el.func).endswith(
                                        "UniqueConstraint"
                                    ):
                                        for kw in el.keywords:
                                            if kw.arg == "fields" and isinstance(
                                                kw.value, ast.List
                                            ):
                                                fields_list = [
                                                    f.value
                                                    for f in kw.value.elts
                                                    if isinstance(f, ast.Constant)
                                                ]
                                                if fields_list:
                                                    uniques.add(tuple(fields_list))
                models[node.name] = {"fields": fields, "unique_constraints": uniques}
    return models


def check_models(
    spec_models: dict[str, Any], models: dict[str, dict[str, Any]]
) -> tuple[dict[str, Any], list[str], list[str]]:
    results: dict[str, Any] = {}
    errors: list[str] = []
    warns: list[str] = []
    for name, info in spec_models.items():
        expected = [tuple(x) for x in info.get("unique_constraints", [])]
        found = models.get(name, {"unique_constraints": set(), "fields": set()})
        found_uc = found["unique_constraints"]
        missing = [uc for uc in expected if uc not in found_uc]
        extra = [uc for uc in sorted(found_uc) if uc not in expected]
        if missing:
            errors.append(f"{name} missing constraints: {missing}")
        if extra:
            warns.append(f"{name} extra constraints: {extra}")
        res = {
            "unique": [list(u) for u in expected],
            "missing": [list(u) for u in missing],
            "extra": [list(u) for u in extra],
            "fields_missing": [],
        }
        if name == "Tournament":
            req_fields = set(info.get("fields_required", []))
            fields_missing = sorted(req_fields - found["fields"])
            if fields_missing:
                errors.append(f"Tournament missing fields: {fields_missing}")
            res["fields_missing"] = fields_missing
        results[name] = res
    return results, errors, warns


# ---------------------------------------------------------------------------
# RNG hygiene

RNG_PATTERNS = {
    "random.Random(": re.compile(r"random\.Random\("),
    "random.shuffle(": re.compile(r"random\.shuffle\("),
    "random.sample(": re.compile(r"random\.sample\("),
}


def check_rng(
    files: dict[str, FileData], rng_modules: list[str]
) -> tuple[list[str], dict[str, bool], list[str]]:
    offenders: list[str] = []
    for rel, fd in files.items():
        if not rel.startswith("msa/services") or rel == "msa/services/randoms.py":
            continue
        for name, pat in RNG_PATTERNS.items():
            for m in pat.finditer(fd.text):
                line = fd.text[: m.start()].count("\n") + 1
                offenders.append(f"{rel}:{line} -> {name}")
    offenders.sort()
    rng_results: dict[str, bool] = {}
    rng_errors: list[str] = []
    for mod in rng_modules:
        fd = files.get(mod)
        text = fd.text if fd else ""
        ok = "rng_for" in text and "rng_for(" in text and "randoms" in text
        rng_results[mod] = ok
        if not ok:
            rng_errors.append(mod)
    return offenders, rng_results, rng_errors


# ---------------------------------------------------------------------------
# Tests coverage


def check_tests(expected: list[str]) -> tuple[list[str], list[str]]:
    present = [p for p in expected if (ROOT / p).exists()]
    missing = [p for p in expected if p not in present]
    return present, missing


# ---------------------------------------------------------------------------
# Risky patterns

RISKY = ["select_for_update(", "get_or_create(", "update_or_create("]


def risky_patterns(files: dict[str, FileData]) -> list[tuple[str, dict[str, int]]]:
    out: list[tuple[str, dict[str, int]]] = []
    for rel, fd in files.items():
        if not rel.startswith("msa/"):
            continue
        counts = {k: fd.text.count(k) for k in RISKY}
        if sum(counts.values()) > 0:
            out.append((rel, counts))
    out.sort(key=lambda x: (-sum(x[1].values()), x[0]))
    return out[:10]


# ---------------------------------------------------------------------------
# Atomic requirements verification


def build_atomic_requirements() -> list[dict[str, str]]:
    """Return deterministic list of Atomic Requirements."""
    return [
        {"id": "AR-REG-001", "title": "Seeding source sorting"},
        {"id": "AR-REG-002", "title": "Manual reordering constraints"},
        {"id": "AR-REG-003", "title": "Seeds power-of-two"},
        {"id": "AR-REC-001", "title": "Recalculate preview/confirm"},
        {"id": "AR-REC-002", "title": "Brutal reset archives snapshot first"},
        {
            "id": "AR-REC-003",
            "title": "Preview fields: rng_seed, anchors, unseeded, matches_changed",
        },
        {"id": "AR-QUAL-001", "title": "Qual seeding tiers 2^(R-2) across K"},
        {"id": "AR-LL-001", "title": "LL queue & order"},
        {"id": "AR-LL-002", "title": "LL prefix invariant & reinstatement rules"},
        {"id": "AR-MD-001", "title": "Canonical seed anchors MD16/32/64"},
        {"id": "AR-MD-004", "title": "Non power-of-two embed, no BYE matches"},
        {"id": "AR-PLN-001", "title": "Planning day operations & unique key"},
        {"id": "AR-RES-001", "title": "Best-of defaults by phase"},
        {"id": "AR-RES-004", "title": "Needs review propagation"},
        {"id": "AR-SCO-002", "title": "BYE rule & cancellation award-up-to"},
        {"id": "AR-CAL-001", "title": "Calendar sync day-order when enabled"},
    ]


def verify_atomic_requirements(
    ar_list: list[dict[str, str]],
    files: dict[str, FileData],
    tests: dict[str, list[str]],
    answers: dict[str, Any],
    _strict: bool,
) -> list[dict[str, str]]:
    """Evaluate ARs and return list with status/evidence/proposed_fix."""

    def has_file(path: str) -> bool:
        return path in files

    def test_exists(path: str) -> bool:
        return path in files or path in tests

    def contains(path: str, substr: str) -> bool:
        fd = files.get(path)
        return bool(fd and substr in fd.text)

    results: list[dict[str, str]] = []
    for ar in ar_list:
        ar_id = ar["id"]
        status = "UNKNOWN"
        evidence = ""
        fix = ""
        if ar_id == "AR-REG-001":
            if contains("msa/services/recalculate.py", "_sort_by_wr"):
                status = "PASS"
                evidence = "recalculate.py:_sort_by_wr"
            else:
                status = "FAIL"
                evidence = "missing _sort_by_wr"
                fix = "add sort-by-WR test"
        elif ar_id == "AR-REG-002":
            status = "FAIL"
            evidence = "no rank-bucket enforcement"
            fix = "add test msa/tests/test_registration_reorder.py"
        elif ar_id == "AR-REG-003":
            found = any("md_seeds_count" in fd.text and "power" in fd.text for fd in files.values())
            if found:
                status = "PASS"
                evidence = "power-of-two hint"
            else:
                status = "FAIL"
                evidence = "no power-of-two validation"
                fix = "add test msa/tests/test_seed_power_of_two.py"
        elif ar_id == "AR-REC-001":
            if has_file("msa/services/recalculate.py") and test_exists(
                "msa/tests/test_recalculate.py"
            ):
                status = "PASS"
                evidence = "recalculate.py & test_recalculate.py"
            else:
                status = "FAIL"
                evidence = "missing recalc module or test"
                fix = "add recalc preview test"
        elif ar_id == "AR-REC-002":
            fd = files.get("msa/services/recalculate.py")
            if fd and "brutal_reset_to_registration" in fd.text and "Snapshot" in fd.text:
                status = "PASS"
                evidence = "brutal_reset_to_registration saves Snapshot"
            else:
                status = "FAIL"
                evidence = "missing snapshot before reset"
                fix = "add test msa/tests/test_recalc_snapshot.py"
        elif ar_id == "AR-REC-003":
            req = answers.get("AR-REC-003", {}).get(
                "require_fields", ["rng_seed", "anchors", "unseeded", "matches_changed"]
            )
            missing = [f for f in req if not any(f in fd.text for fd in files.values())]
            if not missing:
                status = "PASS"
                evidence = ", ".join(req)
            else:
                status = "FAIL"
                evidence = "missing: " + ", ".join(missing)
                fix = "add test msa/tests/test_recalc_preview_fields.py"
        elif ar_id == "AR-QUAL-001":
            if contains("msa/services/qual_generator.py", "2^(R-2)") or contains(
                "msa/services/qual_generator.py", "seeds_per_bracket"
            ):
                status = "PASS"
                evidence = "qual_generator tier formula"
            else:
                status = "FAIL"
                evidence = "missing tier formula"
                fix = "add test msa/tests/test_qual_seed_tiers.py"
        elif ar_id == "AR-LL-001":
            if has_file("msa/services/ll_prefix.py") and test_exists("msa/tests/test_ll_prefix.py"):
                status = "PASS"
                evidence = "ll_prefix.py & test_ll_prefix.py"
            else:
                status = "FAIL"
                evidence = "missing LL queue code or test"
                fix = "add test msa/tests/test_ll_queue.py"
        elif ar_id == "AR-LL-002":
            if has_file("msa/services/ll_prefix.py") and test_exists("msa/tests/test_ll_prefix.py"):
                status = "PASS"
                evidence = "ll_prefix prefix enforcement"
            else:
                status = "FAIL"
                evidence = "missing LL prefix logic"
                fix = "add test msa/tests/test_ll_prefix.py"
        elif ar_id == "AR-MD-001":
            if has_file("msa/services/seed_anchors.py") and test_exists(
                "msa/tests/test_seed_anchors.py"
            ):
                status = "PASS"
                evidence = "seed_anchors.py & test_seed_anchors.py"
            else:
                status = "FAIL"
                evidence = "missing seed anchors"
                fix = "add test msa/tests/test_seed_anchors.py"
        elif ar_id == "AR-MD-004":
            if has_file("msa/services/md_embed.py") and test_exists("msa/tests/test_md_embed.py"):
                status = "PASS"
                evidence = "md_embed.py & test_md_embed.py"
            else:
                status = "FAIL"
                evidence = "missing md embed test"
                fix = "add test msa/tests/test_md_embed.py"
        elif ar_id == "AR-PLN-001":
            if has_file("msa/services/planning.py") and test_exists("msa/tests/test_planning.py"):
                status = "PASS"
                evidence = "planning.py & test_planning.py"
            else:
                status = "FAIL"
                evidence = "missing planning ops"
                fix = "add test msa/tests/test_planning.py"
        elif ar_id == "AR-RES-001":
            if has_file("msa/services/results.py") and test_exists("tests/test_best_of_policy.py"):
                status = "PASS"
                evidence = "results.py & test_best_of_policy.py"
            else:
                status = "FAIL"
                evidence = "missing best-of policy"
                fix = "add test tests/test_best_of_policy.py"
        elif ar_id == "AR-RES-004":
            if has_file("msa/services/results.py") and test_exists(
                "msa/tests/test_results_needs_review.py"
            ):
                status = "PASS"
                evidence = "results.py & test_results_needs_review.py"
            else:
                status = "FAIL"
                evidence = "missing needs review test"
                fix = "add test msa/tests/test_results_needs_review.py"
        elif ar_id == "AR-SCO-002":
            if has_file("msa/services/scoring.py") and test_exists("msa/tests/test_scoring.py"):
                status = "PASS"
                evidence = "scoring.py & test_scoring.py"
            else:
                status = "FAIL"
                evidence = "missing scoring policy"
                fix = "add test msa/tests/test_scoring_policy.py"
        elif ar_id == "AR-CAL-001":
            if any(
                "calendar_sync" in fd.text and rel.startswith("fax_calendar/")
                for rel, fd in files.items()
            ):
                status = "PASS"
                evidence = "calendar sync references"
            else:
                status = "FAIL"
                evidence = "no calendar sync code"
                fix = "add test msa/tests/test_calendar_sync.py"
        results.append(
            {
                "id": ar_id,
                "status": status,
                "evidence": evidence,
                "proposed_fix": fix,
            }
        )
    return results


def write_verification_report(
    out_md: Path,
    spec_path: Path,
    spec_version: str,
    ar_results: list[dict[str, str]],
    model_errors: list[str],
    model_warns: list[str],
    tests_present: list[str],
    tests_missing: list[str],
    rng_off: list[str],
    rng_results: dict[str, bool],
    strict: bool,
) -> None:
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    ar_pass = sum(1 for r in ar_results if r["status"] == "PASS")
    ar_total = len(ar_results)
    ar_pct = int(100 * ar_pass / ar_total) if ar_total else 100
    test_pct = (
        int(100 * len(tests_present) / (len(tests_present) + len(tests_missing)))
        if (tests_present or tests_missing)
        else 100
    )
    rng_status = "OK"
    if rng_off or any(not v for v in rng_results.values()):
        rng_status = "ERROR" if strict or any(not v for v in rng_results.values()) else "WARN"

    lines: list[str] = []
    lines.append("# Full Verification — MSA")
    lines.append(f"Generated: {ts}")
    lines.append(f"Spec: {spec_path.as_posix()} (version: {spec_version})")
    lines.append("")
    lines.append("## Scoreboard")
    lines.append(f"- ARs: {ar_pass}/{ar_total} PASS ({ar_pct}%)")
    lines.append(f"- Models: {len(model_errors)} errors / {len(model_warns)} warns")
    lines.append(
        f"- Tests: {len(tests_present)}/{len(tests_present)+len(tests_missing)} present ({test_pct}%)"
    )
    lines.append(f"- RNG hygiene: {rng_status}")
    lines.append("- Reseed policy: N/A")
    lines.append("")
    lines.append("## Results (all ARs)")
    lines.append("| AR | Status | Evidence | Proposed fix |")
    lines.append("|---|---|---|---|")
    for r in sorted(ar_results, key=lambda x: x["id"]):
        lines.append(f"| {r['id']} | {r['status']} | {r['evidence']} | {r['proposed_fix']} |")
    lines.append("")
    lines.append("## Proposed Fixes")
    fails = [r for r in ar_results if r["status"] != "PASS"]
    if fails:
        for r in fails:
            lines.append(f"- {r['id']}: {r['proposed_fix']}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Open Questions")
    lines.append("- none")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_verification_json(path: Path, timestamp: str, ar_results: list[dict[str, str]]) -> None:
    data = {"timestamp": timestamp, "ars": ar_results}
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


# ---------------------------------------------------------------------------
# Report generation


def generate_report(
    out_md: Path,
    spec_path: Path,
    spec_version: str,
    features: dict[str, dict[str, Any]],
    model_info: dict[str, Any],
    gating: dict[str, GatingInfo],
    rng_off: list[str],
    rng_results: dict[str, bool],
    tests_present: list[str],
    tests_missing: list[str],
    risky: list[tuple[str, dict[str, int]]],
    ungated: list[str],
    model_errors: list[str],
    model_warns: list[str],
    top_errors: list[str],
    top_warns: list[str],
    exit_status: str,
) -> None:
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    feat_pass = sum(1 for f in features.values() if f["pass"])
    feat_total = len(features)
    feat_pct = int(100 * feat_pass / feat_total) if feat_total else 100
    test_pct = (
        int(100 * len(tests_present) / (len(tests_present) + len(tests_missing)))
        if (tests_present or tests_missing)
        else 100
    )
    rng_status = "OK"
    if rng_off or any(not v for v in rng_results.values()):
        rng_status = "ERROR" if any(not v for v in rng_results.values()) else "WARN"

    lines: list[str] = []
    lines.append("# MSA Compliance Report")
    lines.append(f"Generated: {ts}")
    lines.append(f"Spec: {spec_path.as_posix()} (version: {spec_version})")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Features: {feat_pass}/{feat_total} PASS ({feat_pct}%)")
    lines.append(f"- Models: {len(model_errors)} errors / {len(model_warns)} warns")
    lines.append(
        f"- Tests: {len(tests_present)}/{len(tests_present)+len(tests_missing)} present ({test_pct}%)"
    )
    lines.append(f"- RNG hygiene: {rng_status}")
    lines.append(f"- Exit status: {exit_status}")
    lines.append("")
    lines.append("## Features (per spec)")
    lines.append("| Feature | Status | Evidence |")
    lines.append("|---|---|---|")
    for name in sorted(features):
        info = features[name]
        status = "PASS" if info["pass"] else "FAIL"
        lines.append(f"| {name} | {status} | {info['evidence']} |")
    lines.append("")
    lines.append("## Models & Constraints")
    for model in sorted(model_info):
        mi = model_info[model]
        lines.append(f"### {model}")
        lines.append("| Constraint | Status |")
        lines.append("|---|---|")
        for uc in mi["unique"]:
            tup = tuple(uc)
            status = "PASS" if tup not in mi["missing"] else "FAIL"
            lines.append(f"| {', '.join(uc)} | {status} |")
        if mi["extra"]:
            lines.append(f"Extra: {mi['extra']}")
        if mi.get("fields_missing"):
            lines.append(f"Missing fields: {', '.join(mi['fields_missing'])}")
    lines.append("")
    lines.append("## Admin-gating of mutators")
    lines.append("| Module | Mutators | Gated OK | Gated Missing | Examples |")
    lines.append("|---|---|---|---|---|")
    for mod in sorted(gating):
        g = gating[mod]
        examples = ", ".join(g.missing[:3])
        lines.append(f"| {mod} | {g.total} | {g.ok} | {len(g.missing)} | {examples} |")
    lines.append("")
    lines.append("## Central RNG hygiene")
    if rng_off:
        lines.append("Offenders:")
        for o in rng_off:
            lines.append(f"- {o}")
    else:
        lines.append("Offenders: none")
    lines.append("Required rng_for modules:")
    for mod in sorted(rng_results):
        lines.append(f"- {mod}: {'PASS' if rng_results[mod] else 'FAIL'}")
    lines.append("")
    lines.append("## Tests coverage")
    lines.append("Present:")
    for t in tests_present:
        lines.append(f"- {t}")
    lines.append("Missing:")
    for t in tests_missing:
        lines.append(f"- {t}")
    lines.append("")
    lines.append("## Risky patterns (informational)")
    lines.append("### select_for_update / get_or_create / update_or_create counts per file")
    for rel, c in risky:
        lines.append(
            f"- {rel}: select_for_update={c['select_for_update(']}, get_or_create={c['get_or_create(']}, "
            f"update_or_create={c['update_or_create(']}"
        )
    lines.append("### Ungated mutators")
    if ungated:
        for u in ungated:
            lines.append(f"- {u}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Top recommendations")
    recs = sorted(set(top_errors))[:5]
    if len(recs) < 5:
        recs.extend(sorted(set(top_warns))[: 5 - len(recs)])
    for r in recs:
        lines.append(f"- {r}")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# JSON output


def write_json(
    path: Path,
    timestamp: str,
    features: dict[str, dict[str, Any]],
    model_info: dict[str, Any],
    rng_off: list[str],
    rng_results: dict[str, bool],
    tests_present: list[str],
    tests_missing: list[str],
    exit_status: str,
) -> None:
    data = {
        "timestamp": timestamp,
        "features": features,
        "models": model_info,
        "rng": {"offenders": rng_off, "required": rng_results},
        "tests": {"present": tests_present, "missing": tests_missing},
        "scores": {
            "features": (
                sum(1 for f in features.values() if f["pass"]) / len(features) if features else 1.0
            ),
            "tests": (
                len(tests_present) / (len(tests_present) + len(tests_missing))
                if (tests_present or tests_missing)
                else 1.0
            ),
        },
        "exit": exit_status,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main


def main() -> int:
    parser = argparse.ArgumentParser(description="MSA compliance checker")
    parser.add_argument("--msa-dir", default="msa")
    parser.add_argument("--spec", default="docs/MSA_SPEC.yaml")
    parser.add_argument("--out", default="COMPLIANCE_MSA.md")
    parser.add_argument("--verify-out", default="VERIFICATION_FULL_MSA.md")
    parser.add_argument("--answers", default="docs/MSA_ANSWERS.yaml")
    parser.add_argument("--json-out")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--fail-on-warn", action="store_true")
    args = parser.parse_args()

    spec_path = ROOT / args.spec
    spec = load_spec(spec_path)
    files, tests = read_repo(Path(args.msa_dir))
    models = collect_models(files)

    features, feat_errors, feat_warns = feature_checks(spec, files, tests, models)
    model_info, model_errors, model_warns = check_models(spec.get("models", {}), models)
    rng_off, rng_required, rng_errs = check_rng(
        files, spec.get("services", {}).get("use_central_rng", [])
    )
    tests_present, tests_missing = check_tests(spec.get("tests_expected", []))
    risky = risky_patterns(files)
    gating = analyze_admin_gating(spec.get("services", {}).get("must_be_admin_gated", []), files)[0]

    all_errors = feat_errors + model_errors + (rng_errs)
    all_warns = feat_warns + model_warns
    if rng_off:
        all_warns.append("random module used")

    out_md = ROOT / args.out
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    exit_status = "PASS" if not all_errors else "FAIL"
    generate_report(
        out_md,
        spec_path,
        spec.get("spec_version", ""),
        features,
        model_info,
        gating,
        rng_off,
        rng_required,
        tests_present,
        tests_missing,
        risky,
        [u for mod, info in gating.items() for u in info.missing],
        model_errors,
        model_warns,
        all_errors,
        all_warns,
        exit_status,
    )
    print(f"Compliance report written to: {out_md.as_posix()}")

    answers = load_answers(ROOT / args.answers)
    ars = build_atomic_requirements()
    ar_results = verify_atomic_requirements(ars, files, tests, answers, args.strict)
    verify_md = ROOT / args.verify_out
    write_verification_report(
        verify_md,
        spec_path,
        spec.get("spec_version", ""),
        ar_results,
        model_errors,
        model_warns,
        tests_present,
        tests_missing,
        rng_off,
        rng_required,
        args.strict,
    )
    if args.json_out:
        write_verification_json(ROOT / args.json_out, ts, ar_results)
    print(f"Verification report written to: {verify_md.as_posix()}")

    ar_fail = any(r["status"] != "PASS" for r in ar_results)
    if all_errors or ar_fail or (args.fail_on_warn and all_warns):
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
