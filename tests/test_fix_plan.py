import json
from pathlib import Path

import jsonschema

from scripts.lib.fix_plan import build_fix_plan_model, render_fix_plan

ROOT = Path(__file__).resolve().parents[1]


def finding(fid, area, classification="must-fix", *, decision=False, path="README.md", action=None):
    return {
        "id": fid,
        "area": area,
        "classification": classification,
        "title": f"Fynd {fid}",
        "summary": "Verifierat problem.",
        "evidence": [{"kind": "file", "path": path, "observation": "Verifierad observation."}],
        "confidence": "high",
        "recommended_action": action or f"Åtgärda {fid}.",
        "decision_required": decision,
        "decision_reason": "Bekräfta detta beslut." if decision else None,
        "verification": f"Verifiera {fid}.",
        "notes": [],
    }


def test_plan_schema_accepts_generated_model():
    schema = json.loads((ROOT / "schemas/repository-fix-plan.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    model = build_fix_plan_model("demo", [finding("RF-README-001", "readme")])
    jsonschema.Draft202012Validator(schema).validate(model)


def test_passed_findings_are_not_planned():
    passed = finding("RF-README-002", "readme", "passed")
    passed["recommended_action"] = None
    model = build_fix_plan_model("demo", [finding("RF-README-001", "readme"), passed])
    assert model["source_finding_ids"] == ["RF-README-001"]
    assert all("RF-README-002" not in step["finding_ids"] for step in model["steps"])


def test_must_fix_steps_come_before_recommendations():
    findings = [
        finding("RF-DOC-001", "documentation", "recommended"),
        finding("RF-CI-001", "github-actions", "must-fix", path=".github/workflows/ci.yml"),
    ]
    model = build_fix_plan_model("demo", findings)
    assert model["steps"][0]["finding_ids"] == ["RF-CI-001"]


def test_related_documentation_findings_are_grouped():
    findings = [
        finding("RF-README-001", "readme"),
        finding("RF-DOC-001", "documentation", path="docs/runbook.md"),
    ]
    model = build_fix_plan_model("demo", findings)
    assert len(model["steps"]) == 1
    assert model["steps"][0]["finding_ids"] == ["RF-DOC-001", "RF-README-001"]
    assert set(model["steps"][0]["likely_files"]) == {"README.md", "docs/runbook.md"}


def test_large_groups_are_split_into_prompt_sized_steps():
    findings = [finding(f"RF-DOC-{i:03d}", "documentation", path=f"docs/{i}.md") for i in range(1, 7)]
    model = build_fix_plan_model("demo", findings)
    assert len(model["steps"]) == 2
    assert len(model["steps"][0]["finding_ids"]) == 4
    assert len(model["steps"][1]["finding_ids"]) == 2


def test_decision_required_is_explicit_and_risk_not_low():
    model = build_fix_plan_model("demo", [finding("RF-LICENSE-001", "license", decision=True, path="LICENSE")])
    step = model["steps"][0]
    assert step["decisions"] == [{"finding_id": "RF-LICENSE-001", "question": "Bekräfta detta beslut."}]
    assert step["risk"] == "medium"


def test_github_actions_depends_on_build_test_when_present():
    findings = [
        finding("RF-BUILD-001", "build", path="pom.xml"),
        finding("RF-CI-001", "github-actions", path=".github/workflows/ci.yml"),
    ]
    model = build_fix_plan_model("demo", findings)
    build_step = next(s for s in model["steps"] if "RF-BUILD-001" in s["finding_ids"])
    ci_step = next(s for s in model["steps"] if "RF-CI-001" in s["finding_ids"])
    assert ci_step["dependencies"] == [build_step["id"]]


def test_render_contains_all_required_step_fields():
    model = build_fix_plan_model("demo", [finding("RF-HYGIENE-001", "repository-hygiene", decision=True, path="notes-old.md")])
    text = render_fix_plan(model)
    for token in ["## Sammanfattning", "## Planeringsprinciper", "## Steg", "STEP-01", "**Status:**", "**Risk:**", "**Beroenden:**", "**Mål:**", "**Varför:**", "**Fynd som åtgärdas:**", "**Sannolikt berörda filer**", "**Planerade ändringar**", "**Användarbeslut**", "**Verifiering efter steget**"]:
        assert token in text
    assert "RF-HYGIENE-001" in text


def test_empty_findings_produce_no_fake_work():
    model = build_fix_plan_model("demo", [])
    text = render_fix_plan(model)
    assert model["steps"] == []
    assert "Inga åtgärdssteg behövs" in text
