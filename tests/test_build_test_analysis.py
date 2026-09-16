from scripts.lib.build_test_analysis import analyze_build_test
from scripts.lib.finding_model import validate_semantics


def valid(result):
    for finding in result["findings"]:
        assert validate_semantics(finding) == []


def test_pnpm_commands_are_derived_from_package_json_and_lockfile():
    result = analyze_build_test({
        "package.json": '{"scripts":{"build":"vite build","test":"vitest run"}}',
        "pnpm-lock.yaml": "lockfileVersion: '9.0'",
    })
    assert result["build"][0]["command"] == "pnpm run build"
    assert result["tests"][0]["command"] == "pnpm test"
    assert result["build"][0]["status"] == "not-verified"
    valid(result)


def test_maven_wrapper_is_preferred():
    result = analyze_build_test({"pom.xml": "<project/>", "mvnw": "#!/bin/sh"})
    assert result["build"][0]["command"] == "./mvnw -DskipTests package"
    assert result["tests"][0]["command"] == "./mvnw test"
    valid(result)


def test_gradle_wrapper_is_preferred():
    result = analyze_build_test({"build.gradle.kts": "plugins {}", "gradlew": "#!/bin/sh"})
    assert result["build"][0]["command"] == "./gradlew assemble"
    assert result["tests"][0]["command"] == "./gradlew test"
    valid(result)


def test_go_and_rust_commands_are_supported():
    go = analyze_build_test({"go.mod": "module example.com/x"})
    rust = analyze_build_test({"Cargo.toml": "[package]\nname='x'"})
    assert go["build"][0]["command"] == "go build ./..."
    assert go["tests"][0]["command"] == "go test ./..."
    assert rust["build"][0]["command"] == "cargo build"
    assert rust["tests"][0]["command"] == "cargo test"


def test_python_pytest_is_derived_when_test_structure_exists():
    result = analyze_build_test({
        "pyproject.toml": '[build-system]\nbuild-backend="setuptools.build_meta"',
        "tests/test_app.py": "def test_x(): assert True",
    })
    assert result["build"][0]["command"] == "python -m build"
    assert result["tests"][0]["command"] == "python -m pytest"


def test_test_files_without_node_test_script_are_must_fix():
    result = analyze_build_test({
        "package.json": '{"scripts":{"build":"vite build"}}',
        "pnpm-lock.yaml": "lockfileVersion: '9.0'",
        "src/app.test.ts": "test('x',()=>{})",
    })
    f = next(f for f in result["findings"] if "test-script" in f["title"])
    assert f["classification"] == "must-fix"
    valid(result)


def test_execution_success_is_verified_and_emits_passed_findings():
    files = {"pom.xml": "<project/>", "mvnw": "#!/bin/sh"}
    result = analyze_build_test(files, {
        "./mvnw -DskipTests package": {"exit_code": 0},
        "./mvnw test": {"exit_code": 0},
    })
    assert result["build"][0]["status"] == "verified"
    assert result["tests"][0]["status"] == "verified"
    assert sum(f["classification"] == "passed" for f in result["findings"]) == 2
    valid(result)


def test_execution_failure_is_failing_not_refactor_permission():
    files = {"go.mod": "module x"}
    result = analyze_build_test(files, {"go test ./...": {"exit_code": 1, "summary": "one test failed"}})
    assert result["tests"][0]["status"] == "failing"
    f = next(f for f in result["findings"] if "felande" in f["title"])
    assert f["classification"] == "must-fix"
    assert "godtyckligt" in f["recommended_action"]
    valid(result)


def test_unsupported_execution_is_not_verified_not_failure():
    files = {"Cargo.toml": "[package]\nname='x'"}
    result = analyze_build_test(files, {"cargo test": {"executed": False, "reason": "Rust saknas i miljön"}})
    assert result["tests"][0]["status"] == "not-verified"
    assert result["tests"][0]["reason"] == "Rust saknas i miljön"
    assert not any(f["title"] == "Tester verifierades som felande" for f in result["findings"])
    valid(result)


def test_java_runtime_conflict_is_reported():
    result = analyze_build_test({
        "pom.xml": "<project><properties><maven.compiler.release>21</maven.compiler.release></properties></project>",
        ".java-version": "17\n",
    })
    f = next(f for f in result["findings"] if "Java-versioner" in f["title"])
    assert f["classification"] == "must-fix"
    assert f["area"] == "versions"
    valid(result)


def test_unknown_repository_does_not_invent_commands():
    result = analyze_build_test({"README.md": "# Notes", "notes.txt": "x"})
    assert result["build"] == []
    assert result["tests"] == []
    assert result["findings"][0]["classification"] == "consider"
    valid(result)


def test_fullstack_components_are_reported_separately():
    result = analyze_build_test({
        "frontend/package.json": '{"packageManager":"pnpm@10","scripts":{"build":"vite build","test":"vitest run"}}',
        "frontend/pnpm-lock.yaml": "lockfileVersion: '9.0'",
        "backend/pom.xml": "<project/>",
        "backend/mvnw": "#!/bin/sh",
    })
    assert {(x["component"], x["kind"]) for x in result["build"]} == {("frontend", "node"), ("backend", "maven")}
    assert {(x["component"], x["kind"]) for x in result["tests"]} == {("frontend", "node"), ("backend", "maven")}
    valid(result)


def test_execution_results_can_be_component_qualified():
    files = {
        "apps/a/package.json": '{"scripts":{"build":"vite build","test":"vitest run"}}',
        "apps/a/pnpm-lock.yaml": "lockfileVersion: '9.0'",
        "apps/b/package.json": '{"scripts":{"build":"vite build","test":"vitest run"}}',
        "apps/b/pnpm-lock.yaml": "lockfileVersion: '9.0'",
    }
    result = analyze_build_test(files, {
        "apps/a::pnpm test": {"exit_code": 0},
        "apps/b::pnpm test": {"exit_code": 2},
    })
    statuses = {x["component"]: x["status"] for x in result["tests"]}
    assert statuses == {"apps/a": "verified", "apps/b": "failing"}
    valid(result)
