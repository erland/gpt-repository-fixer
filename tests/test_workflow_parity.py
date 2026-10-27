from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_ci_and_release_use_same_pinned_canonical_engine():
    ci = _text(".github/workflows/ci.yml")
    release = _text(".github/workflows/release.yml")
    for text in (ci, release):
        assert "gpt-byggaren-engine-1.6.33.zip" in text
        assert "scripts/install_distribution_engine.py" in text
        assert "scripts/build_distributions.py" in text
        assert "scripts/validate_distributions.py" in text
        assert "--targets project,chat,custom-gpt" not in text


def test_ci_and_release_require_canonical_validation_before_delivery():
    ci = _text(".github/workflows/ci.yml")
    release = _text(".github/workflows/release.yml")
    assert ci.index("scripts/validate_distributions.py") < ci.index("Upload canonical active distributions")
    assert release.index("scripts/validate_distributions.py") < release.index("gh release upload")
    assert "python -m pytest -q -p no:cacheprovider" in ci
    assert "python -m pytest -q -p no:cacheprovider" in release


def test_release_version_is_derived_from_release_tag():
    release = _text(".github/workflows/release.yml")
    assert "github.event.release.tag_name" in release
    assert 'VERSION="${TAG#v}"' in release
    assert "dist/DELIVERY-MANIFEST.json" in release
    assert "dist/SHA256SUMS.txt" in release
