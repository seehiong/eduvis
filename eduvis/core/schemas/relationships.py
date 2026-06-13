"""Relationships schema validation for EduVis Core."""

from __future__ import annotations

VALID_TYPES = frozenset({
    "anchors", "contradicts", "precedes", "reinforces", "parallels",
    "remediation_for",
})


def validate(element_id: str, relationships: dict, known_ids: set[str]) -> list[str]:
    """
    Validate a relationships dict.

    known_ids: all element IDs declared in the lesson (for referential integrity).
    Returns warning strings.
    """
    warnings: list[str] = []

    if not isinstance(relationships, dict):
        warnings.append(
            f"[{element_id}] relationships must be a mapping, got {type(relationships).__name__}"
        )
        return warnings

    for rel_type, targets in relationships.items():
        if rel_type not in VALID_TYPES:
            warnings.append(
                f"[{element_id}] relationships.{rel_type} is not a recognised type; "
                f"choose from: {', '.join(sorted(VALID_TYPES))}"
            )
            continue

        if not isinstance(targets, list):
            warnings.append(
                f"[{element_id}] relationships.{rel_type} must be a list of IDs, "
                f"got {type(targets).__name__}"
            )
            continue

        for target in targets:
            if not isinstance(target, str):
                warnings.append(
                    f"[{element_id}] relationships.{rel_type} entry must be a string ID, "
                    f"got {type(target).__name__}"
                )
            elif known_ids and target not in known_ids:
                warnings.append(
                    f"[{element_id}] relationships.{rel_type} references unknown ID '{target}'"
                )

    return warnings
