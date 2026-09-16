import json
from pathlib import Path

import jsonschema

from scripts.lib.analysis_report import build_report_model, render_analysis_report

ROOT = Path(__file__).resolve().parents[1]


def inventory():
    return {
        "repository": {"root_markers": ["package.json"], "default_branch": "main", "source_mode": "zip"},
        "project_types": ["frontend"],
        "technologies": {
            "languages": ["TypeScript"], "frameworks": ["React", "Vite"], "build_tools": ["Vite"],
            "package_managers": ["pnpm"], "container": [], "ci": ["GitHub Actions"]
        },
        "components": [{"path": ".", "role": "frontend", "build_file": "package.json"}],
        "evidence": [{"claim": "React", "path": "package.json", "signal": "react dependency"}],
        "uncertainties": [], "conflicts": [], "confidence": "high"
    }


def finding(fid="RF-README-001", classification="must-fix"):
    return {
        "id": fid, "area": "readme", "classification": classification, "title": "Fel package manager",
        "summary": "README säger npm men repositoryt använder pnpm.",
        "evidence": [{"kind": "cross-file", "path": "README.md", "observation": "npm står i README", "related_paths": ["pnpm-lock.yaml"]}],
        "confidence": "high", "recommended_action": None if classification == "passed" else "Byt dokumenterat kommando till pnpm.",
        "decision_required": False, "decision_reason": None, "verification": "Jämför README och lockfil.", "notes": []
    }


def build_test(status="not-verified"):
    item = {"component": ".", "command": "pnpm test", "source": "package.json", "kind": "node", "status": status}
    if status == "not-verified":
        item["reason"] = "Kan inte köra kommandot i aktuell miljö."
    elif status == "verified":
        item["exit_code"] = 0
    else:
        item["exit_code"] = 1
        item["summary"] = "Testfel"
    return {"build": [], "tests": [item], "runtime_mismatches": [], "findings": []}


def test_report_schema_is_valid_and_accepts_model():
    schema = json.loads((ROOT / "schemas/repository-analysis.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    model = build_report_model("demo", inventory(), [{"area": "README", "status": "checked", "note": None}], [finding()], build_test())
    store = {}
    for name in ["repository-inventory.schema.json", "repository-finding.schema.json", "build-test-verification.schema.json"]:
        child = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
        store[child["$id"]] = child
    resolver = jsonschema.RefResolver(base_uri=schema["$id"], referrer=schema, store=store)
    jsonschema.Draft202012Validator(schema, resolver=resolver).validate(model)


def test_report_contains_required_sections_and_evidence():
    model = build_report_model("demo", inventory(), [{"area": "README", "status": "checked", "note": "README analyserad"}], [finding()], build_test())
    text = render_analysis_report(model)
    for heading in ["## Sammanfattning", "## Detekterad projekttyp och teknikstack", "## Kontrollöversikt", "## Fynd", "## Godkända kontroller", "## Build- och testverifiering", "## Begränsningar och osäkerheter", "## Rekommenderat nästa steg"]:
        assert heading in text
    assert "RF-README-001" in text
    assert "pnpm-lock.yaml" in text


def test_not_verified_is_not_reported_as_failure():
    model = build_report_model("demo", inventory(), [], [], build_test("not-verified"))
    text = render_analysis_report(model)
    assert "not-verified" in text
    assert "Kan inte köra kommandot" in text
    assert "misslyck" not in text.lower()


def test_passed_checks_are_separated_from_open_findings():
    passed = finding("RF-README-002", "passed")
    passed["title"] = "README package manager verifierad"
    model = build_report_model("demo", inventory(), [], [finding(), passed], build_test("verified"))
    text = render_analysis_report(model)
    findings_part, passed_part = text.split("## Godkända kontroller", 1)
    assert "RF-README-001" in findings_part
    assert "RF-README-002" not in findings_part
    assert "RF-README-002" in passed_part


def test_zero_negative_findings_is_explicit():
    passed = finding("RF-README-001", "passed")
    model = build_report_model("demo", inventory(), [], [passed], build_test("verified"))
    text = render_analysis_report(model)
    assert "Inga öppna negativa fynd" in text


def test_inventory_uncertainties_flow_to_limitations():
    inv = inventory()
    inv["uncertainties"] = ["Framework-version kunde inte fastställas."]
    model = build_report_model("demo", inv, [], [], build_test())
    text = render_analysis_report(model)
    assert "Framework-version kunde inte fastställas." in text


def test_invalid_negative_finding_is_rejected():
    bad = finding()
    bad["evidence"] = []
    try:
        build_report_model("demo", inventory(), [], [bad], build_test())
    except ValueError as exc:
        assert "Ogiltigt fynd" in str(exc)
    else:
        raise AssertionError("invalid finding should be rejected")
