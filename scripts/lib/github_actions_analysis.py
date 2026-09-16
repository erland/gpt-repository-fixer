from __future__ import annotations

import json
import re
from pathlib import PurePosixPath
from typing import Any

import yaml

from scripts.lib.build_test_analysis import analyze_build_test


def _evidence(kind: str, path: str | None, observation: str, related_paths: list[str] | None = None) -> dict:
    item: dict[str, Any] = {"kind": kind, "observation": observation}
    if path:
        item["path"] = path
    if related_paths:
        item["related_paths"] = related_paths
    return item


def _finding(fid: str, classification: str, title: str, summary: str, evidence: list[dict], action: str | None,
             confidence: str = "high", verification: str | None = None) -> dict:
    return {
        "id": fid,
        "area": "github-actions",
        "classification": classification,
        "title": title,
        "summary": summary,
        "evidence": evidence,
        "confidence": confidence,
        "recommended_action": action,
        "decision_required": False,
        "decision_reason": None,
        "verification": verification,
        "notes": [],
    }


def _workflow_paths(files: dict[str, str]) -> list[str]:
    return sorted(
        p for p in files
        if p.startswith(".github/workflows/") and p.lower().endswith((".yml", ".yaml"))
    )


def _parse_yaml(text: str) -> dict[str, Any] | None:
    try:
        data = yaml.load(text, Loader=yaml.BaseLoader)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def _normalize_on(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {str(x) for x in value}
    if isinstance(value, dict):
        return {str(x) for x in value.keys()}
    return set()


def _iter_steps(workflow: dict[str, Any]):
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for step in steps:
            if isinstance(step, dict):
                yield str(job_name), step


def _step_runs(workflow: dict[str, Any]) -> list[tuple[str, str]]:
    result = []
    for job, step in _iter_steps(workflow) or []:
        run = step.get("run")
        if isinstance(run, str):
            result.append((job, run))
    return result


def _step_actions(workflow: dict[str, Any]) -> list[tuple[str, str]]:
    result = []
    for job, step in _iter_steps(workflow) or []:
        uses = step.get("uses")
        if isinstance(uses, str):
            result.append((job, uses))
    return result


def _working_directory(step: dict[str, Any]) -> str:
    wd = step.get("working-directory")
    return str(wd).strip("/") if isinstance(wd, str) else ""


def _run_with_directory(workflow: dict[str, Any]) -> list[tuple[str, str, str]]:
    result = []
    for job, step in _iter_steps(workflow) or []:
        run = step.get("run")
        if isinstance(run, str):
            result.append((job, _working_directory(step), run))
    return result


def _expected_command_tokens(files: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    bt = analyze_build_test(files)
    return {"build": bt.get("build", []), "tests": bt.get("tests", [])}


def _component_matches(component: str, working_dir: str, command: str) -> bool:
    if component in {".", "root", ""}:
        return True
    comp = component.strip("/")
    wd = working_dir.strip("/")
    if wd == comp or wd.startswith(comp + "/"):
        return True
    # Commands that explicitly enter/filter the component also count.
    return bool(re.search(rf"(?:^|[\s'\"]){re.escape(comp)}(?:/|[\s'\"]|$)", command))


def _command_matches(expected: str, actual: str) -> bool:
    expected = expected.strip()
    actual = actual.strip()
    if expected in actual:
        return True
    # npm/pnpm/yarn script commands may be embedded in a larger shell line.
    compact_e = re.sub(r"\s+", " ", expected)
    compact_a = re.sub(r"\s+", " ", actual)
    return compact_e in compact_a


def _runtime_expectations(files: dict[str, str]) -> list[tuple[str, str, str]]:
    expectations: list[tuple[str, str, str]] = []
    java = files.get(".java-version", "").strip()
    if not java:
        for path, text in files.items():
            if PurePosixPath(path).name == "pom.xml":
                m = re.search(r"<(?:maven\.compiler\.release|java\.version|maven\.compiler\.target)>\s*([^<\s]+)", text)
                if m:
                    java = m.group(1)
                    break
    if java:
        expectations.append(("actions/setup-java", java, "java-version"))

    node = files.get(".node-version", "").strip()
    if not node:
        nvm = files.get(".nvmrc", "").strip()
        node = nvm.lstrip("v") if nvm else ""
    if not node:
        for path, text in files.items():
            if PurePosixPath(path).name == "package.json":
                try:
                    obj = json.loads(text)
                except Exception:
                    continue
                engines = obj.get("engines") if isinstance(obj, dict) else None
                if isinstance(engines, dict) and isinstance(engines.get("node"), str):
                    m = re.search(r"(\d+)", engines["node"])
                    if m:
                        node = m.group(1)
                        break
    if node:
        expectations.append(("actions/setup-node", node, "node-version"))

    py = files.get(".python-version", "").strip()
    if py:
        expectations.append(("actions/setup-python", py, "python-version"))
    return expectations


def _extract_setup_versions(workflow: dict[str, Any], action_name: str, key: str) -> list[str]:
    versions = []
    for _, step in _iter_steps(workflow) or []:
        uses = step.get("uses")
        if not isinstance(uses, str) or not uses.startswith(action_name + "@"):
            continue
        with_block = step.get("with")
        if isinstance(with_block, dict) and key in with_block:
            versions.append(str(with_block[key]).strip("'\""))
    return versions


def _major_matches(expected: str, configured: str) -> bool:
    e = re.search(r"(\d+)", expected)
    c = re.search(r"(\d+)", configured)
    return bool(e and c and e.group(1) == c.group(1))


def _referenced_local_paths(command: str) -> set[str]:
    refs: set[str] = set()
    patterns = [
        r"(?:^|\s)(?:\./)?([\w./-]+\.(?:sh|py|js|mjs|cjs|ts))(?=\s|$)",
        r"(?:^|\s)(?:python(?:3)?|bash|sh|node)\s+(?:\./)?([\w./-]+)(?=\s|$)",
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, command):
            refs.add(m.group(1).lstrip("./"))
    return refs


def analyze_github_actions(
    files: dict[str, str],
    *,
    github_ci_expected: bool = True,
    verified_action_majors: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Analyze GitHub Actions coverage conservatively from repository file contents.

    `verified_action_majors` is intentionally injected by the caller. This avoids
    hard-coding claims that a particular action major is current forever.
    """
    workflow_paths = _workflow_paths(files)
    findings: list[dict[str, Any]] = []
    parsed: dict[str, dict[str, Any]] = {}
    idx = 1

    if not workflow_paths:
        if github_ci_expected:
            findings.append(_finding(
                f"RF-GHA-{idx:03d}", "recommended", "GitHub Actions-workflow saknas",
                "Repositoryt saknar workflow för kontinuerlig build/test trots att GitHub CI ingår i granskningsmålet.",
                [_evidence("absence", ".github/workflows/", "Ingen .yml/.yaml-workflow hittades under .github/workflows/.")],
                "Lägg till en minimal GitHub Actions-workflow som bygger och testar relevanta komponenter.",
                verification="Öppna en pull request och verifiera att workflowen kör build och tester framgångsrikt.",
            ))
        return {"workflows": [], "coverage": {"build": [], "tests": []}, "findings": findings}

    for path in workflow_paths:
        wf = _parse_yaml(files[path])
        if wf is None:
            findings.append(_finding(
                f"RF-GHA-{idx:03d}", "must-fix", "Workflow kan inte tolkas som YAML",
                f"{path} kunde inte tolkas som GitHub Actions YAML.",
                [_evidence("file", path, "YAML-parsning misslyckades.")],
                "Korrigera workflowens YAML-syntax innan andra CI-antaganden görs.",
                verification="Validera YAML och låt GitHub Actions läsa workflowen.",
            )); idx += 1
            continue
        parsed[path] = wf

    # Triggers: consider all parseable workflows together.
    trigger_union: set[str] = set()
    for wf in parsed.values():
        trigger_union |= _normalize_on(wf.get("on"))
    missing_triggers = {"pull_request", "push"} - trigger_union
    if missing_triggers:
        findings.append(_finding(
            f"RF-GHA-{idx:03d}", "recommended", "CI saknar relevant Git-trigger",
            "GitHub Actions täcker inte både pull_request och push.",
            [_evidence("configuration", workflow_paths[0], f"Saknade triggers: {', '.join(sorted(missing_triggers))}.", workflow_paths)],
            "Lägg till relevanta push/pull_request-triggers om CI ska verifiera båda flödena.",
            verification="Verifiera en branch-push och en pull request.",
        )); idx += 1

    expected = _expected_command_tokens(files)
    coverage = {"build": [], "tests": []}
    run_steps: list[tuple[str, str, str, str]] = []
    for path, wf in parsed.items():
        for job, wd, run in _run_with_directory(wf):
            run_steps.append((path, job, wd, run))

    for kind in ("build", "tests"):
        for item in expected[kind]:
            matches = []
            for path, job, wd, run in run_steps:
                if _component_matches(item.get("component", "."), wd, run) and _command_matches(item["command"], run):
                    matches.append({"workflow": path, "job": job, "working_directory": wd or ".", "run": run})
            covered = bool(matches)
            coverage[kind].append({
                "component": item.get("component", "."),
                "expected_command": item["command"],
                "covered": covered,
                "matches": matches,
            })
            if not covered:
                label = "build" if kind == "build" else "test"
                classification = "must-fix" if kind == "tests" else "recommended"
                findings.append(_finding(
                    f"RF-GHA-{idx:03d}", classification,
                    f"CI täcker inte komponentens {label}",
                    f"Ingen workflow kör det härledda {label}kommandot `{item['command']}` för komponent `{item.get('component', '.')}`.",
                    [_evidence("cross-file", item.get("source"), f"Förväntat {label}kommando: {item['command']}.", workflow_paths)],
                    f"Lägg till `{item['command']}` i relevant CI-jobb för komponenten.",
                    verification="Kör workflowen på en pull request och verifiera att steget exekveras.",
                )); idx += 1

    # Runtime setup consistency when both repo expectation and setup action exist.
    for action_name, expected_version, key in _runtime_expectations(files):
        configured: list[tuple[str, str]] = []
        for path, wf in parsed.items():
            configured += [(path, v) for v in _extract_setup_versions(wf, action_name, key)]
        if configured and not any(_major_matches(expected_version, version) for _, version in configured):
            findings.append(_finding(
                f"RF-GHA-{idx:03d}", "must-fix", "CI använder inkonsekvent runtime-version",
                f"Repositoryt anger runtime {expected_version}, men {action_name} är konfigurerad med {', '.join(v for _, v in configured)}.",
                [_evidence("cross-file", configured[0][0], f"{action_name} matchar inte repositoryts runtimekrav {expected_version}.", [p for p, _ in configured])],
                "Synkronisera CI-runtime med repositoryts canonical runtime-version.",
                verification="Kör build och tester i GitHub Actions med den synkroniserade versionen.",
            )); idx += 1

    # Package manager mismatch: if repo is unambiguously pnpm/yarn/npm, other install commands are suspicious.
    lock_managers = set()
    for path in files:
        name = PurePosixPath(path).name
        if name == "pnpm-lock.yaml": lock_managers.add("pnpm")
        elif name == "yarn.lock": lock_managers.add("yarn")
        elif name == "package-lock.json": lock_managers.add("npm")
    if len(lock_managers) == 1:
        manager = next(iter(lock_managers))
        bad = []
        for path, job, wd, run in run_steps:
            if manager != "npm" and re.search(r"\bnpm\s+(?:ci|install)\b", run): bad.append((path, job, run))
            if manager != "pnpm" and re.search(r"\bpnpm\s+(?:install|i)\b", run): bad.append((path, job, run))
            if manager != "yarn" and re.search(r"\byarn\s+(?:install)?\b", run): bad.append((path, job, run))
        if bad:
            findings.append(_finding(
                f"RF-GHA-{idx:03d}", "must-fix", "CI använder fel package manager",
                f"Repositoryts lockfil anger {manager}, men workflow använder en annan package manager.",
                [_evidence("cross-file", bad[0][0], f"Workflowkommando: {bad[0][2]}", [p for p in files if PurePosixPath(p).name in {"pnpm-lock.yaml", "yarn.lock", "package-lock.json"}])],
                f"Använd {manager} konsekvent i CI och följ repositoryts lockfil.",
                verification="Kör install, build och tester i CI med repositoryts package manager.",
            )); idx += 1

    # Local script/file references in run steps.
    missing_refs: list[tuple[str, str]] = []
    known_paths = set(files)
    for path, _, wd, run in run_steps:
        for ref in _referenced_local_paths(run):
            candidate = f"{wd}/{ref}".strip("/") if wd else ref
            if candidate not in known_paths and ref not in known_paths:
                missing_refs.append((path, candidate))
    if missing_refs:
        p, ref = missing_refs[0]
        findings.append(_finding(
            f"RF-GHA-{idx:03d}", "must-fix", "Workflow refererar till saknad lokal fil",
            f"Workflowen försöker köra `{ref}`, men filen finns inte i repositoryinventeringen.",
            [_evidence("cross-file", p, f"Refererad lokal fil saknas: {ref}.", [ref])],
            "Korrigera sökvägen eller återställ den avsedda scriptfilen.",
            verification="Kör workflowen från en ren checkout.",
        )); idx += 1

    # Duplicate normalized workflow bodies (comments/whitespace ignored).
    normalized_bodies: dict[str, list[str]] = {}
    for path in workflow_paths:
        body = "\n".join(
            line.strip() for line in files[path].splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        normalized_bodies.setdefault(body, []).append(path)
    for duplicates in normalized_bodies.values():
        if len(duplicates) > 1:
            findings.append(_finding(
                f"RF-GHA-{idx:03d}", "recommended", "Uppenbart duplicerade workflows",
                "Två eller fler workflowfiler har samma effektiva innehåll.",
                [_evidence("cross-file", duplicates[0], "Workflowinnehållet är duplicerat.", duplicates[1:])],
                "Konsolidera duplicerade workflows om de inte är avsiktliga.",
                verification="Verifiera att kvarvarande workflow täcker samma triggers och jobb.",
            )); idx += 1

    # Action major freshness only when caller supplied independently verified current majors.
    if verified_action_majors:
        stale: list[tuple[str, str, int, int]] = []
        for path, wf in parsed.items():
            for _, uses in _step_actions(wf):
                if uses.startswith("./") or "@" not in uses:
                    continue
                action, ref = uses.rsplit("@", 1)
                m = re.fullmatch(r"v(\d+)", ref)
                current = verified_action_majors.get(action)
                if m and current is not None and int(m.group(1)) < int(current):
                    stale.append((path, action, int(m.group(1)), int(current)))
        if stale:
            path, action, actual, current = stale[0]
            findings.append(_finding(
                f"RF-GHA-{idx:03d}", "recommended", "Verifierat äldre action-major används",
                f"{action}@v{actual} är äldre än den separat verifierade aktuella majorversionen v{current}.",
                [_evidence("configuration", path, f"{action}@v{actual}; verifierad aktuell major: v{current}.")],
                f"Granska release notes och uppgradera till {action}@v{current} om kompatibelt.",
                verification="Kör workflowen efter uppgraderingen och kontrollera actionens officiella dokumentation.",
            )); idx += 1

    if parsed and not findings:
        findings.append(_finding(
            "RF-GHA-001", "passed", "GitHub Actions täcker verifieringsbehovet",
            "Analyserade workflows har relevanta triggers och täcker härledda build/test-kommandon utan verifierad konflikt.",
            [_evidence("file", workflow_paths[0], "GitHub Actions-kontrollerna passerade.", workflow_paths[1:])],
            None,
            verification="Fortsätt verifiera workflowkörningar på pull requests och push enligt projektets policy.",
        ))

    workflows = []
    for path, wf in parsed.items():
        workflows.append({
            "path": path,
            "triggers": sorted(_normalize_on(wf.get("on"))),
            "jobs": sorted((wf.get("jobs") or {}).keys()) if isinstance(wf.get("jobs"), dict) else [],
        })
    return {"workflows": workflows, "coverage": coverage, "findings": findings}
