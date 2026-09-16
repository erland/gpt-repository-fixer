#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    import yaml
except Exception as exc:
    raise SystemExit("PyYAML is required") from exc

SUSPICIOUS_SUFFIXES = {".tmp", ".temp", ".bak", ".old"}
SUSPICIOUS_NAMES = {".DS_Store"}
CACHE_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
PLACEHOLDER_MARKERS = {"TODO: placeholder", "PLACEHOLDER", "replace this placeholder"}

PATH_KEYS = {
    "path", "file", "schema", "policy", "model", "template", "script",
    "workflow", "manifest", "canonical", "canonical_root", "root",
    "build_script", "validation_script", "report_template",
    "start_here_template", "delivery_manifest_schema", "manifest_schema",
    "eval_case_schema", "report_schema"
}

def finding(code, severity, message, path=None):
    d = {"code": code, "severity": severity, "message": message}
    if path:
        d["path"] = path
    return d

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def exists_ref(root: Path, value: str) -> bool:
    if any(ch in value for ch in "*?[]"):
        return True
    return (root / value).exists()

def walk_config_paths(obj, prefix=""):
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, str) and k in PATH_KEYS:
                results.append((key, v))
            elif isinstance(v, (dict, list)):
                results.extend(walk_config_paths(v, key))
    elif isinstance(obj, list):
        for idx, v in enumerate(obj):
            if isinstance(v, (dict, list)):
                results.extend(walk_config_paths(v, f"{prefix}[{idx}]"))
    return results

