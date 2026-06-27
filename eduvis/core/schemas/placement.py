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

VALID_ASSESSMENT_OBJECTIVES = frozenset({
    "procedural_fluency", "conceptual_understanding", "application", "reasoning",
})

VALID_INTENTS = frozenset({
    "confidence_building", "reduce_anxiety", "curiosity", "productive_struggle",
})

VALID_SCAFFOLDING_LEVELS = frozenset({
    "high", "medium", "low",
})


def _check_field(element_id: str, name: str, val: str | None, valid_set: frozenset[str], required: bool = False) -> str | None:
    if val is None:
        if required:
            return f"[{element_id}] placement.{name} is required"
        return None
    if val not in valid_set:
        return (
            f"[{element_id}] placement.{name} '{val}' is not valid; "
            f"choose from: {', '.join(sorted(valid_set))}"
        )
    return None


def validate(element_id: str, placement: dict) -> list[str]:
    """Validate a placement dict. Returns warning strings."""
    warnings: list[str] = []

    if not isinstance(placement, dict):
        warnings.append(
            f"[{element_id}] placement must be a mapping, got {type(placement).__name__}"
        )
        return warnings

    checks = [
        ("lesson_phase", placement.get("lesson_phase"), VALID_PHASES, True),
        ("memory_role", placement.get("memory_role"), VALID_MEMORY_ROLES, True),
        ("difficulty", placement.get("difficulty"), VALID_DIFFICULTY, False),
        ("purpose", placement.get("purpose"), VALID_PURPOSES, False),
        ("layout_zone", placement.get("layout_zone"), VALID_LAYOUT_ZONES, False),
        ("visual_weight", placement.get("visual_weight"), VALID_VISUAL_WEIGHTS, False),
        ("assessment_objective", placement.get("assessment_objective"), VALID_ASSESSMENT_OBJECTIVES, False),
    ]

    for name, val, valid_set, required in checks:
        warn = _check_field(element_id, name, val, valid_set, required)
        if warn:
            warnings.append(warn)

    # Validate pedagogical_intent
    pedagogical_intent = placement.get("pedagogical_intent")
    if pedagogical_intent is not None:
        if not isinstance(pedagogical_intent, dict):
            warnings.append(
                f"[{element_id}] placement.pedagogical_intent must be a mapping, got {type(pedagogical_intent).__name__}"
            )
        else:
            # Check unexpected fields
            for key in pedagogical_intent:
                if key not in ("intent", "scaffolding_level"):
                    warnings.append(
                        f"[{element_id}] placement.pedagogical_intent unexpected key '{key}'"
                    )

            intent_checks = [
                ("intent", pedagogical_intent.get("intent"), VALID_INTENTS, False),
                ("scaffolding_level", pedagogical_intent.get("scaffolding_level"), VALID_SCAFFOLDING_LEVELS, False),
            ]
            for name, val, valid_set, required in intent_checks:
                warn = _check_field(element_id, f"pedagogical_intent.{name}", val, valid_set, required)
                if warn:
                    warnings.append(warn)

    _validate_scaffolding_constraints(element_id, placement, warnings)

    return warnings


def _validate_scaffolding_constraints(element_id: str, placement: dict, warnings: list[str]) -> None:
    pedagogical_intent = placement.get("pedagogical_intent")
    lesson_phase = placement.get("lesson_phase")
    if lesson_phase in ("recall", "independent_practice", "challenge") and pedagogical_intent:
        scaffolding = pedagogical_intent.get("scaffolding_level")
        if scaffolding is not None and scaffolding != "low":
            warnings.append(
                f"[{element_id}] lesson_phase '{lesson_phase}' cannot have scaffolding_level '{scaffolding}' "
                f"(must be 'low')"
            )
