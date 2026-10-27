"""Blocking delivery gate: five runtimes, project ZIP, and optional Engine ZIP."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
import yaml


def verify(root: Path, version: str) -> None:
    cfg = yaml.safe_load((root / "gpt-project.yaml").read_text(encoding="utf-8"))
    dist = root / "dist"
    project = cfg["project"]["id"]
    expected = {f"{project}-project-{version}.zip"}
    targets = cfg["build_system"]["runtime_targets"]
    enabled = ("chat", "plugin", "claude_project", "claude_skills", "opencode")
    assert set(targets) == set(enabled), f"Unexpected configured targets: {set(targets)}"
    for key in enabled:
        expected.add(targets[key]["filename_pattern"].replace("<project-id>", project).replace("<version>", version))
    if cfg.get("engine", {}).get("enabled"):
        expected.add(f"{project}-engine-{version}.zip")
    actual = {p.name for p in dist.glob("*.zip")}
    assert actual == expected, f"Wrong ZIP set: missing={expected-actual}, extra={actual-expected}"
    checksums = {}
    for line in (dist / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, filename = line.split(None, 1)
        filename = filename.strip()
        assert filename not in checksums, filename
        checksums[filename] = digest
    assert set(checksums) == expected, "SHA256SUMS does not cover exact ZIP set"
    manifest = json.loads((dist / "DELIVERY-MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["version"] == version
    assert manifest["project"] == project
    artifacts = {x["file"]: x for x in manifest["artifacts"]}
    assert expected <= set(artifacts), "Manifest missing delivery ZIPs"
    for filename in sorted(expected):
        archive = dist / filename
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        assert digest == checksums[filename] == artifacts[filename]["sha256"], filename
        assert artifacts[filename]["size"] == archive.stat().st_size
        with zipfile.ZipFile(archive) as zf:
            assert zf.testzip() is None, filename
            if filename == f"{project}-project-{version}.zip":
                for required in ("gpt-project.yaml", "canonical/core.md", "project-status.yaml"):
                    assert required in zf.namelist(), f"project ZIP missing {required}"
    print(json.dumps({"result": "PASS", "version": version, "zip_count": len(expected),
                      "zip_files": sorted(expected)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    verify(args.project_root, args.version)
