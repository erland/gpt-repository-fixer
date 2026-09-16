from __future__ import annotations

import json
import re
from pathlib import PurePosixPath


def _evidence(kind: str, path: str | None, observation: str, related_paths: list[str] | None = None) -> dict:
    item = {"kind": kind, "observation": observation}
    if path:
        item["path"] = path
    if related_paths:
        item["related_paths"] = related_paths
    return item


def _finding(fid: str, area: str, classification: str, title: str, summary: str,
             evidence: list[dict], action: str | None, confidence: str = "high",
             verification: str | None = None, notes: list[str] | None = None) -> dict:
    return {
        "id": fid,
        "area": area,
        "classification": classification,
        "title": title,
        "summary": summary,
        "evidence": evidence,
        "confidence": confidence,
        "recommended_action": action,
        "decision_required": False,
        "decision_reason": None,
        "verification": verification,
        "notes": notes or [],
    }


def _first(files: dict[str, str], basename: str) -> tuple[str | None, str]:
    candidates = [(p, t) for p, t in files.items() if PurePosixPath(p).name == basename]
    if not candidates:
        return None, ""
    candidates.sort(key=lambda x: (x[0].count("/"), x[0]))
    return candidates[0]


def _package_jsons(files: dict[str, str]) -> list[tuple[str, dict]]:
    result = []
    for path, text in sorted(files.items()):
        if PurePosixPath(path).name != "package.json":
            continue
        try:
            value = json.loads(text)
            result.append((path, value if isinstance(value, dict) else {}))
        except json.JSONDecodeError:
            result.append((path, {}))
    return result


def _package_json(files: dict[str, str]) -> tuple[str | None, dict]:
    entries = _package_jsons(files)
    return entries[0] if entries else (None, {})


def _node_pm(files: dict[str, str], package_path: str, package: dict) -> tuple[str | None, str | None]:
    pm_decl = package.get("packageManager")
    if isinstance(pm_decl, str):
        m = re.match(r"(pnpm|npm|yarn)@", pm_decl)
        if m:
            return m.group(1), package_path
    parent = PurePosixPath(package_path).parent
    candidates = [("pnpm-lock.yaml", "pnpm"), ("package-lock.json", "npm"), ("yarn.lock", "yarn")]
    for lock, pm in candidates:
        local = (parent / lock).as_posix() if parent.as_posix() != "." else lock
        if local in files:
            return pm, local
    for lock, pm in candidates:
        if lock in files:
            return pm, lock
    return None, None


def _has_tests(files: dict[str, str]) -> bool:
    for path in files:
        p = path.lower()
        name = PurePosixPath(p).name
        if "/tests/" in f"/{p}" or "/test/" in f"/{p}" or name.startswith("test_"):
            return True
        if re.search(r"\.(?:test|spec)\.(?:js|jsx|ts|tsx)$", p):
            return True
    return False


def _commands(files: dict[str, str]) -> tuple[list[dict], list[dict]]:
    builds: list[dict] = []
    tests: list[dict] = []
    for package_path, package in _package_jsons(files):
        scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
        pm, pm_evidence = _node_pm(files, package_path, package)
        prefix = pm or "npm"
        component = PurePosixPath(package_path).parent.as_posix()
        if "build" in scripts:
            cmd = f"{prefix} run build" if prefix != "yarn" else "yarn build"
            builds.append({"component": component, "command": cmd, "source": package_path, "kind": "node", **({"package_manager_source": pm_evidence} if pm_evidence else {})})
        if "test" in scripts:
            cmd = f"{prefix} test" if prefix in {"npm", "pnpm"} else "yarn test"
            tests.append({"component": component, "command": cmd, "source": package_path, "kind": "node", **({"package_manager_source": pm_evidence} if pm_evidence else {})})

    for pom_path in sorted(p for p in files if PurePosixPath(p).name == "pom.xml"):
        parent = PurePosixPath(pom_path).parent
        local_wrapper = (parent / "mvnw").as_posix() if parent.as_posix() != "." else "mvnw"
        base = "./mvnw" if local_wrapper in files or "mvnw" in files else "mvn"
        builds.append({"component": parent.as_posix(), "command": f"{base} -DskipTests package", "source": pom_path, "kind": "maven"})
        tests.append({"component": parent.as_posix(), "command": f"{base} test", "source": pom_path, "kind": "maven"})

    for gradle_path in sorted(p for p in files if PurePosixPath(p).name in {"build.gradle", "build.gradle.kts"}):
        parent = PurePosixPath(gradle_path).parent
        local_wrapper = (parent / "gradlew").as_posix() if parent.as_posix() != "." else "gradlew"
        base = "./gradlew" if local_wrapper in files or "gradlew" in files else "gradle"
        builds.append({"component": parent.as_posix(), "command": f"{base} assemble", "source": gradle_path, "kind": "gradle"})
        tests.append({"component": parent.as_posix(), "command": f"{base} test", "source": gradle_path, "kind": "gradle"})

    pyproject_path, pyproject = _first(files, "pyproject.toml")
    req_path, _ = _first(files, "requirements.txt")
    if pyproject_path or req_path:
        source = pyproject_path or req_path
        if pyproject_path and re.search(r"(?m)^\s*build-backend\s*=", pyproject):
            builds.append({"component": PurePosixPath(source).parent.as_posix(), "command": "python -m build", "source": source, "kind": "python"})
        if _has_tests(files) or (pyproject_path and re.search(r"(?i)pytest", pyproject)):
            tests.append({"component": PurePosixPath(source).parent.as_posix(), "command": "python -m pytest", "source": source, "kind": "python"})

    go_path, _ = _first(files, "go.mod")
    if go_path:
        builds.append({"component": PurePosixPath(go_path).parent.as_posix(), "command": "go build ./...", "source": go_path, "kind": "go"})
        tests.append({"component": PurePosixPath(go_path).parent.as_posix(), "command": "go test ./...", "source": go_path, "kind": "go"})

    cargo_path, _ = _first(files, "Cargo.toml")
    if cargo_path:
        builds.append({"component": PurePosixPath(cargo_path).parent.as_posix(), "command": "cargo build", "source": cargo_path, "kind": "rust"})
        tests.append({"component": PurePosixPath(cargo_path).parent.as_posix(), "command": "cargo test", "source": cargo_path, "kind": "rust"})

    return builds, tests


