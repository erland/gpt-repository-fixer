"""Small deterministic helpers for Repository Fixer's finding model."""

CLASS_LABELS = {
    "must-fix": "Bör åtgärdas",
    "recommended": "Rekommenderas",
    "consider": "Överväg",
    "passed": "Godkänd kontroll",
}

NEGATIVE_CLASSES = {"must-fix", "recommended"}


def validate_semantics(finding: dict) -> list[str]:
    """Return semantic errors not conveniently expressed by JSON Schema."""
    errors: list[str] = []
    classification = finding.get("classification")
    evidence = finding.get("evidence") or []

    if classification in NEGATIVE_CLASSES and not evidence:
        errors.append("negative findings require concrete evidence")

    if classification == "passed" and finding.get("recommended_action") is not None:
        errors.append("passed checks must not contain a recommended action")

    if finding.get("decision_required") and not finding.get("decision_reason"):
        errors.append("decision_required needs a decision_reason")

    for item in evidence:
        if item.get("kind") in {"file", "configuration", "cross-file"} and not item.get("path"):
            errors.append(f"{item.get('kind')} evidence requires a path")
        start = item.get("line_start")
        end = item.get("line_end")
        if start is not None and end is not None and end < start:
            errors.append("evidence line_end must be >= line_start")

    return errors
