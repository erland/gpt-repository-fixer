"""Run real Repository Fixer domain functions from the packaged Skill archives.

Tests the *packaged bytes*, not the checkout. This is a portable preflight, not
a substitute for runtime-host execution or the full project test suite.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


def load_from_archive(archive: Path, skill: str, basename: str, workspace: Path):
    prefix = f"skills/{skill}/scripts/"
    with zipfile.ZipFile(archive) as zf:
        candidates = [name for name in zf.namelist() if name.startswith(prefix)
                      and PurePosixPath(name).name == basename]
        if len(candidates) != 1:
            raise AssertionError(f"{archive.name}: expected one {skill}/{basename}, got {candidates}")
        source = zf.read(candidates[0])
    destination = workspace / f"{skill}-{basename}"
    destination.write_bytes(source)
    spec = importlib.util.spec_from_file_location(f"packaged_{skill}_{basename[:-3]}", destination)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def check_archive(archive: Path):
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        inventory = load_from_archive(archive, "repository-analysis", "repository_inventory.py", workspace)
        finding = load_from_archive(archive, "repository-analysis", "finding_model.py", workspace)
        result = inventory.detect_from_paths(["pom.xml", ".github/workflows/ci.yml"])
        assert "Java" in result["languages"], result
        assert "Maven" in result["build_tools"], result
        assert not finding.validate_semantics({"classification": "must-fix", "evidence": [
            {"kind": "file", "path": "pom.xml"}]})
        assert "negative findings require concrete evidence" in finding.validate_semantics(
            {"classification": "must-fix", "evidence": []})
    return {"archive": archive.name, "result": "PASS", "functions": [
        "repository_inventory.detect_from_paths", "finding_model.validate_semantics"]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, required=True)
    args = p.parse_args()
    root = args.project_root
    cfg = json.loads((root / "MIGRATION-BUILD-REPORT.json").read_text())
    by_target = {item["target"]: item for item in cfg.get("distributions", [])}
    results = []
    for target in ("plugin", "claude_skills"):
        assert target in by_target
        archive = root / "dist" / by_target[target]["archive"]
        results.append(check_archive(archive))
    cfg["packaged_domain_smoke"] = results
    (root / "MIGRATION-BUILD-REPORT.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
