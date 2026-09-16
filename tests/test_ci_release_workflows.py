from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(name: str) -> str:
    return (ROOT / '.github' / 'workflows' / name).read_text(encoding='utf-8')


def test_ci_runs_full_local_validation_chain_and_builds_all_targets():
    text = _text('ci.yml')
    required = [
        'python -m pytest -q',
        'scripts/lint_gpt_project.py',
        'scripts/project_hygiene.py --project-root . --mode final',
        '--targets project,chat,custom-gpt',
        'scripts/validate_distributions.py',
        'scripts/validate_release_readiness.py',
    ]
    for marker in required:
        assert marker in text
    assert '|| true' not in text


def test_ci_uploads_built_distribution_artifacts():
    text = _text('ci.yml')
    assert 'actions/upload-artifact@v4' in text
    assert 'dist/*.zip' in text
    assert 'dist/SHA256SUMS.txt' in text
    assert 'dist/DELIVERY-MANIFEST.json' in text


def test_release_uses_release_tag_as_version_and_builds_all_targets():
    text = _text('release.yml')
    assert 'github.event.release.tag_name' in text
    assert 'VERSION="${TAG#v}"' in text
    assert '--targets project,chat,custom-gpt' in text
    assert "--version '${{ steps.version.outputs.version }}'" in text


def test_release_validates_before_publishing_and_uploads_all_assets():
    text = _text('release.yml')
    assert text.index('python -m pytest -q') < text.index('gh release upload')
    assert text.index('scripts/validate_distributions.py') < text.index('gh release upload')
    assert text.index('scripts/validate_release_readiness.py') < text.index('gh release upload')
    assert 'dist/*.zip' in text
    assert 'dist/SHA256SUMS.txt' in text
    assert 'dist/DELIVERY-MANIFEST.json' in text
    assert '--clobber' in text


def test_release_keeps_validation_worktree_clean():
    text = _text('release.yml')
    assert "PYTHONDONTWRITEBYTECODE: '1'" in text
    assert 'python -m pytest -q -p no:cacheprovider' in text


def test_project_distribution_is_versioned():
    build_script = (ROOT / "scripts" / "build_distributions.py").read_text(encoding="utf-8")
    assert 'f"{project_id}-project-{version}.zip"' in build_script
