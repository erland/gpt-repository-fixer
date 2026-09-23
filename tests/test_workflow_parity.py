from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_ci_and_release_build_same_runtime_targets():
    ci = _text(".github/workflows/ci.yml")
    release = _text(".github/workflows/release.yml")
    targets = "--targets project,chat,custom-gpt,opencode"
    assert targets in ci
    assert targets in release


def test_ci_and_release_run_same_release_gates():
    ci = _text(".github/workflows/ci.yml")
    release = _text(".github/workflows/release.yml")
    commands = [
        "python -m pytest -q -p no:cacheprovider",
        "python scripts/lint_gpt_project.py --project-root .",
        "python scripts/project_hygiene.py --project-root . --mode final",
        "python scripts/validate_distributions.py --project-root .",
        "python scripts/validate_runtime_parity.py --project-root . --build-root build",
        "python scripts/validate_release_readiness.py --project-root . --build-root build",
    ]
    for command in commands:
        assert command in ci
        assert command in release


def test_release_version_is_derived_from_release_tag():
    release = _text(".github/workflows/release.yml")
    assert "github.event.release.tag_name" in release
    assert 'VERSION="${TAG#v}"' in release
    assert "dist/DELIVERY-MANIFEST.json" in release
    assert "dist/SHA256SUMS.txt" in release
