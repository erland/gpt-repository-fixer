"""Negative regression tests for byte-level canonical Skill resource parity."""
import importlib.util
import json
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "resource_parity", ROOT / "scripts/verify_canonical_resource_parity.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def make_fixture(tmp_path):
    cfg = {"skills": {"definitions": [{
        "id": "repository-analysis",
        "source": "canonical/skills/repository-analysis/behavior.md",
        "references": ["knowledge/analysis-report.md"],
        "scripts": ["scripts/lib/finding_model.py"],
        "assets": [],
    }]}}
    for path, value in {
        "canonical/skills/repository-analysis/behavior.md": "# Analysis\n## Evidence\nCheck evidence.\n",
        "knowledge/analysis-report.md": "Reference content",
        "scripts/lib/finding_model.py": "def validate(): return True\n",
    }.items():
        dest = tmp_path / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(value, encoding="utf-8")
    (tmp_path / "gpt-project.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    (tmp_path / "dist").mkdir()
    archive = tmp_path / "dist/plugin.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("skills/repository-analysis/SKILL.md", "# repository-analysis\n## Evidence\nCheck evidence.\n")
        z.writestr("skills/repository-analysis/references/analysis-report.md", "Reference content")
        z.writestr("skills/repository-analysis/scripts/finding_model.py", "def validate(): return True\n")
    (tmp_path / "MIGRATION-BUILD-REPORT.json").write_text(json.dumps({
        "distributions": [{"target": "plugin", "archive": "plugin.zip"},
                          {"target": "claude_skills", "archive": "plugin.zip"}]
    }), encoding="utf-8")
    return archive


def replace_archive_entry(path, entry, new_content=None):
    with zipfile.ZipFile(path, "r") as z:
        original = {name: z.read(name) for name in z.namelist()}
    if new_content is None:
        original.pop(entry)
    else:
        original[entry] = new_content.encode("utf-8")
    with zipfile.ZipFile(path, "w") as z:
        for name, data in original.items():
            z.writestr(name, data)


def test_unmodified_resources_pass(tmp_path):
    make_fixture(tmp_path)
    assert module.verify(tmp_path)["status"] == "pass"


def test_tampered_knowledge_fails(tmp_path):
    archive = make_fixture(tmp_path)
    replace_archive_entry(archive, "skills/repository-analysis/references/analysis-report.md", "tampered")
    result = module.verify(tmp_path)
    assert result["status"] == "fail"
    assert any("SHA-256 differs" in err for err in result["errors"])


def test_missing_script_fails(tmp_path):
    archive = make_fixture(tmp_path)
    replace_archive_entry(archive, "skills/repository-analysis/scripts/finding_model.py")
    result = module.verify(tmp_path)
    assert result["status"] == "fail"
    assert any("missing skills/repository-analysis/scripts/finding_model.py" in err
               for err in result["errors"])


def test_missing_canonical_heading_fails(tmp_path):
    archive = make_fixture(tmp_path)
    replace_archive_entry(archive, "skills/repository-analysis/SKILL.md", "# repository-analysis\n")
    result = module.verify(tmp_path)
    assert result["status"] == "fail"
    assert any("behavior heading lost" in err for err in result["errors"])
