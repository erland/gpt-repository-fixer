import json
from pathlib import Path

import jsonschema

from scripts.lib.repository_inventory import detect_from_paths

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "repository-inventory.schema.json"


def test_inventory_schema_is_valid_json_schema():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)


def test_react_vite_pnpm_first_pass():
    r = detect_from_paths([
        "package.json", "pnpm-lock.yaml", "tsconfig.json", "vite.config.ts",
        "src/main.tsx", ".github/workflows/ci.yml", "Dockerfile"
    ])
    assert "frontend" in r["project_types"]
    assert "pnpm" in r["technologies"]["package_managers"]
    assert "Vite" in r["technologies"]["frameworks"]
    assert "TypeScript" in r["technologies"]["languages"]
    assert "GitHub Actions" in r["technologies"]["ci"]
    assert "docker" in r["technologies"]["container"]


def test_java_maven_does_not_invent_framework():
    r = detect_from_paths(["pom.xml", "src/main/java/example/App.java"])
    assert "Java" in r["technologies"]["languages"]
    assert "Maven" in r["technologies"]["build_tools"]
    assert r["technologies"]["frameworks"] == []


def test_python_go_rust_are_detected_from_strong_markers():
    assert "Python" in detect_from_paths(["pyproject.toml", "src/app.py"])["technologies"]["languages"]
    assert "Go" in detect_from_paths(["go.mod", "cmd/app/main.go"])["technologies"]["languages"]
    assert "Rust" in detect_from_paths(["Cargo.toml", "src/main.rs"])["technologies"]["languages"]


def test_monorepo_and_fullstack_detection():
    r = detect_from_paths([
        "pnpm-workspace.yaml", "package.json", "pnpm-lock.yaml",
        "frontend/package.json", "frontend/src/main.tsx",
        "backend/pom.xml", "backend/src/main/java/example/App.java"
    ])
    assert "monorepo" in r["project_types"]
    assert "fullstack" in r["project_types"]


def test_multiple_js_lockfiles_are_conflict_not_guess():
    r = detect_from_paths(["package.json", "pnpm-lock.yaml", "package-lock.json"])
    assert set(r["technologies"]["package_managers"]) == {"npm", "pnpm"}
    assert r["conflicts"]


def test_unknown_stack_falls_back_without_fabrication():
    r = detect_from_paths(["README.md", "src/widget.xyz", "tool.custom"])
    assert r["project_types"] in (["unknown"], ["documentation"])
    assert r["technologies"]["frameworks"] == []
