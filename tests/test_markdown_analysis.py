from scripts.lib.markdown_analysis import analyze_markdown_documentation


def by_title(findings, title):
    return next((f for f in findings if f["title"] == title), None)


def test_missing_package_script_is_must_fix():
    files = {
        "package.json": '{"scripts":{"dev":"vite","test":"vitest"}}',
        "docs/development.md": "Kör `pnpm run serve` för att starta utvecklingsservern.",
    }
    findings = analyze_markdown_documentation(files)
    finding = by_title(findings, "Dokumentationen refererar till ett package-script som saknas")
    assert finding is not None
    assert finding["classification"] == "must-fix"
    assert finding["confidence"] == "high"


def test_wrong_java_version_is_must_fix():
    files = {
        "pom.xml": "<properties><maven.compiler.release>21</maven.compiler.release></properties>",
        "docs/setup.md": "Projektet kräver Java 17.",
    }
    findings = analyze_markdown_documentation(files)
    finding = by_title(findings, "Markdown-dokumentation anger fel Java-version")
    assert finding is not None
    assert finding["classification"] == "must-fix"
    assert "21" in finding["summary"]


def test_wrong_local_port_is_must_fix():
    files = {
        "src/main/resources/application.properties": "quarkus.http.port=8081\n",
        "docs/runbook.md": "Öppna http://localhost:8080/health efter start.",
    }
    findings = analyze_markdown_documentation(files)
    finding = by_title(findings, "Markdown-dokumentation anger fel lokal port")
    assert finding is not None
    assert finding["classification"] == "must-fix"


def test_missing_relative_file_reference_is_must_fix():
    files = {
        "docs/architecture.md": "Se [den gamla API-beskrivningen](old-api.md).",
        "src/main.ts": "export const ok = true;",
    }
    findings = analyze_markdown_documentation(files)
    finding = by_title(findings, "Markdown-dokumentation refererar till en fil som saknas")
    assert finding is not None
    assert finding["classification"] == "must-fix"
    assert "docs/old-api.md" in finding["summary"]


def test_existing_relative_file_reference_passes():
    files = {
        "docs/architecture.md": "Se [API-beskrivningen](api.md).",
        "docs/api.md": "# API",
    }
    findings = analyze_markdown_documentation(files)
    assert all(f["classification"] != "must-fix" for f in findings)
    assert findings[0]["classification"] == "passed"


def test_unverified_env_var_is_recommendation_not_hard_error():
    files = {
        ".env.example": "DATABASE_URL=postgres://localhost/db\n",
        "docs/configuration.md": "Sätt `LEGACY_TOKEN` innan start.",
    }
    findings = analyze_markdown_documentation(files)
    finding = by_title(findings, "Dokumenterad miljövariabel saknar verifierbar repositoryreferens")
    assert finding is not None
    assert finding["classification"] == "recommended"
    assert finding["confidence"] == "medium"


def test_unmatched_endpoint_is_recommendation_not_hard_error():
    files = {
        "src/Routes.java": '@Path("/api/projects")\npublic class Routes {}',
        "docs/api.md": "Anropa `/api/legacy` för den gamla listan.",
    }
    findings = analyze_markdown_documentation(files)
    finding = by_title(findings, "Dokumenterad API-endpoint saknar direkt verifierbar route")
    assert finding is not None
    assert finding["classification"] == "recommended"
    assert finding["confidence"] == "medium"


def test_no_non_readme_markdown_is_passed():
    files = {
        "README.md": "# App",
        "package.json": '{"scripts":{"dev":"vite"}}',
    }
    findings = analyze_markdown_documentation(files)
    assert len(findings) == 1
    assert findings[0]["classification"] == "passed"
    assert "Ingen separat Markdown" in findings[0]["title"]
