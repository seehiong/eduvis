"""
EduVis Core — Full lesson validator.

Validates a complete EduVis lesson document against all five pillars:
  Elements · Actions · Relationships · Placement · Progression
"""

from __future__ import annotations

import logging

from .registry import ElementRegistry
from .schemas import actions as actions_schema
from .schemas import placement as placement_schema
from .schemas import progression as progression_schema
from .schemas import relationships as relationships_schema

logger = logging.getLogger(__name__)


def validate_lesson(lesson_doc: dict) -> list[str]:
    """
    Validate a complete EduVis lesson document.

    lesson_doc: parsed YAML/dict with top-level keys: lesson, progression, content.
    Returns a list of warning strings (empty list = valid).
    """
    warnings: list[str] = []

    # ── lesson block ──────────────────────────────────────────────────────────
    lesson = lesson_doc.get("lesson")
    if not lesson:
        warnings.append("[lesson] missing required top-level 'lesson' block")
    elif not isinstance(lesson, dict):
        warnings.append("[lesson] must be a mapping")

    # ── progression block ─────────────────────────────────────────────────────
    progression = lesson_doc.get("progression")
    if progression is None:
        warnings.append("[lesson] missing 'progression' block")
    else:
        warnings.extend(progression_schema.validate(progression))

    # ── content block ─────────────────────────────────────────────────────────
    content = lesson_doc.get("content")
    if content is None:
        warnings.append("[lesson] missing 'content' block")
        return warnings
    if not isinstance(content, list):
        warnings.append("[lesson] 'content' must be a list")
        return warnings

    # Collect all IDs first for referential integrity
    known_ids: set[str] = set()
    id_counts: dict[str, int] = {}
    for item in content:
        if isinstance(item, dict):
            eid = item.get("id")
            if eid:
                id_counts[eid] = id_counts.get(eid, 0) + 1
                known_ids.add(str(eid))

    for eid, count in id_counts.items():
        if count > 1:
            warnings.append(f"[content] duplicate element id '{eid}'")

    # ── per-element validation ────────────────────────────────────────────────
    for item in content:
        if not isinstance(item, dict):
            warnings.append("[content] each element must be a mapping")
            continue

        element_id = str(item.get("id", "<no-id>"))
        element_type = item.get("type")

        if not item.get("id"):
            warnings.append("[content] element missing required 'id' field")

        if not element_type:
            warnings.append(f"[{element_id}] missing required 'type' field")
        else:
            # Validate element-specific fields against the registry
            warnings.extend(ElementRegistry.validate_fields(str(element_type), item))

        # Placement (required)
        placement = item.get("placement")
        if placement is None:
            warnings.append(f"[{element_id}] missing 'placement' block")
        else:
            warnings.extend(placement_schema.validate(element_id, placement))

        # Actions (optional)
        actions_data = item.get("actions")
        if actions_data is not None:
            warnings.extend(actions_schema.validate(element_id, actions_data))

        # Relationships (optional) — exclude self from referential check
        rels = item.get("relationships")
        if rels is not None:
            ref_ids = known_ids - {element_id}
            warnings.extend(relationships_schema.validate(element_id, rels, ref_ids))

    # ── pedagogy coherence checks ─────────────────────────────────────────────
    if progression:
        warnings.extend(_check_pedagogy_coherence(progression, content))

    return warnings


# ── Pedagogy coherence ────────────────────────────────────────────────────────

def _check_pedagogy_coherence(progression: dict, content: list[dict]) -> list[str]:
    """Check that pedagogy flags declared in progression are honoured by the content."""
    warnings: list[str] = []
    pedagogy = progression.get("pedagogy")
    if not isinstance(pedagogy, dict):
        return warnings

    if pedagogy.get("confidence_first"):
        warnings.extend(_check_confidence_first(content))
    if pedagogy.get("explain_why"):
        warnings.extend(_check_explain_why(content))
    if pedagogy.get("no_skipped_steps"):
        warnings.extend(_check_no_skipped_steps(content))

    return warnings


