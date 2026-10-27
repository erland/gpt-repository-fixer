"""Prove byte-level resource parity for packaged canonical Skills."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import yaml


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def verify(project: Path) -> dict:
    cfg = yaml.safe_load((project / "gpt-project.yaml").read_text(encoding="utf-8"))
    report = json.loads((project / "MIGRATION-BUILD-REPORT.json").read_text(encoding="utf-8"))
    by_target = {item["target"]: item for item in report.get("distributions", [])}
    errors = []
    checked = 0
    for target in ("plugin", "claude_skills"):
        item = by_target.get(target)
        if not item:
            errors.append(f"{target}: missing build report entry")
            continue
        archive = project / "dist" / item["archive"]
        with zipfile.ZipFile(archive) as zf:
            members = set(zf.namelist())
            for skill in cfg["skills"]["definitions"]:
                sid = skill["id"]
                for kind in ("references", "scripts", "assets"):
                    for source in skill[kind]:
                        source_path = project / source
                        dest = f"skills/{sid}/{kind}/{Path(source).name}"
                        if dest not in members:
                            errors.append(f"{target}: missing {dest}")
                            continue
                        if not source_path.is_file():
                            errors.append(f"{target}: expected file {source}")
                            continue
                        source_bytes = source_path.read_bytes()
                        packaged_bytes = zf.read(dest)
                        checked += 1
                        if sha(source_bytes) != sha(packaged_bytes):
                            errors.append(f"{target}: SHA-256 differs for {source} -> {dest}")
                skill_md = f"skills/{sid}/SKILL.md"
                if skill_md not in members:
                    errors.append(f"{target}: missing {skill_md}")
                    continue
                compiled = zf.read(skill_md).decode("utf-8")
                original_behavior = (project / skill["source"]).read_text(encoding="utf-8")
                # Require key source wording to survive compilation; layout/frontmatter may change.
                for line in original_behavior.splitlines():
                    if not line.strip():
                        continue
                    if line not in compiled:
                        errors.append(f"{target}: canonical behavior line lost or altered in {sid}: {line[:120]}")
    result = {"status": "pass" if not errors else "fail",
              "resource_hash_checks": checked, "errors": errors,
              "scope": "Plugin and Claude Skills reference/script/resource bytes and all canonical behavior lines"}
    (project / "RESOURCE-PARITY-REPORT.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if verify(args.project_root)["status"] == "pass" else 1)
