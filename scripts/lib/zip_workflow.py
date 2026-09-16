from __future__ import annotations

import json
import os
import shutil
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


METADATA_DIR = ".repository-fixer"
PORTABLE_FILES = {
    "analysis_md": "analysis.md",
    "plan_md": "plan.md",
    "progress_md": "progress.md",
    "analysis_json": "analysis.json",
    "plan_json": "plan.json",
    "progress_json": "progress.json",
    "state_json": "state.json",
}


class UnsafeZipError(ValueError):
    """Raised when an input archive cannot be extracted safely."""


@dataclass(frozen=True)
class ZipWorkspace:
    source_zip: Path
    extraction_root: Path
    repository_root: Path
    wrapper_prefix: str | None


def _safe_relative_name(name: str) -> PurePosixPath:
    if "\x00" in name:
        raise UnsafeZipError("ZIP-posten innehåller NUL-tecken.")
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or normalized.startswith("/"):
        raise UnsafeZipError(f"Absolut sökväg är inte tillåten i ZIP: {name}")
    if path.parts and ":" in path.parts[0]:
        raise UnsafeZipError(f"Enhets-/drive-sökväg är inte tillåten i ZIP: {name}")
    if any(part in {"", ".", ".."} for part in path.parts if part != "."):
        # Empty segments are harmless in a ZIP filename, but '..' is not. Keep
        # the message strict and handle '.' explicitly below.
        if ".." in path.parts:
            raise UnsafeZipError(f"Path traversal är inte tillåten i ZIP: {name}")
    if any(part == ".." for part in path.parts):
        raise UnsafeZipError(f"Path traversal är inte tillåten i ZIP: {name}")
    return path


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_IFMT(mode) == stat.S_IFLNK


def _mode_from_info(info: zipfile.ZipInfo, default: int) -> int:
    mode = (info.external_attr >> 16) & 0o777
    return mode or default


def _detect_wrapper(extraction_root: Path, extracted_files: list[Path]) -> tuple[Path, str | None]:
    rel_files = [p.relative_to(extraction_root) for p in extracted_files]
    top = {rel.parts[0] for rel in rel_files if rel.parts}
    if len(top) == 1:
        only = next(iter(top))
        candidate = extraction_root / only
        # A wrapper is meaningful only when it is a directory containing the repo,
        # not when the ZIP simply contains one root-level file.
        if candidate.is_dir():
            return candidate, only
    return extraction_root, None


def prepare_workspace(source_zip: Path | str, workspace_dir: Path | str) -> ZipWorkspace:
    """Safely extract a repository ZIP into a disposable workspace.

    The source archive is never modified. Path traversal, absolute paths and
    symbolic-link members are rejected rather than followed.
    """
    source = Path(source_zip).resolve()
    workspace = Path(workspace_dir).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if not zipfile.is_zipfile(source):
        raise ValueError(f"Inte en giltig ZIP-fil: {source}")
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    extracted_files: list[Path] = []
    with zipfile.ZipFile(source, "r") as zf:
        infos = zf.infolist()
        if not infos:
            raise ValueError("Repository-ZIP:en är tom.")
        for info in infos:
            rel = _safe_relative_name(info.filename)
            if _is_symlink(info):
                raise UnsafeZipError(f"Symbolisk länk i ZIP kräver manuell hantering: {info.filename}")
            if not rel.parts:
                continue
            target = workspace.joinpath(*rel.parts)
            # Defence in depth after path parsing.
            try:
                target.resolve().relative_to(workspace)
            except ValueError as exc:
                raise UnsafeZipError(f"ZIP-post lämnar arbetskatalogen: {info.filename}") from exc
            if info.is_dir() or info.filename.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
                os.chmod(target, _mode_from_info(info, 0o755))
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info, "r") as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            os.chmod(target, _mode_from_info(info, 0o644))
            extracted_files.append(target)

    if not extracted_files:
        raise ValueError("Repository-ZIP:en innehåller inga filer.")
    repository_root, wrapper_prefix = _detect_wrapper(workspace, extracted_files)
    return ZipWorkspace(source, workspace, repository_root, wrapper_prefix)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_portable_state(
    repository_root: Path | str,
    *,
    analysis_md: str,
    plan_md: str,
    progress_md: str,
    analysis: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None,
    progress: dict[str, Any] | None = None,
    state: dict[str, Any] | None = None,
) -> Path:
    """Persist human-readable and optional structured resume state in the repo."""
    root = Path(repository_root)
    metadata = root / METADATA_DIR
    metadata.mkdir(parents=True, exist_ok=True)
    _write_text(metadata / PORTABLE_FILES["analysis_md"], analysis_md)
    _write_text(metadata / PORTABLE_FILES["plan_md"], plan_md)
    _write_text(metadata / PORTABLE_FILES["progress_md"], progress_md)
    if analysis is not None:
        _write_json(metadata / PORTABLE_FILES["analysis_json"], analysis)
    if plan is not None:
        _write_json(metadata / PORTABLE_FILES["plan_json"], plan)
    if progress is not None:
        _write_json(metadata / PORTABLE_FILES["progress_json"], progress)

    portable_state = {
        "schema_version": 1,
        "mode": "zip",
        "metadata_dir": METADATA_DIR,
        "artifacts": {
            "analysis": PORTABLE_FILES["analysis_md"],
            "plan": PORTABLE_FILES["plan_md"],
            "progress": PORTABLE_FILES["progress_md"],
        },
        "structured": {
            "analysis": PORTABLE_FILES["analysis_json"] if analysis is not None else None,
            "plan": PORTABLE_FILES["plan_json"] if plan is not None else None,
            "progress": PORTABLE_FILES["progress_json"] if progress is not None else None,
        },
    }
    if state:
        portable_state.update(state)
    _write_json(metadata / PORTABLE_FILES["state_json"], portable_state)
    return metadata


