#!/usr/bin/env python3
"""Inventory the msa app and produce a Markdown status report."""

from __future__ import annotations

import argparse
import ast
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

VERSION = "1.0"

KEY_PATTERNS = {
    "select_for_update(": re.compile(r"select_for_update\("),
    "@transaction.atomic": re.compile(r"@transaction\.atomic"),
    "UniqueConstraint(": re.compile(r"UniqueConstraint\("),
    "get_or_create(": re.compile(r"get_or_create\("),
    "update_or_create(": re.compile(r"update_or_create\("),
    "q_best_of": re.compile(r"q_best_of"),
    "md_best_of": re.compile(r"md_best_of"),
    "rng_seed": re.compile(r"rng_seed"),
    "needs_review": re.compile(r"needs_review"),
    "LL": re.compile(r"\bLL\b"),
    "ALT": re.compile(r"\bALT\b"),
    "BYE": re.compile(r"\bBYE\b"),
}


@dataclass
class ModelInfo:
    fields: dict[str, tuple[str, bool]] = field(default_factory=dict)
    unique: list[dict[str, list[str] | None]] = field(default_factory=list)
    check: list[dict[str, str | None]] = field(default_factory=list)


@dataclass
class FileInfo:
    classes: dict[str, list[str]] = field(default_factory=dict)
    functions: dict[str, list[str]] = field(default_factory=dict)
    decorators: set[str] = field(default_factory=set)


def dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = dotted(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def parse_model(node: ast.ClassDef) -> ModelInfo:
    info = ModelInfo()
    for stmt in node.body:
        target: str | None = None
        value: ast.AST | None = None
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            if isinstance(stmt.targets[0], ast.Name):
                target = stmt.targets[0].id
                value = stmt.value
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            target = stmt.target.id
            value = stmt.value
        if target and isinstance(value, ast.Call):
            ftype = dotted(value.func).split(".")[-1]
            db_index = False
            for kw in value.keywords:
                if kw.arg == "db_index" and isinstance(kw.value, ast.Constant):
                    db_index = bool(kw.value.value)
            info.fields[target] = (ftype, db_index)
    for stmt in node.body:
        if isinstance(stmt, ast.ClassDef) and stmt.name == "Meta":
            for body in stmt.body:
                if isinstance(body, ast.Assign):
                    for tgt in body.targets:
                        if isinstance(tgt, ast.Name) and tgt.id == "constraints":
                            elts: list[ast.AST] = []
                            if isinstance(body.value, ast.List | ast.Tuple):
                                elts = list(body.value.elts)
                            for cons in elts:
                                if not isinstance(cons, ast.Call):
                                    continue
                                name = dotted(cons.func).split(".")[-1]
                                if name == "UniqueConstraint":
                                    fields: list[str] | None = None
                                    cname: str | None = None
                                    for kw in cons.keywords:
                                        if kw.arg == "fields" and isinstance(
                                            kw.value, ast.List | ast.Tuple
                                        ):
                                            fields = [
                                                el.value
                                                for el in kw.value.elts
                                                if isinstance(el, ast.Constant)
                                            ]
                                        if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                                            cname = str(kw.value.value)
                                    info.unique.append({"fields": fields, "name": cname})
                                if name == "CheckConstraint":
                                    check_expr: str | None = None
                                    cname: str | None = None
                                    for kw in cons.keywords:
                                        if kw.arg == "check":
                                            check_expr = ast.unparse(kw.value)
                                        if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                                            cname = str(kw.value.value)
                                    info.check.append({"check": check_expr, "name": cname})
    return info


def scan_msa(msa_path: Path) -> dict:
    root = msa_path.parent
    files: dict[str, FileInfo] = {}
    models: dict[str, ModelInfo] = {}
    services: dict[str, dict[str, list[str]]] = {}
    tests: dict[str, dict] = {}
    keyword_counts: dict[str, dict[str, int]] = {}
    total_py = 0
    migrations = 0
    generate_draw = False

    for path in sorted(msa_path.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        if "migrations" in path.parts and path.name != "__init__.py":
            migrations += 1
            continue
        total_py += 1
        text = path.read_text(encoding="utf-8")
        keyword_counts[rel] = {k: len(p.findall(text)) for k, p in KEY_PATTERNS.items()}
        if "generate_draw" in text:
            generate_draw = True
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            files[rel] = FileInfo(classes={"PARSE_ERROR": []})
            continue
        finfo = FileInfo()
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                bases = [dotted(b) for b in node.bases]
                finfo.classes[node.name] = bases
                if any(b == "models.Model" for b in bases):
                    models[node.name] = parse_model(node)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                decs = [dotted(d) for d in node.decorator_list]
                finfo.functions[node.name] = decs
                finfo.decorators.update(decs)
        files[rel] = finfo
        if "services" in path.parts:
            services[path.relative_to(root).as_posix()] = {
                fn: finfo.functions[fn] for fn in sorted(finfo.functions)
            }
        if "tests" in path.parts:
            tinfo = {"classes": {}, "functions": []}
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                    methods = [
                        n.name
                        for n in node.body
                        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
                        and n.name.startswith("test_")
                    ]
                    tinfo["classes"][node.name] = sorted(methods)
                elif isinstance(
                    node, ast.FunctionDef | ast.AsyncFunctionDef
                ) and node.name.startswith("test_"):
                    tinfo["functions"].append(node.name)
            tinfo["functions"].sort()
            tests[rel] = tinfo
    packages = []
    for name in [
        "services",
        "models.py",
        "admin.py",
        "tests",
        "apps.py",
        "forms.py",
        "views.py",
    ]:
        if (msa_path / name).exists():
            packages.append(name)
    metrics = {
        "total_py": total_py,
        "migrations": migrations,
        "packages": sorted(packages),
    }
    evidence = {
        "rng_seed": any(c["rng_seed"] > 0 for c in keyword_counts.values()),
        "generate_draw": generate_draw,
        "BYE": any(c["BYE"] > 0 for c in keyword_counts.values()),
        "LL": any(c["LL"] > 0 for c in keyword_counts.values()),
        "ALT": any(c["ALT"] > 0 for c in keyword_counts.values()),
        "needs_review": any(c["needs_review"] > 0 for c in keyword_counts.values()),
    }

    def _has_service(path: str) -> bool:
        return any(k.startswith(path) for k in services)

    def _has_test(mod: str) -> bool:
        return any(p.endswith(mod) for p in tests)

    def _has_test_name(substr: str) -> bool:
        return any(
            any(substr in m for m in tinfo.get("functions", []))
            or any(
                any(substr in mm for mm in methods) for methods in tinfo.get("classes", {}).values()
            )
            for tinfo in tests.values()
        )

    def _file_contains(path: str, substr: str) -> bool:
        return any(
            substr in (Path(root / p).read_text(encoding="utf-8"))
            for p in files
            if p.endswith(path)
        )

    features = {
        "det_seeding": (
            (
                _has_service("msa/services/md_generator.py")
                or _has_service("msa/services/qual_generator.py")
            )
            and (
                _has_test("msa/tests/test_md_generator.py")
                or _has_test("msa/tests/test_qual_generator.py")
                or _has_test_name("seed_positions_deterministic")
                or _has_test_name("unseeded_determinism")
            )
        ),
        "no_bye": (
            _has_service("msa/services/md_embed.py") and _has_test("msa/tests/test_md_embed.py")
        ),
        "ll_prefix": (
            _has_service("msa/services/ll_prefix.py") and _has_test("msa/tests/test_ll_prefix.py")
        ),
        "wc_qwc": (_has_service("msa/services/wc.py") and _has_test("msa/tests/test_wc_qwc.py")),
        "snapshots": (
            ("Snapshot" in models or _has_service("msa/services/archiver.py"))
            and _has_test("msa/tests/test_recalculate.py")
        ),
        "planning": (
            _has_service("msa/services/planning.py") and _has_test("msa/tests/test_planning.py")
        ),
        "recalculate": (
            _has_service("msa/services/recalculate.py")
            and _has_test("msa/tests/test_recalculate.py")
        ),
        "rankings": (
            _has_service("msa/services/standings.py") and _has_test("msa/tests/test_standings.py")
        ),
        "license_gate": (
            _has_service("msa/services/licenses.py")
            and (
                _has_test("msa/tests/test_md_confirm.py")
                or _has_test("msa/tests/test_qual_confirm.py")
            )
        ),
        "needs_review": (
            _has_service("msa/services/results.py")
            and _has_test("msa/tests/test_results_needs_review.py")
        ),
    }
    return {
        "files": files,
        "models": models,
        "services": services,
        "tests": tests,
        "keyword_counts": keyword_counts,
        "metrics": metrics,
        "evidence": evidence,
        "features": features,
    }


def write_markdown(out: Path, msa_path: Path, data: dict | None) -> None:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    lines: list[str] = ["# STATUS: MSA Inventory"]
    lines.append(f"Generated: {now} UTC")
    lines.append(f"Script version: {VERSION}")
    if not data:
        lines.append("")
        lines.append(f"msa not found at {msa_path}")
        out.write_text("\n".join(lines))
        return
    metrics = data["metrics"]
    lines.append(f"Total Python files (excluding migrations): {metrics['total_py']}")
    lines.append(f"Migrations count: {metrics['migrations']}")
    lines.append(f"Packages: {', '.join(metrics['packages']) if metrics['packages'] else 'none'}")
    lines.append("")
    files = data["files"]
    lines.append("## Files Overview")
    lines.append("| path | classes | functions | key decorators found |")
    lines.append("| --- | --- | --- | --- |")
    for path in sorted(files):
        finfo: FileInfo = files[path]
        cls = ", ".join(sorted(finfo.classes))
        funcs = ", ".join(sorted(finfo.functions))
        decs = ", ".join(sorted(finfo.decorators))
        lines.append(f"| {path} | {cls} | {funcs} | {decs} |")
    lines.append("")
    lines.append("## Models")
    models = data["models"]
    if not models:
        lines.append("None")
    else:
        for name in sorted(models):
            minfo = models[name]
            lines.append(f"### {name}")
            if minfo.fields:
                lines.append("- fields:")
                for field in sorted(minfo.fields):
                    ftype, dbi = minfo.fields[field]
                    extra = ", db_index=True" if dbi else ""
                    lines.append(f"  - {field}: {ftype}{extra}")
            if minfo.unique or minfo.check:
                lines.append("- constraints:")
                for u in minfo.unique:
                    lines.append(f"  - UniqueConstraint(fields={u['fields']}, name={u['name']})")
                for c in minfo.check:
                    lines.append(f"  - CheckConstraint(check={c['check']}, name={c['name']})")
            lines.append("")
    lines.append("## Services (public API)")
    services = data["services"]
    if not services:
        lines.append("None")
    else:
        for spath in sorted(services):
            lines.append(f"- {spath}")
            for fn, decs in sorted(services[spath].items()):
                dstr = f" ({', '.join(decs)})" if decs else ""
                lines.append(f"  - {fn}{dstr}")
    lines.append("")
    lines.append("## Tests discovered")
    tests = data["tests"]
    if not tests:
        lines.append("None")
    else:
        for tpath in sorted(tests):
            tinfo = tests[tpath]
            lines.append(f"- {tpath}")
            for cls, methods in sorted(tinfo["classes"].items()):
                lines.append(f"  - {cls}")
                for m in methods:
                    lines.append(f"    - {m}")
            for fn in tinfo["functions"]:
                lines.append(f"  - {fn}")
    lines.append("")
    lines.append("## Keyword scan (per file)")
    header = "| path | " + " | ".join(KEY_PATTERNS) + " |"
    lines.append(header)
    lines.append("| --- | " + " | ".join(["---"] * len(KEY_PATTERNS)) + " |")
    for path in sorted(data["keyword_counts"]):
        counts = data["keyword_counts"][path]
        row = [str(counts[k]) for k in KEY_PATTERNS]
        lines.append(f"| {path} | " + " | ".join(row) + " |")
    lines.append("")
    lines.append('## Gaps vs "MSA 1.0 – kompletní specifikace"')
    checks = [
        (
            "Deterministic seeding (rng_seed + generate_draw)",
            data["features"]["det_seeding"],
        ),
        (
            "No-BYE templates (embed non-power-of-two)",
            data["features"]["no_bye"],
        ),
        (
            "LL queue + prefix invariant, ALT flow",
            data["features"]["ll_prefix"],
        ),
        (
            "WC/QWC capacity validation",
            data["features"]["wc_qwc"],
        ),
        (
            "Snapshots (Confirm/Generate/Regenerate/Reopen/Manual) + audit",
            data["features"]["snapshots"],
        ),
        (
            "Planning day (swap/insert) with locks + preview",
            data["features"]["planning"],
        ),
        (
            "Recalculate with diff preview",
            data["features"]["recalculate"],
        ),
        (
            "Rankings (61-week rolling, Monday activation/expiry, Season/RtF, best-N penalty, adjustments)",
            data["features"]["rankings"],
        ),
        (
            "License gate (season license required)",
            data["features"]["license_gate"],
        ),
        (
            "needs_review propagation on results",
            data["features"]["needs_review"],
        ),
    ]
    for text, ok in checks:
        mark = "x" if ok else " "
        lines.append(f"- [{mark}] {text}")
    out.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--msa-dir", default="msa")
    parser.add_argument("--out", default="STATUS_MSA.md")
    args = parser.parse_args()
    msa_path = Path(args.msa_dir)
    out_path = Path(args.out)
    if not msa_path.exists():
        write_markdown(out_path, msa_path, None)
        return
    data = scan_msa(msa_path)
    write_markdown(out_path, msa_path, data)


if __name__ == "__main__":
    main()
