import json
from pathlib import Path

import jsonschema

from scripts.lib.finding_model import validate_semantics
from scripts.lib.hygiene_analysis import analyze_repository_hygiene

ROOT = Path(__file__).resolve().parents[1]
FINDING_SCHEMA = json.loads((ROOT / "schemas" / "repository-finding.schema.json").read_text())


def validate(findings):
    for finding in findings:
        jsonschema.Draft202012Validator(FINDING_SCHEMA).validate(finding)
        assert validate_semantics(finding) == []


def test_ds_store_is_high_confidence_recommendation_and_gitignore_gap():
    findings = analyze_repository_hygiene({"README.md": "# Demo", ".DS_Store": "binary-ish"})
    validate(findings)
    artifact = next(f for f in findings if f["title"] == "Sannolikt genererad eller lokal artefakt")
    assert artifact["classification"] == "recommended"
    assert artifact["decision_required"] is False
    assert any(f["title"].startswith(".gitignore") for f in findings)


def test_ignored_artifact_is_still_reported_but_notes_snapshot_ambiguity():
    findings = analyze_repository_hygiene({".gitignore": ".DS_Store\n", ".DS_Store": "x"})
    validate(findings)
    artifact = next(f for f in findings if f["title"] == "Sannolikt genererad eller lokal artefakt")
    assert artifact["notes"]
    assert not any(f["title"].startswith(".gitignore") for f in findings)


def test_cache_and_logs_are_recommended_not_user_decisions():
    findings = analyze_repository_hygiene({
        ".gitignore": "__pycache__/\n*.log\n",
        "src/__pycache__/module.pyc": "x",
        "app.log": "log",
    })
    validate(findings)
    artifacts = [f for f in findings if f["title"] == "Sannolikt genererad eller lokal artefakt"]
    assert len(artifacts) == 2
    assert all(f["classification"] == "recommended" for f in artifacts)
    assert all(f["decision_required"] is False for f in artifacts)


def test_old_backup_zip_and_patch_require_user_decision():
    findings = analyze_repository_hygiene({
        "README-old.md": "old",
        "backup.zip": "archive",
        "changes.patch": "diff",
    })
    validate(findings)
    ambiguous = [f for f in findings if f["classification"] == "consider"]
    assert len(ambiguous) == 3
    assert all(f["decision_required"] is True for f in ambiguous)
    assert all(f["confidence"] == "medium" for f in ambiguous)


def test_reference_to_ambiguous_file_is_preserved_as_warning_note():
    findings = analyze_repository_hygiene({
        "docs/design-old.md": "historical design",
        "README.md": "See docs/design-old.md for migration history.",
    })
    validate(findings)
    f = next(f for f in findings if f["classification"] == "consider")
    assert any("refereras" in note for note in f["notes"])


def test_multiple_lockfiles_same_root_require_decision():
    findings = analyze_repository_hygiene({
        "package.json": '{"packageManager":"pnpm@10"}',
        "pnpm-lock.yaml": "lockfileVersion: '9.0'",
        "package-lock.json": "{}",
    })
    validate(findings)
    f = next(f for f in findings if "lockfiler" in f["title"])
    assert f["classification"] == "recommended"
    assert f["decision_required"] is True
    assert f["confidence"] == "high"


def test_lockfiles_in_different_monorepo_packages_do_not_conflict():
    findings = analyze_repository_hygiene({
        "apps/a/package-lock.json": "{}",
        "apps/b/pnpm-lock.yaml": "lockfileVersion: '9.0'",
        ".gitignore": "node_modules/\n",
    })
    validate(findings)
    assert not any("lockfiler" in f["title"] for f in findings)


def test_repository_fixer_state_is_not_treated_as_junk():
    findings = analyze_repository_hygiene({
        ".repository-fixer/analysis.md": "analysis",
        ".repository-fixer/plan.md": "plan",
        "README.md": "# Demo",
    })
    validate(findings)
    assert [f["classification"] for f in findings] == ["passed"]


def test_clean_repository_gets_passed_check():
    findings = analyze_repository_hygiene({
        ".gitignore": "node_modules/\ntarget/\n",
        "README.md": "# Demo",
        "src/main.py": "print('ok')",
    })
    validate(findings)
    assert len(findings) == 1
    assert findings[0]["classification"] == "passed"
    assert findings[0]["recommended_action"] is None
