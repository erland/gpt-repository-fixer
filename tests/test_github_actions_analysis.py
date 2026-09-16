import json
from pathlib import Path

import jsonschema

from scripts.lib.github_actions_analysis import analyze_github_actions
from scripts.lib.finding_model import validate_semantics


def valid(result):
    for finding in result["findings"]:
        assert validate_semantics(finding) == []


def test_missing_workflow_is_recommended_when_ci_expected():
    result = analyze_github_actions({"package.json": '{"scripts":{"build":"vite build","test":"vitest run"}}'}, github_ci_expected=True)
    assert result["findings"][0]["classification"] == "recommended"
    assert "saknas" in result["findings"][0]["title"]
    valid(result)


def test_missing_workflow_is_not_invented_when_ci_not_expected():
    result = analyze_github_actions({"README.md": "# x"}, github_ci_expected=False)
    assert result["findings"] == []


def test_invalid_yaml_is_must_fix():
    result = analyze_github_actions({".github/workflows/ci.yml": "jobs: ["})
    f = next(f for f in result["findings"] if "YAML" in f["title"])
    assert f["classification"] == "must-fix"
    valid(result)


def test_workflow_must_cover_build_and_tests():
    files = {
        "package.json": '{"scripts":{"build":"vite build","test":"vitest run"}}',
        "pnpm-lock.yaml": "lockfileVersion: '9.0'",
        ".github/workflows/ci.yml": """
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pnpm test
""",
    }
    result = analyze_github_actions(files)
    assert result["coverage"]["tests"][0]["covered"] is True
    assert result["coverage"]["build"][0]["covered"] is False
    f = next(f for f in result["findings"] if "build" in f["title"].lower())
    assert f["classification"] == "recommended"
    valid(result)


def test_fullstack_components_are_checked_separately():
    files = {
        "frontend/package.json": '{"scripts":{"build":"vite build","test":"vitest run"}}',
        "frontend/pnpm-lock.yaml": "lockfileVersion: '9.0'",
        "backend/pom.xml": "<project/>",
        "backend/mvnw": "#!/bin/sh",
        ".github/workflows/ci.yml": """
name: CI
on: [push, pull_request]
jobs:
  frontend:
    runs-on: ubuntu-latest
    steps:
      - run: pnpm run build
        working-directory: frontend
      - run: pnpm test
        working-directory: frontend
  backend:
    runs-on: ubuntu-latest
    steps:
      - run: ./mvnw -DskipTests package
        working-directory: backend
""",
    }
    result = analyze_github_actions(files)
    tests = {x["component"]: x["covered"] for x in result["coverage"]["tests"]}
    assert tests == {"frontend": True, "backend": False}
    assert any(f["classification"] == "must-fix" and "test" in f["title"].lower() for f in result["findings"])
    valid(result)


def test_runtime_version_conflict_is_must_fix():
    files = {
        ".java-version": "21\n",
        "pom.xml": "<project/>",
        ".github/workflows/ci.yml": """
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-java@v4
        with:
          java-version: '17'
      - run: mvn -DskipTests package
      - run: mvn test
""",
    }
    result = analyze_github_actions(files)
    f = next(f for f in result["findings"] if "runtime-version" in f["title"])
    assert f["classification"] == "must-fix"
    valid(result)


def test_wrong_package_manager_is_must_fix():
    files = {
        "package.json": '{"scripts":{"build":"vite build","test":"vitest run"}}',
        "pnpm-lock.yaml": "lockfileVersion: '9.0'",
        ".github/workflows/ci.yml": """
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: npm ci
      - run: pnpm run build
      - run: pnpm test
""",
    }
    result = analyze_github_actions(files)
    f = next(f for f in result["findings"] if "package manager" in f["title"])
    assert f["classification"] == "must-fix"
    valid(result)


def test_missing_local_script_reference_is_must_fix():
    files = {
        ".github/workflows/ci.yml": """
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - run: ./scripts/verify.sh
""",
    }
    result = analyze_github_actions(files)
    f = next(f for f in result["findings"] if "saknad lokal fil" in f["title"])
    assert f["classification"] == "must-fix"
    valid(result)


def test_duplicate_workflows_are_recommended():
    body = """
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
"""
    result = analyze_github_actions({
        ".github/workflows/a.yml": body,
        ".github/workflows/b.yml": body,
    })
    f = next(f for f in result["findings"] if "duplicerade" in f["title"])
    assert f["classification"] == "recommended"
    valid(result)


def test_action_freshness_requires_separately_verified_current_major():
    files = {
        ".github/workflows/ci.yml": """
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
""",
    }
    no_external_fact = analyze_github_actions(files)
    assert not any("action-major" in f["title"] for f in no_external_fact["findings"])
    verified = analyze_github_actions(files, verified_action_majors={"actions/checkout": 4})
    f = next(f for f in verified["findings"] if "action-major" in f["title"])
    assert f["classification"] == "recommended"
    valid(verified)


def test_complete_workflow_can_pass():
    files = {
        "package.json": '{"scripts":{"build":"vite build","test":"vitest run"}}',
        "pnpm-lock.yaml": "lockfileVersion: '9.0'",
        ".github/workflows/ci.yml": """
on: [push, pull_request]
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pnpm install --frozen-lockfile
      - run: pnpm run build
      - run: pnpm test
""",
    }
    result = analyze_github_actions(files)
    assert len(result["findings"]) == 1
    assert result["findings"][0]["classification"] == "passed"
    valid(result)


def test_github_actions_schema_is_valid_and_accepts_result():
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "schemas/github-actions-analysis.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    result = analyze_github_actions({
        "package.json": '{"scripts":{"build":"vite build","test":"vitest run"}}',
        "pnpm-lock.yaml": "lockfileVersion: '9.0'",
        ".github/workflows/ci.yml": "on: [push, pull_request]\njobs:\n  verify:\n    runs-on: ubuntu-latest\n    steps:\n      - run: pnpm run build\n      - run: pnpm test\n",
    })
    jsonschema.Draft202012Validator(schema).validate(result)
