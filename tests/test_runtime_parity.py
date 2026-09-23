from __future__ import annotations

from pathlib import Path

from scripts.build_distributions import build_chat, build_custom, build_opencode, load_config
from scripts.validate_runtime_parity import validate_runtime_parity


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_parity_passes_for_enabled_peer_builds(tmp_path):
    cfg = load_config(ROOT)
    build_root = tmp_path / "build"
    build_chat(ROOT, cfg, build_root, "test-parity")
    build_custom(ROOT, cfg, build_root, "test-parity")
    build_opencode(ROOT, cfg, build_root, "test-parity")

    report = validate_runtime_parity(ROOT, build_root)
    assert report["result"] == "pass", report["errors"]


def test_runtime_parity_assesses_all_registered_runtimes():
    cfg = load_config(ROOT)
    registered = set(cfg["runtime_parity"]["registered_runtimes"])
    candidates = {item["runtime_id"] for item in cfg["analysis"]["runtime"]["candidates"]}
    assert registered == candidates
    assert registered == {
        "chatgpt_chat",
        "chatgpt_custom",
        "claude_project",
        "opencode",
        "openai_plugin",
    }
