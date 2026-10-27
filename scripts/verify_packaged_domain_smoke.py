"""Run real Repository Fixer domain functions from the packaged Skill archives.

Tests the *packaged bytes*, not the checkout. This is a portable preflight, not
a substitute for runtime-host execution or the full project test suite.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


def load_from_archive(archive: Path, skill: str, basename: str, workspace: Path):
    prefix = f"skills/{skill}/scripts/"
    with zipfile.ZipFile(archive) as zf:
        candidates = [name for name in zf.namelist() if name.startswith(prefix)
                      and PurePosixPath(name).name == basename]
        if len(candidates) != 1:
            raise AssertionError(f"{archive.name}: expected one {skill}/{basename}, got {candidates}")
        source = zf.read(candidates[0])
    destination = workspace / f"{skill}-{basename}"
    destination.write_bytes(source)
    spec = importlib.util.spec_from_file_location(f"packaged_{skill}_{basename[:-3]}", destination)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def check_archive(archive: Path):
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        inventory = load_from_archive(archive, "repository-analysis", "repository_inventory.py", workspace)
        finding = load_from_archive(archive, "repository-analysis", "finding_model.py", workspace)
        result = inventory.detect_from_paths(["pom.xml", ".github/workflows/ci.yml"])
        assert "Java" in result["technologies"]["languages"], result
        assert "Maven" in result["technologies"]["build_tools"], result
        assert not finding.validate_semantics({"classification": "must-fix", "evidence": [
            {"kind": "file", "path": "pom.xml"}]})
        assert "negative findings require concrete evidence" in finding.validate_semantics(
            {"classification": "must-fix", "evidence": []})
        step_control = load_from_archive(
            archive, "repository-remediation", "step_control.py", workspace)
        verification = load_from_archive(
            archive, "repository-verification", "step_verification.py", workspace)
        plan = {"repository_name": "smoke-repo", "source_finding_ids": ["F-1"],
                "steps": [{"id": "step-1", "decisions": [], "dependencies": [],
                           "likely_files": ["README.md"]}]}
        progress = step_control.initialize_progress(plan)
        assert progress["steps"][0]["id"] == "step-1"
        assert progress["steps"][0]["status"] == "planned"
        scoped = verification.diff_scope_check(plan["steps"][0], ["README.md"])
        assert scoped["status"] == "verified", scoped
        unscoped = verification.diff_scope_check(plan["steps"][0], ["pom.xml"])
        assert unscoped["status"] == "not-verified", unscoped
        # End-to-end state transition from approved step through verified completion.
        step_control.apply_user_action(plan, progress, "do", "step-1")
        assert progress["steps"][0]["status"] == "in-progress"
        checked = verification.assess_step_verification(
            plan["steps"][0],
            changed_paths=["README.md"],
            results={"docs-consistency": {
                "status": "verified",
                "summary": "README references checked against changed content",
            }},
        )
        assert checked["status"] == "verified", checked
        step_control.record_execution_result(
            plan, progress, "step-1", success=True,
            verification_status=checked["status"],
        )
        assert progress["steps"][0]["status"] == "completed", progress
        assert progress["steps"][0]["verification_status"] == "verified"

        # GitHub is an optional host capability. Denied or unknown write access
        # must not create a branch/PR state, while verified access may proceed.
        github_write = load_from_archive(
            archive, "repository-remediation", "github_write_workflow.py", workspace)
        source = {
            "mode": "github",
            "repository": {"owner": "example", "name": "demo"},
            "default_branch": "main",
            "commit_sha": "a" * 40,
        }
        for access in (False, None):
            denied = dict(source, writable=access)
            try:
                github_write.initialize_github_write_state(denied)
            except github_write.GitHubWriteBlocked as exc:
                assert "Skrivåtkomst måste vara verifierad" in str(exc)
            else:
                raise AssertionError(
                    f"{archive.name}: GitHub write state accepted unverified access {access!r}")
        authorized = github_write.initialize_github_write_state(
            dict(source, writable=True))
        target = github_write.plan_write_target(authorized, "step-1")
        assert target["action"] == "create-branch-and-pr", target
        assert target["base_branch"] == "main"
        assert target["branch"] != "main"

        # Persist and restore an unfinished step using actual packaged logic.
        pending = step_control.initialize_progress(plan)
        step_control.apply_user_action(plan, pending, "do", "step-1")
        state_file = workspace / "project-status.json"
        state_file.write_text(json.dumps(pending, ensure_ascii=False), encoding="utf-8")
        restored = json.loads(state_file.read_text(encoding="utf-8"))
        action = step_control.select_next_action(plan, restored)
        assert action["action"] == "resume-execution", action
        assert action["step_id"] == "step-1", action
        assert restored["steps"][0]["status"] == "in-progress"
        resumed_check = verification.assess_step_verification(
            plan["steps"][0],
            changed_paths=["README.md"],
            results={"docs-consistency": {
                "status": "verified", "summary": "Verified after restoring saved state",
            }},
        )
        step_control.record_execution_result(
            plan, restored, "step-1", success=True,
            verification_status=resumed_check["status"],
        )
        assert restored["steps"][0]["status"] == "completed"
        state_file.write_text(json.dumps(restored, ensure_ascii=False), encoding="utf-8")
        reloaded = json.loads(state_file.read_text(encoding="utf-8"))
        assert reloaded["steps"][0]["verification_status"] == "verified"
        assert reloaded["steps"][0]["status"] == "completed"

        # Regression gate: an observed verification failure may never complete.
        blocked = step_control.initialize_progress(plan)
        step_control.apply_user_action(plan, blocked, "do", "step-1")
        failed = verification.assess_step_verification(
            plan["steps"][0],
            changed_paths=["README.md"],
            results={"docs-consistency": {
                "status": "failing", "summary": "Broken reference in README",
            }},
        )
        assert failed["status"] == "failing", failed
        step_control.record_execution_result(
            plan, blocked, "step-1", success=True,
            verification_status=failed["status"],
        )
        assert blocked["steps"][0]["status"] == "blocked", blocked
        assert blocked["steps"][0]["verification_status"] == "failing"

        # An unavailable required check must remain not-verified, never verified.
        # It is permitted to complete the file change, but the uncertainty must
        # survive in persistent progress and must not masquerade as a pass.
        uncertain = step_control.initialize_progress(plan)
        step_control.apply_user_action(plan, uncertain, "do", "step-1")
        unverified = verification.assess_step_verification(
            plan["steps"][0],
            changed_paths=["README.md"],
            results={"docs-consistency": {
                "status": "not-verified",
                "summary": "Documentation checker unavailable in this host",
            }},
        )
        assert unverified["status"] == "not-verified", unverified
        assert unverified["correction_required"] is False
        assert any(c["name"] == "docs-consistency" and c["status"] == "not-verified"
                   for c in unverified["checks"]), unverified
        step_control.record_execution_result(
            plan, uncertain, "step-1", success=True,
            verification_status=unverified["status"],
        )
        assert uncertain["steps"][0]["status"] == "completed", uncertain
        assert uncertain["steps"][0]["verification_status"] == "not-verified"
        assert step_control.select_next_action(plan, uncertain)["action"] == "complete"

        # A failing optional check is still a regression, even if all required
        # checks passed; a blocked step must be corrected before ordinary work.
        optional_failure = step_control.initialize_progress(plan)
        step_control.apply_user_action(plan, optional_failure, "do", "step-1")
        assessed = verification.assess_step_verification(
            plan["steps"][0],
            changed_paths=["README.md"],
            results={
                "docs-consistency": {"status": "verified"},
                "extra-regression-check": {
                    "status": "failing", "summary": "Unexpected regression",
                },
            },
        )
        assert assessed["status"] == "failing", assessed
        step_control.record_execution_result(
            plan, optional_failure, "step-1", success=True,
            verification_status=assessed["status"],
        )
        assert optional_failure["steps"][0]["status"] == "blocked"
        assert step_control.select_next_action(plan, optional_failure)["action"] == "correct-step"
    return {"archive": archive.name, "result": "PASS", "functions": [
        "repository_inventory.detect_from_paths", "finding_model.validate_semantics",
        "step_control.initialize_progress", "step_verification.diff_scope_check",
        "step_control.apply_user_action", "step_verification.assess_step_verification",
        "step_control.record_execution_result", "step_control.select_next_action",
        "github_write_workflow.initialize_github_write_state",
        "github_write_workflow.plan_write_target"]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, required=True)
    args = p.parse_args()
    root = args.project_root
    cfg = json.loads((root / "MIGRATION-BUILD-REPORT.json").read_text())
    by_target = {item["target"]: item for item in cfg.get("distributions", [])}
    results = []
    for target in ("plugin", "claude_skills"):
        assert target in by_target
        archive = root / "dist" / by_target[target]["archive"]
        results.append(check_archive(archive))
    cfg["packaged_domain_smoke"] = results
    (root / "MIGRATION-BUILD-REPORT.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
