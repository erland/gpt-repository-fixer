import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from scripts.lib.github_write_workflow import (
    GitHubWriteBlocked,
    branch_name,
    conventional_commit_message,
    initialize_github_write_state,
    plan_write_target,
    record_pr_created,
    record_step_commit,
)

ROOT = Path(__file__).resolve().parents[1]


def _context(**overrides):
    data = {
        "mode": "github",
        "repository": {"owner": "acme", "name": "demo", "url": "https://github.com/acme/demo"},
        "default_branch": "main",
        "analyzed_ref": "main",
        "commit_sha": "base1",
        "writable": True,
        "repository_fixer_pull_requests": [],
        "limitations": [],
    }
    data.update(overrides)
    return data


def _open_pr(number=7, head="repository-fixer/01-step-1", base="main"):
    return {"number": number, "state": "open", "merged": False, "head_ref": head, "base_ref": base, "url": f"https://github.com/acme/demo/pull/{number}"}


def test_write_state_requires_verified_write_access():
    with pytest.raises(GitHubWriteBlocked, match="Skrivåtkomst"):
        initialize_github_write_state(_context(writable=None))
    with pytest.raises(GitHubWriteBlocked, match="Skrivåtkomst"):
        initialize_github_write_state(_context(writable=False))


def test_first_step_creates_branch_and_pr_from_default_branch():
    state = initialize_github_write_state(_context())
    action = plan_write_target(state, "step-1")
    assert action == {
        "action": "create-branch-and-pr",
        "branch": "repository-fixer/01-step-1",
        "base_branch": "main",
        "base_sha": "base1",
        "step_id": "step-1",
        "sequence": 1,
    }


def test_open_pr_is_reused_after_status_refresh():
    state = initialize_github_write_state(_context())
    pr = _open_pr()
    record_pr_created(state, branch=pr["head_ref"], pr=pr, sequence=1)
    action = plan_write_target(state, "step-2", refreshed_pr=pr)
    assert action["action"] == "reuse-open-pr"
    assert action["pr_number"] == 7
    assert action["branch"] == pr["head_ref"]


def test_merged_pr_forces_default_refresh_before_new_pr():
    state = initialize_github_write_state(_context())
    pr = _open_pr()
    record_pr_created(state, branch=pr["head_ref"], pr=pr, sequence=1)
    merged = {**pr, "state": "closed", "merged": True}
    first = plan_write_target(state, "step-2", refreshed_pr=merged)
    assert first["action"] == "refresh-default-branch"
    second = plan_write_target(state, "step-2", refreshed_pr=merged, default_branch_sha="base2")
    assert second["action"] == "create-branch-and-pr"
    assert second["base_sha"] == "base2"
    assert second["branch"] == "repository-fixer/02-step-2"
    assert state["active_pr"] is None


def test_closed_unmerged_pr_never_reuses_branch_automatically():
    state = initialize_github_write_state(_context())
    pr = _open_pr()
    record_pr_created(state, branch=pr["head_ref"], pr=pr, sequence=1)
    closed = {**pr, "state": "closed", "merged": False}
    action = plan_write_target(state, "step-2", refreshed_pr=closed)
    assert action["action"] == "review-closed-pr"
    assert action["pr_number"] == 7


def test_base_branch_mismatch_requires_review():
    state = initialize_github_write_state(_context())
    pr = _open_pr(base="release")
    # Record against a temporarily matching default, then restore main to model a changed repository default.
    state["default_branch"] = "release"
    record_pr_created(state, branch=pr["head_ref"], pr=pr, sequence=1)
    state["default_branch"] = "main"
    action = plan_write_target(state, "step-2", refreshed_pr=pr)
    assert action["action"] == "review-pr"


def test_commit_is_one_step_and_requires_open_pr():
    state = initialize_github_write_state(_context())
    with pytest.raises(GitHubWriteBlocked, match="öppen"):
        record_step_commit(state, step_id="step-1", commit_sha="c1", message="docs: update readme")
    pr = _open_pr()
    record_pr_created(state, branch=pr["head_ref"], pr=pr, sequence=1)
    record_step_commit(state, step_id="step-1", commit_sha="c1", message="docs: update readme")
    assert state["commits"][0]["step_id"] == "step-1"
    with pytest.raises(GitHubWriteBlocked, match="redan"):
        record_step_commit(state, step_id="step-1", commit_sha="c2", message="docs: second")


def test_commit_message_uses_conservative_category():
    assert conventional_commit_message({"id": "step-1", "title": "Uppdatera README", "finding_ids": ["RF-README-001"]}).startswith("docs:")
    assert conventional_commit_message({"id": "step-2", "title": "Förbättra CI", "finding_ids": ["RF-CI-001"]}).startswith("ci:")
    assert conventional_commit_message({"id": "step-3", "title": "Rensa arbetsfiler", "finding_ids": ["RF-HYGIENE-001"]}).startswith("chore:")


def test_branch_name_is_stable_and_namespaced():
    assert branch_name("STEP-16", sequence=2) == "repository-fixer/02-step-16"
    with pytest.raises(GitHubWriteBlocked):
        branch_name("../../bad")


def test_write_state_schema_validates():
    state = initialize_github_write_state(_context())
    pr = _open_pr()
    record_pr_created(state, branch=pr["head_ref"], pr=pr, sequence=1)
    record_step_commit(state, step_id="step-1", commit_sha="abc123", message="docs: update readme")
    schema = json.loads((ROOT / "schemas/repository-github-write-state.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(state)
