#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except Exception as exc:
    raise SystemExit('PyYAML is required') from exc

CACHE_NAMES = {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache'}
TEMP_SUFFIXES = {'.pyc', '.pyo', '.tmp', '.temp'}


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def _canonical_knowledge(root: Path, cfg: dict) -> dict[str, Path]:
    knowledge_root = root / cfg['knowledge_architecture']['canonical_root']
    return {
        p.relative_to(knowledge_root).as_posix(): p
        for p in sorted(knowledge_root.rglob('*'))
        if p.is_file() and p.name != 'KNOWLEDGE.md'
    }


def _compare_file(errors: list[str], source: Path, generated: Path, label: str) -> None:
    if not generated.exists():
        errors.append(f'Missing generated parity file: {label} -> {generated}')
        return
    if source.read_bytes() != generated.read_bytes():
        errors.append(f'Generated file diverges from canonical source: {label}')


def validate_readiness(root: Path, build_root: Path | None = None, *, check_source_clean: bool = True) -> dict:
    root = root.resolve()
    build_root = (build_root or (root / 'build')).resolve()
    cfg = yaml.safe_load(_read(root / 'gpt-project.yaml'))
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({'name': name, 'status': 'pass' if ok else 'fail', 'detail': detail})

    # 1. Canonical instruction must be byte-identical in both peer runtimes.
    canonical_instruction = root / cfg['instructions']['canonical']
    chat_instruction = build_root / 'chat' / 'assistant' / 'instructions.md'
    custom_instruction = build_root / 'custom-gpt' / 'builder' / 'instructions.md'
    before = len(errors)
    _compare_file(errors, canonical_instruction, chat_instruction, 'chat instructions')
    _compare_file(errors, canonical_instruction, custom_instruction, 'custom-gpt instructions')
    check('canonical-instruction-parity', len(errors) == before,
          'Chat ZIP och Custom GPT använder canonical src/instructions/system.md utan avvikelse.')

    # 2. Canonical Knowledge must be present and byte-identical in both runtimes.
    canonical_knowledge = _canonical_knowledge(root, cfg)
    before = len(errors)
    for rel, source in canonical_knowledge.items():
        _compare_file(errors, source, build_root / 'chat' / 'knowledge' / rel, f'chat knowledge/{rel}')
        _compare_file(errors, source, build_root / 'custom-gpt' / 'builder' / 'knowledge-package' / rel,
                      f'custom-gpt knowledge/{rel}')
    check('canonical-knowledge-parity', len(errors) == before,
          f'{len(canonical_knowledge)} canonical Knowledge-filer finns identiskt i båda distributionerna.')

    # 3. Chat runtime policies must also be generated from canonical policy source.
    policy_root = root / cfg['structure']['runtime_policy']['path']
    before = len(errors)
    policy_files = [p for p in sorted(policy_root.rglob('*.md')) if p.name != 'README.md']
    for source in policy_files:
        _compare_file(errors, source, build_root / 'chat' / 'assistant' / 'policies' / source.name,
                      f'chat policy/{source.name}')
    check('chat-policy-parity', len(errors) == before,
          f'{len(policy_files)} runtime policies genereras från canonical src/runtime-policy/.')

    # 4. Build reports must show no silent Custom GPT knowledge reduction.
    compilation = build_root / 'custom-gpt' / 'builder' / 'compilation-report.json'
    before = len(errors)
    if not compilation.exists():
        errors.append('Missing Custom GPT compilation-report.json')
    else:
        try:
            report = json.loads(_read(compilation))
            knowledge = report['knowledge']
            instruction = report['instruction']
            if knowledge['excluded']:
                errors.append('Custom GPT compilation excludes canonical Knowledge files')
            if knowledge['selected_files'] != knowledge['canonical_files']:
                errors.append('Custom GPT selected Knowledge count differs from canonical count')
            if instruction['compiled_characters'] > instruction['max_characters']:
                errors.append('Custom GPT instruction exceeds configured character limit')
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            errors.append(f'Invalid compilation-report.json: {exc}')
    check('custom-gpt-compilation', len(errors) == before,
          'Ingen tyst Knowledge-reduktion och instruktionen håller Builder-gränsen.')

    # 5. Known platform limitation must be explicit, not simulated away.
    compat = build_root / 'custom-gpt' / 'COMPATIBILITY.md'
    caps = build_root / 'custom-gpt' / 'builder' / 'capabilities.json'
    before = len(errors)
    if not compat.exists() or not caps.exists():
        errors.append('Custom GPT compatibility/capability documentation missing')
    else:
        compat_text = _read(compat)
        required_terms = ['GitHub branch/commit/PR', 'autentiserad GitHub-skrivintegration', 'read-only']
        for term in required_terms:
            if term not in compat_text:
                errors.append(f'COMPATIBILITY.md missing platform limitation term: {term}')
        try:
            profile = json.loads(_read(caps))
            if profile['capabilities']['github_write_integration']['level'] != 'conditional_external':
                errors.append('GitHub write integration must remain conditional_external')
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            errors.append(f'Invalid capabilities.json: {exc}')
    check('platform-limitations-documented', len(errors) == before,
          'GitHub-skrivning är explicit villkorad och read-only fallback dokumenterad.')

    # 6. Canonical source tree must not contain generated/cache/temp artifacts outside build/dist/fixtures.
    before = len(errors)
    if check_source_clean:
        for p in root.rglob('*'):
            rel = p.relative_to(root)
            if rel.parts and rel.parts[0] in {'build', 'dist', '.git'}:
                continue
            if len(rel.parts) >= 2 and rel.parts[0] == 'tests' and rel.parts[1] == 'fixtures':
                continue
            if p.name in CACHE_NAMES:
                errors.append(f'Cache artifact in canonical source tree: {rel.as_posix()}')
            elif p.is_file() and p.suffix.lower() in TEMP_SUFFIXES:
                errors.append(f'Temporary/generated artifact in canonical source tree: {rel.as_posix()}')
        detail = 'Cache/temp-filer saknas utanför genererade build/dist och avsiktliga fixtures.'
    else:
        detail = 'Källträdets cleanliness-kontroll hoppades över av anroparen; övrig readiness-paritet verifierades.'
    check('canonical-tree-clean', len(errors) == before, detail)

    # 7. Human/machine project status and README must describe the same current step.
    before = len(errors)
    status = yaml.safe_load(_read(root / 'project-status.yaml'))
    progress = status.get('progress', {})
    next_step = status.get('next_step', {})
    last_completed = progress.get('last_completed_step')
    completed_steps = progress.get('completed_steps') or []
    recommended = next_step.get('recommended')
    if not isinstance(last_completed, int) or last_completed < 1:
        errors.append('project-status.yaml has no valid last_completed_step')
    elif last_completed not in completed_steps:
        errors.append(f'project-status.yaml completed_steps is missing step {last_completed}')
    if isinstance(last_completed, int) and isinstance(recommended, int) and recommended <= last_completed:
        errors.append('project-status.yaml next recommended step must be after last_completed_step')
    readme_text = _read(root / 'README.md')
    status_text = _read(root / 'STATUS.md')
    project_text = _read(root / 'PROJECT.md')
    if isinstance(last_completed, int) and f'Steg 1–{last_completed} är genomförda' not in readme_text:
        errors.append('README.md project status is stale')
    if isinstance(recommended, int) and f'Nästa rekommenderade steg: **{recommended}' not in status_text:
        errors.append('STATUS.md next-step status is stale')
    if 'ska senare generera' in project_text:
        errors.append('PROJECT.md still says peer distributions will be generated later')
    check('project-status-current', len(errors) == before,
          'README, STATUS, PROJECT och project-status.yaml beskriver samma aktuella projektläge.')

    result = 'pass' if not errors else 'fail'
    return {
        'result': result,
        'summary': {'errors': len(errors), 'warnings': len(warnings), 'checks': len(checks)},
        'checks': checks,
        'errors': errors,
        'warnings': warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', default='.')
    parser.add_argument('--build-root')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    build_root = Path(args.build_root).resolve() if args.build_root else None
    report = validate_readiness(root, build_root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in report['checks']:
            print(f"{item['status'].upper():4} {item['name']}: {item['detail']}")
        for error in report['errors']:
            print(f'ERROR {error}')
        print(f"RELEASE READINESS: {report['result'].upper()} (errors={report['summary']['errors']})")
    return 0 if report['result'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
