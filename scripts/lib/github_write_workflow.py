from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any


class GitHubWriteBlocked(ValueError):
    """Raised when a GitHub write action would be unsafe or unsupported."""


_ALLOWED_PR_STATES = {"open", "merged", "closed"}
_STEP_ID = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class PullRequestStatus:
    number: int
    state: str
    head_ref: str
    base_ref: str
    url: str | None = None


def normalize_pr(pr: dict[str, Any]) -> PullRequestStatus:
    """Normalize provider PR metadata without guessing merge state."""
    try:
        number = int(pr["number"])
    except (KeyError, TypeError, ValueError) as exc:
        raise GitHubWriteBlocked("PR-metadata saknar giltigt nummer.") from exc

    merged = pr.get("merged")
    raw_state = str(pr.get("state", "")).lower().strip()
    if merged is True:
        state = "merged"
    elif raw_state == "closed":
        state = "closed"
    elif raw_state == "open":
        state = "open"
    else:
        raise GitHubWriteBlocked("PR-status måste kunna verifieras som open, merged eller closed.")

    head = str(pr.get("head_ref") or pr.get("branch") or "").strip()
    base = str(pr.get("base_ref") or pr.get("base") or "").strip()
    if not head or not base:
        raise GitHubWriteBlocked("PR-metadata måste innehålla head_ref och base_ref.")
    return PullRequestStatus(number=number, state=state, head_ref=head, base_ref=base, url=pr.get("url"))


def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:40] or "step"


def branch_name(step_id: str, *, sequence: int = 1) -> str:
    if not _STEP_ID.match(step_id):
        raise GitHubWriteBlocked(f"Ogiltigt steg-id för branch: {step_id}")
    suffix = _slug(step_id)
    return f"repository-fixer/{sequence:02d}-{suffix}"


def initialize_github_write_state(source_context: dict[str, Any]) -> dict[str, Any]:
    """Create portable write-state from a verified GitHub read context."""
    if source_context.get("mode") != "github":
        raise GitHubWriteBlocked("GitHub write-state kräver GitHub-källkontext.")
    if source_context.get("writable") is not True:
        raise GitHubWriteBlocked("Skrivåtkomst måste vara verifierad innan branch eller PR skapas.")
    default_branch = str(source_context.get("default_branch") or "").strip()
    if not default_branch:
        raise GitHubWriteBlocked("Default branch måste vara verifierad före skrivning.")
    return {
        "repository": deepcopy(source_context["repository"]),
        "default_branch": default_branch,
        "base_sha": source_context.get("commit_sha"),
        "active_branch": None,
        "active_pr": None,
        "pr_sequence": 0,
        "commits": [],
        "history": [],
    }


def _history(state: dict[str, Any], action: str, **extra: Any) -> None:
    event = {"sequence": len(state["history"]) + 1, "action": action}
    event.update({k: v for k, v in extra.items() if v is not None})
    state["history"].append(event)


def refresh_pr_state(state: dict[str, Any], pr: dict[str, Any] | None) -> dict[str, Any]:
    """Refresh current PR status before another write step."""
    if state.get("active_pr") is None:
        return state
    if pr is None:
        raise GitHubWriteBlocked("Aktiv PR måste statuskontrolleras före nästa GitHub-ändring.")
    normalized = normalize_pr(pr)
    if normalized.number != state["active_pr"]["number"]:
        raise GitHubWriteBlocked("PR-statusen avser inte den aktiva Repository Fixer-PR:n.")
    state["active_pr"] = {
        "number": normalized.number,
        "state": normalized.state,
        "head_ref": normalized.head_ref,
        "base_ref": normalized.base_ref,
        "url": normalized.url,
    }
    _history(state, "pr-refreshed", pr_number=normalized.number, pr_state=normalized.state)
    return state


