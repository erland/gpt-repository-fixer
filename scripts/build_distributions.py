#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

try:
    import yaml
except Exception as exc:
    raise SystemExit("PyYAML is required to run build_distributions.py") from exc


FIXED_ZIP_DATE = (2020, 1, 1, 0, 0, 0)


def load_config(root: Path) -> dict:
    path = root / "gpt-project.yaml"
    if not path.exists():
        raise SystemExit(f"Missing config: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_write_zip(zip_path: Path, root: Path, files: list[Path]) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(files, key=lambda p: p.as_posix()):
            rel = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(rel, FIXED_ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_tree_filtered(src: Path, dst: Path, ignore_names: set[str] | None = None) -> None:
    # Runtime distributions must never contain local Python/cache artifacts.
    ignore_names = set(ignore_names or set()) | {
        "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"
    }
    if not src.exists():
        return
    for p in src.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(src)
        if any(part in ignore_names for part in rel.parts):
            continue
        if p.suffix in {".pyc", ".pyo"}:
            continue
        copy_file(p, dst / rel)


def render_template(text: str, replacements: dict[str, str]) -> str:
    for k, v in replacements.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def build_manifest(root: Path, runtime_id: str, version: str, entrypoint: str | None = None) -> dict:
    files = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.json":
            files.append({
                "path": p.relative_to(root).as_posix(),
                "sha256": sha256(p),
                "size": p.stat().st_size,
            })
    result = {
        "runtime_id": runtime_id,
        "version": version,
        "files": files,
    }
    if entrypoint:
        result["entrypoint"] = entrypoint
    return result


def write_manifest(root: Path, runtime_id: str, version: str, entrypoint: str | None = None) -> None:
    manifest = build_manifest(root, runtime_id, version, entrypoint)
    (root / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_chat(root: Path, cfg: dict, build_root: Path, version: str) -> Path:
    out = build_root / "chat"
    ensure_clean_dir(out)

    assistant = out / "assistant"
    policies = assistant / "policies"
    policies.mkdir(parents=True)

    instr_src = root / cfg["instructions"]["canonical"]
    copy_file(instr_src, assistant / "instructions.md")

    starters_root = root / cfg["structure"]["conversation_starters"]["path"]
    if starters_root.exists():
        starters = [p for p in starters_root.rglob("*") if p.is_file() and p.name != "README.md"]
        if starters:
            combined = "\n\n".join(p.read_text(encoding="utf-8") for p in sorted(starters))
            (assistant / "conversation-starters.md").write_text(combined, encoding="utf-8")

    policy_root = root / cfg["structure"]["runtime_policy"]["path"]
    if policy_root.exists():
        for p in sorted(policy_root.rglob("*.md")):
            copy_file(p, policies / p.name)

    knowledge_root = root / cfg["knowledge_architecture"]["canonical_root"]
    if knowledge_root.exists():
        for p in sorted(knowledge_root.rglob("*")):
            if p.is_file() and p.name != "KNOWLEDGE.md":
                copy_file(p, out / "knowledge" / p.relative_to(knowledge_root))

    # Runtime-relevant schemas/scripts/templates are included for now.
    # Later steps may refine this with explicit per-file role metadata.
    for key in ["schemas", "scripts", "templates"]:
        path = root / cfg["structure"][key]["path"]
        if path.exists():
            copy_tree_filtered(path, out / key, ignore_names={"README.md"})

    template_path = root / cfg["runtime"]["chat_zip"]["start_here_template"]
    template = template_path.read_text(encoding="utf-8")
    start_here = render_template(template, {
        "GPT_NAME": cfg["project"]["name"],
        "VERSION": version,
    })
    (out / "START-HERE.md").write_text(start_here, encoding="utf-8")
    (out / "VERSION").write_text(version + "\n", encoding="utf-8")
    write_manifest(out, cfg["project"]["id"] + "-chat", version, "START-HERE.md")
    return out


def _knowledge_priority_patterns(cfg: dict) -> list[str]:
    return list(cfg.get("knowledge_architecture", {}).get("custom_gpt", {}).get("priority", []) or [])


def _rank_knowledge(files: list[Path], root: Path, cfg: dict) -> list[Path]:
    patterns = _knowledge_priority_patterns(cfg)
    ranked = []
    for p in files:
        rel_from_project = p.relative_to(root).as_posix()
        rank = len(patterns) + 1
        for idx, pattern in enumerate(patterns):
            if fnmatch.fnmatch(rel_from_project, pattern):
                rank = idx
                break
        ranked.append((rank, rel_from_project, p))
    return [p for _, _, p in sorted(ranked)]


def collect_custom_knowledge(root: Path, cfg: dict, target: Path) -> list[Path]:
    knowledge_root = root / cfg["knowledge_architecture"]["canonical_root"]
    files = [p for p in sorted(knowledge_root.rglob("*")) if p.is_file() and p.name != "KNOWLEDGE.md"] if knowledge_root.exists() else []
    max_files = int(cfg["runtime"]["custom_gpt"]["knowledge"]["max_files"])
    strategy = cfg["runtime"]["custom_gpt"]["knowledge"]["strategy"]

    if len(files) <= max_files:
        selected = files
    elif strategy in {"prioritize", "hybrid"}:
        selected = _rank_knowledge(files, root, cfg)[:max_files]
    else:
        raise SystemExit(
            f"Custom GPT Knowledge has {len(files)} files but max is {max_files}; "
            f"strategy {strategy!r} requires explicit consolidation support for overflow."
        )

    copied = []
    for p in selected:
        dst = target / p.relative_to(knowledge_root)
        copy_file(p, dst)
        copied.append(dst)
    return copied


def compile_custom_instruction(text: str, mode: str, max_chars: int, core_markers: list[str]) -> str:
    if mode == "identical":
        compiled = text
    elif mode in {"compressed", "compiled"}:
        # Conservative deterministic compression: preserve wording and headings,
        # remove trailing whitespace and collapse repeated blank lines.
        lines = [line.rstrip() for line in text.splitlines()]
        out = []
        blank = False
        for line in lines:
            if not line.strip():
                if blank:
                    continue
                blank = True
                out.append("")
            else:
                blank = False
                out.append(line)
        compiled = "\n".join(out).strip() + "\n"
    else:
        raise SystemExit(f"Unknown Custom GPT instruction mode: {mode!r}")

    missing = [marker for marker in core_markers if marker not in compiled]
    if missing:
        raise SystemExit(f"Custom GPT instruction compilation removed core behavior markers: {missing}")
    if len(compiled) > max_chars:
        raise SystemExit(
            f"Custom GPT instruction is {len(compiled)} characters after {mode!r} compilation; max is {max_chars}. "
            "Reduce or explicitly mark distribution-specific source material; do not move core behavior to Knowledge."
        )
    return compiled


def build_custom(root: Path, cfg: dict, build_root: Path, version: str) -> Path:
    out = build_root / "custom-gpt"
    ensure_clean_dir(out)
    builder = out / "builder"
    kp = builder / "knowledge-package"
    kp.mkdir(parents=True)

    instr = (root / cfg["instructions"]["canonical"]).read_text(encoding="utf-8")
    max_chars = int(cfg["runtime"]["custom_gpt"]["instruction"]["max_characters"])
    mode = cfg["runtime"]["custom_gpt"]["instruction"]["mode"]
    core_markers = list(cfg.get("instructions", {}).get("core_contract", {}).get("required_markers", []) or [])
    compiled_instr = compile_custom_instruction(instr, mode, max_chars, core_markers)
    (builder / "instructions.md").write_text(compiled_instr, encoding="utf-8")

    starters_root = root / cfg["structure"]["conversation_starters"]["path"]
    starters = [p for p in starters_root.rglob("*") if p.is_file() and p.name != "README.md"] if starters_root.exists() else []
    combined = "\n\n".join(p.read_text(encoding="utf-8") for p in sorted(starters))
    (builder / "conversation-starters.md").write_text(combined, encoding="utf-8")

    capability_profile = {
        "schema_version": 1,
        "capabilities": {
            "web_search": {
                "level": "required",
                "reason": "Behövs för GitHub-länkar och aktuell extern verifiering när sådan ingår i analysen.",
            },
            "data_analysis": {
                "level": "required",
                "reason": "Behövs för ZIP-/filbearbetning, generering av Markdown-filer och uppdaterade repository-ZIP:ar.",
            },
            "file_uploads": {
                "level": "required",
                "reason": "Behövs för repository-ZIP som indata och filartefakter som output.",
            },
            "image_generation": {
                "level": "disabled",
                "reason": "Ingår inte i Repository Fixers kärnflöde.",
            },
            "github_write_integration": {
                "level": "conditional_external",
                "reason": "Krävs bara för branch, commit och PR och måste tillhandahållas av en separat autentiserad GitHub-integration/Action.",
            },
        },
        "fallback": {
            "github_write_unavailable": "read_only_analysis_and_plan",
        },
    }
    cap_lines = [
        "- **Webbsökning: krävs.** För GitHub-länkar och aktuell extern verifiering när den behövs.",
        "- **Dataanalys/Code Interpreter: krävs.** För ZIP- och filbearbetning samt nedladdningsbara rapporter och uppdaterade ZIP-filer.",
        "- **Filuppladdning: krävs i användningsytan.** Repository Fixer ska kunna ta emot repository-ZIP.",
        "- **Bildgenerering: av.** Behövs inte för kärnflödet.",
        "- **GitHub-skrivintegration: villkorad och extern.** Krävs endast för branch/commit/PR.",
    ]
    cap_tpl = (root / cfg["runtime"]["custom_gpt"]["templates"]["capabilities"]).read_text(encoding="utf-8")
    cap_text = render_template(cap_tpl, {"CAPABILITY_RECOMMENDATIONS": "\n".join(cap_lines)})
    (builder / "capabilities.md").write_text(cap_text, encoding="utf-8")
    (builder / "capabilities.json").write_text(
        json.dumps(capability_profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    copied_knowledge = collect_custom_knowledge(root, cfg, kp)

    knowledge_root = root / cfg["knowledge_architecture"]["canonical_root"]
    canonical_knowledge = [p for p in sorted(knowledge_root.rglob("*")) if p.is_file() and p.name != "KNOWLEDGE.md"] if knowledge_root.exists() else []
    selected_rel = [p.relative_to(kp).as_posix() for p in copied_knowledge]
    selected_set = set(selected_rel)
    excluded_rel = [p.relative_to(knowledge_root).as_posix() for p in canonical_knowledge if p.relative_to(knowledge_root).as_posix() not in selected_set]
    compilation_report = {
        "instruction": {
            "mode": mode,
            "canonical_characters": len(instr),
            "compiled_characters": len(compiled_instr),
            "max_characters": max_chars,
            "core_markers_verified": len(core_markers),
        },
        "knowledge": {
            "strategy": cfg["runtime"]["custom_gpt"]["knowledge"]["strategy"],
            "canonical_files": len(canonical_knowledge),
            "selected_files": len(copied_knowledge),
            "max_files": int(cfg["runtime"]["custom_gpt"]["knowledge"]["max_files"]),
            "priority_patterns": _knowledge_priority_patterns(cfg),
            "selected": selected_rel,
            "excluded": excluded_rel,
        },
    }
    (builder / "compilation-report.json").write_text(json.dumps(compilation_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    readme_tpl = (root / cfg["runtime"]["custom_gpt"]["templates"]["readme"]).read_text(encoding="utf-8")
    (out / "README.md").write_text(
        render_template(readme_tpl, {"GPT_NAME": cfg["project"]["name"], "VERSION": version}),
        encoding="utf-8",
    )

    compat_tpl = (root / cfg["runtime"]["custom_gpt"]["templates"]["compatibility"]).read_text(encoding="utf-8")
    parity_table = """| Funktion | Chat ZIP | Custom GPT | Kommentar |
| --- | --- | --- | --- |
| Canonical analysbeteende | Fullt | Fullt | Samma canonical instruktion och Knowledge-regler. |
| ZIP-analys | Fullt | Fullt med Dataanalys | Custom GPT behöver kunna läsa/skriva filer och arkiv. |
| Rapport + fix-plan som filer | Fullt | Fullt med Dataanalys | Samma artefaktnamn och semantik. |
| Portabel `.repository-fixer/`-progress | Fullt | Fullt vid ZIP-arbete | State ligger i repositoryt, inte i plattformens minne. |
| GitHub public/read | Fullt när web/läsåtkomst finns | Fullt när web/läsåtkomst finns | Samma read-only fallback. |
| GitHub branch/commit/PR | Miljöberoende | Villkorat | Kräver separat autentiserad GitHub-skrivintegration. |
| Deterministiska hjälpscript | Medföljer runtime | Medföljer inte som körbar runtime | Custom GPT följer motsvarande kontrakt via Instructions + Knowledge. |
| Slutverifiering | Fullt | Fullt | Ny analys av faktiskt slutläge krävs i båda. |"""
    reduced = (
        "- GitHub-skrivflödet är villkorat: utan separat autentiserad skrivintegration stannar Custom GPT i read-only-läge.\n"
        "- Custom GPT-paketet innehåller inte de deterministiska Python-hjälpscripten som en exekverbar runtime; Builder-versionen använder Instructions + Knowledge och plattformens Dataanalys där filbearbetning behövs."
    )
    missing = "Inga kärnfunktioner saknas när Webbsökning, Dataanalys/filhantering och vid behov GitHub-skrivintegration finns tillgängliga."
    compat = render_template(compat_tpl, {
        "GPT_NAME": cfg["project"]["name"],
        "RUNTIME_RECOMMENDATION": "Aktivera Webbsökning och Dataanalys/Code Interpreter. Lägg endast till GitHub-skrivintegration om branch/commit/PR ska kunna genomföras.",
        "PARITY_TABLE": parity_table,
        "REDUCED_FEATURES": reduced,
        "MISSING_FEATURES": missing,
    })
    (out / "COMPATIBILITY.md").write_text(compat, encoding="utf-8")
    (out / "VERSION").write_text(version + "\n", encoding="utf-8")

    write_manifest(out, cfg["project"]["id"] + "-custom-gpt", version)
    return out



def opencode_runtime_contract(cfg: dict) -> dict:
    return {
        "schema_version": 1,
        "runtime_id": "opencode",
        "capabilities": cfg.get("capabilities", {}),
        "artifacts": cfg.get("artifacts", {}),
        "workspace_state": cfg.get("workspace_state", {}),
        "tools": cfg.get("tools", {}),
        "adapter": {
            "mode": "opencode_workspace",
            "instructions": "AGENTS.md",
            "workspace_first": True,
            "skills_included": True,
            "tool_integration": "host_tools",
        },
    }


def build_opencode(root: Path, cfg: dict, build_root: Path, version: str) -> Path:
    out = build_root / "opencode"
    ensure_clean_dir(out)
    runtime_cfg = cfg["runtime"]["opencode"]

    canonical = (root / cfg["instructions"]["canonical"]).read_text(encoding="utf-8")
    agents_path = out / runtime_cfg["layout"]["instructions"]
    agents_path.write_text(
        canonical.rstrip()
        + "\n\n## OpenCode adapter\n\n"
        + "- Arbeta i aktuellt workspace och följ den strukturerade statusen före chattminne.\n"
        + "- Använd OpenCodes fil-, shell- och kodverktyg för verifiering när de är tillgängliga.\n"
        + "- Kör ett avgränsat mål åt gången och korrigera failing verifiering före progression.\n",
        encoding="utf-8",
    )

    knowledge_root = root / cfg["knowledge_architecture"]["canonical_root"]
    knowledge_target = out / runtime_cfg["layout"]["knowledge"]
    if knowledge_root.exists():
        for p in sorted(knowledge_root.rglob("*")):
            if p.is_file() and p.name != "KNOWLEDGE.md":
                copy_file(p, knowledge_target / p.relative_to(knowledge_root))

    skills_dir = out / runtime_cfg["skills"].get("directory", ".opencode/skills")
    skill_dir = skills_dir / cfg["project"]["id"]
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        f"name: {cfg['project']['id']}\n"
        f"description: {cfg['project']['description'].strip()}\n"
        "compatibility: opencode\n"
        "---\n\n"
        "## Purpose\n\n"
        "Använd Repository Fixers canonical arbetsflöde för analys, planering, stegvis korrigering och verifiering.\n\n"
        "## Workflow\n\n"
        "- Läs aktuell repository-status före progression.\n"
        "- Analysera före ändring.\n"
        "- Utför ett avgränsat plansteg i taget.\n"
        "- Verifiera efter ändring och korrigera failing resultat före nästa steg.\n",
        encoding="utf-8",
    )

    config_path = out / runtime_cfg["layout"]["config"]
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "$schema": "https://opencode.ai/config.json",
                "permission": {
                    "skill": {"*": "allow"},
                    "bash": "ask",
                    "edit": "ask",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    contract_path = out / runtime_cfg["layout"]["runtime_contract"]
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(
        json.dumps(opencode_runtime_contract(cfg), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    readme_tpl = (root / runtime_cfg["templates"]["readme"]).read_text(encoding="utf-8")
    (out / "README.md").write_text(
        render_template(readme_tpl, {
            "GPT_NAME": cfg["project"]["name"],
            "VERSION": version,
        }),
        encoding="utf-8",
    )
    (out / "VERSION").write_text(version + "\n", encoding="utf-8")
    write_manifest(out, cfg["project"]["id"] + "-opencode", version, "AGENTS.md")
    return out


def project_files(root: Path) -> list[Path]:
    excluded_top = {"build", "dist", ".git"}
    result = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if rel.parts and rel.parts[0] in excluded_top:
            continue
        if "__pycache__" in rel.parts or ".pytest_cache" in rel.parts:
            continue
        result.append(p)
    return result


def write_checksums(dist: Path) -> None:
    lines = []
    for p in sorted(dist.glob("*.zip")):
        lines.append(f"{sha256(p)}  {p.name}")
    (dist / "SHA256SUMS.txt").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def write_delivery_manifest(dist: Path, cfg: dict, version: str) -> None:
    artifacts = []
    for p in sorted(dist.iterdir()):
        if not p.is_file() or p.name in {"DELIVERY-MANIFEST.json"}:
            continue
        if p.suffix == ".zip":
            if "-project" in p.name:
                artifact_type = "project_zip"
            elif "-chat-" in p.name:
                artifact_type = "chat_zip"
            elif "-custom-gpt-" in p.name:
                artifact_type = "custom_gpt_zip"
            elif "-opencode-" in p.name:
                artifact_type = "opencode_zip"
            else:
                artifact_type = "zip"
        elif p.name == "SHA256SUMS.txt":
            artifact_type = "checksums"
        else:
            artifact_type = "file"
        artifacts.append({
            "type": artifact_type,
            "file": p.name,
            "sha256": sha256(p),
            "size": p.stat().st_size,
        })

    payload = {
        "project": cfg["project"]["id"],
        "project_name": cfg["project"]["name"],
        "version": version,
        "runtime_strategy": "peer_distributions",
        "custom_gpt_enabled": bool(cfg["runtime"]["custom_gpt"]["enabled"]),
        "artifacts": artifacts,
    }
    (dist / "DELIVERY-MANIFEST.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--version", default="0.0.0-dev")
    parser.add_argument("--targets", default="project,chat,custom-gpt,opencode")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    cfg = load_config(root)
    build_root = root / "build"
    dist = root / "dist"
    build_root.mkdir(exist_ok=True)
    dist.mkdir(exist_ok=True)

    targets = {t.strip() for t in args.targets.split(",") if t.strip()}
    project_id = cfg["project"]["id"]
    version = args.version

    if "chat" in targets:
        chat_root = build_chat(root, cfg, build_root, version)
        chat_zip = dist / f"{project_id}-chat-{version}.zip"
        stable_write_zip(chat_zip, chat_root, [p for p in chat_root.rglob("*") if p.is_file()])

    if "custom-gpt" in targets and cfg["runtime"]["custom_gpt"]["enabled"]:
        custom_root = build_custom(root, cfg, build_root, version)
        custom_zip = dist / f"{project_id}-custom-gpt-{version}.zip"
        stable_write_zip(custom_zip, custom_root, [p for p in custom_root.rglob("*") if p.is_file()])

    if "opencode" in targets and cfg.get("runtime", {}).get("opencode", {}).get("enabled"):
        opencode_root = build_opencode(root, cfg, build_root, version)
        opencode_zip = dist / f"{project_id}-opencode-{version}.zip"
        stable_write_zip(opencode_zip, opencode_root, [p for p in opencode_root.rglob("*") if p.is_file()])

    if "project" in targets:
        project_zip = dist / f"{project_id}-project-{version}.zip"
        stable_write_zip(project_zip, root, project_files(root))

    write_checksums(dist)
    write_delivery_manifest(dist, cfg, version)

    print(f"Build complete: {dist}")
    for p in sorted(dist.iterdir()):
        if p.is_file():
            print(p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
