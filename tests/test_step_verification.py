import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from scripts.lib.step_verification import (
    assess_step_verification,
    deleted_reference_check,
    diff_scope_check,
    required_checks,
    syntax_config_check,
    verification_note,
    record_verification_result,
)

ROOT = Path(__file__).resolve().parents[1]


def _step(**overrides):
    step = {
        "id": "STEP-01",
        "title": "Uppdatera README",
        "goal": "Synkronisera dokumentationen",
        "finding_ids": ["RF-README-001"],
        "likely_files": ["README.md"],
        "planned_changes": ["Korrigera dokumenterat startkommando."],
        "verification": "Kontrollera README mot package.json.",
    }
    step.update(overrides)
    return step


def test_required_checks_are_change_sensitive():
    assert required_checks(_step(), ["README.md"]) == ["diff-review", "docs-consistency"]
    code = _step(title="Ändra implementation", finding_ids=["RF-BUILD-001"], likely_files=["src/app.ts"])
    checks = required_checks(code, ["src/app.ts"])
    assert checks == ["diff-review", "build", "tests"]
    checks = required_checks(_step(), ["README.md"], ["docs/old.md"])
    assert "deleted-references" in checks


def test_diff_scope_verified_inside_planned_files():
    result = diff_scope_check(_step(), ["README.md"])
    assert result["status"] == "verified"


def test_diff_scope_outside_plan_requires_review_not_false_failure():
    result = diff_scope_check(_step(), ["README.md", "docs/usage.md"])
    assert result["status"] == "not-verified"
    assert result["paths"] == ["docs/usage.md"]


def test_empty_diff_is_failing():
    assert diff_scope_check(_step(), [])["status"] == "failing"


def test_syntax_check_detects_invalid_json_and_valid_yaml():
    bad = syntax_config_check({"package.json": "{"}, ["package.json"])
    assert bad["status"] == "failing"
    good = syntax_config_check({".github/workflows/ci.yml": "name: CI\non: push\n"}, [".github/workflows/ci.yml"])
    assert good["status"] == "verified"


def test_deleted_reference_check_detects_remaining_exact_path():
    files = {"README.md": "See docs/old.md for details.", "docs/new.md": "new"}
    result = deleted_reference_check(files, ["docs/old.md"])
    assert result["status"] == "failing"
    assert result["references"][0]["referenced_from"] == "README.md"


def test_assessment_failing_blocks_even_if_other_checks_pass():
    step = _step()
    report = assess_step_verification(
        step,
        changed_paths=["README.md"],
        files_after={"README.md": "ok"},
        results={"docs-consistency": {"status": "failing", "summary": "README beskriver fortfarande npm i stället för pnpm."}},
    )
    assert report["status"] == "failing"
    assert report["correction_required"] is True
    assert "Korrigera" in verification_note(report)


def test_assessment_not_verified_is_not_failure():
    report = assess_step_verification(_step(), changed_paths=["README.md"], files_after={"README.md": "ok"})
    assert report["status"] == "not-verified"
    assert report["correction_required"] is False
    assert any(c["name"] == "docs-consistency" and c["status"] == "not-verified" for c in report["checks"])


def test_all_required_checks_verified():
    report = assess_step_verification(
        _step(),
        changed_paths=["README.md"],
        files_after={"README.md": "ok"},
        results={"docs-consistency": {"status": "verified", "summary": "README matchar verifierbara källor."}},
    )
    assert report["status"] == "verified"
    assert report["correction_required"] is False


def test_optional_failing_check_is_still_regression_signal():
    report = assess_step_verification(
        _step(),
        changed_paths=["README.md"],
        files_after={"README.md": "ok"},
        results={
            "docs-consistency": {"status": "verified", "summary": "ok"},
            "tests": {"status": "failing", "summary": "Existing test suite fails after change."},
        },
    )
    assert report["status"] == "failing"


def test_schema_validates_report():
    report = assess_step_verification(
        _step(),
        changed_paths=["README.md"],
        files_after={"README.md": "ok"},
        results={"docs-consistency": {"status": "verified", "summary": "ok"}},
    )
    schema = json.loads((ROOT / "schemas/repository-step-verification.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(report)


def test_record_verification_result_blocks_and_prioritizes_failed_step():
    from scripts.lib.step_control import apply_user_action, initialize_progress, select_next_action
    plan = {
        "repository_name": "demo",
        "source_finding_ids": ["RF-README-001"],
        "steps": [{**_step(), "why": "Consistency", "decisions": [], "risk": "low", "dependencies": [], "status": "planned"}],
        "notes": [],
    }
    progress = initialize_progress(plan)
    apply_user_action(plan, progress, "do", "STEP-01")
    report = assess_step_verification(
        plan["steps"][0],
        changed_paths=["README.md"],
        files_after={"README.md": "still wrong"},
        results={"docs-consistency": {"status": "failing", "summary": "Mismatch remains."}},
    )
    record_verification_result(plan, progress, report)
    assert progress["steps"][0]["status"] == "blocked"
    assert select_next_action(plan, progress)["action"] == "correct-step"
