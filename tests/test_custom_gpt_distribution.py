"""Retired Custom GPT must not be emitted by the five-runtime distribution."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

def test_custom_gpt_is_explicitly_disabled():
    cfg = yaml.safe_load((ROOT / "gpt-project.yaml").read_text(encoding="utf-8"))
    assert cfg["runtime"]["custom_gpt"]["enabled"] is False
    assert cfg["build"]["build_custom_gpt_zip"] is False
    assert "custom-gpt" not in cfg["build_system"]["targets"]
    assert "custom-gpt" not in cfg["build_system"]["runtime_targets"]

def test_five_peer_targets_are_configured():
    cfg = yaml.safe_load((ROOT / "gpt-project.yaml").read_text(encoding="utf-8"))
    assert set(cfg["build_system"]["runtime_targets"]) == {
        "chat", "plugin", "claude_project", "claude_skills", "opencode"
    }
    assert cfg["instructions"]["mode"] == "modular_skills"
    assert (ROOT / cfg["instructions"]["core"]).is_file()