def lint(root: Path) -> dict:
    findings = []
    cfg_path = root / "gpt-project.yaml"
    if not cfg_path.exists():
        return {"result": "fail", "summary": {"errors": 1, "warnings": 0, "findings": 1},
                "findings": [finding("GP001", "error", "Missing gpt-project.yaml")]}

    try:
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"result": "fail", "summary": {"errors": 1, "warnings": 0, "findings": 1},
                "findings": [finding("GP002", "error", f"Invalid gpt-project.yaml: {exc}", "gpt-project.yaml")]}

    instr_ref = cfg.get("instructions", {}).get("canonical")
    if not instr_ref:
        findings.append(finding("GP010", "error", "Canonical instruction is not configured"))
    else:
        instr_path = root / instr_ref
        if not instr_path.exists():
            findings.append(finding("GP011", "error", "Canonical instruction file is missing", instr_ref))
        else:
            text = instr_path.read_text(encoding="utf-8").strip()
            if not text:
                findings.append(finding("GP012", "error", "Canonical instruction is empty", instr_ref))
            for marker in PLACEHOLDER_MARKERS:
                if marker.lower() in text.lower():
                    findings.append(finding("GP013", "warning", f"Placeholder marker found: {marker}", instr_ref))
            custom = cfg.get("runtime", {}).get("custom_gpt", {})
            mode = custom.get("instruction", {}).get("mode")
            max_chars = custom.get("instruction", {}).get("max_characters")
            if mode == "identical" and isinstance(max_chars, int) and len(text) > max_chars:
                findings.append(finding("GP014", "error",
                    f"Identical Custom GPT instruction exceeds limit: {len(text)} > {max_chars}", instr_ref))

    # Small-model/runtime-complexity contract. This is opt-in per project but GPT Byggaren
    # should generate it for new projects. Critical behavior must be directly present in the
    # canonical instruction; supporting files may deepen behavior but not be required to recover it.
    core = cfg.get("instructions", {}).get("core_contract", {})
    if core.get("enabled"):
        if not instr_ref or not (root / instr_ref).exists():
            findings.append(finding("GP500", "error", "Core behavior contract requires a canonical instruction"))
        else:
            canonical_text = (root / instr_ref).read_text(encoding="utf-8")
            required_markers = core.get("required_markers", [])
            if not isinstance(required_markers, list) or not required_markers:
                findings.append(finding("GP501", "warning", "Core behavior contract has no required markers", instr_ref))
            else:
                for required in required_markers:
                    if not isinstance(required, str) or not required.strip():
                        continue
                    if required not in canonical_text:
                        findings.append(finding("GP502", "error",
                            f"Critical behavior marker is missing from canonical instruction: {required}", instr_ref))

        deps = core.get("required_runtime_dependencies", []) or []
        max_hops = core.get("max_required_file_hops", 1)
        if not isinstance(deps, list):
            findings.append(finding("GP503", "error", "required_runtime_dependencies must be a list"))
            deps = []
        if isinstance(max_hops, int) and len(deps) > max_hops:
            findings.append(finding("GP504", "warning",
                f"Core workflow requires {len(deps)} supporting file hops; configured maximum is {max_hops}"))
        for dep in deps:
            if not isinstance(dep, str):
                continue
            normalized = dep.replace("\\", "/").lstrip("./")
            if normalized.startswith("knowledge/") and core.get("knowledge_may_not_be_required_for_core_behavior", True):
                findings.append(finding("GP505", "error",
                    "Critical core behavior may not require a Knowledge file", dep))
            if not exists_ref(root, dep):
                findings.append(finding("GP506", "error", "Required runtime dependency does not exist", dep))

    ignore_symbolic = {"chat_zip", "custom_gpt", "project", "chat", "build", "dist",
                       "knowledge", "scripts", "schemas", "templates", "runtime",
                       "tests", "evals", "research", "src"}
    for key, value in walk_config_paths(cfg):
        if not value or value in ignore_symbolic or value.startswith(("http://", "https://")):
            continue
        if not exists_ref(root, value):
            findings.append(finding("GP100", "error", f"Configured path does not exist ({key})", value))

    for rel in ["README.md", "PROJECT.md", "STATUS.md", "project-status.yaml"]:
        if not (root / rel).exists():
            findings.append(finding("GP110", "error", f"Required project file missing: {rel}", rel))

    kroot_ref = cfg.get("knowledge_architecture", {}).get("canonical_root")
    if kroot_ref:
        kroot = root / kroot_ref
        if not kroot.exists():
            findings.append(finding("GP120", "error", "Canonical Knowledge root is missing", kroot_ref))
        else:
            files = [p for p in kroot.rglob("*") if p.is_file() and p.name != "KNOWLEDGE.md"]
            custom = cfg.get("runtime", {}).get("custom_gpt", {}).get("knowledge", {})
            max_files = custom.get("max_files")
            strategy = custom.get("strategy")
            if isinstance(max_files, int) and len(files) > max_files and strategy == "identical":
                findings.append(finding("GP121", "error",
                    f"Knowledge has {len(files)} files but identical strategy allows max {max_files}", kroot_ref))
            for p in files:
                n = p.name.lower()
                if "policy" in n or "instruction" in n:
                    findings.append(finding("GP122", "warning",
                        "Knowledge filename suggests behavior content; verify layer placement",
                        p.relative_to(root).as_posix()))

    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if p.name in CACHE_NAMES:
            findings.append(finding("GP200", "error", "Cache directory found in source tree", rel.as_posix()))
        is_fixture = len(rel.parts) >= 2 and rel.parts[0] == "tests" and rel.parts[1] == "fixtures"
        if p.is_file() and not is_fixture and (p.suffix.lower() in SUSPICIOUS_SUFFIXES or p.name in SUSPICIOUS_NAMES):
            findings.append(finding("GP201", "warning", "Suspicious temporary/historical file", rel.as_posix()))
        if rel.parts and rel.parts[0] in {"build", "dist"}:
            findings.append(finding("GP202", "warning", "Generated output exists in source tree", rel.as_posix()))

    hashes = {}
    for p in root.rglob("*.md"):
        if any(part in {"build", "dist"} for part in p.parts) or p.stat().st_size == 0:
            continue
        hashes.setdefault(sha256(p), []).append(p)
    for same in hashes.values():
        if len(same) > 1:
            paths = [p.relative_to(root).as_posix() for p in same]
            findings.append(finding("GP210", "warning",
                "Identical Markdown files detected: " + ", ".join(paths)))

    testing = cfg.get("testing", {})
    for key in ["manifest", "manifest_schema", "eval_case_schema"]:
        ref = testing.get(key)
        if ref and not (root / ref).exists():
            findings.append(finding("GP300", "error", f"Testing {key} missing", ref))

    ci = cfg.get("ci", {})
    ci_enabled = ci.get("enabled", ci.get("default", False))
    wf = ci.get("workflow")
    if ci_enabled and not wf:
        findings.append(finding("GP400", "error", "CI is enabled but no workflow is configured"))
    elif wf:
        p = root / wf
        if not p.exists():
            findings.append(finding("GP400", "error", "CI workflow missing", wf))
        else:
            text = p.read_text(encoding="utf-8")
            if "build_distributions.py" not in text:
                findings.append(finding("GP401", "error", "CI does not invoke build_distributions.py", wf))
            if "validate_distributions.py" not in text:
                findings.append(finding("GP402", "error", "CI does not invoke validate_distributions.py", wf))

    release = cfg.get("release", {}).get("github", {})
    release_enabled = release.get("enabled", release.get("default", False))
    wf = release.get("workflow")
    if release_enabled and not wf:
        findings.append(finding("GP410", "error", "GitHub release support is enabled but no workflow is configured"))
    elif wf:
        p = root / wf
        if not p.exists():
            findings.append(finding("GP410", "error", "Release workflow missing", wf))
        else:
            text = p.read_text(encoding="utf-8")
            if "github.event.release.tag_name" not in text:
                findings.append(finding("GP411", "error", "Release workflow does not derive version from release tag", wf))
            if "gh release upload" not in text:
                findings.append(finding("GP412", "error", "Release workflow does not upload built artifacts", wf))

    errors = sum(f["severity"] == "error" for f in findings)
    warnings = sum(f["severity"] == "warning" for f in findings)
    result = "fail" if errors else ("warning" if warnings else "pass")
    return {"result": result,
            "summary": {"errors": errors, "warnings": warnings, "findings": len(findings)},
            "findings": findings}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    try:
        report = lint(Path(args.project_root).resolve())
    except Exception as exc:
        print(f"LINTER INTERNAL ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for f in report["findings"]:
            suffix = f" [{f['path']}]" if "path" in f else ""
            print(f"{f['severity'].upper():7} {f['code']} {f['message']}{suffix}")
        s = report["summary"]
        print(f"Lint result: {report['result'].upper()} (errors={s['errors']}, warnings={s['warnings']})")
    return 1 if report["result"] == "fail" else 0

if __name__ == "__main__":
    raise SystemExit(main())
