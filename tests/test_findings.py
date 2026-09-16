import json
from pathlib import Path

import jsonschema

from scripts.lib.finding_model import CLASS_LABELS, validate_semantics

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "repository-finding.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)


def finding(**overrides):
    value = {
        "id": "RF-README-001",
        "area": "readme",
        "classification": "must-fix",
        "title": "Dokumenterat kommando saknas",
        "summary": "README refererar till ett script som inte finns.",
        "evidence": [{
            "kind": "cross-file",
            "path": "README.md",
            "observation": "README anger npm run dev men package.json saknar dev-script.",
            "related_paths": ["package.json"]
        }],
        "confidence": "high",
        "recommended_action": "Uppdatera README till det faktiska startkommandot.",
        "decision_required": False,
        "decision_reason": None,
        "verification": "Kontrollera kommandot mot package.json och kör det om miljön tillåter.",
        "notes": []
    }
    value.update(overrides)
    return value


def test_finding_schema_is_valid_json_schema():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)


def test_negative_finding_with_concrete_evidence_is_valid():
    item = finding()
    VALIDATOR.validate(item)
    assert validate_semantics(item) == []


def test_must_fix_requires_evidence():
    item = finding(evidence=[])
    errors = list(VALIDATOR.iter_errors(item))
    assert errors
    assert "concrete evidence" in validate_semantics(item)[0]


def test_recommended_requires_evidence_too():
    item = finding(classification="recommended", evidence=[])
    assert list(VALIDATOR.iter_errors(item))


def test_passed_check_has_no_repair_action():
    item = finding(
        id="RF-CI-001",
        area="github-actions",
        classification="passed",
        title="Build och tester körs i CI",
        summary="Workflow bygger projektet och kör tester.",
        evidence=[{
            "kind": "file",
            "path": ".github/workflows/ci.yml",
            "observation": "Workflow innehåller build- och teststeg."
        }],
        recommended_action=None,
        confidence="high",
    )
    VALIDATOR.validate(item)
    assert validate_semantics(item) == []


def test_passed_check_must_not_smuggle_in_action():
    item = finding(classification="passed", recommended_action="Refaktorera ändå")
    assert list(VALIDATOR.iter_errors(item))
    assert validate_semantics(item)


def test_user_decision_requires_reason():
    item = finding(decision_required=True, decision_reason=None)
    assert list(VALIDATOR.iter_errors(item))
    assert validate_semantics(item)


def test_file_like_evidence_requires_path_semantically():
    item = finding(evidence=[{"kind": "file", "observation": "Något observerades."}])
    VALIDATOR.validate(item)
    assert "file evidence requires a path" in validate_semantics(item)


def test_labels_match_canonical_report_vocabulary():
    assert CLASS_LABELS == {
        "must-fix": "Bör åtgärdas",
        "recommended": "Rekommenderas",
        "consider": "Överväg",
        "passed": "Godkänd kontroll",
    }
