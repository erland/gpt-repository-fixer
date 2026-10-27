"""Ensure runtime registration and canonical behavior coverage match migration targets."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

def test_runtime_registry_has_exactly_five_active_runtimes():
    cfg = yaml.safe_load((ROOT / "gpt-project.yaml").read_text(encoding="utf-8"))
    expected = {"chatgpt_chat", "openai_plugin", "claude_project", "claude_skills", "opencode"}
    actual = {v["runtime_id"] for v in cfg["build_system"]["runtime_targets"].values()}
    assert actual == expected
    assert set(cfg["runtime_parity"]["registered_runtimes"]) == expected
    assert all(cfg["runtime"][key]["enabled"] for key in ("chat_zip", "plugin", "claude", "opencode"))

def test_canonical_skill_sources_and_resources_are_present():
    cfg = yaml.safe_load((ROOT / "gpt-project.yaml").read_text(encoding="utf-8"))
    assert cfg["skills"]["resource_policy"] == "explicit"
    assert {s["id"] for s in cfg["skills"]["definitions"]} == {
        "repository-analysis", "repository-remediation", "repository-verification"
    }
    for skill in cfg["skills"]["definitions"]:
        assert (ROOT / skill["source"]).is_file()
        for kind in ("references", "scripts", "assets"):
            for relative in skill[kind]:
                assert (ROOT / relative).is_file(), (skill["id"], relative)
