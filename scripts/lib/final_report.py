from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from .finding_model import CLASS_LABELS, validate_semantics

NEGATIVE = {"must-fix", "recommended", "consider"}
AREA_KEYS = ["readme", "documentation", "license", "github-actions", "repository-hygiene"]
AREA_LABELS = {
    "readme": "README",
    "documentation": "Dokumentationskonsistens",
    "license": "LICENSE",
    "github-actions": "GitHub Actions",
    "repository-hygiene": "Repository hygiene",
}


def _negative(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [f for f in findings if f.get("classification") in NEGATIVE]


def _fingerprint(finding: dict[str, Any]) -> tuple[Any, ...]:
    paths = sorted({e.get("path") for e in finding.get("evidence", []) if e.get("path")})
    return (finding.get("area"), finding.get("title", "").strip().lower(), tuple(paths))


def _match_findings(initial: list[dict[str, Any]], fresh: list[dict[str, Any]]) -> tuple[dict[str, dict], set[str]]:
    """Match fresh findings to initial findings, preferring stable IDs then conservative fingerprints."""
    fresh_by_id = {f.get("id"): f for f in fresh if f.get("id")}
    fresh_by_fp: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for f in fresh:
        fresh_by_fp.setdefault(_fingerprint(f), []).append(f)

    matches: dict[str, dict] = {}
    consumed: set[str] = set()
    for old in initial:
        old_id = old.get("id")
        if old_id in fresh_by_id:
            matches[old_id] = fresh_by_id[old_id]
            consumed.add(fresh_by_id[old_id].get("id"))
            continue
        candidates = [f for f in fresh_by_fp.get(_fingerprint(old), []) if f.get("id") not in consumed]
        if len(candidates) == 1:
            matches[old_id] = candidates[0]
            consumed.add(candidates[0].get("id"))
    return matches, consumed


def _skipped_finding_ids(progress: dict[str, Any] | None) -> set[str]:
    if not progress:
        return set()
    result: set[str] = set()
    for step in progress.get("steps", []):
        if step.get("status") == "skipped":
            result.update(step.get("finding_ids") or [])
    return result


def _area_status(fresh_analysis: dict[str, Any], area: str) -> dict[str, Any]:
    negative_ids = [
        f["id"] for f in fresh_analysis.get("findings", [])
        if f.get("area") == area and f.get("classification") in NEGATIVE
    ]
    controls = [c for c in fresh_analysis.get("checked_areas", []) if str(c.get("area", "")).strip().lower() in {area, AREA_LABELS.get(area, "").lower()}]
    if negative_ids:
        status = "issues"
    elif any(c.get("status") == "partial" for c in controls):
        status = "partial"
    elif any(c.get("status") == "checked" for c in controls) or any(
        f.get("area") == area and f.get("classification") == "passed" for f in fresh_analysis.get("findings", [])
    ):
        status = "pass"
    else:
        status = "not-checked"
    return {"area": area, "status": status, "finding_ids": negative_ids}


def build_final_report_model(
    repository_name: str,
    initial_analysis: dict[str, Any],
    fresh_analysis: dict[str, Any],
    progress: dict[str, Any] | None = None,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    """Build a final report from a fresh re-analysis, never from progress alone."""
    if initial_analysis is fresh_analysis:
        raise ValueError("fresh_analysis must be a separate re-analysis result")
    for source_name, analysis in (("initial", initial_analysis), ("fresh", fresh_analysis)):
        if not analysis.get("inventory") or "findings" not in analysis or "build_test" not in analysis:
            raise ValueError(f"{source_name} analysis is incomplete")
        for finding in analysis.get("findings", []):
            errors = validate_semantics(finding)
            if errors:
                raise ValueError(f"Ogiltigt {source_name} fynd {finding.get('id')}: {', '.join(errors)}")

    initial_open = _negative(initial_analysis.get("findings", []))
    fresh_open = _negative(fresh_analysis.get("findings", []))
    matches, consumed_fresh_ids = _match_findings(initial_open, fresh_open)
    skipped_ids = _skipped_finding_ids(progress)

    resolved = []
    remaining = []
    skipped = []
    for old in initial_open:
        old_id = old["id"]
        current = matches.get(old_id)
        record = {"initial": deepcopy(old), "current": deepcopy(current) if current else None}
        if old_id in skipped_ids:
            record["current_state"] = "remaining" if current else "not-observed"
            skipped.append(record)
        if current:
            remaining.append(record)
        else:
            resolved.append(record)

    new_findings = [deepcopy(f) for f in fresh_open if f.get("id") not in consumed_fresh_ids]
    initial_counts = Counter(f.get("classification") for f in initial_analysis.get("findings", []))
    fresh_counts = Counter(f.get("classification") for f in fresh_analysis.get("findings", []))

    merged_limitations = list(limitations or [])
    merged_limitations.extend(fresh_analysis.get("limitations") or [])
    merged_limitations.extend(fresh_analysis.get("inventory", {}).get("uncertainties") or [])
    seen: set[str] = set()
    merged_limitations = [x for x in merged_limitations if x and not (x in seen or seen.add(x))]

    return {
        "repository_name": repository_name,
        "fresh_reanalysis": True,
        "initial_summary": {
            "total": len(initial_analysis.get("findings", [])),
            "must_fix": initial_counts["must-fix"],
            "recommended": initial_counts["recommended"],
            "consider": initial_counts["consider"],
            "passed": initial_counts["passed"],
        },
        "final_summary": {
            "total": len(fresh_analysis.get("findings", [])),
            "must_fix": fresh_counts["must-fix"],
            "recommended": fresh_counts["recommended"],
            "consider": fresh_counts["consider"],
            "passed": fresh_counts["passed"],
        },
        "resolved": resolved,
        "skipped": skipped,
        "remaining": remaining,
        "new_findings": new_findings,
        "build_test": deepcopy(fresh_analysis.get("build_test", {})),
        "area_status": [_area_status(fresh_analysis, area) for area in AREA_KEYS],
        "limitations": merged_limitations,
        "fresh_checked_areas": deepcopy(fresh_analysis.get("checked_areas", [])),
    }


def _finding_line(finding: dict[str, Any]) -> str:
    return f"- **{finding['id']} – {finding['title']}** ({CLASS_LABELS.get(finding['classification'], finding['classification'])})"


def _records(records: list[dict[str, Any]], include_state: bool = False) -> str:
    if not records:
        return "- Inga."
    lines = []
    for record in records:
        line = _finding_line(record["initial"])
        current = record.get("current")
        if current and current.get("id") != record["initial"].get("id"):
            line += f" → återfunnet som `{current['id']}`"
        if include_state:
            line += f" — slutstatus: `{record.get('current_state', 'okänd')}`"
        lines.append(line)
    return "\n".join(lines)


def _new_findings(findings: list[dict[str, Any]]) -> str:
    return "\n".join(_finding_line(f) for f in findings) if findings else "- Inga."


def _build_test_rows(build_test: dict[str, Any]) -> str:
    rows = ["| Typ | Komponent | Kommando | Status | Kommentar |", "|---|---|---|---|---|"]
    found = False
    for kind, label in (("build", "Build"), ("tests", "Test")):
        for item in build_test.get(kind, []):
            found = True
            detail = item.get("summary") or item.get("reason") or ("exit-kod 0" if item.get("status") == "verified" else "")
            rows.append(f"| {label} | `{item.get('component') or '.'}` | `{item['command']}` | {item.get('status', 'not-verified')} | {detail} |")
    return "\n".join(rows) if found else "Ingen standardiserad build/test-verifiering kunde härledas vid slutanalysen."


def _area_rows(items: list[dict[str, Any]]) -> str:
    rows = ["| Område | Slutstatus | Kvarstående fynd |", "|---|---|---|"]
    for item in items:
        ids = ", ".join(f"`{x}`" for x in item.get("finding_ids", [])) or "–"
        rows.append(f"| {AREA_LABELS.get(item['area'], item['area'])} | {item['status']} | {ids} |")
    return "\n".join(rows)


def render_final_report(model: dict[str, Any], template_text: str | None = None) -> str:
    initial = model["initial_summary"]
    final = model["final_summary"]
    summary = (
        f"Den ursprungliga analysen innehöll **{initial['must_fix']} Bör åtgärdas**, "
        f"**{initial['recommended']} Rekommenderas** och **{initial['consider']} Överväg**. "
        f"Den nya fulla analysen innehåller **{final['must_fix']} Bör åtgärdas**, "
        f"**{final['recommended']} Rekommenderas** och **{final['consider']} Överväg**. "
        f"**{len(model['resolved'])}** ursprungliga fynd observeras inte längre, "
        f"**{len(model['remaining'])}** kvarstår och **{len(model['new_findings'])}** nya fynd har identifierats."
    )
    limitations = "\n".join(f"- {x}" for x in model.get("limitations", [])) or "- Inga särskilda kvarstående begränsningar registrerades."
    template = template_text or Path(__file__).resolve().parents[2].joinpath("templates/repository-final-report.md.tpl").read_text(encoding="utf-8")
    replacements = {
        "REPOSITORY_NAME": model["repository_name"],
        "SUMMARY": summary,
        "RESOLVED": _records(model["resolved"]),
        "SKIPPED": _records(model["skipped"], include_state=True),
        "REMAINING": _records(model["remaining"]),
        "NEW_FINDINGS": _new_findings(model["new_findings"]),
        "BUILD_TEST": _build_test_rows(model["build_test"]),
        "AREA_STATUS": _area_rows(model["area_status"]),
        "LIMITATIONS": limitations,
    }
    for key, value in replacements.items():
        template = template.replace("{{" + key + "}}", value)
    return template.rstrip() + "\n"
