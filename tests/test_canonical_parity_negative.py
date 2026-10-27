"""Negative tests prove that canonical parity validation rejects missing safeguards."""
import importlib.util
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("canonical_parity", ROOT / "scripts/validate_canonical_parity_preview.py")
parity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parity)


def _fixture(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    rows = []
    common = "# Rules\n" + "\n".join(parity.MARKERS) + "\nGitHub branch och PR\n"
    for target in parity.TARGETS:
        filename = f"{target}.zip"
        with zipfile.ZipFile(dist / filename, "w") as z:
            z.writestr("README.md", common)
            if target in ("plugin", "claude_skills"):
                for skill in parity.SKILLS:
                    z.writestr(f"skills/{skill}/SKILL.md", f"# {skill}\n{common}")
        rows.append({"target": target, "archive": filename})
    (tmp_path / "MIGRATION-BUILD-REPORT.json").write_text(
        json.dumps({"distributions": rows}), encoding="utf-8")
    return dist


def test_complete_five_runtime_package_set_passes(tmp_path):
    _fixture(tmp_path)
    assert parity.check(tmp_path) is False
    assert json.loads((tmp_path / "CANONICAL-PARITY-REPORT.json").read_text())["result"] == "pass"


def test_missing_canonical_policy_is_detected(tmp_path):
    dist = _fixture(tmp_path)
    with zipfile.ZipFile(dist / "chat.zip", "w") as z:
        z.writestr("README.md", "GitHub PR without canonical rules")
    assert parity.check(tmp_path) is True
    report = json.loads((tmp_path / "CANONICAL-PARITY-REPORT.json").read_text())
    assert any("chat: missing policy marker" in issue for issue in report["issues"])


def test_missing_plugin_skill_is_detected(tmp_path):
    dist = _fixture(tmp_path)
    with zipfile.ZipFile(dist / "plugin.zip", "w") as z:
        body = "\n".join(parity.MARKERS) + "\nGitHub PR"
        z.writestr("README.md", body)
        for skill in parity.SKILLS:
            if skill != "repository-verification":
                z.writestr(f"skills/{skill}/SKILL.md", skill)
    assert parity.check(tmp_path) is True
    report = json.loads((tmp_path / "CANONICAL-PARITY-REPORT.json").read_text())
    assert any("plugin: missing skills/repository-verification/SKILL.md" in issue for issue in report["issues"])


def test_missing_fifth_distribution_is_detected(tmp_path):
    _fixture(tmp_path)
    report_file = tmp_path / "MIGRATION-BUILD-REPORT.json"
    report = json.loads(report_file.read_text())
    report["distributions"] = [d for d in report["distributions"] if d["target"] != "opencode"]
    report_file.write_text(json.dumps(report))
    assert parity.check(tmp_path) is True
    assert any("Expected exactly five targets" in issue for issue in
               json.loads((tmp_path / "CANONICAL-PARITY-REPORT.json").read_text())["issues"])
