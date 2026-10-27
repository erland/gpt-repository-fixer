"""Check every canonical Knowledge file is represented in each Skills distribution."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import yaml


def verify(root: Path) -> dict:
    cfg = yaml.safe_load((root / "gpt-project.yaml").read_text(encoding="utf-8"))
    knowledge_root = root / cfg["knowledge_architecture"]["canonical_root"]
    source_files = sorted(
        p for p in knowledge_root.rglob("*")
        if p.is_file() and p.name != "KNOWLEDGE.md"
    )
    skills = cfg["skills"]["definitions"]
    report = json.loads((root / "MIGRATION-BUILD-REPORT.json").read_text(encoding="utf-8"))
    distributions = {d["target"]: d["archive"] for d in report.get("distributions", [])}
    errors = []
    declared = {ref for skill in skills for ref in skill["references"]}
    for path in source_files:
        rel = path.relative_to(root).as_posix()
        if rel not in declared:
            errors.append(f"Canonical Knowledge has no Skill owner: {rel}")
    for target in ("plugin", "claude_skills"):
        archive = distributions.get(target)
        if not archive:
            errors.append(f"{target}: missing distribution")
            continue
        with zipfile.ZipFile(root / "dist" / archive) as zf:
            names = set(zf.namelist())
            for path in source_files:
                rel = path.relative_to(root).as_posix()
                owners = [s["id"] for s in skills if rel in s["references"]]
                if not owners:
                    continue
                digest = hashlib.sha256(path.read_bytes()).digest()
                if not any(
                    f"skills/{sid}/references/{path.name}" in names
                    and hashlib.sha256(zf.read(f"skills/{sid}/references/{path.name}")).digest() == digest
                    for sid in owners
                ):
                    errors.append(f"{target}: missing or changed canonical Knowledge: {rel}")
    result = {"status": "pass" if not errors else "fail",
              "canonical_knowledge_count": len(source_files),
              "declared_reference_count": len(declared),
              "errors": errors}
    (root / "KNOWLEDGE-COVERAGE-REPORT.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if verify(args.project_root)["status"] == "pass" else 1)
