#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


ACTIVE_BUILDS = {
    "chatgpt_chat": ("chat_zip", "chat"),
    "chatgpt_custom": ("custom_gpt", "custom-gpt"),
    "opencode": ("opencode", "opencode"),
}

REGISTERED = {"chatgpt_chat", "chatgpt_custom", "claude_project", "opencode", "openai_plugin"}
CATEGORIES = {"behavior", "capability", "artifact", "workspace_state", "tool"}


def validate_runtime_parity(root: Path, build_root: Path | None = None) -> dict:
    root = root.resolve()
    build_root = (build_root or root / "build").resolve()
    cfg = yaml.safe_load((root / "gpt-project.yaml").read_text(encoding="utf-8"))

    errors: list[str] = []
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})

    parity = cfg.get("runtime_parity", {})
    registered = set(parity.get("registered_runtimes", []))
    categories = set(parity.get("compared_categories", []))

    before = len(errors)
    if registered != REGISTERED:
        errors.append(f"registered_runtimes must equal {sorted(REGISTERED)}")
    if categories != CATEGORIES:
        errors.append(f"compared_categories must equal {sorted(CATEGORIES)}")
    check("registered-runtime-contract", len(errors) == before,
          "Alla fem peer runtimes och fem kontraktskategorier är registrerade.")

    candidates = {
        item.get("runtime_id"): item
        for item in cfg.get("analysis", {}).get("runtime", {}).get("candidates", [])
        if isinstance(item, dict) and item.get("runtime_id")
    }

    before = len(errors)
    if set(candidates) != REGISTERED:
        errors.append("analysis.runtime.candidates must assess all registered runtimes")
    for runtime_id in REGISTERED:
        item = candidates.get(runtime_id, {})
        if not item.get("reason"):
            errors.append(f"{runtime_id} missing suitability reason")
        if item.get("suitability") not in {"ready", "reduced", "not_viable"}:
            errors.append(f"{runtime_id} has invalid suitability")
    check("runtime-assessment-complete", len(errors) == before,
          "Alla registrerade runtimes har explicit suitability och motivering.")

    before = len(errors)
    for runtime_id, (runtime_key, build_dir) in ACTIVE_BUILDS.items():
        if not cfg.get("runtime", {}).get(runtime_key, {}).get("enabled"):
            errors.append(f"{runtime_id} must be enabled")
        if not candidates.get(runtime_id, {}).get("activate_by_default"):
            errors.append(f"{runtime_id} must be activate_by_default")
        if not (build_root / build_dir).exists():
            errors.append(f"{runtime_id} build missing: {build_dir}")
    check("active-runtime-builds", len(errors) == before,
          "Chat, Custom GPT och OpenCode är aktiva och har byggda distributioner.")

    before = len(errors)
    for runtime_id, runtime_key in (("claude_project", "claude"), ("openai_plugin", "plugin")):
        if cfg.get("runtime", {}).get(runtime_key, {}).get("enabled"):
            errors.append(f"{runtime_id} must remain disabled in this migration")
        if candidates.get(runtime_id, {}).get("activate_by_default"):
            errors.append(f"{runtime_id} must not activate by default")
        if candidates.get(runtime_id, {}).get("suitability") != "reduced":
            errors.append(f"{runtime_id} must be assessed as reduced")
    check("inactive-runtime-decisions", len(errors) == before,
          "Claude Projects och OpenAI Plugin är bedömda men explicit ej aktiverade.")

    result = "pass" if not errors else "fail"
    return {
        "result": result,
        "summary": {"errors": len(errors), "checks": len(checks)},
        "checks": checks,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--build-root")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root)
    build_root = Path(args.build_root) if args.build_root else None
    report = validate_runtime_parity(root, build_root)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in report["checks"]:
            print(f"{item['status'].upper():4} {item['name']}: {item['detail']}")
        for error in report["errors"]:
            print(f"ERROR {error}")
        print(f"RUNTIME PARITY: {report['result'].upper()} (errors={report['summary']['errors']})")

    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
