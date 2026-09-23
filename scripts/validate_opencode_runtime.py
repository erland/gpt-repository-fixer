#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def validate_runtime(root: Path) -> list[str]:
    errors: list[str] = []
    required = [
        root / "AGENTS.md",
        root / "opencode.json",
        root / ".opencode" / "runtime-contract.json",
        root / "README.md",
        root / "VERSION",
        root / "MANIFEST.json",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"Missing required file: {path.relative_to(root)}")

    skills = root / ".opencode" / "skills"
    if not skills.exists() or not any(p.name == "SKILL.md" for p in skills.rglob("SKILL.md")):
        errors.append("Missing OpenCode SKILL.md")

    contract = root / ".opencode" / "runtime-contract.json"
    if contract.exists():
        try:
            payload = json.loads(contract.read_text(encoding="utf-8"))
            if payload.get("runtime_id") != "opencode":
                errors.append("runtime-contract.json runtime_id must be opencode")
            if payload.get("adapter", {}).get("mode") != "opencode_workspace":
                errors.append("runtime-contract.json adapter mode must be opencode_workspace")
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid runtime-contract.json: {exc}")

    return errors


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "build/opencode").resolve()
    errors = validate_runtime(root)
    if errors:
        print("OPENCODE RUNTIME: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("OPENCODE RUNTIME: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
