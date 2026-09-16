from __future__ import annotations

import fnmatch
import json
import re
import tomllib
from pathlib import PurePosixPath
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

STATUSES = {"verified", "failing", "not-verified"}
CHECK_ORDER = ["diff-review", "syntax-config", "build", "tests", "docs-consistency", "deleted-references"]


def _norm(path: str) -> str:
    value = path.replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    while "//" in value:
        value = value.replace("//", "/")
    return value


def _matches_expected(path: str, expected: list[str]) -> bool:
    path = _norm(path)
    if path.startswith(".repository-fixer/"):
        return True
    for pattern in expected:
        pattern = _norm(pattern)
        if not pattern:
            continue
        if fnmatch.fnmatch(path, pattern):
            return True
        if pattern.endswith("/") and path.startswith(pattern):
            return True
    return False


def required_checks(step: dict[str, Any], changed_paths: list[str], deleted_paths: list[str] | None = None) -> list[str]:
    """Derive the minimum relevant verification set from actual changes and plan intent."""
    deleted_paths = deleted_paths or []
    paths = [_norm(p) for p in changed_paths + deleted_paths]
    text = " ".join(
        [str(step.get("title", "")), str(step.get("goal", "")), str(step.get("verification", ""))]
        + [str(x) for x in step.get("planned_changes", [])]
        + [str(x) for x in step.get("finding_ids", [])]
    ).lower()

    required = ["diff-review"]
    config_suffixes = {".json", ".yaml", ".yml", ".toml"}
    config_names = {"dockerfile", "pom.xml", "build.gradle", "build.gradle.kts", "package.json"}
    if any(PurePosixPath(p).suffix.lower() in config_suffixes or PurePosixPath(p).name.lower() in config_names or p.startswith(".github/workflows/") for p in paths):
        required.append("syntax-config")

    code_suffixes = {".java", ".kt", ".kts", ".js", ".jsx", ".ts", ".tsx", ".py", ".go", ".rs"}
    build_names = {"pom.xml", "build.gradle", "build.gradle.kts", "package.json", "pyproject.toml", "go.mod", "cargo.toml"}
    if any(PurePosixPath(p).suffix.lower() in code_suffixes or PurePosixPath(p).name.lower() in build_names for p in paths) or "build" in text:
        required.append("build")
    if any(PurePosixPath(p).suffix.lower() in code_suffixes for p in paths) or "test" in text:
        required.append("tests")
    if any(PurePosixPath(p).suffix.lower() == ".md" for p in paths) or any(fid.startswith(("RF-README-", "RF-DOCS-")) for fid in step.get("finding_ids", [])):
        required.append("docs-consistency")
    if deleted_paths:
        required.append("deleted-references")
    return [name for name in CHECK_ORDER if name in required]


def diff_scope_check(step: dict[str, Any], changed_paths: list[str], deleted_paths: list[str] | None = None) -> dict[str, Any]:
    deleted_paths = deleted_paths or []
    actual = sorted({_norm(p) for p in changed_paths + deleted_paths if _norm(p)})
    if not actual:
        return {"name": "diff-review", "status": "failing", "summary": "Steget registrerar inga faktiska filändringar."}
    expected = [str(p) for p in step.get("likely_files", [])]
    if not expected:
        return {"name": "diff-review", "status": "not-verified", "summary": "Plansteget saknar filscope; faktisk diff måste granskas manuellt.", "paths": actual}
    unexpected = [p for p in actual if not _matches_expected(p, expected)]
    if unexpected:
        return {
            "name": "diff-review",
            "status": "not-verified",
            "summary": "Diffen innehåller filer utanför planens angivna sannolika scope och kräver explicit granskning.",
            "paths": unexpected,
        }
    return {"name": "diff-review", "status": "verified", "summary": "Faktiska ändringar ligger inom planstegets angivna filscope.", "paths": actual}


def syntax_config_check(files_after: dict[str, str], changed_paths: list[str]) -> dict[str, Any]:
    checked: list[str] = []
    errors: list[str] = []
    for raw in changed_paths:
        path = _norm(raw)
        if path not in files_after:
            continue
        name = PurePosixPath(path).name.lower()
        suffix = PurePosixPath(path).suffix.lower()
        text = files_after[path]
        try:
            if suffix == ".json":
                json.loads(text)
            elif suffix == ".toml":
                tomllib.loads(text)
            elif suffix in {".yaml", ".yml"}:
                if yaml is None:
                    continue
                yaml.safe_load(text)
            else:
                continue
            checked.append(path)
        except Exception as exc:
            checked.append(path)
            errors.append(f"{path}: {exc}")
    if errors:
        return {"name": "syntax-config", "status": "failing", "summary": "Minst en ändrad konfigurationsfil kunde inte parsas.", "details": errors, "paths": checked}
    if checked:
        return {"name": "syntax-config", "status": "verified", "summary": "Ändrade JSON/YAML/TOML-filer kunde parsas.", "paths": checked}
    return {"name": "syntax-config", "status": "not-verified", "summary": "Ingen deterministiskt parsbar ändrad konfigurationsfil hittades."}


