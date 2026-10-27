"""Exercise actual packaged Chat step-control logic through a persisted restart."""
import argparse
import importlib.util
import json
import tempfile
import zipfile
from pathlib import Path


def verify(root: Path) -> dict:
    report = json.loads((root / "MIGRATION-BUILD-REPORT.json").read_text())
    item = next(x for x in report["distributions"] if x["target"] == "chat")
    archive = root / "dist" / item["archive"]
    script = "assistant/skills/repository-remediation/scripts/step_control.py"
    errors = []
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(archive) as zf:
        if script not in zf.namelist():
            errors.append(f"Chat ZIP missing {script}")
        else:
            source = Path(tmp) / "step_control.py"
            source.write_bytes(zf.read(script))
            spec = importlib.util.spec_from_file_location("packaged_chat_step_control", source)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            plan = {"repository_name": "chat-resume", "source_finding_ids": [],
                    "steps": [{"id": "s1", "dependencies": [], "decisions": [],
                               "likely_files": ["README.md"]}]}
            progress = module.initialize_progress(plan)
            module.apply_user_action(plan, progress, "do", "s1")
            persisted = Path(tmp) / "project-status.json"
            persisted.write_text(json.dumps(progress, ensure_ascii=False), encoding="utf-8")
            restored = json.loads(persisted.read_text(encoding="utf-8"))
            next_action = module.select_next_action(plan, restored)
            if next_action.get("action") != "resume-execution" or next_action.get("step_id") != "s1":
                errors.append(f"Chat resume chose wrong action: {next_action}")
            module.record_execution_result(
                plan, restored, "s1", success=True, verification_status="verified")
            persisted.write_text(json.dumps(restored, ensure_ascii=False), encoding="utf-8")
            reloaded = json.loads(persisted.read_text(encoding="utf-8"))
            if reloaded["steps"][0]["status"] != "completed" or reloaded["steps"][0]["verification_status"] != "verified":
                errors.append("Chat failed to persist verified completion")
    result = {"status": "pass" if not errors else "fail", "archive": archive.name, "errors": errors}
    (root / "CHAT-RESUME-REPORT.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if verify(args.project_root)["status"] == "pass" else 1)
