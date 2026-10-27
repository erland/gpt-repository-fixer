"""Regression gate for real packaged report renderers and runtime documentation.

Unlike source-only tests, this extracts Skill scripts/assets from every generated
runtime ZIP and imports them in an isolated Python package before rendering.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path

SKILLS = {
    "repository-analysis": ("analysis_report", "render_analysis_report", "repository-analysis.md.tpl", "# Repository analysis"),
    "repository-remediation": ("fix_plan", "render_fix_plan", "repository-fix-plan.md.tpl", "# Repository fix plan"),
    "repository-verification": ("final_report", "render_final_report", "repository-final-report.md.tpl", "# Repository final report"),
}
PREFIXES = {
    "chat": "assistant/skills/",
    "plugin": "skills/",
    "claude_skills": "skills/",
    "opencode": ".opencode/skills/",
}


def _sample_models():
    inventory = {"technologies": {}, "project_types": [], "confidence": "medium"}
    analysis = {"repository_name": "packaged-smoke", "inventory": inventory, "findings": [], "build_test": {},
                "checked_areas": []}
    return {
        "repository-analysis": analysis,
        "repository-remediation": {"repository_name": "packaged-smoke",
                                    "steps": [], "source_finding_ids": []},
        "repository-verification": {
            "repository_name": "packaged-smoke",
            "initial_summary": {"must_fix": 0, "recommended": 0, "consider": 0},
            "final_summary": {"must_fix": 0, "recommended": 0, "consider": 0},
            "resolved": [], "remaining": [], "skipped": [], "new_findings": [],
            "build_test": {}, "area_status": [], "limitations": [],
        },
    }


def verify(root: Path) -> dict:
    report_path = root / "MIGRATION-BUILD-REPORT.json"
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        archives = {item["target"]: root / "dist" / item["archive"]
                    for item in report["distributions"]}
    else:
        # Release builds do not produce a migration report; inspect final ZIPs.
        patterns = {
            "chat": "repository-fixer-chat-v*.zip",
            "plugin": "repository-fixer-plugin-v*.zip",
            "claude_skills": "repository-fixer-claude-skills-v*.zip",
            "opencode": "repository-fixer-opencode-v*.zip",
        }
        archives = {}
        for target, pattern in patterns.items():
            matches = list((root / "dist").glob(pattern))
            assert len(matches) == 1, (target, matches)
            archives[target] = matches[0]
    tested = []
    with tempfile.TemporaryDirectory(prefix="report-renderers-") as temp:
        base = Path(temp)
        sys.path.insert(0, str(base))
        try:
            for target, prefix in PREFIXES.items():
                with zipfile.ZipFile(archives[target]) as zf:
                    names = set(zf.namelist())
                    for skill, (module_name, renderer_name, template, heading) in SKILLS.items():
                        source_prefix = prefix + skill + "/"
                        package_name = f"packaged_{target}_{skill.replace('-', '_')}"
                        package = base / package_name
                        scripts = package / "scripts"
                        assets = package / "assets"
                        scripts.mkdir(parents=True)
                        assets.mkdir()
                        (package / "__init__.py").write_text("", encoding="utf-8")
                        (scripts / "__init__.py").write_text("", encoding="utf-8")
                        for name in names:
                            if name.startswith(source_prefix + "scripts/") and name.endswith(".py"):
                                relative = name[len(source_prefix + "scripts/"):]
                                dest = scripts / relative
                                dest.parent.mkdir(parents=True, exist_ok=True)
                                dest.write_bytes(zf.read(name))
                            elif name.startswith(source_prefix + "assets/") and name.endswith(".tpl"):
                                relative = name[len(source_prefix + "assets/"):]
                                dest = assets / relative
                                dest.parent.mkdir(parents=True, exist_ok=True)
                                dest.write_bytes(zf.read(name))
                        assert (assets / template).is_file(), f"{target}/{skill}: missing {template}"
                        module = importlib.import_module(f"{package_name}.scripts.{module_name}")
                        renderer = getattr(module, renderer_name)
                        model = _sample_models()[skill]
                        generated = renderer(model)
                        assert generated.startswith(heading), (target, skill, generated[:120])
                        assert "{{" not in generated, (target, skill, generated)
                        custom = renderer(model, template_text="CUSTOM {{REPOSITORY_NAME}}")
                        assert custom == "CUSTOM packaged-smoke\n", (target, skill, custom)
                        tested.append(f"{target}/{skill}")
                    if target == "chat":
                        guide = zf.read("START-HERE.md").decode("utf-8")
                        assert "assistant/skills/<skill-id>/scripts/" in guide
                    if target == "opencode":
                        readme = zf.read("README.md").decode("utf-8")
                        assert "inga projektlokala OpenCode custom tools" in readme
                        assert "gpt_build_distributions" in readme and "ingår därför inte" in readme
                    if target == "plugin":
                        readme = zf.read("README.md").decode("utf-8")
                        assert "deklarerade tool-script-integrationer" in readme
                        contract = json.loads(zf.read("runtime-contract.json"))
                        assert contract["capabilities"]["requirements"]["code_execution"]["level"] == "required"
                        assert contract["adapter"]["runtime_requirements"]["code_execution"]["level"] == "not_required"
                        assert not contract["tools"]["tools"]
        finally:
            sys.path.remove(str(base))
            for name in list(sys.modules):
                if name.startswith("packaged_"):
                    del sys.modules[name]
    result = {"status": "pass", "tested": tested, "count": len(tested)}
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    verify(args.project_root)
