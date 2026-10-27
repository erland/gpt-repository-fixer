"""Negative checks for runtime contract safety guardrails."""
import importlib.util
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("contracts", ROOT / "scripts/verify_canonical_runtime_contracts.py")
contracts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contracts)


def setup(tmp_path, *, mutation=None):
    dist = tmp_path / "dist"
    dist.mkdir()
    content = {"runtime_id": "claude_project", "adapter": {"mode": "claude_project", "embedded_local_tools": False},
               "capabilities": {"requirements": {"external_tools": {"level": "optional"}}},
               "artifacts": {}, "tools": {},
               "workspace_state": {"state": {"authority": "workspace_file", "persistence": "required",
                                            "conversation_fallback": False}}}
    entries = []
    for target, filename in [("claude_project", "project/runtime-contract.json"),
                             ("opencode", ".opencode/runtime-contract.json")]:
        contract = json.loads(json.dumps(content))
        contract["runtime_id"] = target
        contract["adapter"]["mode"] = "opencode_workspace" if target == "opencode" else "claude_project"
        if mutation and mutation[0] == target:
            mutation[1](contract)
        with zipfile.ZipFile(dist / (target + ".zip"), "w") as z:
            z.writestr(filename, json.dumps(contract))
        entries.append({"target": target, "archive": target + ".zip"})
    with zipfile.ZipFile(dist / "plugin.zip", "w") as z:
        z.writestr("plugin.json", json.dumps({"name": "repository-fixer"}))
        z.writestr("runtime-contract.json", json.dumps({"runtime_id": "openai_plugin", "capabilities": {"requirements": {"external_tools": {"level": "optional"}}}, "adapter": {"mcp_generated": False, "script_resources": {"mcp_required_for_resource_use": False}}}))
        z.writestr("skills/repository-analysis/SKILL.md",
                   "Statusfilen går före chattminne; failing blockerar.")
        z.writestr("skills/repository-remediation/SKILL.md",
                   "Om skrivåtkomst saknas, gör ingen GitHub-ändring.")
        z.writestr("skills/repository-remediation/references/github-write-workflow.md",
                   "Skriv inte direkt till default branch.")
        z.writestr("skills/repository-verification/SKILL.md",
                   "Verifiera varje steg.")
    entries.append({"target": "plugin", "archive": "plugin.zip"})
    (tmp_path / "MIGRATION-BUILD-REPORT.json").write_text(json.dumps({"distributions": entries}))
    return tmp_path


def test_valid_contracts_pass(tmp_path):
    assert contracts.verify(setup(tmp_path))["status"] == "pass"


def test_conversation_only_state_is_rejected(tmp_path):
    root = setup(tmp_path, mutation=("claude_project", lambda c: c["workspace_state"]["state"].update(
        {"authority": "conversation", "conversation_fallback": True})))
    report = contracts.verify(root)
    assert report["status"] == "fail"
    assert any("workspace state authority weakened" in e for e in report["errors"])


def test_mandatory_external_tools_are_rejected(tmp_path):
    root = setup(tmp_path, mutation=("opencode", lambda c: c["capabilities"]["requirements"]["external_tools"].update(
        {"level": "required"})))
    report = contracts.verify(root)
    assert report["status"] == "fail"
    assert any("external tools must remain optional" in e for e in report["errors"])


def test_invented_claude_local_execution_is_rejected(tmp_path):
    root = setup(tmp_path, mutation=("claude_project", lambda c: c["adapter"].update(
        {"embedded_local_tools": True})))
    report = contracts.verify(root)
    assert report["status"] == "fail"
    assert any("embedded local tools incorrectly assumed" in e for e in report["errors"])


def rewrite_plugin(tmp_path, path, replacement=None):
    archive = tmp_path / "dist/plugin.zip"
    with zipfile.ZipFile(archive) as z:
        files = {name: z.read(name) for name in z.namelist()}
    if replacement is None:
        files.pop(path)
    else:
        files[path] = replacement.encode("utf-8")
    with zipfile.ZipFile(archive, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)


def test_plugin_missing_workspace_authority_is_rejected(tmp_path):
    root = setup(tmp_path)
    rewrite_plugin(root, "skills/repository-analysis/SKILL.md", "failing blockerar.")
    report = contracts.verify(root)
    assert report["status"] == "fail"
    assert any("core status safeguard missing: Statusfilen" in e for e in report["errors"])


def test_plugin_missing_github_write_fallback_is_rejected(tmp_path):
    root = setup(tmp_path)
    rewrite_plugin(root, "skills/repository-remediation/SKILL.md", "GitHub workflow.")
    report = contracts.verify(root)
    assert report["status"] == "fail"
    assert any("GitHub fallback safeguard missing: skrivåtkomst saknas" in e for e in report["errors"])


def test_plugin_missing_default_branch_safety_is_rejected(tmp_path):
    root = setup(tmp_path)
    rewrite_plugin(root, "skills/repository-remediation/references/github-write-workflow.md")
    report = contracts.verify(root)
    assert report["status"] == "fail"
    assert any("GitHub fallback safeguard missing: Skriv inte direkt" in e for e in report["errors"])


def test_plugin_missing_verification_skill_is_rejected(tmp_path):
    root = setup(tmp_path)
    rewrite_plugin(root, "skills/repository-verification/SKILL.md")
    report = contracts.verify(root)
    assert report["status"] == "fail"
    assert any("missing policy resource skills/repository-verification/SKILL.md" in e
               for e in report["errors"])


def test_wrong_opencode_identity_is_rejected(tmp_path):
    root = setup(tmp_path, mutation=("opencode", lambda c: c.update({"runtime_id": "chatgpt_chat"})))
    report = contracts.verify(root)
    assert report["status"] == "fail"
    assert any("opencode: incorrect runtime_id" in e for e in report["errors"])


def test_wrong_opencode_adapter_is_rejected(tmp_path):
    root = setup(tmp_path, mutation=("opencode", lambda c: c["adapter"].update({"mode": "claude_project"})))
    report = contracts.verify(root)
    assert report["status"] == "fail"
    assert any("opencode: incorrect adapter mode" in e for e in report["errors"])


def test_plugin_mandatory_mcp_is_rejected(tmp_path):
    root = setup(tmp_path)
    rewrite_plugin(root, "runtime-contract.json", json.dumps({
        "runtime_id": "openai_plugin",
        "capabilities": {"requirements": {"external_tools": {"level": "optional"}}},
        "adapter": {"mcp_generated": True,
                    "script_resources": {"mcp_required_for_resource_use": True}}
    }))
    report = contracts.verify(root)
    assert report["status"] == "fail"
    assert any("mandatory MCP dependency detected" in e for e in report["errors"])


def test_plugin_required_external_github_integration_is_rejected(tmp_path):
    root = setup(tmp_path)
    rewrite_plugin(root, "runtime-contract.json", json.dumps({
        "runtime_id": "openai_plugin",
        "capabilities": {"requirements": {"external_tools": {"level": "required"}}},
        "adapter": {
            "mcp_generated": False,
            "script_resources": {"mcp_required_for_resource_use": False},
        },
    }))
    report = contracts.verify(root)
    assert report["status"] == "fail"
    assert any("GitHub/external write integration must remain optional" in e
               for e in report["errors"])
