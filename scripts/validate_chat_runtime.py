#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path


def _safe_extract(zf: zipfile.ZipFile, target: Path) -> None:
    root = target.resolve()
    for info in zf.infolist():
        dest = (target / info.filename).resolve()
        if dest != root and root not in dest.parents:
            raise RuntimeError(f"Unsafe Chat ZIP member: {info.filename}")
    zf.extractall(target)


def _write_sample_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / 'package.json').write_text(json.dumps({
        'name': 'chat-smoke',
        'scripts': {'build': 'vite build', 'test': 'vitest run'},
        'devDependencies': {'vite': '^7.0.0', 'vitest': '^3.0.0'},
    }, indent=2) + '\n', encoding='utf-8')
    (root / 'pnpm-lock.yaml').write_text('lockfileVersion: 9.0\n', encoding='utf-8')
    (root / 'README.md').write_text(
        '# Chat smoke\n\nInstall with `npm install`.\n\nRun `npm run build` and `npm test`.\n',
        encoding='utf-8',
    )


def validate_runtime(runtime_root: Path) -> list[str]:
    errors: list[str] = []
    required = [
        'START-HERE.md', 'VERSION', 'MANIFEST.json', 'assistant/instructions.md',
        'scripts/lib/e2e_analysis.py', 'scripts/lib/zip_workflow.py',
        'scripts/lib/step_control.py', 'templates/repository-analysis.md.tpl',
        'templates/repository-fix-plan.md.tpl',
    ]
    for rel in required:
        if not (runtime_root / rel).exists():
            errors.append(f'Missing standalone Chat runtime file: {rel}')
    if errors:
        return errors

    sys.path.insert(0, str(runtime_root))
    try:
        e2e = importlib.import_module('scripts.lib.e2e_analysis')
        zipwf = importlib.import_module('scripts.lib.zip_workflow')
        control = importlib.import_module('scripts.lib.step_control')

        with tempfile.TemporaryDirectory(prefix='repository-fixer-chat-smoke-') as tmp:
            tmp = Path(tmp)
            repo = tmp / 'repo'
            _write_sample_repo(repo)
            result = e2e.analyze_repository(repo, 'chat-smoke')
            analysis_path = tmp / 'repository-analysis.md'
            plan_path = tmp / 'repository-fix-plan.md'
            analysis_path.write_text(result['report_markdown'], encoding='utf-8')
            plan_path.write_text(result['plan_markdown'], encoding='utf-8')
            if not analysis_path.read_text(encoding='utf-8').startswith('# Repository analysis'):
                errors.append('Standalone Chat runtime did not produce repository-analysis.md')
            if '# Repository fix plan' not in plan_path.read_text(encoding='utf-8'):
                errors.append('Standalone Chat runtime did not produce repository-fix-plan.md')

            progress = control.initialize_progress(result['plan_model'])
            first = next((s for s in progress['steps'] if s['status'] == 'planned'), None)
            if first:
                control.apply_user_action(result['plan_model'], progress, 'do', first['id'])
                control.record_execution_result(
                    result['plan_model'], progress, first['id'], success=True,
                    verification_status='not-verified',
                )
            zipwf.write_portable_state(
                repo,
                analysis_md=result['report_markdown'],
                plan_md=result['plan_markdown'],
                progress_md='# Repository Fixer progress\n',
                analysis=result['report_model'],
                plan=result['plan_model'],
                progress=progress,
            )
            loaded = zipwf.load_portable_state(repo)
            if loaded.get('progress_json') != progress:
                errors.append('Standalone Chat runtime could not resume portable progress state')
    except Exception as exc:
        errors.append(f'Standalone Chat runtime smoke test failed: {type(exc).__name__}: {exc}')
    finally:
        try:
            sys.path.remove(str(runtime_root))
        except ValueError:
            pass
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('artifact', help='Chat ZIP artifact or extracted runtime directory')
    args = parser.parse_args()
    artifact = Path(args.artifact).resolve()

    if artifact.is_dir():
        errors = validate_runtime(artifact)
    else:
        with tempfile.TemporaryDirectory(prefix='repository-fixer-chat-runtime-') as tmp:
            target = Path(tmp)
            with zipfile.ZipFile(artifact) as zf:
                _safe_extract(zf, target)
            errors = validate_runtime(target)

    if errors:
        print('CHAT RUNTIME VALIDATION: FAIL')
        for error in errors:
            print(f'- {error}')
        return 1
    print('CHAT RUNTIME VALIDATION: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
