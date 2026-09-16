import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from scripts.lib.step_control import (
    apply_user_action,
    initialize_progress,
    record_execution_result,
    render_progress,
    select_next_action,
    step_preview,
)

ROOT = Path(__file__).resolve().parents[1]


def sample_plan():
    return {
        "repository_name": "demo",
        "source_finding_ids": ["RF-BUILD-001", "RF-LICENSE-001", "RF-CI-001", "RF-DOC-001"],
        "steps": [
            {
                "id": "STEP-01", "title": "Build", "goal": "Fix build", "why": "Needed",
                "finding_ids": ["RF-BUILD-001"], "likely_files": ["pom.xml"],
                "planned_changes": ["Fix build"], "decisions": [], "verification": ["Run build"],
                "risk": "medium", "dependencies": [], "status": "planned",
            },
            {
                "id": "STEP-02", "title": "License", "goal": "Fix license", "why": "Consistency",
                "finding_ids": ["RF-LICENSE-001"], "likely_files": ["LICENSE"],
                "planned_changes": ["Create license"],
                "decisions": [{"finding_id": "RF-LICENSE-001", "question": "Vilken licens ska användas?"}],
                "verification": ["Check license"], "risk": "medium", "dependencies": [], "status": "planned",
            },
            {
                "id": "STEP-03", "title": "CI", "goal": "Fix CI", "why": "Automation",
                "finding_ids": ["RF-CI-001"], "likely_files": [".github/workflows/ci.yml"],
                "planned_changes": ["Fix CI"], "decisions": [], "verification": ["Validate CI"],
                "risk": "medium", "dependencies": ["STEP-01"], "status": "planned",
            },
            {
                "id": "STEP-04", "title": "Docs", "goal": "Fix docs", "why": "Usability",
                "finding_ids": ["RF-DOC-001"], "likely_files": ["docs/run.md"],
                "planned_changes": ["Fix docs"], "decisions": [], "verification": ["Check docs"],
                "risk": "low", "dependencies": [], "status": "planned",
            },
        ],
        "notes": [],
    }


def test_initial_progress_is_schema_valid_and_decision_is_blocked():
    plan = sample_plan()
    progress = initialize_progress(plan)
    schema = json.loads((ROOT / "schemas/repository-progress.schema.json").read_text())
    Draft202012Validator(schema).validate(progress)
    assert progress["steps"][0]["status"] == "planned"
    assert progress["steps"][1]["status"] == "blocked"
    assert progress["steps"][2]["status"] == "blocked"
    assert progress["history"][0]["action"] == "initialized"


def test_next_action_uses_first_executable_step():
    plan = sample_plan()
    progress = initialize_progress(plan)
    assert select_next_action(plan, progress)["step_id"] == "STEP-01"


def test_blocked_earlier_step_does_not_hide_independent_step():
    plan = sample_plan()
    progress = initialize_progress(plan)
    apply_user_action(plan, progress, "skip", "STEP-01", note="Build fix deferred")
    # STEP-02 needs a decision, STEP-03 depends on skipped STEP-01, but STEP-04 is independent.
    nxt = select_next_action(plan, progress)
    assert nxt["action"] == "execute"
    assert nxt["step_id"] == "STEP-04"


def test_do_sets_in_progress_and_must_be_resumed_first():
    plan = sample_plan()
    progress = initialize_progress(plan)
    apply_user_action(plan, progress, "do", "STEP-01")
    assert progress["steps"][0]["status"] == "in-progress"
    assert select_next_action(plan, progress)["action"] == "resume-execution"


def test_details_does_not_change_step_status():
    plan = sample_plan()
    progress = initialize_progress(plan)
    before = progress["steps"][0]["status"]
    apply_user_action(plan, progress, "details", "STEP-01")
    assert progress["steps"][0]["status"] == before
    assert progress["history"][-1]["action"] == "details"


def test_modify_records_override_and_can_clear_execution_blocker():
    plan = sample_plan()
    progress = initialize_progress(plan)
    apply_user_action(plan, progress, "do", "STEP-01")
    record_execution_result(plan, progress, "STEP-01", success=False, verification_status="failing", note="Tests failed")
    assert progress["steps"][0]["status"] == "blocked"
    apply_user_action(plan, progress, "modify", "STEP-01", note="Begränsa ändringen till testkonfigurationen")
    assert progress["steps"][0]["status"] == "planned"
    assert progress["steps"][0]["overrides"] == ["Begränsa ändringen till testkonfigurationen"]


def test_skip_is_persisted_with_reason():
    plan = sample_plan()
    progress = initialize_progress(plan)
    apply_user_action(plan, progress, "skip", "STEP-01", note="Accepterad risk")
    state = progress["steps"][0]
    assert state["status"] == "skipped"
    assert state["skip_reason"] == "Accepterad risk"
    assert state["verification_status"] == "not-verified"


def test_unresolved_decision_prevents_do_until_resolved():
    plan = sample_plan()
    progress = initialize_progress(plan)
    with pytest.raises(ValueError, match="blockerat"):
        apply_user_action(plan, progress, "do", "STEP-02")
    apply_user_action(plan, progress, "decide", "STEP-02", finding_id="RF-LICENSE-001", answer="MIT, Example AB, 2026")
    preview = step_preview(plan, progress, "STEP-02")
    assert preview["status"] == "planned"
    assert "do" in preview["available_actions"]


def test_completed_dependency_unlocks_dependent_step():
    plan = sample_plan()
    progress = initialize_progress(plan)
    apply_user_action(plan, progress, "do", "STEP-01")
    record_execution_result(plan, progress, "STEP-01", success=True, verification_status="verified")
    preview = step_preview(plan, progress, "STEP-03")
    assert preview["status"] == "planned"
    assert not preview["blockers"]


def test_failed_verification_is_prioritized_before_later_independent_work():
    plan = sample_plan()
    progress = initialize_progress(plan)
    apply_user_action(plan, progress, "do", "STEP-01")
    record_execution_result(plan, progress, "STEP-01", success=False, verification_status="failing", note="Build failed")
    nxt = select_next_action(plan, progress)
    assert nxt["action"] == "correct-step"
    assert nxt["step_id"] == "STEP-01"




def test_failing_verification_can_never_complete_step():
    plan = sample_plan()
    progress = initialize_progress(plan)
    apply_user_action(plan, progress, "do", "STEP-01")
    record_execution_result(plan, progress, "STEP-01", success=True, verification_status="failing", note="Tests failed after change")
    assert progress["steps"][0]["status"] == "blocked"
    assert progress["steps"][0]["verification_status"] == "failing"

def test_all_terminal_steps_return_complete():
    plan = sample_plan()
    progress = initialize_progress(plan)
    for step in list(progress["steps"]):
        if step["id"] == "STEP-02":
            apply_user_action(plan, progress, "skip", step["id"], note="Not chosen")
        elif step["id"] == "STEP-03":
            # Dependency is deliberately skipped; skip this dependent step too.
            apply_user_action(plan, progress, "skip", step["id"], note="Dependency skipped")
        else:
            apply_user_action(plan, progress, "skip", step["id"], note="Deferred")
    assert select_next_action(plan, progress)["action"] == "complete"


def test_render_progress_contains_skips_blockers_and_next_action():
    plan = sample_plan()
    progress = initialize_progress(plan)
    apply_user_action(plan, progress, "skip", "STEP-01", note="Deferred")
    text = render_progress(plan, progress)
    assert "STEP-01" in text and "skipped" in text and "Deferred" in text
    assert "dependency" in text
    assert "STEP-04" in text