def _runtime_mismatches(files: dict[str, str]) -> list[dict]:
    out: list[dict] = []
    pom_path, pom = _first(files, "pom.xml")
    java_path, java_file = _first(files, ".java-version")
    if pom_path and java_path:
        m = re.search(r"<(?:maven\.compiler\.release|maven\.compiler\.source|java\.version)>\s*(\d+)\s*</", pom, re.I)
        jf = re.search(r"(\d+)", java_file)
        if m and jf and m.group(1) != jf.group(1):
            out.append({"runtime": "Java", "expected": m.group(1), "actual": jf.group(1), "paths": [pom_path, java_path]})

    package_path, package = _package_json(files)
    nvm_path, nvm = _first(files, ".nvmrc")
    engines = package.get("engines") if isinstance(package.get("engines"), dict) else {}
    node_req = engines.get("node") if isinstance(engines, dict) else None
    if package_path and nvm_path and isinstance(node_req, str):
        req_nums = re.findall(r"\d+", node_req)
        nvm_num = re.search(r"\d+", nvm)
        if req_nums and nvm_num and nvm_num.group(0) not in req_nums:
            out.append({"runtime": "Node.js", "expected": node_req, "actual": nvm_num.group(0), "paths": [package_path, nvm_path]})
    return out


def _status_for(command: str, execution_results: dict[str, dict] | None, component: str = ".") -> dict:
    qualified = f"{component}::{command}"
    if not execution_results or (qualified not in execution_results and command not in execution_results):
        return {"status": "not-verified", "reason": "Kommandot har inte körts i aktuell exekveringsmiljö."}
    result = execution_results.get(qualified, execution_results.get(command, {}))
    if result.get("not_supported") or result.get("executed") is False:
        return {"status": "not-verified", "reason": result.get("reason") or "Kommandot kunde inte köras i aktuell exekveringsmiljö."}
    code = result.get("exit_code")
    if code == 0:
        return {"status": "verified", "exit_code": 0}
    if isinstance(code, int):
        return {"status": "failing", "exit_code": code, "summary": result.get("summary") or "Kommandot avslutades med fel."}
    return {"status": "not-verified", "reason": result.get("reason") or "Körresultatet saknar verifierbar exit-kod."}


