import hashlib
import json
import os
import stat
import zipfile
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from scripts.lib.zip_workflow import (
    UnsafeZipError,
    load_portable_state,
    package_workspace,
    prepare_workspace,
    remove_portable_state,
    write_portable_state,
)

ROOT = Path(__file__).resolve().parents[1]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_zip(path: Path, entries: dict[str, bytes], executable: set[str] | None = None):
    executable = executable or set()
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in entries.items():
            info = zipfile.ZipInfo(name)
            mode = 0o755 if name in executable else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            zf.writestr(info, content)


def test_prepare_workspace_preserves_wrapper_bytes_and_source(tmp_path):
    source = tmp_path / "repo.zip"
    _make_zip(source, {
        "demo/README.md": b"# Demo\n",
        "demo/.gitignore": b"dist/\n",
        "demo/bin/run.sh": b"#!/bin/sh\necho ok\n",
    }, executable={"demo/bin/run.sh"})
    before = _sha(source)
    ws = prepare_workspace(source, tmp_path / "work")
    assert ws.wrapper_prefix == "demo"
    assert ws.repository_root.name == "demo"
    assert (ws.repository_root / ".gitignore").read_bytes() == b"dist/\n"
    assert os.access(ws.repository_root / "bin/run.sh", os.X_OK)
    assert _sha(source) == before


def test_prepare_workspace_rejects_path_traversal(tmp_path):
    source = tmp_path / "bad.zip"
    _make_zip(source, {"../escape.txt": b"bad"})
    with pytest.raises(UnsafeZipError, match="Path traversal"):
        prepare_workspace(source, tmp_path / "work")
    assert not (tmp_path / "escape.txt").exists()


def test_prepare_workspace_rejects_absolute_path(tmp_path):
    source = tmp_path / "bad.zip"
    _make_zip(source, {"/etc/repository-fixer-test": b"bad"})
    with pytest.raises(UnsafeZipError, match="Absolut"):
        prepare_workspace(source, tmp_path / "work")


def test_prepare_workspace_rejects_symlink_member(tmp_path):
    source = tmp_path / "bad.zip"
    with zipfile.ZipFile(source, "w") as zf:
        info = zipfile.ZipInfo("demo/link")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        zf.writestr(info, "../outside")
    with pytest.raises(UnsafeZipError, match="Symbolisk länk"):
        prepare_workspace(source, tmp_path / "work")


def test_portable_state_roundtrips_and_schema_validates(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    metadata = write_portable_state(
        root,
        analysis_md="# Analysis",
        plan_md="# Plan",
        progress_md="# Progress",
        analysis={"repository_name": "demo"},
        plan={"repository_name": "demo", "steps": []},
        progress={"repository_name": "demo", "steps": [], "history": []},
        state={"last_completed_step": "STEP-01", "repository_fingerprint": "abc123"},
    )
    assert (metadata / "analysis.md").exists()
    loaded = load_portable_state(root)
    assert loaded["analysis_md"].startswith("# Analysis")
    assert loaded["plan_json"]["repository_name"] == "demo"
    assert loaded["state"]["last_completed_step"] == "STEP-01"
    schema = json.loads((ROOT / "schemas/repository-zip-state.schema.json").read_text())
    Draft202012Validator(schema).validate(loaded["state"])


def test_package_workspace_is_complete_and_keeps_wrapper(tmp_path):
    source = tmp_path / "repo.zip"
    _make_zip(source, {"demo/README.md": b"old\n", "demo/src/app.txt": b"code\n"})
    ws = prepare_workspace(source, tmp_path / "work")
    (ws.repository_root / "README.md").write_text("new\n", encoding="utf-8")
    write_portable_state(ws.repository_root, analysis_md="a", plan_md="p", progress_md="s")
    out = package_workspace(ws, tmp_path / "updated.zip")
    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist())
        assert "demo/README.md" in names
        assert "demo/src/app.txt" in names
        assert "demo/.repository-fixer/analysis.md" in names
        assert zf.read("demo/README.md") == b"new\n"


def test_package_workspace_can_strip_only_portable_metadata(tmp_path):
    source = tmp_path / "repo.zip"
    _make_zip(source, {"README.md": b"hello\n", ".hidden": b"keep\n"})
    ws = prepare_workspace(source, tmp_path / "work")
    write_portable_state(ws.repository_root, analysis_md="a", plan_md="p", progress_md="s")
    out = package_workspace(ws, tmp_path / "clean.zip", include_portable_state=False)
    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist())
        assert "README.md" in names
        assert ".hidden" in names
        assert not any(name.startswith(".repository-fixer/") for name in names)
    # Packaging a clean final ZIP must not silently delete the working metadata.
    assert (ws.repository_root / ".repository-fixer/progress.md").exists()


def test_remove_portable_state_is_explicit(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    write_portable_state(root, analysis_md="a", plan_md="p", progress_md="s")
    assert remove_portable_state(root) is True
    assert not (root / ".repository-fixer").exists()
    assert remove_portable_state(root) is False