def plan_write_target(
    state: dict[str, Any],
    step_id: str,
    *,
    refreshed_pr: dict[str, Any] | None = None,
    default_branch_sha: str | None = None,
) -> dict[str, Any]:
    """Return the only safe next GitHub write preparation action.

    This function does not perform network writes. It tells the caller whether to
    reuse an open PR, create a new branch/PR, or stop for user/provider handling.
    """
    if state.get("active_pr") is not None:
        refresh_pr_state(state, refreshed_pr)
        pr = state["active_pr"]
        if pr["state"] == "open":
            if pr["base_ref"] != state["default_branch"]:
                return {
                    "action": "review-pr",
                    "reason": "Den öppna PR:n har annan base branch än aktuell default branch.",
                    "pr_number": pr["number"],
                }
            return {
                "action": "reuse-open-pr",
                "branch": pr["head_ref"],
                "pr_number": pr["number"],
                "step_id": step_id,
            }
        if pr["state"] == "closed":
            return {
                "action": "review-closed-pr",
                "pr_number": pr["number"],
                "reason": "PR:n är stängd utan verifierad merge; fortsätt inte på branchen automatiskt.",
            }
        if pr["state"] == "merged":
            if not default_branch_sha:
                return {
                    "action": "refresh-default-branch",
                    "reason": "Efter merge måste aktuell default branch läsas om innan ny arbetsbranch skapas.",
                }
            state["base_sha"] = default_branch_sha
            state["active_branch"] = None
            state["active_pr"] = None
            _history(state, "merged-pr-retired", base_sha=default_branch_sha)

    sequence = int(state.get("pr_sequence", 0)) + 1
    return {
        "action": "create-branch-and-pr",
        "branch": branch_name(step_id, sequence=sequence),
        "base_branch": state["default_branch"],
        "base_sha": state.get("base_sha"),
        "step_id": step_id,
        "sequence": sequence,
    }


def record_pr_created(
    state: dict[str, Any],
    *,
    branch: str,
    pr: dict[str, Any],
    sequence: int | None = None,
) -> dict[str, Any]:
    normalized = normalize_pr(pr)
    if normalized.state != "open":
        raise GitHubWriteBlocked("En ny Repository Fixer-PR måste vara open när den registreras.")
    if normalized.head_ref != branch:
        raise GitHubWriteBlocked("PR head_ref matchar inte den skapade arbetsbranchen.")
    if normalized.base_ref != state["default_branch"]:
        raise GitHubWriteBlocked("PR base_ref matchar inte aktuell default branch.")
    state["active_branch"] = branch
    state["active_pr"] = {
        "number": normalized.number,
        "state": normalized.state,
        "head_ref": normalized.head_ref,
        "base_ref": normalized.base_ref,
        "url": normalized.url,
    }
    state["pr_sequence"] = sequence if sequence is not None else int(state.get("pr_sequence", 0)) + 1
    _history(state, "pr-created", pr_number=normalized.number, branch=branch)
    return state


def conventional_commit_message(step: dict[str, Any]) -> str:
    """Create a conservative commit subject from the plan step, not from guesses."""
    categories = {str(fid).split("-")[1].lower() for fid in step.get("finding_ids", []) if str(fid).startswith("RF-") and len(str(fid).split("-")) > 2}
    title = str(step.get("title") or step.get("id") or "repository maintenance").strip()
    if categories and categories <= {"readme", "docs", "markdown"}:
        prefix = "docs"
    elif categories and categories <= {"ci", "github", "actions"}:
        prefix = "ci"
    else:
        prefix = "chore"
    subject = re.sub(r"\s+", " ", title).rstrip(".")
    return f"{prefix}: {subject}"[:72].rstrip()


def record_step_commit(
    state: dict[str, Any],
    *,
    step_id: str,
    commit_sha: str,
    message: str,
) -> dict[str, Any]:
    pr = state.get("active_pr")
    if not pr or pr.get("state") != "open" or not state.get("active_branch"):
        raise GitHubWriteBlocked("Commit får bara registreras på en verifierat öppen Repository Fixer-PR.")
    if any(c.get("step_id") == step_id for c in state.get("commits", [])):
        raise GitHubWriteBlocked("Plansteget har redan en registrerad commit i aktuell GitHub-state.")
    if not str(commit_sha).strip() or not str(message).strip():
        raise GitHubWriteBlocked("Commit kräver verifierad SHA och commitmeddelande.")
    state["commits"].append({
        "step_id": step_id,
        "sha": str(commit_sha).strip(),
        "message": str(message).strip(),
        "pr_number": pr["number"],
        "branch": state["active_branch"],
    })
    _history(state, "step-committed", step_id=step_id, commit_sha=str(commit_sha).strip(), pr_number=pr["number"])
    return state
