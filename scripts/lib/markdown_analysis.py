from __future__ import annotations

import json
import re
from pathlib import PurePosixPath


README_NAMES = {"readme.md", "readme.markdown"}
MARKDOWN_SUFFIXES = {".md", ".markdown"}


def _evidence(kind: str, path: str | None, observation: str, related_paths: list[str] | None = None) -> dict:
    item = {"kind": kind, "observation": observation}
    if path:
        item["path"] = path
    if related_paths:
        item["related_paths"] = related_paths
    return item


def _finding(fid: str, classification: str, title: str, summary: str, evidence: list[dict],
             action: str | None, confidence: str = "high", verification: str = "Granska dokumentation och källfiler igen.") -> dict:
    return {
        "id": fid,
        "area": "documentation",
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


def _markdown_files(files: dict[str, str]) -> list[tuple[str, str]]:
    docs = []
    for path, text in files.items():
        p = PurePosixPath(path)
        if p.suffix.lower() not in MARKDOWN_SUFFIXES:
            continue
        if p.name.lower() in README_NAMES:
            continue
        # Ignore Repository Fixer's own portable work metadata if analyzing a repository mid-flow.
        if p.parts and p.parts[0] == ".repository-fixer":
            continue
        docs.append((path, text))
    return sorted(docs)


def _package_scripts(files: dict[str, str]) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    for path, text in files.items():
        if PurePosixPath(path).name != "package.json":
            continue
        try:
            payload = json.loads(text)
        except Exception:
            continue
        scripts = payload.get("scripts") or {}
        if isinstance(scripts, dict):
            for name, command in scripts.items():
                if isinstance(name, str) and isinstance(command, str):
                    result[name] = (command, path)
    return result


def _documented_package_scripts(text: str) -> set[str]:
    names: set[str] = set()
    for m in re.finditer(r"(?mi)(?:npm\s+run|pnpm\s+(?:run\s+)?|yarn\s+(?:run\s+)?)([A-Za-z0-9:_-]+)\b", text):
        names.add(m.group(1))
    # npm test/start are special commands backed by scripts with those names.
    if re.search(r"(?mi)(?:^|[`$>\s])npm\s+test\b", text):
        names.add("test")
    if re.search(r"(?mi)(?:^|[`$>\s])npm\s+start\b", text):
        names.add("start")
    return names


def _java_version(files: dict[str, str]) -> tuple[str | None, str | None]:
    for path, text in files.items():
        if PurePosixPath(path).name == "pom.xml":
            for pattern in [
                r"<maven\.compiler\.release>\s*(\d+)\s*</maven\.compiler\.release>",
                r"<maven\.compiler\.source>\s*(\d+)\s*</maven\.compiler\.source>",
                r"<java\.version>\s*(\d+)\s*</java\.version>",
            ]:
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


def _documented_java_versions(text: str) -> set[str]:
    result = set()
    for pattern in [
        r"(?i)\b(?:java|jdk)\s*(?:version\s*)?(?:>=?\s*)?(\d{1,2})\b",
        r"(?i)\b(?:requires?|kräver)\s+(?:java|jdk)\s*(\d{1,2})\b",
    ]:
        result.update(re.findall(pattern, text))
    return result


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
            for host, _container in re.findall(r"['\"]?(\d{2,5}):(\d{2,5})['\"]?", text):
                found.append((host, path))
    return sorted(set(found))


def _localhost_ports(text: str) -> set[str]:
    return set(re.findall(r"(?i)(?:localhost|127\.0\.0\.1):([0-9]{2,5})", text))


def _candidate_file_refs(text: str) -> set[str]:
    refs: set[str] = set()
    # Markdown links, excluding URLs, anchors and images/data URIs.
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = target.strip().split()[0].strip("<>")
        if not target or target.startswith(("http://", "https://", "mailto:", "#", "data:")):
            continue
        target = target.split("#", 1)[0].split("?", 1)[0]
        if target:
            refs.add(target)
    # Inline code paths with common repository file suffixes.
    path_pattern = r"`((?:\.?\.?/)?[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+\.(?:md|json|ya?ml|toml|xml|properties|ts|tsx|js|jsx|java|py|go|rs|sh))`"
    refs.update(re.findall(path_pattern, text, re.I))
    return refs


def _resolve_ref(doc_path: str, ref: str) -> str:
    ref = ref.replace("\\", "/")
    if ref.startswith("/"):
        return ref.lstrip("/")
    base = PurePosixPath(doc_path).parent
    parts: list[str] = []
    for part in (base / ref).parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
        else:
            parts.append(part)
    return "/".join(parts)


def _known_env_vars(files: dict[str, str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for path, text in files.items():
        base = PurePosixPath(path).name.lower()
        names: set[str] = set()
        if base in {".env", ".env.example", ".env.sample", "env.example", "env.sample"} or base.endswith(".env.example"):
            names.update(re.findall(r"(?m)^\s*([A-Z][A-Z0-9_]*)\s*=", text))
        if base in {"compose.yaml", "compose.yml", "docker-compose.yml", "docker-compose.yaml"}:
            names.update(re.findall(r"\$\{([A-Z][A-Z0-9_]*)", text))
        if base == "application.properties":
            names.update(re.findall(r"\$\{([A-Z][A-Z0-9_]*)", text))
        for name in names:
            result.setdefault(name, []).append(path)
    return result


def _documented_env_vars(text: str) -> set[str]:
    # Restrict to explicit shell-style references or inline-code uppercase names to reduce false positives.
    result = set(re.findall(r"\$\{?([A-Z][A-Z0-9_]{2,})\}?", text))
    result.update(re.findall(r"`([A-Z][A-Z0-9_]{2,})`", text))
    return result


def _route_evidence(files: dict[str, str]) -> dict[str, list[str]]:
    routes: dict[str, list[str]] = {}
    route_patterns = [
        r"@Path\(\s*[\"']([^\"']+)[\"']\s*\)",
        r"@(?:Get|Post|Put|Delete|Patch)Mapping\(\s*[\"']([^\"']+)[\"']",
        r"app\.(?:get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']",
        r"router\.(?:get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']",
    ]
    for path, text in files.items():
        if PurePosixPath(path).suffix.lower() not in {".java", ".js", ".jsx", ".ts", ".tsx", ".py", ".go", ".rs"}:
            continue
        for pattern in route_patterns:
            for route in re.findall(pattern, text):
                if route.startswith("/"):
                    routes.setdefault(route.rstrip("/") or "/", []).append(path)
    return routes


def _documented_api_paths(text: str) -> set[str]:
    # Only explicit /api/... references; generic URL paths are too noisy for hard findings.
    return {p.rstrip("/") or "/" for p in re.findall(r"(?<![A-Za-z0-9_])(/api/[A-Za-z0-9_./{}:-]+)", text)}


def analyze_markdown_documentation(files: dict[str, str]) -> list[dict]:
    """Analyze non-README Markdown against repository evidence.

    This deterministic first pass intentionally handles only claims with a strong
    machine-checkable counterpart. Semantic feature coverage remains an LLM task
    governed by `knowledge/markdown-documentation-analysis.md`.
    """
    docs = _markdown_files(files)
    if not docs:
        return [_finding(
            "RF-DOC-001", "passed", "Ingen separat Markdown-dokumentation att kontrollera",
            "Repositoryt har ingen Markdown-dokumentation utöver README som kräver denna kontroll.",
            [_evidence("absence", None, "Ingen icke-README Markdown-fil hittades.")],
            None,
            verification="Kontrollera på nytt om dokumentation senare läggs till.",
        )]

    findings: list[dict] = []
    idx = 1

    def emit(classification: str, title: str, summary: str, evidence: list[dict], action: str | None,
             confidence: str = "high", verification: str = "Jämför dokumentet med repositoryts faktiska filer igen.") -> None:
        nonlocal idx
        findings.append(_finding(
            f"RF-DOC-{idx:03d}", classification, title, summary, evidence, action, confidence, verification
        ))
        idx += 1

    scripts = _package_scripts(files)
    java_version, java_path = _java_version(files)
    configured_ports = _configured_ports(files)
    unique_ports = {p for p, _ in configured_ports}
    env_vars = _known_env_vars(files)
    routes = _route_evidence(files)
    repo_paths = set(files)

    checked_script_claims = 0
    checked_version_claims = 0
    checked_port_claims = 0
    checked_file_refs = 0
    checked_env_claims = 0
    checked_route_claims = 0

    for doc_path, text in docs:
        for script in sorted(_documented_package_scripts(text)):
            checked_script_claims += 1
            if scripts and script not in scripts:
                package_paths = sorted({path for _cmd, path in scripts.values()})
                emit(
                    "must-fix", "Dokumentationen refererar till ett package-script som saknas",
                    f"{doc_path} beskriver scriptet `{script}`, men inget analyserat package.json definierar det.",
                    [_evidence("cross-file", doc_path, f"Dokumenterat package-script `{script}` saknas i package.json scripts.", package_paths)],
                    f"Uppdatera dokumentationen till ett befintligt script eller återinför scriptet om det fortfarande är avsiktligt.",
                    verification="Verifiera kommandot mot package.json och kör det om miljön tillåter.",
                )

        if java_version:
            doc_java = _documented_java_versions(text)
            if doc_java:
                checked_version_claims += 1
                if java_version not in doc_java:
                    emit(
                        "must-fix", "Markdown-dokumentation anger fel Java-version",
                        f"{doc_path} anger Java/JDK {', '.join(sorted(doc_java))}, medan buildkonfigurationen kräver Java {java_version}.",
                        [_evidence("cross-file", doc_path,
                                   f"Dokumenterad Java-version {', '.join(sorted(doc_java))} avviker från Java {java_version} i buildkonfigurationen.",
                                   [java_path] if java_path else None)],
                        f"Uppdatera dokumentet så att Java-förutsättningen motsvarar version {java_version}.",
                        verification=f"Verifiera mot {java_path} och relevanta CI/runtime-inställningar.",
                    )

        doc_ports = _localhost_ports(text)
        if doc_ports and len(unique_ports) == 1:
            checked_port_claims += 1
            expected = next(iter(unique_ports))
            if expected not in doc_ports:
                config_paths = sorted({path for _, path in configured_ports})
                emit(
                    "must-fix", "Markdown-dokumentation anger fel lokal port",
                    f"{doc_path} anger localhost-port {', '.join(sorted(doc_ports))}, medan entydig repositorykonfiguration anger {expected}.",
                    [_evidence("cross-file", doc_path,
                               f"Dokumenterad lokal port {', '.join(sorted(doc_ports))} avviker från konfigurerad port {expected}.",
                               config_paths)],
                    f"Uppdatera dokumentationen till port {expected}, eller dokumentera uttryckligen eventuell proxy/alternativ port.",
                    verification="Starta tjänsten om möjligt och kontrollera den dokumenterade URL:en.",
                )

        for ref in sorted(_candidate_file_refs(text)):
            checked_file_refs += 1
            resolved = _resolve_ref(doc_path, ref)
            # Directory links cannot be proven absent from the text-file map, so only enforce file-like refs.
            if resolved not in repo_paths:
                emit(
                    "must-fix", "Markdown-dokumentation refererar till en fil som saknas",
                    f"{doc_path} refererar till `{ref}`, men den upplösta repositorysökvägen `{resolved}` finns inte bland analyserade filer.",
                    [_evidence("cross-file", doc_path, f"Filreferensen `{ref}` kan inte matchas mot `{resolved}` i repositoryt.")],
                    "Korrigera filreferensen eller ta bort den om målfilerna inte längre finns.",
                    verification="Kontrollera länken från dokumentets katalog och verifiera att målet existerar.",
                )

        if env_vars:
            for name in sorted(_documented_env_vars(text)):
                checked_env_claims += 1
                if name not in env_vars:
                    authoritative_paths = sorted({p for paths in env_vars.values() for p in paths})
                    emit(
                        "recommended", "Dokumenterad miljövariabel saknar verifierbar repositoryreferens",
                        f"{doc_path} dokumenterar `{name}`, men variabeln hittades inte i analyserade env-exempel, Compose eller property-substitutioner.",
                        [_evidence("cross-file", doc_path, f"`{name}` saknar matchning i de konfigurationskällor som kunde verifieras.", authoritative_paths)],
                        "Kontrollera om variabeln fortfarande används. Uppdatera dokumentationen eller lägg till en verifierbar konfigurationsreferens.",
                        confidence="medium",
                        verification="Sök efter variabeln i källkod och deploykonfiguration innan dokumentationen ändras.",
                    )

        if routes:
            normalized_routes = set(routes)
            for api_path in sorted(_documented_api_paths(text)):
                checked_route_claims += 1
                if api_path not in normalized_routes:
                    route_paths = sorted({p for paths in routes.values() for p in paths})
                    emit(
                        "recommended", "Dokumenterad API-endpoint saknar direkt verifierbar route",
                        f"{doc_path} refererar till `{api_path}`, men ingen exakt route med den sökvägen hittades i stödda route-mönster.",
                        [_evidence("cross-file", doc_path, f"Endpoint `{api_path}` kunde inte matchas exakt mot upptäckta routes.", route_paths)],
                        "Verifiera endpointen semantiskt innan dokumentationen ändras; den kan byggas upp av prefix eller routingkonfiguration.",
                        confidence="medium",
                        verification="Kontrollera route-prefix, controllers/routers och körande API innan ändring.",
                    )

    if not findings:
        total_checks = sum([
            checked_script_claims, checked_version_claims, checked_port_claims,
            checked_file_refs, checked_env_claims, checked_route_claims,
        ])
        observation = (
            f"{len(docs)} Markdown-fil(er) granskades; {total_checks} maskinellt verifierbara dokumentationspåståenden kontrollerades utan konkret avvikelse."
        )
        findings.append(_finding(
            "RF-DOC-001", "passed", "Markdown-dokumentationen saknar verifierade tekniska avvikelser",
            "Den deterministiska dokumentationskontrollen hittade ingen konkret motsägelse mot repositoryts verifierbara konfiguration.",
            [_evidence("file", docs[0][0], observation, [p for p, _ in docs[1:]] or None)],
            None,
            verification="Komplettera med semantisk granskning av funktionsbeskrivningar och arkitekturdokumentation.",
        ))

    return findings
