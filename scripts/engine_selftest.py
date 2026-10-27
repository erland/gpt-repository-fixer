"""Deterministic self-test for a standalone Repository Fixer Engine ZIP.

Run after extracting the Engine: python scripts/engine_selftest.py
Only Python's standard library is required.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    from scripts.lib.analysis_report import render_analysis_report
    from scripts.lib.fix_plan import render_fix_plan
    from scripts.lib.final_report import render_final_report

    inventory = {"technologies": {}, "project_types": [], "confidence": "medium"}
    analysis = {
        "repository_name": "engine-selftest",
        "inventory": inventory,
        "findings": [],
        "build_test": {},
        "recommended_next_step": "Review",
        "checked_areas": [],
    }
    models = (
        (render_analysis_report, analysis, "# Repository analysis"),
        (render_fix_plan, {"repository_name": "engine-selftest", "steps": [], "source_finding_ids": []}, "# Repository fix plan"),
        (render_final_report, {
            "repository_name": "engine-selftest",
            "initial_summary": {"must_fix": 0, "recommended": 0, "consider": 0},
            "final_summary": {"must_fix": 0, "recommended": 0, "consider": 0},
            "resolved": [], "remaining": [], "skipped": [], "new_findings": [],
            "build_test": {}, "area_status": [], "limitations": [],
        }, "# Repository final report"),
    )
    for renderer, model, heading in models:
        output = renderer(model)
        assert output.startswith(heading), (renderer.__name__, output[:100])
        assert "{{" not in output, renderer.__name__
        explicit = renderer(model, template_text="CUSTOM {{REPOSITORY_NAME}}")
        assert explicit == "CUSTOM engine-selftest\n", renderer.__name__

    manifest_path = root / "engine-package.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for rel, expected in manifest["files"].items():
            path = root / rel
            assert path.is_file(), f"Engine file missing: {rel}"
            assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, f"Engine checksum mismatch: {rel}"
    print(json.dumps({"status": "pass", "renderers": 3, "modes": ["default", "explicit"], "integrity": manifest_path.is_file()}))


if __name__ == "__main__":
    main()
