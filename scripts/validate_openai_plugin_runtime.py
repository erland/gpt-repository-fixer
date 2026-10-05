#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED_LIB = {
    "__init__.py",
    "analysis_report.py",
    "build_test_analysis.py",
    "e2e_analysis.py",
    "final_report.py",
    "finding_model.py",
    "fix_plan.py",
    "github_actions_analysis.py",
    "github_read_workflow.py",
    "github_write_workflow.py",
    "hygiene_analysis.py",
    "license_analysis.py",
    "markdown_analysis.py",
    "project_model.py",
    "readme_analysis.py",
    "repository_inventory.py",
    "step_control.py",
    "step_verification.py",
    "zip_workflow.py",
}

FORBIDDEN = {
    "build_distributions.py",
    "validate_distributions.py",
    "validate_runtime_parity.py",
    "validate_release_readiness.py",
    "lint_gpt_project.py",
    "project_hygiene.py",
}

CORE_MARKERS = [
    "Analys före ändring",
    "Evidens före antaganden",
    "Minimum necessary change",
    "Mänskligt beslut när det behövs",
    "Verifiera efter ändring",
    "Operativ kärna",
    "Auktoritativ status",
]

PLUGIN_MARKERS = [
    "Chattminne ersätter aldrig workspace-state",
    "kräver writable workspace",
    "GitHub branch/commit/PR kräver faktisk auktoriserad GitHub write-capability",
    "Komplett uppdaterad ZIP får endast påstås levererad",
    "kräver ingen MCP-wrapper",
]

def validate_runtime(root: Path) -> list[str]:
    errors: list[str] = []
    required = [
        root / "plugin.json",
        root / "runtime-contract.json",
        root / "README.md",
        root / "VERSION",
        root / "MANIFEST.json",
        root / "skills" / "repository-fixer" / "SKILL.md",
        root / "skills" / "repository-fixer" / "references" / "knowledge" / "zip-workflow.md",
        root / "skills" / "repository-fixer" / "references" / "knowledge" / "github-read-workflow.md",
        root / "skills" / "repository-fixer" / "references" / "knowledge" / "github-write-workflow.md",
        root / "skills" / "repository-fixer" / "references" / "schemas" / "repository-zip-state.schema.json",
        root / "skills" / "repository-fixer" / "references" / "schemas" / "repository-step-verification.schema.json",
        root / "skills" / "repository-fixer" / "references" / "runtime-policy" / "operational-execution-policy.md",
        root / "skills" / "repository-fixer" / "templates" / "repository-analysis.md.tpl",
        root / "skills" / "repository-fixer" / "templates" / "repository-fix-plan.md.tpl",
        root / "skills" / "repository-fixer" / "templates" / "repository-final-report.md.tpl",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"Missing required file: {path.relative_to(root)}")

    plugin_path = root / "plugin.json"
    if plugin_path.exists():
        try:
            plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
            if plugin.get("name") != "repository-fixer":
                errors.append("plugin.json name must be repository-fixer")
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid plugin.json: {exc}")

    contract_path = root / "runtime-contract.json"
    if contract_path.exists():
        try:
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            if contract.get("runtime_id") != "openai_plugin":
                errors.append("runtime-contract.json runtime_id must be openai_plugin")
            if contract.get("compatibility") != "equivalent_runtime_dependent":
                errors.append("Plugin parity must be equivalent_runtime_dependent")
            adapter = contract.get("adapter", {})
            if adapter.get("mode") != "openai_plugin":
                errors.append("Plugin adapter mode must be openai_plugin")
            if adapter.get("skills_first") is not True or adapter.get("workspace_first") is not True:
                errors.append("Plugin must be skills-first and workspace-first")
            if adapter.get("state_authority") != "workspace_file":
                errors.append("workspace_file must remain state authority")
            if adapter.get("local_scripts_are_runtime_tools") is not False:
                errors.append("scripts/lib resources must not become canonical runtime tools")
            resources = adapter.get("script_resources", {})
            if set(resources.get("packaged", [])) != EXPECTED_LIB:
                errors.append("Plugin runtime library closure differs")
            if resources.get("mcp_required_for_resource_use") is not False:
                errors.append("Plugin runtime libraries must not require MCP")
            fallback = adapter.get("fallback_policy", {})
            if fallback.get("without_code_execution") != "do_not_mark_changes_verified":
                errors.append("verification fallback weakened")
            if fallback.get("without_github_write") != "read_only_analysis_or_zip_mode":
                errors.append("GitHub fallback weakened")
            if fallback.get("without_archive_output") != "do_not_claim_updated_zip_delivered":
                errors.append("ZIP delivery fallback weakened")
            if contract.get("tools", {}).get("tools") != []:
                errors.append("canonical tools contract must remain empty")
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid runtime-contract.json: {exc}")

    skill_path = root / "skills" / "repository-fixer" / "SKILL.md"
    if skill_path.exists():
        text = skill_path.read_text(encoding="utf-8")
        for marker in CORE_MARKERS + PLUGIN_MARKERS:
            if marker not in text:
                errors.append(f"SKILL.md missing marker: {marker}")

    lib_root = root / "skills" / "repository-fixer" / "scripts" / "lib"
    actual = {p.name for p in lib_root.glob("*.py")} if lib_root.exists() else set()
    if actual != EXPECTED_LIB:
        errors.append(f"Plugin runtime library differs: {sorted(actual)}")
    if actual & FORBIDDEN:
        errors.append(f"Project build/validation scripts leaked into Plugin: {sorted(actual & FORBIDDEN)}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default="build/plugin")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    errors = validate_runtime(root)
    if errors:
        print("OPENAI PLUGIN RUNTIME: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("OPENAI PLUGIN RUNTIME: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
