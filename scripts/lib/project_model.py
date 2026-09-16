from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def load_project_config(root: Path) -> dict[str, Any]:
    return load_yaml(root / "gpt-project.yaml")


def load_project_status(root: Path) -> dict[str, Any]:
    return load_yaml(root / "project-status.yaml")


def select_reference_profile(features: dict[str, Any]) -> str:
    """Return the canonical reference profile for a feature set."""
    if (
        features.get("research_heavy")
        or features.get("evidence_required")
        or features.get("multi_stage_workflow")
    ):
        return "workflow_research_heavy"

    if (
        features.get("project_zip_manipulation")
        or features.get("scripts_required")
        or features.get("rich_structured_runtime")
    ):
        return "zip_first_advanced"

    if (
        features.get("structured_knowledge")
        or features.get("repeatable_outputs")
        or features.get("moderate_workflow")
    ):
        return "standard"

    return "simple"


def get_registered_next_step(status: dict[str, Any]) -> dict[str, Any] | None:
    value = status.get("next_step")
    return value if isinstance(value, dict) and value else None


def get_blockers(status: dict[str, Any]) -> list[Any]:
    return list(status.get("blocking_issues") or status.get("blockers") or [])
