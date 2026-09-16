import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from scripts.lib.github_read_workflow import (
    GitHubRepositorySnapshot,
    InvalidGitHubRepository,
    build_github_read_context,
    materialize_snapshot,
    parse_github_repository_url,
    repository_fixer_pull_requests,
)
from scripts.lib.repository_inventory import detect_from_paths

ROOT = Path(__file__).resolve().parents[1]


def _snapshot(**overrides):
    ref = parse_github_repository_url("https://github.com/acme/demo")
    data = dict(
        repository=ref,
        default_branch="main",
        resolved_ref="main",
        commit_sha="abc123",
        writable=True,
        files={
            "README.md": b"# Demo\n",
            "package.json": b'{"scripts":{"build":"vite build","test":"vitest run"}}',
            "pnpm-lock.yaml": b"lockfileVersion: '9.0'\n",
            "vite.config.ts": b"export default {}\n",
            ".github/workflows/ci.yml": b"name: CI\n",
        },
        open_pull_requests=(),
    )
    data.update(overrides)
    return GitHubRepositorySnapshot(**data)


def test_parse_github_repository_url_normalizes_repo_and_dot_git():
    a = parse_github_repository_url("https://github.com/acme/demo.git")
    b = parse_github_repository_url("https://www.github.com/acme/demo/tree/main/src")
    assert (a.owner, a.repo, a.web_url) == ("acme", "demo", "https://github.com/acme/demo")
    assert b.web_url == a.web_url


def test_parse_rejects_non_github_and_missing_repo():
    with pytest.raises(InvalidGitHubRepository):
        parse_github_repository_url("https://example.com/acme/demo")
    with pytest.raises(InvalidGitHubRepository):
        parse_github_repository_url("https://github.com/acme")


def test_materialized_snapshot_uses_same_inventory_semantics_as_file_list(tmp_path):
    snap = _snapshot()
    workspace = materialize_snapshot(snap, tmp_path / "work")
    paths = [p.relative_to(workspace.repository_root).as_posix() for p in workspace.repository_root.rglob("*") if p.is_file()]
    github_inventory = detect_from_paths(paths)
    zip_equivalent_inventory = detect_from_paths(list(snap.files))
    assert github_inventory == zip_equivalent_inventory
    assert github_inventory["technologies"]["package_managers"] == ["pnpm"]
    assert github_inventory["technologies"]["ci"] == ["GitHub Actions"]


def test_materialize_rejects_unsafe_snapshot_path(tmp_path):
    snap = _snapshot(files={"../outside.txt": b"bad"})
    with pytest.raises(InvalidGitHubRepository, match="sökväg"):
        materialize_snapshot(snap, tmp_path / "work")
    assert not (tmp_path / "outside.txt").exists()


def test_read_context_exposes_default_ref_sha_and_write_access():
    context = build_github_read_context(_snapshot())
    assert context["mode"] == "github"
    assert context["default_branch"] == "main"
    assert context["analyzed_ref"] == "main"
    assert context["commit_sha"] == "abc123"
    assert context["writable"] is True
    assert context["limitations"] == []


def test_read_only_and_unknown_write_access_are_capability_limitations_not_findings():
    readonly = build_github_read_context(_snapshot(writable=False))
    unknown = build_github_read_context(_snapshot(writable=None))
    assert "Skrivåtkomst saknas" in readonly["limitations"][0]
    assert "inte verifierad" in unknown["limitations"][0]
    assert "findings" not in readonly
    assert "findings" not in unknown


def test_repository_fixer_pr_detection_requires_concrete_signal():
    prs = [
        {"number": 1, "state": "open", "head_ref": "repository-fixer/20260916", "title": "Docs"},
        {"number": 2, "state": "open", "head_ref": "feature/x", "title": "Repository Fixer cleanup"},
        {"number": 3, "state": "open", "head_ref": "feature/y", "title": "Other"},
        {"number": 4, "state": "closed", "head_ref": "repository-fixer/old", "title": "Old"},
    ]
    matches = repository_fixer_pull_requests(prs)
    assert [p["number"] for p in matches] == [1, 2]


def test_read_context_schema_validates():
    schema = json.loads((ROOT / "schemas/repository-github-source.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(build_github_read_context(_snapshot(writable=None)))
