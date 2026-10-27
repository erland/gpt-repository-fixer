"""Validate five-runtime canonical package parity from actual generated ZIPs."""
import argparse
import json
import zipfile
from pathlib import Path

TARGETS = ("chat", "plugin", "claude_project", "claude_skills", "opencode")
SKILLS = ("repository-analysis", "repository-remediation", "repository-verification")
MARKERS = ("Analys före ändring", "Evidens före antaganden",
           "Verifiera efter ändring", "Auktoritativ status")
GITHUB_MARKERS = ("GitHub", "PR")


def check(root: Path):
    report = json.loads((root / "MIGRATION-BUILD-REPORT.json").read_text(encoding="utf-8"))
    found = {item["target"]: item for item in report.get("distributions", [])}
    issues = []
    if set(found) != set(TARGETS):
        issues.append(f"Expected exactly five targets: {sorted(found)}")
    for target in TARGETS:
        item = found.get(target)
        if not item:
            continue
        archive = root / "dist" / item["archive"]
        if not archive.is_file():
            issues.append(f"{target}: missing ZIP")
            continue
        with zipfile.ZipFile(archive) as z:
            content = {p: z.read(p).decode("utf-8", errors="replace") for p in z.namelist()
                       if p.endswith((".md", ".json")) and not p.startswith("__MACOSX/")}
            combined = "\n".join(content.values())
            for marker in MARKERS:
                if marker not in combined:
                    issues.append(f"{target}: missing policy marker {marker}")
            if not all(m in combined for m in GITHUB_MARKERS):
                issues.append(f"{target}: GitHub/PR safeguards not evident")
            if target in {"plugin", "claude_skills"}:
                for sid in SKILLS:
                    p = f"skills/{sid}/SKILL.md"
                    if p not in content:
                        issues.append(f"{target}: missing {p}")
                    elif sid not in content[p]:
                        issues.append(f"{target}: incorrect Skill identity {sid}")
    result = {"result": "pass" if not issues else "fail", "issues": issues, "targets": list(TARGETS)}
    (root / "CANONICAL-PARITY-REPORT.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return bool(issues)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", required=True, type=Path)
    args = p.parse_args()
    raise SystemExit(check(args.project_root))
