"""Canonical release readiness protects release workflow and delivery verifier."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

def test_release_uses_pinned_engine_and_verifies_before_publication():
    release = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    for marker in (
        "gpt-byggaren-engine-1.6.33.zip",
        "selftest_distribution_engine.py",
        "install_distribution_engine.py",
        "scripts/validate_distributions.py",
        "scripts/verify_canonical_delivery.py",
    ):
        assert marker in release
        assert release.index(marker) < release.index("gh release upload")
    assert "github.event.release.tag_name" in release

def test_canonical_delivery_gate_requires_exact_runtime_manifest_checksums():
    verifier = (ROOT / "scripts/verify_canonical_delivery.py").read_text(encoding="utf-8")
    for marker in ("SHA256SUMS.txt", "DELIVERY-MANIFEST.json", "testzip()", "sha256", "project-status.yaml"):
        assert marker in verifier
    cfg = yaml.safe_load((ROOT / "gpt-project.yaml").read_text(encoding="utf-8"))
    assert set(cfg["build_system"]["runtime_targets"]) == {
        "chat", "plugin", "claude_project", "claude_skills", "opencode"
    }