def deleted_reference_check(files_after: dict[str, str], deleted_paths: list[str]) -> dict[str, Any]:
    deleted = [_norm(p) for p in deleted_paths]
    if not deleted:
        return {"name": "deleted-references", "status": "verified", "summary": "Inga filer togs bort i steget."}
    refs: list[dict[str, str]] = []
    for deleted_path in deleted:
        # Prefer exact repository-relative references; basename-only matching is too noisy.
        escaped = re.escape(deleted_path)
        pattern = re.compile(rf"(?<![A-Za-z0-9_.-]){escaped}(?![A-Za-z0-9_.-])")
        for path, content in files_after.items():
            if _norm(path) in deleted:
                continue
            if pattern.search(content):
                refs.append({"deleted_path": deleted_path, "referenced_from": _norm(path)})
    if refs:
        return {"name": "deleted-references", "status": "failing", "summary": "Borttagna filer refereras fortfarande från repositoryt.", "references": refs}
    return {"name": "deleted-references", "status": "verified", "summary": "Inga exakta kvarvarande referenser till borttagna paths hittades."}


def normalize_check(name: str, result: dict[str, Any] | None) -> dict[str, Any]:
    if result is None:
        return {"name": name, "status": "not-verified", "summary": "Kontrollen har inte körts i aktuell miljö."}
    status = result.get("status")
    if status not in STATUSES:
        raise ValueError(f"Ogiltig verifieringsstatus för {name}: {status}")
    out = dict(result)
    out["name"] = name
    out.setdefault("summary", "Verifieringsresultat registrerat.")
    return out


def assess_step_verification(
    step: dict[str, Any],
    *,
    changed_paths: list[str],
    deleted_paths: list[str] | None = None,
    files_after: dict[str, str] | None = None,
    results: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Aggregate relevant per-step verification without turning unavailable checks into failures."""
    deleted_paths = deleted_paths or []
    files_after = files_after or {}
    results = dict(results or {})
    results.setdefault("diff-review", diff_scope_check(step, changed_paths, deleted_paths))
    needed = required_checks(step, changed_paths, deleted_paths)
    if "syntax-config" in needed and "syntax-config" not in results:
        results["syntax-config"] = syntax_config_check(files_after, changed_paths)
    if "deleted-references" in needed and "deleted-references" not in results:
        results["deleted-references"] = deleted_reference_check(files_after, deleted_paths)

    checks = [normalize_check(name, results.get(name)) for name in needed]
    # A performed optional check that fails is still a regression signal and must block.
    for name, result in results.items():
        if name not in needed:
            normalized = normalize_check(name, result)
            if normalized["status"] == "failing":
                checks.append(normalized)

    if any(c["status"] == "failing" for c in checks):
        overall = "failing"
    elif any(c["status"] == "not-verified" for c in checks):
        overall = "not-verified"
    else:
        overall = "verified"

    return {
        "step_id": step["id"],
        "status": overall,
        "required_checks": needed,
        "checks": checks,
        "changed_paths": sorted({_norm(p) for p in changed_paths}),
        "deleted_paths": sorted({_norm(p) for p in deleted_paths}),
        "correction_required": overall == "failing",
    }


def verification_note(report: dict[str, Any]) -> str:
    status = report["status"]
    failing = [c["name"] for c in report.get("checks", []) if c.get("status") == "failing"]
    unverified = [c["name"] for c in report.get("checks", []) if c.get("status") == "not-verified"]
    if status == "failing":
        return "Verifiering misslyckades: " + ", ".join(failing) + ". Korrigera verifieringsfelet före nästa ordinarie plansteg."
    if status == "not-verified":
        return "Steget genomfördes utan känd regressionssignal, men följande relevanta kontroller kunde inte verifieras: " + ", ".join(unverified) + "."
    return "Alla relevanta kontroller för steget verifierades utan kända regressionssignaler."


def record_verification_result(plan: dict[str, Any], progress: dict[str, Any], report: dict[str, Any], *, execution_success: bool = True) -> dict[str, Any]:
    """Persist an assessed report into step-control semantics.

    `failing` can never complete a step. `not-verified` may complete only when the
    change itself succeeded and the unavailable checks are explicitly recorded.
    """
    from scripts.lib.step_control import record_execution_result

    return record_execution_result(
        plan,
        progress,
        report["step_id"],
        success=execution_success and report["status"] != "failing",
        verification_status=report["status"],
        note=verification_note(report),
    )
