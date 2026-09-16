#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_INSTRUCTION_MARKERS = [
    "Analys före ändring",
    "Evidens före antaganden",
    "Minimum necessary change",
    "Mänskligt beslut när det behövs",
    "Verifiera efter ändring",
]

REQUIRED_KNOWLEDGE = {
    "analysis-report.md",
    "build-test-analysis.md",
    "final-verification.md",
    "finding-model.md",
    "fix-plan.md",
    "github-actions-analysis.md",
    "github-read-workflow.md",
    "github-write-workflow.md",
    "interactive-step-control.md",
    "license-analysis.md",
    "markdown-documentation-analysis.md",
    "readme-analysis.md",
    "repository-hygiene.md",
    "repository-inventory.md",
    "step-verification.md",
    "zip-workflow.md",
}

FORBIDDEN_PLACEHOLDERS = {
    "Ej automatiskt analyserat ännu.",
    "Paritetsrapport genereras mer fullständigt i senare buildsteg.",
}


def validate_runtime(root: Path) -> list[str]:
    errors: list[str] = []
    builder = root / "builder"

    required = [
        builder / "instructions.md",
        builder / "conversation-starters.md",
        builder / "capabilities.md",
        builder / "capabilities.json",
        builder / "compilation-report.json",
        root / "README.md",
        root / "COMPATIBILITY.md",
        root / "VERSION",
        root / "MANIFEST.json",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"Missing required Custom GPT file: {path.relative_to(root)}")

    instr = builder / "instructions.md"
    if instr.exists():
        text = instr.read_text(encoding="utf-8")
        for marker in REQUIRED_INSTRUCTION_MARKERS:
            if marker not in text:
                errors.append(f"Instruction missing core marker: {marker}")
        if "repository-analysis.md" not in text or "repository-fix-plan.md" not in text:
            errors.append("Instruction must require analysis and fix-plan artifacts")
        if "GitHub" not in text or "PR" not in text:
            errors.append("Instruction must retain GitHub/PR workflow semantics")

    kp = builder / "knowledge-package"
    knowledge = {p.name for p in kp.glob("*.md")} if kp.exists() else set()
    missing_knowledge = sorted(REQUIRED_KNOWLEDGE - knowledge)
    if missing_knowledge:
        errors.append("Missing required Knowledge files: " + ", ".join(missing_knowledge))

    capabilities_json = builder / "capabilities.json"
    if capabilities_json.exists():
        try:
            profile = json.loads(capabilities_json.read_text(encoding="utf-8"))
            caps = profile["capabilities"]
            if caps["web_search"]["level"] != "required":
                errors.append("web_search must be required")
            if caps["data_analysis"]["level"] != "required":
                errors.append("data_analysis must be required")
            if caps["image_generation"]["level"] != "disabled":
                errors.append("image_generation must be disabled")
            if caps["github_write_integration"]["level"] != "conditional_external":
                errors.append("github_write_integration must be conditional_external")
            if profile.get("fallback", {}).get("github_write_unavailable") != "read_only_analysis_and_plan":
                errors.append("GitHub write fallback must be read_only_analysis_and_plan")
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            errors.append(f"Invalid capabilities.json: {exc}")

    compilation = builder / "compilation-report.json"
    if compilation.exists():
        try:
            report = json.loads(compilation.read_text(encoding="utf-8"))
            instruction = report["instruction"]
            knowledge_report = report["knowledge"]
            if instruction["compiled_characters"] > instruction["max_characters"]:
                errors.append("Compiled instruction exceeds declared limit")
            if knowledge_report["selected_files"] > knowledge_report["max_files"]:
                errors.append("Selected Knowledge exceeds declared limit")
            if knowledge_report["excluded"]:
                errors.append("Step 21 requires full canonical Knowledge parity; excluded files found")
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            errors.append(f"Invalid compilation-report.json: {exc}")

    compat = root / "COMPATIBILITY.md"
    if compat.exists():
        text = compat.read_text(encoding="utf-8")
        for placeholder in FORBIDDEN_PLACEHOLDERS:
            if placeholder in text:
                errors.append(f"Compatibility still contains placeholder: {placeholder}")
        required_terms = [
            "GitHub branch/commit/PR",
            "autentiserad GitHub-skrivintegration",
            "read-only",
            "Dataanalys",
            "Slutverifiering",
        ]
        for term in required_terms:
            if term not in text:
                errors.append(f"Compatibility missing required capability/parity term: {term}")

    readme = root / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        if "builder/capabilities.json" not in text:
            errors.append("Custom GPT README must document capabilities.json")
        if "separat autentiserad GitHub-integration" not in text:
            errors.append("Custom GPT README must document GitHub write dependency")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runtime_root")
    args = parser.parse_args()
    root = Path(args.runtime_root).resolve()
    errors = validate_runtime(root)
    if errors:
        print("CUSTOM GPT RUNTIME: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("CUSTOM GPT RUNTIME: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