def analyze_build_test(files: dict[str, str], execution_results: dict[str, dict] | None = None) -> dict:
    """Analyze build/test structure and optional execution results.

    The function never treats lack of execution capability as a failure. Callers may
    pass results keyed by exact discovered command. Each result may contain
    `exit_code`, or `executed: false`/`not_supported: true` plus a reason.
    """
    builds, tests = _commands(files)
    findings: list[dict] = []
    idx_build = idx_test = idx_versions = 1

    package_entries = _package_jsons(files)
    for package_path, package in package_entries:
        scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
        component = PurePosixPath(package_path).parent.as_posix()
        component_prefix = "" if component == "." else component.rstrip("/") + "/"
        component_tests = [p for p in files if p.startswith(component_prefix) and re.search(r"(?:^|/)(?:test|tests)/|\.(?:test|spec)\.(?:js|jsx|ts|tsx)$", p.lower())]
        if "build" not in scripts:
            findings.append(_finding(
                f"RF-BUILD-{idx_build:03d}", "build", "recommended",
                "Node-projekt saknar explicit build-script",
                f"{package_path} saknar ett standardiserat build-script; det gör lokal verifiering och CI mindre förutsägbar.",
                [_evidence("configuration", package_path, "package.json innehåller inget scripts.build.")],
                "Överväg att lägga till ett build-script om komponenten faktiskt har ett byggsteg.",
                "medium", "Verifiera att det valda build-kommandot fungerar från en ren checkout.",
            )); idx_build += 1
        if component_tests and "test" not in scripts:
            findings.append(_finding(
                f"RF-TESTS-{idx_test:03d}", "tests", "must-fix",
                "Tester finns men package.json saknar test-script",
                f"{package_path} hör till en komponent med testfiler men saknar ett standardiserat test-script.",
                [_evidence("cross-file", package_path, "Testfiler hittades men scripts.test saknas.", sorted(component_tests)[:10])],
                "Lägg till ett test-script som kör komponentens faktiska testverktyg.",
                verification="Kör det nya testkommandot från komponentens rena checkout/workspace.",
            )); idx_test += 1

    for mismatch in _runtime_mismatches(files):
        findings.append(_finding(
            f"RF-VERSIONS-{idx_versions:03d}", "versions", "must-fix",
            f"Motstridiga {mismatch['runtime']}-versioner",
            f"Repositoryts versionsfiler anger olika {mismatch['runtime']}-krav ({mismatch['expected']} respektive {mismatch['actual']}).",
            [_evidence("cross-file", mismatch["paths"][0], "Runtime-versionerna är inkonsekventa.", mismatch["paths"][1:])],
            "Bestäm vilken runtime-version som är canonical och synkronisera versionsfilerna.",
            verification="Kör build och tester med den dokumenterade canonical-versionen.",
        )); idx_versions += 1

    build_checks = []
    test_checks = []
    for item in builds:
        status = _status_for(item["command"], execution_results, item["component"])
        build_checks.append({**item, **status})
        if status["status"] == "failing":
            findings.append(_finding(
                f"RF-BUILD-{idx_build:03d}", "build", "must-fix", "Build verifierades som felande",
                f"Build-kommandot `{item['command']}` kördes och misslyckades.",
                [_evidence("command", item["source"], f"{item['command']} gav exit-kod {status.get('exit_code')}.")],
                "Analysera den konkreta build-orsaken och lägg en avgränsad korrigering i fix-planen; refaktorera inte godtyckligt.",
                verification=f"Kör `{item['command']}` igen efter korrigeringen.",
            )); idx_build += 1
        elif status["status"] == "verified":
            findings.append(_finding(
                f"RF-BUILD-{idx_build:03d}", "build", "passed", "Build verifierad",
                f"Build-kommandot `{item['command']}` kördes med exit-kod 0.",
                [_evidence("command", item["source"], f"{item['command']} passerade med exit-kod 0.")],
                None, verification=f"Kör `{item['command']}` vid relevanta framtida ändringar.",
            )); idx_build += 1

    for item in tests:
        status = _status_for(item["command"], execution_results, item["component"])
        test_checks.append({**item, **status})
        if status["status"] == "failing":
            findings.append(_finding(
                f"RF-TESTS-{idx_test:03d}", "tests", "must-fix", "Tester verifierades som felande",
                f"Testkommandot `{item['command']}` kördes och misslyckades.",
                [_evidence("command", item["source"], f"{item['command']} gav exit-kod {status.get('exit_code')}.")],
                "Analysera det konkreta testfelet och planera minsta nödvändiga korrigering; ändra inte tester eller produktionskod godtyckligt för att få grönt.",
                verification=f"Kör `{item['command']}` igen efter korrigeringen.",
            )); idx_test += 1
        elif status["status"] == "verified":
            findings.append(_finding(
                f"RF-TESTS-{idx_test:03d}", "tests", "passed", "Tester verifierade",
                f"Testkommandot `{item['command']}` kördes med exit-kod 0.",
                [_evidence("command", item["source"], f"{item['command']} passerade med exit-kod 0.")],
                None, verification=f"Kör `{item['command']}` vid relevanta framtida ändringar.",
            )); idx_test += 1

    if not builds and not tests:
        findings.append(_finding(
            "RF-BUILD-001", "build", "consider", "Ingen standardiserad build/test-struktur identifierades",
            "Repositoryt innehåller ingen build- eller testkonfiguration som Repository Fixer säkert kan härleda ett standardkommando från.",
            [_evidence("absence", None, "Inga stödda buildmanifest eller testkommandon identifierades.")],
            "Kontrollera om repositoryt avsiktligt saknar build/test eller om projektspecifika instruktioner behöver dokumenteras.",
            "medium", "Verifiera mot projektets faktiska utvecklings- och leveransflöde.",
        ))

    return {
        "build": build_checks,
        "tests": test_checks,
        "runtime_mismatches": _runtime_mismatches(files),
        "findings": findings,
    }
