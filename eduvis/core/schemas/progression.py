"""Progression schema validation for EduVis Core."""

from __future__ import annotations

VALID_PATTERNS = frozenset({"confidence_ladder", "direct_instruction", "flipped_recall"})
VALID_PEDAGOGY_FLAGS = frozenset({"confidence_first", "explain_why", "no_skipped_steps"})
VALID_PHASES = frozenset({
    "hook", "explore", "explain", "guided_practice",
    "independent_practice", "challenge", "reflect", "recall",
})
VALID_DIFFICULTY = frozenset({"starter", "routine", "challenge"})
VALID_PURPOSES = frozenset({
    "conceptual_model", "worked_example", "comparison", "procedure", "summary",
})


def validate(progression: dict) -> list[str]:
    """Validate a progression dict. Returns warning strings."""
    warnings: list[str] = []

    if not isinstance(progression, dict):
        warnings.append(
            f"[progression] must be a mapping, got {type(progression).__name__}"
        )
        return warnings

    pattern = progression.get("pattern")
    if pattern is None:
        warnings.append("[progression] pattern is required")
    elif pattern not in VALID_PATTERNS:
        warnings.append(
            f"[progression] pattern '{pattern}' is not valid; "
            f"choose from: {', '.join(sorted(VALID_PATTERNS))}"
        )

    pedagogy = progression.get("pedagogy", {})
    if not isinstance(pedagogy, dict):
        warnings.append("[progression] pedagogy must be a mapping")
    else:
        for flag, value in pedagogy.items():
            if flag not in VALID_PEDAGOGY_FLAGS:
                warnings.append(
                    f"[progression] pedagogy.{flag} is not a recognised flag; "
                    f"choose from: {', '.join(sorted(VALID_PEDAGOGY_FLAGS))}"
                )
            elif not isinstance(value, bool):
                warnings.append(
                    f"[progression] pedagogy.{flag} must be a boolean, "
                    f"got {type(value).__name__}"
                )

    phases = progression.get("phases", [])
    if not isinstance(phases, list):
        warnings.append("[progression] phases must be a list")
        return warnings

    for i, entry in enumerate(phases):
        if not isinstance(entry, dict):
            warnings.append(f"[progression] phases[{i}] must be a mapping")
            continue

        phase_name = entry.get("phase")
        if phase_name is None:
            warnings.append(f"[progression] phases[{i}] missing required 'phase' key")
        elif phase_name not in VALID_PHASES:
            warnings.append(
                f"[progression] phases[{i}].phase '{phase_name}' is not valid; "
                f"choose from: {', '.join(sorted(VALID_PHASES))}"
            )

        difficulty = entry.get("difficulty")
        if difficulty is not None and difficulty not in VALID_DIFFICULTY:
            warnings.append(
                f"[progression] phases[{i}].difficulty '{difficulty}' is not valid; "
                f"choose from: {', '.join(sorted(VALID_DIFFICULTY))}"
            )

        purpose = entry.get("purpose")
        if purpose is not None and purpose not in VALID_PURPOSES:
            warnings.append(
                f"[progression] phases[{i}].purpose '{purpose}' is not valid; "
                f"choose from: {', '.join(sorted(VALID_PURPOSES))}"
            )

        count = entry.get("count")
        if count is not None and (not isinstance(count, int) or count < 1):
            warnings.append(
                f"[progression] phases[{i}].count must be a positive integer, got {count!r}"
            )

    return warnings