def _check_confidence_first(content: list[dict]) -> list[str]:
    """
    confidence_first: every starter-difficulty element must appear before
    every routine-difficulty element within independent_practice.
    """
    warnings: list[str] = []

    # Collect (doc_index, element_id, difficulty) for independent_practice only
    practice: list[tuple[int, str, str]] = []
    for doc_index, item in enumerate(content):
        if not isinstance(item, dict):
            continue
        placement = item.get("placement") or {}
        if not isinstance(placement, dict):
            continue
        if placement.get("lesson_phase") != "independent_practice":
            continue
        difficulty = placement.get("difficulty")
        if difficulty in ("starter", "routine", "challenge"):
            practice.append((doc_index, str(item.get("id", f"<index-{doc_index}>")), difficulty))

    starter_indices = [i for i, (_, _, d) in enumerate(practice) if d == "starter"]
    routine_indices = [i for i, (_, _, d) in enumerate(practice) if d == "routine"]

    if routine_indices and not starter_indices:
        warnings.append(
            "[pedagogy:confidence_first] no starter-difficulty independent_practice "
            "elements found; add at least one starter element before routine practice"
        )
    elif starter_indices and routine_indices:
        last_starter = max(starter_indices)
        first_routine = min(routine_indices)
        if first_routine < last_starter:
            offending_id = practice[first_routine][1]
            warnings.append(
                f"[pedagogy:confidence_first] routine element '{offending_id}' "
                f"appears before the last starter element; "
                f"all starter practice must precede routine practice"
            )

    return warnings


def _check_explain_why(content: list[dict]) -> list[str]:
    """
    explain_why: within the explain phase, a conceptual_model element must
    appear before any procedure element.
    """
    warnings: list[str] = []

    explain: list[tuple[int, str, str]] = []
    for doc_index, item in enumerate(content):
        if not isinstance(item, dict):
            continue
        placement = item.get("placement") or {}
        if not isinstance(placement, dict):
            continue
        if placement.get("lesson_phase") != "explain":
            continue
        purpose = placement.get("purpose")
        if purpose in ("conceptual_model", "procedure"):
            explain.append((doc_index, str(item.get("id", f"<index-{doc_index}>")), purpose))

    if not explain:
        return warnings

    conceptual_indices = [i for i, (_, _, p) in enumerate(explain) if p == "conceptual_model"]
    procedure_indices = [i for i, (_, _, p) in enumerate(explain) if p == "procedure"]

    if procedure_indices and not conceptual_indices:
        warnings.append(
            "[pedagogy:explain_why] explain phase has a 'procedure' element but no "
            "'conceptual_model' element; add a conceptual_model before the procedure"
        )
    elif conceptual_indices and procedure_indices:
        last_conceptual = max(conceptual_indices)
        first_procedure = min(procedure_indices)
        if first_procedure < last_conceptual:
            offending_id = explain[first_procedure][1]
            warnings.append(
                f"[pedagogy:explain_why] procedure element '{offending_id}' appears "
                f"before conceptual_model in the explain phase; "
                f"conceptual_model must come first"
            )

    return warnings


def _check_no_skipped_steps(content: list[dict]) -> list[str]:
    """
    no_skipped_steps: every guided_practice element must declare at least one
    action (conceptual or procedural). An undocumented guided example is always
    a violation. For computation topics, actions.procedural is expected; for
    purely conceptual topics, actions.conceptual is acceptable.
    """
    warnings: list[str] = []

    for item in content:
        if not isinstance(item, dict):
            continue
        placement = item.get("placement") or {}
        if not isinstance(placement, dict):
            continue
        if placement.get("lesson_phase") != "guided_practice":
            continue

        element_id = str(item.get("id", "<no-id>"))
        actions = item.get("actions") or {}
        if not isinstance(actions, dict):
            warnings.append(
                f"[pedagogy:no_skipped_steps] guided_practice element '{element_id}' "
                f"has no actions block; every guided example must document its steps"
            )
            continue

        conceptual = actions.get("conceptual") or []
        procedural = actions.get("procedural") or []
        total_actions = (len(conceptual) if isinstance(conceptual, list) else 0) + \
                        (len(procedural) if isinstance(procedural, list) else 0)

        if total_actions == 0:
            warnings.append(
                f"[pedagogy:no_skipped_steps] guided_practice element '{element_id}' "
                f"has an empty actions block; every step must be an explicit action "
                f"(use procedural for computation steps, conceptual for reasoning steps)"
            )

    return warnings
