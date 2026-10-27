"""Validate concrete runtime identities and adapter contracts in canonical archives."""
import argparse
import json
import zipfile
from pathlib import Path


def verify(root: Path) -> dict:
    build = json.loads((root / "MIGRATION-BUILD-REPORT.json").read_text())
    archives = {entry["target"]: root / "dist" / entry["archive"]
                for entry in build.get("distributions", [])}
    required = {
        "claude_project": ("project/runtime-contract.json", "claude_project", "claude_project"),
        "opencode": (".opencode/runtime-contract.json", "opencode", "opencode_workspace"),
    }
    errors = []
    checked = []
    for target, (filename, runtime_id, adapter_mode) in required.items():
        path = archives.get(target)
        if path is None or not path.is_file():
            errors.append(f"{target}: distribution missing")
            continue
        with zipfile.ZipFile(path) as z:
            if filename not in z.namelist():
                errors.append(f"{target}: runtime contract missing: {filename}")
                continue
            contract = json.loads(z.read(filename))
        if contract.get("runtime_id") != runtime_id:
            errors.append(f"{target}: incorrect runtime_id")
        if (contract.get("adapter") or {}).get("mode") != adapter_mode:
            errors.append(f"{target}: incorrect adapter mode")
        for field in ("capabilities", "artifacts", "workspace_state", "tools"):
            if not isinstance(contract.get(field), dict):
                errors.append(f"{target}: missing {field} contract")
        state = (contract.get("workspace_state") or {}).get("state") or {}
        if state.get("authority") != "workspace_file" or state.get("persistence") != "required":
            errors.append(f"{target}: persistent workspace state authority weakened")
        if state.get("conversation_fallback") is not False:
            errors.append(f"{target}: conversation fallback must not replace workspace state")
        if target == "claude_project":
            adapter = contract.get("adapter") or {}
            if adapter.get("embedded_local_tools") is not False:
                errors.append("claude_project: embedded local tools incorrectly assumed")
        # GitHub writes are never assumed: host/integration support is conditional.
        capability = contract.get("capabilities") or {}
        requirements = capability.get("requirements") or {}
        external = requirements.get("external_tools") or {}
        if external.get("level") != "optional":
            errors.append(f"{target}: external tools must remain optional")
        checked.append(target)
    path = archives.get("plugin")
    if path is None or not path.is_file():
        errors.append("plugin: distribution missing")
    else:
        with zipfile.ZipFile(path) as z:
            manifest = json.loads(z.read("plugin.json"))
        if manifest.get("name") != "repository-fixer":
            errors.append("plugin: unexpected manifest identity")
        checked.append("plugin")
    result = {"status": "pass" if not errors else "fail",
              "checked": checked, "errors": errors}
    (root / "RUNTIME-CONTRACT-REPORT.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, required=True)
    args = p.parse_args()
    raise SystemExit(0 if verify(args.project_root)["status"] == "pass" else 1)
