#!/usr/bin/env python3
"""Generate an isolated five-runtime migration candidate; never alter the source repository."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--engine-root", type=Path, required=True)
    args = parser.parse_args()
    root, engine = args.project_root.resolve(), args.engine_root.resolve()
    cfg_path = root / "gpt-project.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    cfg["instructions"]["mode"] = "modular_skills"
    cfg["instructions"]["core"] = "canonical/core.md"
    cfg["instructions"]["canonical"] = "canonical/core.md"
    cfg["runtime"]["custom_gpt"]["enabled"] = False
    cfg["runtime"]["claude"]["enabled"] = True
    cfg["runtime"]["claude"]["mode"] = "claude_project"
    cfg["runtime"]["claude"]["project"] = {
        "instructions": "project/instructions.md",
        "knowledge": "project/knowledge",
        "runtime_contract": "project/runtime-contract.json",
    }
    cfg["runtime"]["plugin"].setdefault("templates", {})["readme"] = "templates/README.plugin.md.tpl"
    cfg["runtime"]["plugin"]["layout"] = {
        "manifest_file": "plugin.json",
        "skills": "skills",
        "references": "references",
        "assets": "assets",
        "scripts": "scripts",
    }
    cfg["runtime"]["plugin"].setdefault("validation", {}).update({
        "require_manifest": True,
        "require_skill": True,
        "require_skill_frontmatter": True,
    })
    cfg["runtime"]["claude"].setdefault("templates", {})["readme"] = "templates/README.claude.md.tpl"
    cfg["build"]["build_custom_gpt_zip"] = False
    cfg["build"]["build_claude_zip"] = True
    cfg["build"]["build_claude_skills_zip"] = True
    cfg["build_system"]["targets"] = ["project", "chat", "plugin", "claude_project", "claude_skills", "opencode"]
    targets = cfg["build_system"]["runtime_targets"]
    targets.pop("custom-gpt", None)
    targets["claude_project"] = {
        "runtime_id": "claude_project", "runtime_key": "claude",
        "builder": "claude", "artifact_type": "claude_project_zip",
        "filename_pattern": "<project-id>-claude-project-v<version>.zip",
    }
    targets["claude_skills"] = {
        "runtime_id": "claude_skills", "runtime_key": "claude",
        "builder": "claude_skills", "artifact_type": "claude_skills_zip",
        "filename_pattern": "<project-id>-claude-skills-v<version>.zip",
    }
    cfg["runtime_parity"]["registered_runtimes"] = [
        "chatgpt_chat", "openai_plugin", "claude_project", "claude_skills", "opencode"
    ]
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")

    report = {"source_unchanged": True, "target": "canonical_1.6.33", "checks": []}
    commands = [
        ("install", [sys.executable, str(engine / "scripts/install_distribution_engine.py"),
                     "--source", str(engine), "--project-root", str(root)]),
        ("build", [sys.executable, str(root / "scripts/build_distributions.py"),
                   "--project-root", str(root), "--version", "0.0.0-migration"]),
        ("validate", [sys.executable, str(root / "scripts/validate_distributions.py"),
                      "--project-root", str(root)]),
    ]
    for label, command in commands:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True)
        entry = {
            "step": label, "exit_code": result.returncode,
            "stdout_tail": result.stdout[-5000:],
            "stderr_tail": result.stderr[-5000:],
        }
        report["checks"].append(entry)
        print(f"{label}: {'PASS' if result.returncode == 0 else 'FAIL'}", flush=True)
        if result.returncode:
            print(entry["stdout_tail"], entry["stderr_tail"], flush=True)
            break
    path = root / "MIGRATION-BUILD-REPORT.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0  # Preview is diagnostic; activation stays gated until all checks pass.


if __name__ == "__main__":
    raise SystemExit(main())
