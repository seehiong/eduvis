"""Actions schema validation for EduVis Core."""

from __future__ import annotations

from typing import Any

VALID_CONCEPTUAL = frozenset({"compare", "predict", "identify", "retrieve", "apply"})
VALID_PROCEDURAL = frozenset({"substitute", "simplify", "calculate", "round"})


def _action_name(action: Any) -> str:
    """Extract the name from a bare string or a single-key dict."""
    if isinstance(action, str):
        return action
    if isinstance(action, dict):
        return next(iter(action), "")
    return str(action)


def validate(element_id: str, actions: dict) -> list[str]:
    """Validate an actions dict. Returns warning strings."""
    warnings: list[str] = []

    if not isinstance(actions, dict):
        warnings.append(
            f"[{element_id}] actions must be a mapping with 'conceptual' and/or "
            f"'procedural' keys, got {type(actions).__name__}"
        )
        return warnings

    for key in actions:
        if key not in ("conceptual", "procedural"):
            warnings.append(
                f"[{element_id}] actions.{key} is not a recognised group; "
                f"use 'conceptual' or 'procedural'"
            )

    conceptual = actions.get("conceptual", [])
    if not isinstance(conceptual, list):
        warnings.append(f"[{element_id}] actions.conceptual must be a list")
    else:
        for action in conceptual:
            name = _action_name(action)
            if name not in VALID_CONCEPTUAL:
                warnings.append(
                    f"[{element_id}] actions.conceptual unknown action '{name}'; "
                    f"choose from: {', '.join(sorted(VALID_CONCEPTUAL))}"
                )

    procedural = actions.get("procedural", [])
    if not isinstance(procedural, list):
        warnings.append(f"[{element_id}] actions.procedural must be a list")
    else:
        for action in procedural:
            name = _action_name(action)
            if name not in VALID_PROCEDURAL:
                warnings.append(
                    f"[{element_id}] actions.procedural unknown action '{name}'; "
                    f"choose from: {', '.join(sorted(VALID_PROCEDURAL))}"
                )

    return warnings
