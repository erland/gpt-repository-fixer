from __future__ import annotations

from pathlib import Path

from scripts.build_distributions import build_chat, build_custom, build_opencode, load_config
from scripts.validate_release_readiness import validate_readiness

ROOT = Path(__file__).resolve().parents[1]


def test_release_readiness_passes_for_peer_builds(tmp_path):
    cfg = load_config(ROOT)
    build_root = tmp_path / 'build'
    build_chat(ROOT, cfg, build_root, 'test-readiness')
    build_custom(ROOT, cfg, build_root, 'test-readiness')
    build_opencode(ROOT, cfg, build_root, 'test-readiness')
    report = validate_readiness(ROOT, build_root, check_source_clean=False)
    assert report['result'] == 'pass', report['errors']
    assert report['summary']['errors'] == 0
    assert len(report['checks']) == 8


def test_release_readiness_detects_instruction_divergence(tmp_path):
    cfg = load_config(ROOT)
    build_root = tmp_path / 'build'
    build_chat(ROOT, cfg, build_root, 'test-readiness')
    build_custom(ROOT, cfg, build_root, 'test-readiness')
    build_opencode(ROOT, cfg, build_root, 'test-readiness')
    (build_root / 'custom-gpt' / 'builder' / 'instructions.md').write_text('diverged\n', encoding='utf-8')
    report = validate_readiness(ROOT, build_root, check_source_clean=False)
    assert report['result'] == 'fail'
    assert any('instructions' in error for error in report['errors'])


def test_release_readiness_detects_knowledge_divergence(tmp_path):
    cfg = load_config(ROOT)
    build_root = tmp_path / 'build'
    build_chat(ROOT, cfg, build_root, 'test-readiness')
    build_custom(ROOT, cfg, build_root, 'test-readiness')
    build_opencode(ROOT, cfg, build_root, 'test-readiness')
    target = build_root / 'chat' / 'knowledge' / 'finding-model.md'
    target.write_text(target.read_text(encoding='utf-8') + '\nchanged\n', encoding='utf-8')
    report = validate_readiness(ROOT, build_root, check_source_clean=False)
    assert report['result'] == 'fail'
    assert any('knowledge/finding-model.md' in error for error in report['errors'])
