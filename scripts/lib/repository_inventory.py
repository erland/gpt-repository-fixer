from __future__ import annotations

from pathlib import PurePosixPath


def detect_from_paths(paths: list[str]) -> dict:
    """Conservative path-only inventory used for deterministic contract tests.

    This is deliberately a first-pass helper. Framework-specific conclusions that
    require manifest contents must be made from those contents, not invented here.
    """
    normalized = sorted({p.strip("/") for p in paths if p and p.strip("/")})
    names = set(normalized)
    basenames = {PurePosixPath(p).name for p in normalized}

    languages: set[str] = set()
    frameworks: set[str] = set()
    build_tools: set[str] = set()
    package_managers: set[str] = set()
    container: set[str] = set()
    ci: set[str] = set()
    evidence: list[dict] = []
    conflicts: list[str] = []

    def add(claim: str, path: str, signal: str):
        evidence.append({"claim": claim, "path": path, "signal": signal})

    if "package.json" in names or any(p.endswith("/package.json") for p in names):
        languages.add("JavaScript/TypeScript")
        build_tools.add("Node.js")
        p = "package.json" if "package.json" in names else next(p for p in normalized if p.endswith("/package.json"))
        add("Node ecosystem", p, "package.json")
    if "pnpm-lock.yaml" in basenames:
        package_managers.add("pnpm"); add("pnpm", next(p for p in normalized if p.endswith("pnpm-lock.yaml")), "pnpm lockfile")
    if "package-lock.json" in basenames:
        package_managers.add("npm"); add("npm", next(p for p in normalized if p.endswith("package-lock.json")), "npm lockfile")
    if "yarn.lock" in basenames:
        package_managers.add("yarn"); add("Yarn", next(p for p in normalized if p.endswith("yarn.lock")), "Yarn lockfile")
    if len(package_managers) > 1:
        conflicts.append("Multiple JavaScript package-manager lockfiles detected")
    if any(PurePosixPath(p).name.startswith("vite.config.") for p in normalized):
        frameworks.add("Vite"); p = next(p for p in normalized if PurePosixPath(p).name.startswith("vite.config.")); add("Vite", p, "Vite config")
    if "tsconfig.json" in basenames or any(p.endswith((".ts", ".tsx")) for p in normalized):
        languages.add("TypeScript")

    if "pom.xml" in basenames:
        languages.add("Java"); build_tools.add("Maven"); p = next(p for p in normalized if p.endswith("pom.xml")); add("Maven", p, "pom.xml")
    if "build.gradle" in basenames or "build.gradle.kts" in basenames:
        languages.add("Java/Kotlin"); build_tools.add("Gradle"); p = next(p for p in normalized if PurePosixPath(p).name in {"build.gradle", "build.gradle.kts"}); add("Gradle", p, "Gradle build file")

    if any(PurePosixPath(p).name in {"pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "Pipfile"} for p in normalized) or any(p.endswith(".py") for p in normalized):
        languages.add("Python"); p = next((p for p in normalized if PurePosixPath(p).name in {"pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "Pipfile"}), next((p for p in normalized if p.endswith(".py")), "")); add("Python", p, "Python manifest/source")
    if "go.mod" in basenames:
        languages.add("Go"); build_tools.add("Go modules"); p = next(p for p in normalized if p.endswith("go.mod")); add("Go", p, "go.mod")
    if "Cargo.toml" in basenames:
        languages.add("Rust"); build_tools.add("Cargo"); p = next(p for p in normalized if p.endswith("Cargo.toml")); add("Rust", p, "Cargo.toml")

    if "Dockerfile" in basenames or any(PurePosixPath(p).name.endswith(".Dockerfile") for p in normalized):
        container.add("docker"); p = next(p for p in normalized if PurePosixPath(p).name == "Dockerfile" or PurePosixPath(p).name.endswith(".Dockerfile")); add("Docker", p, "Dockerfile")
    compose_names = {"compose.yaml", "compose.yml", "docker-compose.yml", "docker-compose.yaml"}
    if any(PurePosixPath(p).name in compose_names for p in normalized):
        container.add("docker-compose"); p = next(p for p in normalized if PurePosixPath(p).name in compose_names); add("Docker Compose", p, "Compose file")
    workflows = [p for p in normalized if p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml"))]
    if workflows:
        ci.add("GitHub Actions")
        for p in workflows:
            add("GitHub Actions", p, "workflow file")

    monorepo = "pnpm-workspace.yaml" in basenames
    if monorepo:
        add("monorepo", next(p for p in normalized if p.endswith("pnpm-workspace.yaml")), "pnpm workspace")
    has_frontend_dir = any(p.startswith(("frontend/", "apps/web/", "packages/web/")) for p in normalized)
    has_backend_dir = any(p.startswith(("backend/", "services/", "apps/api/")) for p in normalized)

    project_types: list[str] = []
    if monorepo:
        project_types.append("monorepo")
    if has_frontend_dir and has_backend_dir:
        project_types.append("fullstack")
    elif has_frontend_dir:
        project_types.append("frontend")
    elif has_backend_dir:
        project_types.append("backend")
    elif "package.json" in names and any(p in basenames for p in {"vite.config.ts", "vite.config.js", "vite.config.mjs", "vite.config.cjs"}):
        project_types.append("frontend")
    elif not languages and not build_tools:
        md = [p for p in normalized if p.lower().endswith(".md")]
        project_types.append("documentation" if md and len(md) >= max(1, len(normalized) // 2) else "unknown")
    else:
        project_types.append("unknown")

    confidence = "high" if len(evidence) >= 3 and project_types != ["unknown"] else "medium" if evidence else "low"
    return {
        "project_types": project_types,
        "technologies": {
            "languages": sorted(languages),
            "frameworks": sorted(frameworks),
            "build_tools": sorted(build_tools),
            "package_managers": sorted(package_managers),
            "container": sorted(container),
            "ci": sorted(ci),
        },
        "evidence": evidence,
        "conflicts": conflicts,
        "confidence": confidence,
    }
