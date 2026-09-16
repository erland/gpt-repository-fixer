from __future__ import annotations

import re
from pathlib import PurePosixPath


def _evidence(kind: str, path: str | None, observation: str, related_paths: list[str] | None = None) -> dict:
    item = {"kind": kind, "observation": observation}
    if path:
        item["path"] = path
    if related_paths:
        item["related_paths"] = related_paths
    return item


def _finding(fid: str, classification: str, title: str, summary: str, evidence: list[dict],
             action: str | None, confidence: str = "high", verification: str = "Granska relevanta filer igen.") -> dict:
    return {
        "id": fid,
        "area": "readme",
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


def _find_readme(files: dict[str, str]) -> tuple[str | None, str]:
    candidates = []
    for path, text in files.items():
        name = PurePosixPath(path).name.lower()
        if name in {"readme.md", "readme.markdown"}:
            candidates.append((path, text))
    if not candidates:
        return None, ""
    candidates.sort(key=lambda x: (x[0].count("/"), x[0].lower()))
    return candidates[0]


def _package_managers(files: dict[str, str]) -> list[tuple[str, str]]:
    lockfiles = {
        "pnpm-lock.yaml": "pnpm",
        "package-lock.json": "npm",
        "yarn.lock": "yarn",
    }
    found = []
    for path in files:
        base = PurePosixPath(path).name
        if base in lockfiles:
            found.append((lockfiles[base], path))
    return found


def _readme_package_commands(text: str) -> set[str]:
    commands = set()
    for pm in ("npm", "pnpm", "yarn"):
        if re.search(rf"(?mi)(?:^|[`$>\s]){pm}\s+(?:install|i|run|test|build|dev|start)\b", text):
            commands.add(pm)
    return commands


def _java_version(files: dict[str, str]) -> tuple[str | None, str | None]:
    for path, text in files.items():
        if PurePosixPath(path).name != "pom.xml":
            continue
        patterns = [
            r"<maven\.compiler\.release>\s*(\d+)\s*</maven\.compiler\.release>",
            r"<maven\.compiler\.source>\s*(\d+)\s*</maven\.compiler\.source>",
            r"<java\.version>\s*(\d+)\s*</java\.version>",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.I)
            if m:
                return m.group(1), path
    for path, text in files.items():
        if PurePosixPath(path).name in {"build.gradle", "build.gradle.kts"}:
            m = re.search(r"JavaLanguageVersion\.of\((\d+)\)", text)
            if not m:
                m = re.search(r"sourceCompatibility\s*=\s*(?:JavaVersion\.VERSION_)?(\d+)", text)
            if m:
                return m.group(1), path
    return None, None


def _readme_java_versions(text: str) -> set[str]:
    versions = set()
    patterns = [
        r"(?i)\b(?:java|jdk)\s*(?:version\s*)?(?:>=?\s*)?(\d{1,2})\b",
        r"(?i)\b(?:requires?|kräver)\s+(?:java|jdk)\s*(\d{1,2})\b",
    ]
    for p in patterns:
        versions.update(re.findall(p, text))
    return versions


def _configured_ports(files: dict[str, str]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for path, text in files.items():
        base = PurePosixPath(path).name
        if base in {"application.properties", "application.yaml", "application.yml"}:
            for pattern in [
                r"(?m)^\s*quarkus\.http\.port\s*[=:]\s*(\d{2,5})\s*$",
                r"(?m)^\s*server\.port\s*[=:]\s*(\d{2,5})\s*$",
                r"(?m)^\s*port\s*:\s*(\d{2,5})\s*$",
            ]:
                m = re.search(pattern, text)
                if m:
                    found.append((m.group(1), path))
        if base in {"compose.yaml", "compose.yml", "docker-compose.yml", "docker-compose.yaml"}:
            for host, container in re.findall(r"['\"]?(\d{2,5}):(\d{2,5})['\"]?", text):
                found.append((host, path))
    # unique, stable
    seen = set()
    result = []
    for port, path in found:
        if (port, path) not in seen:
            seen.add((port, path)); result.append((port, path))
    return result


def _readme_localhost_ports(text: str) -> set[str]:
    return set(re.findall(r"(?i)(?:localhost|127\.0\.0\.1):([0-9]{2,5})", text))


def _has_any_command_block(text: str) -> bool:
    if re.search(r"```(?:bash|sh|shell|console|powershell)?\s*\n[^`]+```", text, re.I | re.S):
        return True
    return bool(re.search(r"(?mi)^\s*(?:\$\s*)?(?:npm|pnpm|yarn|mvnw?|gradlew?|python|pip|go|cargo|docker)\b", text))


def _buildable(files: dict[str, str]) -> bool:
    bases = {PurePosixPath(p).name for p in files}
    return bool(bases & {"package.json", "pom.xml", "build.gradle", "build.gradle.kts", "pyproject.toml", "go.mod", "Cargo.toml"})


def _has_tests(files: dict[str, str]) -> bool:
    for path in files:
        p = path.lower()
        if "/test/" in f"/{p}" or "/tests/" in f"/{p}" or PurePosixPath(p).name.startswith("test_"):
            return True
    package = next((text for path, text in files.items() if PurePosixPath(path).name == "package.json"), "")
    return bool(re.search(r'"test"\s*:', package))


def _readme_mentions_test(text: str) -> bool:
    return bool(re.search(r"(?i)\b(test|tests|testing|tester|testning)\b", text))


def analyze_readme(files: dict[str, str]) -> list[dict]:
    """Return conservative README findings from repository file contents.

    `files` maps repository-relative POSIX paths to UTF-8 text. Binary files should
    simply be omitted by the caller. The analyzer only emits hard inconsistencies
    when repository files provide a reasonably authoritative counterpart.
    """
    findings: list[dict] = []
    readme_path, readme = _find_readme(files)

    if readme_path is None:
        return [_finding(
            "RF-README-001", "must-fix", "README saknas",
            "Repositoryt saknar en README på repositoryts toppnivå eller närmaste motsvarande plats.",
            [_evidence("absence", None, "Ingen README.md eller README.markdown hittades i repositoryt.")],
            "Skapa en README som beskriver projektets syfte och centrala användningsinstruktioner.",
            verification="Kontrollera att README finns och stämmer mot build- och runtimekonfigurationen.",
        )]

    idx = 1
    def emit(classification: str, title: str, summary: str, evidence: list[dict], action: str | None,
             confidence: str = "high", verification: str = "Jämför README med repositoryts faktiska konfiguration."):
        nonlocal idx
        findings.append(_finding(f"RF-README-{idx:03d}", classification, title, summary, evidence, action, confidence, verification))
        idx += 1

    package_managers = _package_managers(files)
    pm_names = {name for name, _ in package_managers}
    readme_pms = _readme_package_commands(readme)
    if len(pm_names) == 1:
        expected = next(iter(pm_names))
        wrong = sorted(readme_pms - {expected})
        if wrong:
            lock_path = next(path for name, path in package_managers if name == expected)
            emit(
                "must-fix", "README använder fel package manager",
                f"README visar kommandon för {', '.join(wrong)}, medan repositoryts lockfil anger {expected}.",
                [_evidence("cross-file", readme_path,
                           f"README innehåller {', '.join(wrong)}-kommandon men repositoryt har {expected}-lockfil.",
                           [lock_path])],
                f"Uppdatera README till {expected}-kommandon som motsvarar projektets faktiska scripts.",
                verification=f"Verifiera kommandona mot package.json och {lock_path}.",
            )

    java_version, java_path = _java_version(files)
    documented_java = _readme_java_versions(readme)
    if java_version and documented_java and java_version not in documented_java:
        emit(
            "must-fix", "README anger fel Java-version",
            f"README anger Java/JDK {', '.join(sorted(documented_java))}, medan buildkonfigurationen kräver Java {java_version}.",
            [_evidence("cross-file", readme_path,
                       f"Dokumenterad Java-version {', '.join(sorted(documented_java))} avviker från buildkravet Java {java_version}.",
                       [java_path] if java_path else None)],
            f"Uppdatera README så att förutsättningarna anger Java {java_version}.",
            verification=f"Verifiera Java-versionen mot {java_path} och kör builden med den dokumenterade versionen.",
        )

    configured_ports = _configured_ports(files)
    documented_ports = _readme_localhost_ports(readme)
    unique_config_ports = {p for p, _ in configured_ports}
    if len(unique_config_ports) == 1 and documented_ports and not (documented_ports & unique_config_ports):
        expected = next(iter(unique_config_ports))
        config_paths = sorted({path for _, path in configured_ports})
        emit(
            "must-fix", "README anger fel lokal port",
            f"README pekar på lokal port {', '.join(sorted(documented_ports))}, medan repositoryts konfiguration anger {expected}.",
            [_evidence("cross-file", readme_path,
                       f"Dokumenterad localhost-port {', '.join(sorted(documented_ports))} avviker från konfigurerad port {expected}.",
                       config_paths)],
            f"Uppdatera README till den faktiska lokala porten {expected}, eller dokumentera varför en proxy ger en annan port.",
            verification="Starta tjänsten om möjligt och kontrollera den dokumenterade URL:en.",
        )

    if _buildable(files) and not _has_any_command_block(readme):
        emit(
            "must-fix", "README saknar centrala build- eller körinstruktioner",
            "Projektet har en buildkonfiguration men README saknar konkreta kommandon för att bygga eller köra projektet.",
            [_evidence("cross-file", readme_path,
                       "README saknar konkreta build-/körkommandon trots att repositoryt innehåller buildmanifest.",
                       sorted([p for p in files if PurePosixPath(p).name in {"package.json", "pom.xml", "build.gradle", "build.gradle.kts", "pyproject.toml", "go.mod", "Cargo.toml"}]))],
            "Dokumentera de minsta verifierade kommandona för installation/build och lokal körning.",
            verification="Följ README från en ren checkout och verifiera att kommandona fungerar.",
        )

    if _has_tests(files) and not _readme_mentions_test(readme):
        emit(
            "recommended", "README beskriver inte hur tester körs",
            "Repositoryt innehåller tester eller ett testscript men README beskriver inte testkörning.",
            [_evidence("cross-file", readme_path,
                       "Tester finns i repositoryt men README saknar testrelaterad instruktion.",
                       sorted([p for p in files if "/test/" in f"/{p.lower()}" or "/tests/" in f"/{p.lower()}" or PurePosixPath(p.lower()).name.startswith("test_")])[:10])],
            "Lägg till det faktiska kommandot för att köra projektets tester.",
            verification="Kör det dokumenterade testkommandot och kontrollera resultatet.",
        )

    if not findings:
        emit(
            "passed", "README:s centrala tekniska uppgifter är konsekventa",
            "De README-kontroller som kunde verifieras mot repositoryts konfiguration visade ingen relevant avvikelse.",
            [_evidence("file", readme_path, "README granskades mot tillgängliga build-, package manager-, Java- och portsignaler.")],
            None,
            verification="Ingen åtgärd krävs för de verifierade README-kontrollerna.",
        )

    return findings
