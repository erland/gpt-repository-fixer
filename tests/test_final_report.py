import json
from copy import deepcopy
from pathlib import Path

import jsonschema
import pytest

from scripts.lib.final_report import build_final_report_model, render_final_report

ROOT = Path(__file__).resolve().parents[1]


def inv():
    return {
        "repository": {"root_markers": ["package.json"], "default_branch": "main", "source_mode": "zip"},
        "project_types": ["frontend"],
        "technologies": {"languages": ["TypeScript"], "frameworks": ["React"], "build_tools": ["Vite"], "package_managers": ["pnpm"], "container": [], "ci": ["GitHub Actions"]},
        "components": [{"path": ".", "role": "frontend", "build_file": "package.json"}],
        "evidence": [{"claim": "React", "path": "package.json", "signal": "react dependency"}],
        "uncertainties": [], "conflicts": [], "confidence": "high"
    }


def finding(fid, area="readme", classification="must-fix", title="Problem"):
    return {
        "id": fid, "area": area, "classification": classification, "title": title, "summary": "Problem beskrivet.",
        "evidence": [{"kind": "file", "path": "README.md", "observation": "Observerad avvikelse."}],
        "confidence": "high", "recommended_action": None if classification == "passed" else "Åtgärda.",
        "decision_required": False, "decision_reason": None, "verification": "Kontrollera på nytt.", "notes": []
    }


def build_test(status="verified"):
    item = {"component": ".", "command": "pnpm test", "source": "package.json", "kind": "node", "status": status}
    if status == "verified": item["exit_code"] = 0
    if status == "failing": item.update({"exit_code": 1, "summary": "Testfel"})
    if status == "not-verified": item["reason"] = "Runtime saknas"
    return {"build": [], "tests": [item], "runtime_mismatches": [], "findings": []}


def analysis(findings, status="verified"):
    return {
        "repository_name": "demo", "inventory": inv(),
        "checked_areas": [
            {"area": "readme", "status": "checked", "note": None},
            {"area": "documentation", "status": "checked", "note": None},
            {"area": "license", "status": "checked", "note": None},
            {"area": "github-actions", "status": "checked", "note": None},
            {"area": "repository-hygiene", "status": "checked", "note": None},
        ],
        "findings": findings, "build_test": build_test(status), "limitations": [], "recommended_next_step": "x"
    }


def progress(skipped_ids=None):
    skipped_ids = skipped_ids or []
    return {"steps": [{"id": "STEP-1", "status": "skipped", "finding_ids": skipped_ids}]}


def test_schema_accepts_final_model_offline():
    initial = analysis([finding("RF-README-001")])
    fresh = analysis([])
    model = build_final_report_model("demo", initial, fresh)
    schema = json.loads((ROOT / "schemas/repository-final-report.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    store = {}
    for name in ["repository-finding.schema.json", "build-test-verification.schema.json"]:
        child = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
        store[child["$id"]] = child
    resolver = jsonschema.RefResolver(base_uri=schema["$id"], referrer=schema, store=store)
    jsonschema.Draft202012Validator(schema, resolver=resolver).validate(model)


def test_resolved_remaining_and_new_are_based_on_fresh_analysis():
    old1 = finding("RF-README-001", title="Fel kommando")
    old2 = finding("RF-LICENSE-001", area="license", title="Licenskonflikt")
    current2 = deepcopy(old2)
    new = finding("RF-CI-009", area="github-actions", title="CI saknar test")
    model = build_final_report_model("demo", analysis([old1, old2]), analysis([current2, new]))
    assert [x["initial"]["id"] for x in model["resolved"]] == ["RF-README-001"]
    assert [x["initial"]["id"] for x in model["remaining"]] == ["RF-LICENSE-001"]
    assert [x["id"] for x in model["new_findings"]] == ["RF-CI-009"]


def test_completed_progress_does_not_override_fresh_remaining_finding():
    old = finding("RF-README-001")
    model = build_final_report_model("demo", analysis([old]), analysis([deepcopy(old)]), {"steps": [{"id": "S1", "status": "completed", "finding_ids": ["RF-README-001"]}]})
    assert len(model["remaining"]) == 1
    assert len(model["resolved"]) == 0


def test_skipped_history_reports_current_observation_separately():
    old = finding("RF-LICENSE-001", area="license")
    model = build_final_report_model("demo", analysis([old]), analysis([deepcopy(old)]), progress([old["id"]]))
    assert model["skipped"][0]["current_state"] == "remaining"
    assert len(model["remaining"]) == 1


def test_fingerprint_can_match_changed_id_conservatively():
    old = finding("RF-README-001", title="Fel kommando")
    fresh = deepcopy(old); fresh["id"] = "RF-README-099"
    model = build_final_report_model("demo", analysis([old]), analysis([fresh]))
    assert len(model["remaining"]) == 1
    assert model["remaining"][0]["current"]["id"] == "RF-README-099"
    assert model["new_findings"] == []


def test_area_status_requires_actual_check_for_pass():
    model = build_final_report_model("demo", analysis([]), analysis([]))
    statuses = {x["area"]: x["status"] for x in model["area_status"]}
    assert statuses["readme"] == "pass"
    fresh = analysis([]); fresh["checked_areas"] = []
    model2 = build_final_report_model("demo", analysis([]), fresh)
    assert {x["area"]: x["status"] for x in model2["area_status"]}["readme"] == "not-checked"


def test_failing_build_test_is_preserved_in_final_report():
    model = build_final_report_model("demo", analysis([]), analysis([], "failing"))
    text = render_final_report(model)
    assert "failing" in text
    assert "Testfel" in text


def test_render_contains_required_final_sections():
    old = finding("RF-README-001")
    model = build_final_report_model("demo", analysis([old]), analysis([]), progress([old["id"]]))
    text = render_final_report(model)
    for heading in ["## Sammanfattning", "## Lösta ursprungliga fynd", "## Hoppade eller avvisade fynd", "## Kvarstående ursprungliga fynd", "## Nya fynd efter ändringarna", "## Build- och teststatus", "## Status per kontrollområde", "## Kvarstående begränsningar och rekommendationer"]:
        assert heading in text
    assert "ny full analys" in text


def test_same_analysis_object_is_rejected_as_not_fresh():
    current = analysis([])
    with pytest.raises(ValueError, match="separate re-analysis"):
        build_final_report_model("demo", current, current)
