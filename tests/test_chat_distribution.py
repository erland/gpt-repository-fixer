from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.build_distributions import build_chat, load_config


ROOT = Path(__file__).resolve().parents[1]


def test_chat_distribution_is_standalone(tmp_path):
    cfg = load_config(ROOT)
    out = build_chat(ROOT, cfg, tmp_path / 'build', 'test-chat')
    proc = subprocess.run(
        [sys.executable, str(ROOT / 'scripts' / 'validate_chat_runtime.py'), str(out)],
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert 'CHAT RUNTIME VALIDATION: PASS' in proc.stdout


def test_chat_start_here_explains_analysis_plan_and_resume(tmp_path):
    cfg = load_config(ROOT)
    out = build_chat(ROOT, cfg, tmp_path / 'build', 'test-chat')
    text = (out / 'START-HERE.md').read_text(encoding='utf-8')
    assert 'repository-analysis.md' in text
    assert 'repository-fix-plan.md' in text
    assert '.repository-fixer/' in text
    assert 'återuppta' in text.lower()