def load_portable_state(repository_root: Path | str) -> dict[str, Any] | None:
    root = Path(repository_root)
    metadata = root / METADATA_DIR
    state_path = metadata / PORTABLE_FILES["state_json"]
    if not state_path.exists():
        return None
    state = json.loads(state_path.read_text(encoding="utf-8"))
    result: dict[str, Any] = {"state": state, "metadata_dir": metadata}
    for key in ["analysis_md", "plan_md", "progress_md"]:
        path = metadata / PORTABLE_FILES[key]
        result[key] = path.read_text(encoding="utf-8") if path.exists() else None
    for key in ["analysis_json", "plan_json", "progress_json"]:
        path = metadata / PORTABLE_FILES[key]
        result[key] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    return result


def remove_portable_state(repository_root: Path | str) -> bool:
    metadata = Path(repository_root) / METADATA_DIR
    if not metadata.exists():
        return False
    shutil.rmtree(metadata)
    return True


def _zip_info_for(path: Path, arcname: str, is_dir: bool = False) -> zipfile.ZipInfo:
    # Keep the archive reproducible enough for tests while preserving executable
    # permission bits from the working tree.
    info = zipfile.ZipInfo(arcname + ("/" if is_dir and not arcname.endswith("/") else ""))
    info.compress_type = zipfile.ZIP_DEFLATED
    mode = stat.S_IMODE(path.stat().st_mode)
    kind = stat.S_IFDIR if is_dir else stat.S_IFREG
    info.external_attr = (kind | mode) << 16
    return info


def package_workspace(
    workspace: ZipWorkspace,
    output_zip: Path | str,
    *,
    include_portable_state: bool = True,
) -> Path:
    """Build a complete updated ZIP from the repository working copy."""
    root = workspace.repository_root
    output = Path(output_zip).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output.with_suffix(output.suffix + ".tmp")
    if temp_output.exists():
        temp_output.unlink()

    prefix = workspace.wrapper_prefix
    with zipfile.ZipFile(temp_output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        paths = sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix())
        for path in paths:
            rel = path.relative_to(root)
            if not include_portable_state and rel.parts and rel.parts[0] == METADATA_DIR:
                continue
            arc = PurePosixPath(prefix, *rel.parts).as_posix() if prefix else rel.as_posix()
            if path.is_symlink():
                raise UnsafeZipError(f"Symbolisk länk i arbetskopian kräver manuell hantering: {rel.as_posix()}")
            if path.is_dir():
                # Keep empty directories; non-empty directories are implicit.
                try:
                    next(path.iterdir())
                except StopIteration:
                    zf.writestr(_zip_info_for(path, arc, is_dir=True), b"")
                continue
            info = _zip_info_for(path, arc)
            zf.writestr(info, path.read_bytes())
    temp_output.replace(output)
    return output
