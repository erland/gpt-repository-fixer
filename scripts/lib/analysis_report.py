from __future__ import annotations

from collections import Counter
from pathlib import Path

from .finding_model import CLASS_LABELS, validate_semantics

ORDER = {"must-fix": 0, "recommended": 1, "consider": 2, "passed": 3}
AREA_LABELS = {
    "inventory": "Repository-inventering",
    "readme": "README",
    "documentation": "Markdown-dokumentation",
    "license": "LICENSE",
    "repository-hygiene": "Repository hygiene",
    "build": "Build",
    "tests": "Tester",
    "github-actions": "GitHub Actions",
    "versions": "Versioner",
    "other": "Övrigt",
}


def _list(values: list[str], fallback: str = "Inget identifierat") -> str:
    return ", ".join(values) if values else fallback


def _evidence_text(item: dict) -> str:
    where = ""
    if item.get("path"):
        where = f" `{item['path']}`"
        if item.get("line_start"):
            where += f" rad {item['line_start']}"
            if item.get("line_end") and item["line_end"] != item["line_start"]:
                where += f"–{item['line_end']}"
    related = item.get("related_paths") or []
    suffix = f" Relaterat: {', '.join(f'`{p}`' for p in related)}." if related else ""
    return f"- **{item.get('kind', 'evidens')}**{where}: {item['observation']}{suffix}"


def _finding_block(finding: dict) -> str:
    lines = [
        f"### {finding['id']} – {finding['title']}",
        "",
        f"**Klass:** {CLASS_LABELS[finding['classification']]}  ",
        f"**Område:** {AREA_LABELS.get(finding['area'], finding['area'])}  ",
        f"**Confidence:** {finding['confidence']}",
        "",
        finding["summary"],
    ]
    if finding.get("evidence"):
        lines += ["", "**Evidens**", ""] + [_evidence_text(e) for e in finding["evidence"]]
    if finding.get("recommended_action"):
        lines += ["", f"**Rekommenderad åtgärd:** {finding['recommended_action']}"]
    if finding.get("decision_required"):
        lines += ["", f"**Användarbeslut krävs:** {finding.get('decision_reason') or 'Ja'}"]
    if finding.get("verification"):
        lines += ["", f"**Verifiering:** {finding['verification']}"]
    if finding.get("notes"):
        lines += ["", "**Noteringar**", ""] + [f"- {n}" for n in finding["notes"]]
    return "\n".join(lines)


def _build_test_section(build_test: dict) -> str:
    rows = []
    for kind, label in (("build", "Build"), ("tests", "Test")):
        for item in build_test.get(kind, []):
            component = item.get("component") or "."
            status = item.get("status", "not-verified")
            detail = item.get("summary") or item.get("reason") or ("exit-kod 0" if status == "verified" else "")
            rows.append(f"| {label} | `{component}` | `{item['command']}` | {status} | {detail} |")
    if not rows:
        return "Ingen standardiserad build/test-verifiering kunde härledas."
    return "\n".join([
        "| Typ | Komponent | Kommando | Status | Kommentar |",
        "|---|---|---|---|---|",
        *rows,
    ])


def build_report_model(repository_name: str, inventory: dict, checked_areas: list[dict], findings: list[dict],
                       build_test: dict, limitations: list[str] | None = None,
                       recommended_next_step: str = "Skapa `repository-fix-plan.md` utifrån fynden och låt användaren granska planen innan några ändringar görs.") -> dict:
    for finding in findings:
        errors = validate_semantics(finding)
        if errors:
            raise ValueError(f"Ogiltigt fynd {finding.get('id')}: {', '.join(errors)}")
    return {
        "repository_name": repository_name,
        "inventory": inventory,
        "checked_areas": checked_areas,
        "findings": findings,
        "build_test": build_test,
        "limitations": limitations or [],
        "recommended_next_step": recommended_next_step,
    }


def render_analysis_report(model: dict, template_text: str | None = None) -> str:
    findings = sorted(model["findings"], key=lambda f: (ORDER.get(f["classification"], 9), f["area"], f["id"]))
    counts = Counter(f["classification"] for f in findings)
    negative = [f for f in findings if f["classification"] != "passed"]
    passed = [f for f in findings if f["classification"] == "passed"]

    summary = (
        f"Analysen innehåller **{len(findings)} fynd/kontroller**: "
        f"**{counts['must-fix']} Bör åtgärdas**, **{counts['recommended']} Rekommenderas**, "
        f"**{counts['consider']} Överväg** och **{counts['passed']} Godkänd kontroll**."
    )
    if not negative:
        summary += " Inga öppna negativa fynd identifierades i de kontrollerade områdena."

    inv = model["inventory"]
    tech = inv["technologies"]
    stack = "\n".join([
        f"- **Projekttyp:** {_list(inv.get('project_types', []))}",
        f"- **Språk:** {_list(tech.get('languages', []))}",
        f"- **Ramverk:** {_list(tech.get('frameworks', []))}",
        f"- **Buildverktyg:** {_list(tech.get('build_tools', []))}",
        f"- **Package managers:** {_list(tech.get('package_managers', []))}",
        f"- **Container:** {_list(tech.get('container', []))}",
        f"- **CI:** {_list(tech.get('ci', []))}",
        f"- **Inventerings-confidence:** {inv.get('confidence', 'okänd')}",
    ])

    controls = ["| Område | Status | Kommentar |", "|---|---|---|"]
    for item in model["checked_areas"]:
        controls.append(f"| {item['area']} | {item['status']} | {item.get('note') or ''} |")

    findings_text = "\n\n".join(_finding_block(f) for f in negative) if negative else "Inga öppna fynd i de kontrollerade områdena."
    passed_text = "\n\n".join(_finding_block(f) for f in passed) if passed else "Inga kontroller är markerade som uttryckligen godkända."

    limitations = list(model.get("limitations") or [])
    limitations.extend(inv.get("uncertainties") or [])
    limitations.extend(inv.get("conflicts") or [])
    seen = set()
    limitations = [x for x in limitations if not (x in seen or seen.add(x))]
    limitations_text = "\n".join(f"- {x}" for x in limitations) if limitations else "- Inga särskilda begränsningar registrerades."

    template = template_text or Path(__file__).resolve().parents[2].joinpath("templates/repository-analysis.md.tpl").read_text(encoding="utf-8")
    replacements = {
        "REPOSITORY_NAME": model["repository_name"],
        "SUMMARY": summary,
        "STACK": stack,
        "CONTROL_OVERVIEW": "\n".join(controls),
        "FINDINGS": findings_text,
        "PASSED_CHECKS": passed_text,
        "BUILD_TEST": _build_test_section(model["build_test"]),
        "LIMITATIONS": limitations_text,
        "NEXT_STEP": model["recommended_next_step"],
    }
    for key, value in replacements.items():
        template = template.replace("{{" + key + "}}", value)
    return template.rstrip() + "\n"
