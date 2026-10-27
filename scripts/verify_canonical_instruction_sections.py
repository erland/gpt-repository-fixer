"""Verify every canonical core section survives all five generated runtime projections."""
import argparse
import json
import re
import zipfile
from pathlib import Path

import yaml

PROJECTIONS = {
    "chat": "assistant/instructions.md",
    "claude_project": "project/instructions.md",
    "opencode": "AGENTS.md",
}


def verify(root: Path) -> dict:
    cfg = yaml.safe_load((root / "gpt-project.yaml").read_text(encoding="utf-8"))
    source = (root / cfg["instructions"]["core"]).read_text(encoding="utf-8")
    headings = re.findall(r"^#{2,3} (.+)$", source, re.MULTILINE)
    # Headings alone cannot detect policy drift when the body is silently altered.
    source_lines = [line.strip() for line in source.splitlines() if line.strip()]
    build = json.loads((root / "MIGRATION-BUILD-REPORT.json").read_text(encoding="utf-8"))
    archives = {item["target"]: root / "dist" / item["archive"] for item in build["distributions"]}
    issues = []
    counts = {}
    for target in ("chat", "plugin", "claude_project", "claude_skills", "opencode"):
        with zipfile.ZipFile(archives[target]) as zf:
            names = set(zf.namelist())
            if target in PROJECTIONS:
                candidates = [PROJECTIONS[target]]
            else:
                candidates = [f"skills/{skill['id']}/SKILL.md" for skill in cfg["skills"]["definitions"]]
            texts = []
            for path in candidates:
                if path not in names:
                    issues.append(f"{target}: missing instruction projection {path}")
                else:
                    texts.append(zf.read(path).decode("utf-8"))
            projected = "\n".join(texts)
            counts[target] = len(texts)
            for heading in headings:
                if heading not in projected:
                    issues.append(f"{target}: canonical section missing: {heading}")
            for line in source_lines:
                if line not in projected:
                    issues.append(f"{target}: canonical instruction line lost or altered: {line[:120]}")
    report = {"status": "pass" if not issues else "fail", "canonical_sections": len(headings), "canonical_lines": len(source_lines),
              "projections": counts, "issues": issues}
    (root / "INSTRUCTION-PARITY-REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, required=True)
    args = p.parse_args()
    raise SystemExit(0 if verify(args.project_root)["status"] == "pass" else 1)
