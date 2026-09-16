from __future__ import annotations

from pathlib import Path
from typing import Any

from .repository_inventory import detect_from_paths
from .readme_analysis import analyze_readme
from .markdown_analysis import analyze_markdown_documentation
from .license_analysis import analyze_license
from .hygiene_analysis import analyze_repository_hygiene
from .build_test_analysis import analyze_build_test
from .github_actions_analysis import analyze_github_actions
from .analysis_report import build_report_model, render_analysis_report
from .fix_plan import build_fix_plan_model, render_fix_plan

TEXT_SUFFIXES = {'.md', '.json', '.xml', '.yaml', '.yml', '.toml', '.properties', '.txt', '.js', '.jsx', '.ts', '.tsx', '.java', '.py', '.go', '.rs', '.gradle', '.kts', ''}


def read_repository_files(root: Path | str) -> dict[str, str]:
    root = Path(root)
    files: dict[str, str] = {}
    for path in sorted(root.rglob('*')):
        if not path.is_file() or '.repository-fixer' in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {'Dockerfile', '.gitignore', 'LICENSE', 'LICENCE', 'Makefile'}:
            continue
        try:
            files[rel] = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
    return files


def analyze_repository(root: Path | str, repository_name: str | None = None, execution_results: dict | None = None) -> dict[str, Any]:
    root = Path(root)
    files = read_repository_files(root)
    inventory = detect_from_paths(list(files))
    build_test = analyze_build_test(files, execution_results=execution_results)
    gha = analyze_github_actions(files)

    findings = []
    findings.extend(analyze_readme(files))
    findings.extend(analyze_markdown_documentation(files))
    findings.extend(analyze_license(files))
    findings.extend(analyze_repository_hygiene(files))
    findings.extend(build_test.get('findings', []))
    findings.extend(gha.get('findings', []))

    checked_areas = [
        {'area': 'readme', 'status': 'checked', 'note': 'README analyserad mot verifierbara repositoryfakta.'},
        {'area': 'documentation', 'status': 'checked', 'note': 'Övrig Markdown analyserad.'},
        {'area': 'license', 'status': 'checked', 'note': 'Licensfiler och licensreferenser analyserade.'},
        {'area': 'repository-hygiene', 'status': 'checked', 'note': 'Repository hygiene analyserad.'},
        {'area': 'github-actions', 'status': 'checked', 'note': 'GitHub Actions analyserad.'},
    ]
    name = repository_name or root.name
    report_model = build_report_model(name, inventory, checked_areas, findings, build_test)
    plan_model = build_fix_plan_model(name, findings)
    return {
        'files': files,
        'inventory': inventory,
        'build_test': build_test,
        'github_actions': gha,
        'findings': findings,
        'report_model': report_model,
        'report_markdown': render_analysis_report(report_model),
        'plan_model': plan_model,
        'plan_markdown': render_fix_plan(plan_model),
    }
