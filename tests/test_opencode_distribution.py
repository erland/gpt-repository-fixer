from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.build_distributions import build_opencode, load_config


ROOT = Path(__file__).resolve().parents[1]


def test_opencode_distribution_is_standalone(tmp_path):
    cfg = load_config(ROOT)
    out = build_opencode(ROOT, cfg, tmp_path / "build", "test-opencode")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_opencode_runtime.py"), str(out)],
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OPENCODE RUNTIME: PASS" in proc.stdout


def test_opencode_runtime_contract_and_skill(tmp_path):
    cfg = load_config(ROOT)
    out = build_opencode(ROOT, cfg, tmp_path / "build", "test-opencode")

    contract = json.loads((out / ".opencode" / "runtime-contract.json").read_text(encoding="utf-8"))
    assert contract["runtime_id"] == "opencode"
    assert contract["adapter"]["mode"] == "opencode_workspace"
    assert contract["workspace_state"]["state"]["authority"] == "workspace_file"

    skill = out / ".opencode" / "skills" / "repository-fixer" / "SKILL.md"
    assert skill.exists()
    assert "Analys" in skill.read_text(encoding="utf-8")

    agents = (out / "AGENTS.md").read_text(encoding="utf-8")
    assert "Repository Fixer" in agents
    assert "OpenCode adapter" in agents
