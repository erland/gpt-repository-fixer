from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import urlparse


class InvalidGitHubRepository(ValueError):
    """Raised when a GitHub repository URL or snapshot is unsafe/invalid."""


@dataclass(frozen=True)
class GitHubRepositoryRef:
    owner: str
    repo: str
    web_url: str


@dataclass(frozen=True)
class GitHubRepositorySnapshot:
    repository: GitHubRepositoryRef
    default_branch: str
    resolved_ref: str
    files: dict[str, bytes]
    commit_sha: str | None = None
    writable: bool | None = None
    open_pull_requests: tuple[dict[str, Any], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class GitHubWorkspace:
    snapshot: GitHubRepositorySnapshot
    workspace_root: Path
    repository_root: Path


_OWNER_REPO = re.compile(r"^[A-Za-z0-9_.-]+$")


def parse_github_repository_url(url: str) -> GitHubRepositoryRef:
    """Normalize a github.com repository URL to owner/repo.

    Repository subpaths such as /tree/<ref>/... are accepted as navigation input,
    but the canonical source identity remains the repository itself. The actual
    analyzed ref must come from repository metadata, not be guessed from URL text.
    """
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"github.com", "www.github.com"}:
        raise InvalidGitHubRepository("Endast http(s)-länkar till github.com stöds.")
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        raise InvalidGitHubRepository("GitHub-länken måste innehålla owner/repository.")
    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not owner or not repo or not _OWNER_REPO.match(owner) or not _OWNER_REPO.match(repo):
        raise InvalidGitHubRepository("Ogiltigt owner- eller repositorynamn.")
    return GitHubRepositoryRef(owner=owner, repo=repo, web_url=f"https://github.com/{owner}/{repo}")


def _safe_repo_path(value: str) -> PurePosixPath:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or normalized.startswith("/"):
        raise InvalidGitHubRepository(f"Ogiltig repository-sökväg: {value}")
    if path.parts and ":" in path.parts[0]:
        raise InvalidGitHubRepository(f"Drive-sökväg är inte tillåten: {value}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise InvalidGitHubRepository(f"Osäker repository-sökväg: {value}")
    return path


def validate_snapshot(snapshot: GitHubRepositorySnapshot) -> None:
    if not snapshot.default_branch.strip():
        raise InvalidGitHubRepository("Default branch saknas i GitHub-metadata.")
    if not snapshot.resolved_ref.strip():
        raise InvalidGitHubRepository("Analyserad Git-ref saknas.")
    if not snapshot.files:
        raise InvalidGitHubRepository("GitHub-repositoryt innehåller inga läsbara filer.")
    for path in snapshot.files:
        _safe_repo_path(path)


def materialize_snapshot(snapshot: GitHubRepositorySnapshot, workspace_dir: Path | str) -> GitHubWorkspace:
    """Materialize an already fetched GitHub snapshot for the common analyzers.

    Network access intentionally lives outside this helper. A GitHub connector/API/web
    reader fetches metadata and file bytes, then this function provides the exact same
    local filesystem shape consumed by ZIP analysis.
    """
    validate_snapshot(snapshot)
    workspace = Path(workspace_dir).resolve()
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    repo_root = workspace / snapshot.repository.repo
    repo_root.mkdir()

    for name, content in snapshot.files.items():
        rel = _safe_repo_path(name)
        target = repo_root.joinpath(*rel.parts)
        try:
            target.resolve().relative_to(repo_root)
        except ValueError as exc:
            raise InvalidGitHubRepository(f"Repositoryfil lämnar arbetskatalogen: {name}") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        # GitHub content APIs do not always expose executable mode. Do not invent it.
        os.chmod(target, 0o644)
    return GitHubWorkspace(snapshot=snapshot, workspace_root=workspace, repository_root=repo_root)


def repository_fixer_pull_requests(open_pull_requests: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return open PRs that plausibly belong to Repository Fixer without guessing ownership."""
    matches: list[dict[str, Any]] = []
    for pr in open_pull_requests:
        state = str(pr.get("state", "open")).lower()
        if state != "open":
            continue
        branch = str(pr.get("head_ref") or pr.get("branch") or "")
        title = str(pr.get("title") or "")
        if branch.startswith("repository-fixer/") or "repository fixer" in title.lower():
            matches.append(dict(pr))
    return matches


def build_github_read_context(snapshot: GitHubRepositorySnapshot) -> dict[str, Any]:
    """Create normalized source metadata used by reports/plans and later write flow."""
    validate_snapshot(snapshot)
    fixer_prs = repository_fixer_pull_requests(snapshot.open_pull_requests)
    limitations: list[str] = []
    if snapshot.writable is False:
        limitations.append(
            "Skrivåtkomst saknas. Analys och rapport kan göras, men branch/commit/PR kan inte skapas i GitHub-läget."
        )
    elif snapshot.writable is None:
        limitations.append(
            "Skrivåtkomst är inte verifierad. Analys är tillåten; verifiera behörighet innan branch/commit/PR skapas."
        )
    return {
        "mode": "github",
        "repository": {
            "owner": snapshot.repository.owner,
            "name": snapshot.repository.repo,
            "url": snapshot.repository.web_url,
        },
        "default_branch": snapshot.default_branch,
        "analyzed_ref": snapshot.resolved_ref,
        "commit_sha": snapshot.commit_sha,
        "writable": snapshot.writable,
        "repository_fixer_pull_requests": fixer_prs,
        "limitations": limitations,
    }
