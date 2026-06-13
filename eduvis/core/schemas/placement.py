"""Placement schema validation for EduVis Core."""

from __future__ import annotations

VALID_PHASES = frozenset({
    "hook", "explore", "explain", "guided_practice",
    "independent_practice", "challenge", "reflect", "recall",
})

VALID_MEMORY_ROLES = frozenset({
    "anchor", "example", "practice", "misconception_fix", "retrieval", "review",
})

VALID_DIFFICULTY = frozenset({"starter", "routine", "challenge"})

VALID_PURPOSES = frozenset({
    "conceptual_model", "worked_example", "comparison", "procedure", "summary",
})

VALID_LAYOUT_ZONES = frozenset({"center", "left", "right", "full", "bottom"})

VALID_VISUAL_WEIGHTS = frozenset({"primary", "supporting"})


def validate(element_id: str, placement: dict) -> list[str]:
    """Validate a placement dict. Returns warning strings."""
    warnings: list[str] = []

    if not isinstance(placement, dict):
        warnings.append(
            f"[{element_id}] placement must be a mapping, got {type(placement).__name__}"
        )
        return warnings

    phase = placement.get("lesson_phase")
    if phase is None:
        warnings.append(f"[{element_id}] placement.lesson_phase is required")
    elif phase not in VALID_PHASES:
        warnings.append(
            f"[{element_id}] placement.lesson_phase '{phase}' is not valid; "
            f"choose from: {', '.join(sorted(VALID_PHASES))}"
        )

    role = placement.get("memory_role")
    if role is None:
        warnings.append(f"[{element_id}] placement.memory_role is required")
    elif role not in VALID_MEMORY_ROLES:
        warnings.append(
            f"[{element_id}] placement.memory_role '{role}' is not valid; "
            f"choose from: {', '.join(sorted(VALID_MEMORY_ROLES))}"
        )

    difficulty = placement.get("difficulty")
    if difficulty is not None and difficulty not in VALID_DIFFICULTY:
        warnings.append(
            f"[{element_id}] placement.difficulty '{difficulty}' is not valid; "
            f"choose from: {', '.join(sorted(VALID_DIFFICULTY))}"
        )

    purpose = placement.get("purpose")
    if purpose is not None and purpose not in VALID_PURPOSES:
        warnings.append(
            f"[{element_id}] placement.purpose '{purpose}' is not valid; "
            f"choose from: {', '.join(sorted(VALID_PURPOSES))}"
        )

    layout_zone = placement.get("layout_zone")
    if layout_zone is not None and layout_zone not in VALID_LAYOUT_ZONES:
        warnings.append(
            f"[{element_id}] placement.layout_zone '{layout_zone}' is not valid; "
            f"choose from: {', '.join(sorted(VALID_LAYOUT_ZONES))}"
        )

    visual_weight = placement.get("visual_weight")
    if visual_weight is not None and visual_weight not in VALID_VISUAL_WEIGHTS:
        warnings.append(
            f"[{element_id}] placement.visual_weight '{visual_weight}' is not valid; "
            f"choose from: {', '.join(sorted(VALID_VISUAL_WEIGHTS))}"
        )

    return warnings
