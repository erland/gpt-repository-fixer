from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.build_distributions import build_custom, load_config


ROOT = Path(__file__).resolve().parents[1]


def test_custom_gpt_distribution_passes_standalone_validation(tmp_path):
    cfg = load_config(ROOT)
    out = build_custom(ROOT, cfg, tmp_path / 'build', 'test-custom')
    proc = subprocess.run(
        [sys.executable, str(ROOT / 'scripts' / 'validate_custom_gpt_runtime.py'), str(out)],
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert 'CUSTOM GPT RUNTIME: PASS' in proc.stdout


def test_custom_gpt_capability_profile_is_explicit(tmp_path):
    cfg = load_config(ROOT)
    out = build_custom(ROOT, cfg, tmp_path / 'build', 'test-custom')
    profile = json.loads((out / 'builder' / 'capabilities.json').read_text(encoding='utf-8'))
    caps = profile['capabilities']
    assert caps['web_search']['level'] == 'required'
    assert caps['data_analysis']['level'] == 'required'
    assert caps['image_generation']['level'] == 'disabled'
    assert caps['github_write_integration']['level'] == 'conditional_external'
    assert profile['fallback']['github_write_unavailable'] == 'read_only_analysis_and_plan'


def test_custom_gpt_compatibility_has_no_placeholder_text(tmp_path):
    cfg = load_config(ROOT)
    out = build_custom(ROOT, cfg, tmp_path / 'build', 'test-custom')
    text = (out / 'COMPATIBILITY.md').read_text(encoding='utf-8')
    assert 'Ej automatiskt analyserat ännu.' not in text
    assert 'senare buildsteg' not in text
    assert 'GitHub branch/commit/PR' in text
    assert 'autentiserad GitHub-skrivintegration' in text
    assert 'Dataanalys' in text


def test_custom_gpt_uses_all_canonical_knowledge(tmp_path):
    cfg = load_config(ROOT)
    out = build_custom(ROOT, cfg, tmp_path / 'build', 'test-custom')
    report = json.loads((out / 'builder' / 'compilation-report.json').read_text(encoding='utf-8'))
    assert report['knowledge']['excluded'] == []
    assert report['knowledge']['selected_files'] == report['knowledge']['canonical_files']
    assert report['instruction']['compiled_characters'] <= report['instruction']['max_characters']
