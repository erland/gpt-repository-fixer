from scripts.lib.readme_analysis import analyze_readme
from scripts.lib.finding_model import validate_semantics


def by_title(findings, text):
    return next(f for f in findings if text.lower() in f["title"].lower())


def assert_semantically_valid(findings):
    for finding in findings:
        assert validate_semantics(finding) == []


def test_detects_old_npm_command_when_repo_uses_pnpm():
    files = {
        "README.md": "# App\n\n```bash\nnpm install\nnpm run dev\n```\n",
        "package.json": '{"scripts":{"dev":"vite"}}',
        "pnpm-lock.yaml": "lockfileVersion: '9.0'",
        "vite.config.ts": "export default {}",
    }
    findings = analyze_readme(files)
    item = by_title(findings, "package manager")
    assert item["classification"] == "must-fix"
    assert "pnpm-lock.yaml" in item["evidence"][0]["related_paths"]
    assert_semantically_valid(findings)


def test_detects_wrong_java_version():
    files = {
        "README.md": "# API\n\nRequires Java 17.\n\n```bash\n./mvnw quarkus:dev\n```",
        "pom.xml": "<project><properties><maven.compiler.release>21</maven.compiler.release></properties></project>",
        "mvnw": "#!/bin/sh",
    }
    findings = analyze_readme(files)
    item = by_title(findings, "Java-version")
    assert item["classification"] == "must-fix"
    assert "Java 21" in item["summary"]
    assert_semantically_valid(findings)


def test_detects_wrong_local_port():
    files = {
        "README.md": "# API\n\nRun:\n```bash\n./mvnw quarkus:dev\n```\nOpen http://localhost:8080",
        "pom.xml": "<project />",
        "src/main/resources/application.properties": "quarkus.http.port=8081\n",
    }
    findings = analyze_readme(files)
    item = by_title(findings, "lokal port")
    assert item["classification"] == "must-fix"
    assert "8081" in item["summary"]
    assert_semantically_valid(findings)


def test_detects_missing_core_run_instructions():
    files = {
        "README.md": "# Widget service\n\nA small service for widgets.\n",
        "package.json": '{"scripts":{"build":"vite build","dev":"vite"}}',
        "pnpm-lock.yaml": "lockfileVersion: '9.0'",
    }
    findings = analyze_readme(files)
    item = by_title(findings, "build- eller körinstruktioner")
    assert item["classification"] == "must-fix"
    assert_semantically_valid(findings)


def test_recommends_test_instruction_when_tests_exist():
    files = {
        "README.md": "# App\n\n```bash\npnpm install\npnpm run dev\n```\n",
        "package.json": '{"scripts":{"dev":"vite","test":"vitest"}}',
        "pnpm-lock.yaml": "lockfileVersion: '9.0'",
        "src/example.test.ts": "it('works',()=>{})",
    }
    findings = analyze_readme(files)
    item = by_title(findings, "tester")
    assert item["classification"] == "recommended"
    assert_semantically_valid(findings)


def test_emits_passed_check_when_verified_signals_are_consistent():
    files = {
        "README.md": "# App\n\nRequires Java 21.\n\n```bash\n./mvnw test\n./mvnw quarkus:dev\n```\nOpen http://localhost:8081",
        "pom.xml": "<project><properties><maven.compiler.release>21</maven.compiler.release></properties></project>",
        "src/main/resources/application.properties": "quarkus.http.port=8081\n",
    }
    findings = analyze_readme(files)
    assert len(findings) == 1
    assert findings[0]["classification"] == "passed"
    assert_semantically_valid(findings)


def test_missing_readme_is_must_fix():
    findings = analyze_readme({"pom.xml": "<project />"})
    assert findings[0]["classification"] == "must-fix"
    assert "README saknas" == findings[0]["title"]
    assert_semantically_valid(findings)
