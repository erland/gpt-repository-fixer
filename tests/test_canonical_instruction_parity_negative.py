"""Reject canonical instruction body drift even when all headings remain present."""
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "instruction_parity", ROOT / "scripts/verify_canonical_instruction_sections.py")
parity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parity)

TARGETS = {
    "chat": "assistant/instructions.md",
    "plugin": "skills/repository-analysis/SKILL.md",
    "claude_project": "project/instructions.md",
    "claude_skills": "skills/repository-analysis/SKILL.md",
    "opencode": "AGENTS.md",
}
CORE = ("# Canonical instructions\n\n## Safety\n"
        "Always require verified evidence before changing code.\n\n"
        "## State\nKeep state in a persisted workspace file.\n")


def make_fixture(root: Path):
    (root / "canonical").mkdir()
    (root / "canonical/core.md").write_text(CORE, encoding="utf-8")
    (root / "gpt-project.yaml").write_text(yaml.safe_dump({
        "instructions": {"core": "canonical/core.md"},
        "skills": {"definitions": [{"id": "repository-analysis"}]},
    }), encoding="utf-8")
    (root / "dist").mkdir()
    for target, filename in TARGETS.items():
        with zipfile.ZipFile(root / "dist" / f"{target}.zip", "w") as archive:
            archive.writestr(filename, CORE)
    (root / "MIGRATION-BUILD-REPORT.json").write_text(json.dumps({
        "distributions": [
            {"target": target, "archive": f"{target}.zip"} for target in TARGETS
        ],
    }), encoding="utf-8")


def replace_entry(archive_path: Path, filename: str, content: str):
    with zipfile.ZipFile(archive_path) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    members[filename] = content.encode("utf-8")
    with zipfile.ZipFile(archive_path, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)


def test_all_five_intact_instruction_projections_pass(tmp_path):
    make_fixture(tmp_path)
    report = parity.verify(tmp_path)
    assert report["status"] == "pass", report


@pytest.mark.parametrize("target", sorted(TARGETS))
def test_altered_instruction_body_with_unchanged_headings_fails(tmp_path, target):
    make_fixture(tmp_path)
    archive = tmp_path / "dist" / f"{target}.zip"
    replace_entry(archive, TARGETS[target],
                  CORE.replace("Always require verified evidence",
                               "Never require verified evidence"))
    report = parity.verify(tmp_path)
    assert report["status"] == "fail", report
    assert any(target + ": canonical instruction line lost or altered:" in issue
               for issue in report["issues"]), report


@pytest.mark.parametrize("target", sorted(TARGETS))
def test_missing_instruction_projection_fails(tmp_path, target):
    make_fixture(tmp_path)
    archive = tmp_path / "dist" / f"{target}.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("unrelated.txt", "no canonical instructions")
    report = parity.verify(tmp_path)
    assert report["status"] == "fail", report
    assert any(target + ": missing instruction projection" in issue
               for issue in report["issues"]), report
