"""
EduVis Core — Full lesson validator.

Validates a complete EduVis lesson document against all five pillars:
  Elements · Actions · Relationships · Placement · Progression
"""

from __future__ import annotations

import logging
from typing import Any

from .registry import ElementRegistry
from .constants import SCHEMA_VERSION
from .schemas import actions as actions_schema
from .schemas import placement as placement_schema
from .schemas import progression as progression_schema
from .schemas import relationships as relationships_schema
from .schemas import presentation as presentation_schema
from .concepts_validator import (
    check_concept_coherence,
    check_concept_prerequisites,
    is_assessment_element,
)
from .pedagogy_validator import (
    check_phase_sequence,
    check_pedagogy_coherence,
    check_anchor_density,
    check_remediations,
)

logger = logging.getLogger(__name__)


def validate_lesson(lesson_doc: dict) -> list[str]:
    """
    Validate a complete EduVis lesson document.

    lesson_doc: parsed YAML/dict with top-level keys: lesson, progression, content.
    Returns a list of warning/error strings (empty list = valid).
    """
    warnings: list[str] = []

    # ── schema version validation ─────────────────────────────────────────────
    version = lesson_doc.get("schema_version")
    if version is None:
        warnings.append(
            f"WARN: [lesson:version] missing 'schema_version' field. Assuming default \"{SCHEMA_VERSION}\"."
        )
    elif not isinstance(version, str):
        warnings.append(
            f"ERROR: [lesson:version] 'schema_version' must be a string, got {type(version).__name__}"
        )
    elif version != SCHEMA_VERSION:
        warnings.append(
            f"ERROR: [lesson:version] unsupported schema version \"{version}\". Expected \"{SCHEMA_VERSION}\"."
        )

    # ── curriculum block ──────────────────────────────────────────────────────
    curriculum = lesson_doc.get("curriculum")
    lesson = lesson_doc.get("lesson")
    _validate_curriculum(curriculum, lesson, warnings)

    # ── lesson block ──────────────────────────────────────────────────────────
    _validate_lesson_metadata(lesson, warnings)

    # ── progression block ─────────────────────────────────────────────────────
    progression = lesson_doc.get("progression")
    if progression is None:
        warnings.append("ERROR: [lesson] missing 'progression' block")
    else:
        for w in progression_schema.validate(progression):
            warnings.append(f"ERROR: {w}")

    # ── content block ─────────────────────────────────────────────────────────
    content = lesson_doc.get("content")
    if content is None:
        warnings.append("ERROR: [lesson] missing 'content' block")
        return warnings
    if not isinstance(content, list):
        warnings.append("ERROR: [content] 'content' must be a list")
        return warnings

    # Collect and validate IDs
    known_ids, valid_content = _validate_content_metadata(content, warnings)
    if not valid_content:
        return warnings

    _validate_remaining_blocks(lesson_doc, content, known_ids, progression, warnings)

    return warnings


def _validate_remaining_blocks(lesson_doc: dict, content: list, known_ids: set[str], progression: Any, warnings: list[str]) -> None:
    # ── presentation block ────────────────────────────────────────────────────
    presentation = lesson_doc.get("presentation")
    if presentation is not None:
        warnings.extend(presentation_schema.validate(presentation, known_ids))

    # ── per-element validation ────────────────────────────────────────────────
    for item in content:
        if isinstance(item, dict):
            _validate_element_fields(item, known_ids, warnings, lesson_doc)

    # ── phase sequence & coverage validation ──────────────────────────────────
    if progression and isinstance(progression, dict):
        progression_phases = progression.get("phases", [])
        if isinstance(progression_phases, list):
            warnings.extend(check_phase_sequence(progression_phases, content))

    # ── pedagogy coherence checks ─────────────────────────────────────────────
    if progression:
        warnings.extend(check_pedagogy_coherence(progression, content))

    # ── anchor density checks ─────────────────────────────────────────────────
    warnings.extend(check_anchor_density(content))

    # ── remediation checks ────────────────────────────────────────────────────
    warnings.extend(check_remediations(content))

    # ── concept coherence checks ──────────────────────────────────────────────
    warnings.extend(check_concept_coherence(lesson_doc))
    warnings.extend(check_concept_prerequisites(lesson_doc, content))


def _validate_curriculum(curriculum: Any, lesson: Any, warnings: list[str]) -> None:
    if curriculum is not None:
        if not isinstance(curriculum, dict):
            warnings.append("ERROR: [curriculum] 'curriculum' block must be a mapping")
        else:
            _validate_curriculum_fields(curriculum, warnings)
            _validate_curriculum_graph(curriculum, warnings)
    elif isinstance(lesson, dict) and ("syllabus" in lesson or "topic" in lesson):
        warnings.append(
            "WARN: [curriculum] legacy 'lesson.syllabus' and 'lesson.topic' are deprecated; "
            "migrate to the top-level 'curriculum' block"
        )
    else:
        warnings.append("ERROR: [curriculum] missing required top-level 'curriculum' block")


def _validate_curriculum_fields(curriculum: dict, warnings: list[str]) -> None:
    code = curriculum.get("code")
    topic = curriculum.get("topic")
    if not isinstance(code, str) or not code.strip():
        warnings.append("ERROR: [curriculum] 'code' must be a non-empty string")
    if not isinstance(topic, str) or not topic.strip():
        warnings.append("ERROR: [curriculum] 'topic' must be a non-empty string")

    concept = curriculum.get("concept")
    if concept is not None:
        if not isinstance(concept, str) or not concept.strip():
            warnings.append("ERROR: [curriculum] 'concept' must be a non-empty string")

    # Validate list of strings fields
    list_fields = ["learning_outcomes", "requires", "supports", "remediated_by", "assessment_targets", "assessment_objectives"]
    for field in list_fields:
        val = curriculum.get(field)
        if val is not None:
            if not isinstance(val, list):
                warnings.append(f"ERROR: [curriculum] '{field}' must be a list of strings")
            else:
                for i, item in enumerate(val):
                    if not isinstance(item, str) or not item.strip():
                        warnings.append(f"ERROR: [curriculum] '{field}' entry at index {i} must be a non-empty string")


def _validate_curriculum_graph(curriculum: dict, warnings: list[str]) -> None:
    concept = curriculum.get("concept")
    requires = curriculum.get("requires") or []
    supports = curriculum.get("supports") or []

    if concept:
        concept_str = concept.strip()
        if isinstance(requires, list) and concept_str in [r.strip() for r in requires if isinstance(r, str)]:
            warnings.append(f"ERROR: [curriculum:graph] concept '{concept_str}' cannot require itself")
        if isinstance(supports, list) and concept_str in [s.strip() for s in supports if isinstance(s, str)]:
            warnings.append(f"ERROR: [curriculum:graph] concept '{concept_str}' cannot support itself")

    if isinstance(requires, list) and isinstance(supports, list):
        req_set = {r.strip() for r in requires if isinstance(r, str) and r.strip()}
        sup_set = {s.strip() for s in supports if isinstance(s, str) and s.strip()}
        overlap = req_set & sup_set
        if overlap:
            warnings.append(
                f"ERROR: [curriculum:graph] concepts cannot be in both 'requires' and 'supports': "
                f"{', '.join(sorted(overlap))}"
            )


def _validate_lesson_metadata(lesson: Any, warnings: list[str]) -> None:
    if not lesson:
        warnings.append("ERROR: [lesson] missing required top-level 'lesson' block")
    elif not isinstance(lesson, dict):
        warnings.append("ERROR: [lesson] must be a mapping")
    else:
        # Validate lesson-level concepts
        concepts = lesson.get("concepts")
        if concepts is not None:
            if not isinstance(concepts, list):
                warnings.append("ERROR: [lesson] 'concepts' must be a list of strings")
            else:
                for c in concepts:
                    if not isinstance(c, str):
                        warnings.append(f"ERROR: [lesson] 'concepts' entry must be a string, got {type(c).__name__}")


def _validate_content_metadata(content: list, warnings: list[str]) -> tuple[set[str], bool]:
    known_ids: set[str] = set()
    id_counts: dict[str, int] = {}
    valid = True

    for item in content:
        if not isinstance(item, dict):
            warnings.append("ERROR: [content] each element must be a mapping")
            valid = False
            continue
        eid = item.get("id")
        if eid:
            id_counts[eid] = id_counts.get(eid, 0) + 1
            known_ids.add(str(eid))

    for eid, count in id_counts.items():
        if count > 1:
            warnings.append(f"ERROR: [content] duplicate element id '{eid}'")

    return known_ids, valid


def _check_assessment_objective_constraint(element_id: str, element_type: str | None, placement: Any, warnings: list[str]) -> None:
    if placement is not None and isinstance(placement, dict):
        obj = placement.get("assessment_objective")
        if obj is not None:
            if not element_type or not is_assessment_element(element_type):
                warnings.append(
                    f"ERROR: [{element_id}] 'placement.assessment_objective' is only allowed "
                    f"on assessment elements, but element has type '{element_type}'"
                )


def _validate_element_fields(item: dict, known_ids: set[str], warnings: list[str], lesson_doc: dict) -> None:
    element_id = str(item.get("id", "<no-id>"))
    element_type = item.get("type")

    if not item.get("id"):
        warnings.append("ERROR: [content] element missing required 'id' field")

    if not element_type:
        warnings.append(f"ERROR: [{element_id}] missing required 'type' field")
    else:
        # Validate element-specific fields against the registry
        for w in ElementRegistry.validate_fields(str(element_type), item):
            warnings.append(f"ERROR: {w}")

    # Placement (required)
    placement = item.get("placement")
    if placement is None:
        warnings.append(f"ERROR: [{element_id}] missing 'placement' block")
    else:
        for w in placement_schema.validate(element_id, placement):
            warnings.append(f"ERROR: {w}")

    # Validate assessment_objective is only on assessment elements
    _check_assessment_objective_constraint(element_id, element_type, placement, warnings)

    _validate_element_actions_rels_concepts(item, element_id, known_ids, warnings)
    _validate_diagnostic_fields(item, warnings, lesson_doc)

    if element_type == "multiple_choice":
        _validate_mcq_element(item, warnings)
    elif element_type == "structured_response":
        _validate_structured_response_element(item, warnings)


def _validate_diagnostic_fields(item: dict, warnings: list[str], lesson_doc: dict) -> None:
    element_id = str(item.get("id", "<no-id>"))
    element_type = item.get("type")
    if not element_type or not is_assessment_element(element_type):
        return

    # Extract lesson-level concepts
    lesson = lesson_doc.get("lesson") or {}
    lesson_concepts = set(lesson.get("concepts", []))

    # 1. Validate top-level diagnostic block
    _validate_diagnostic_block(item, element_id, "element", lesson_concepts, warnings)

    # 2. Validate part-level diagnostic blocks for structured_response
    if element_type == "structured_response":
        parts = item.get("parts")
        if isinstance(parts, list):
            for part in parts:
                if isinstance(part, dict):
                    part_id = part.get("id", "<no-id>")
                    _validate_diagnostic_block(part, element_id, f"part '{part_id}'", lesson_concepts, warnings)


def _validate_assesses_block(
    assesses: Any,
    element_id: str,
    label_prefix: str,
    lesson_concepts: set[str],
    warnings: list[str]
) -> None:
    if assesses is None:
        return
    if not isinstance(assesses, dict):
        warnings.append(
            f"ERROR: [{element_id}] {label_prefix} 'assesses' must be a mapping of concept IDs to weights"
        )
        return

    for concept, weight in assesses.items():
        if not isinstance(weight, (int, float)):
            warnings.append(
                f"ERROR: [{element_id}] {label_prefix} 'assesses' weight for concept '{concept}' must be a number"
            )
        elif weight < 0.0 or weight > 1.0:
            warnings.append(
                f"ERROR: [{element_id}] {label_prefix} 'assesses' weight for concept '{concept}' must be between 0.0 and 1.0"
            )
        if lesson_concepts and concept not in lesson_concepts:
            warnings.append(
                f"ERROR: [content:concept] [{element_id}] {label_prefix} 'assesses' references concept '{concept}' "
                f"which is not declared in the lesson-level 'lesson.concepts'"
            )


def _validate_rubric_criteria_items(
    criteria: list,
    element_id: str,
    label_prefix: str,
    criteria_id_to_idx: dict[str, int],
    warnings: list[str]
) -> None:
    seen_criteria_ids = []
    for idx, crit in enumerate(criteria):
        if not isinstance(crit, dict):
            warnings.append(
                f"ERROR: [{element_id}] {label_prefix} 'rubric.criteria' entry at index {idx} must be a mapping"
            )
            continue

        crit_id = crit.get("id")
        crit_marks = crit.get("marks")
        crit_desc = crit.get("description")

        if not crit_id:
            warnings.append(
                f"ERROR: [{element_id}] {label_prefix} 'rubric.criteria' entry at index {idx} missing required field 'id'"
            )
        else:
            crit_id = str(crit_id).strip()
            if crit_id in criteria_id_to_idx:
                warnings.append(
                    f"ERROR: [{element_id}] {label_prefix} 'rubric.criteria' duplicate criterion ID '{crit_id}'"
                )
            else:
                seen_criteria_ids.append(crit_id)
                criteria_id_to_idx[crit_id] = idx

        if crit_marks is None:
            warnings.append(
                f"ERROR: [{element_id}] {label_prefix} 'rubric.criteria' entry at index {idx} missing required field 'marks'"
            )
        elif not isinstance(crit_marks, int) or crit_marks < 0:
            warnings.append(
                f"ERROR: [{element_id}] {label_prefix} 'rubric.criteria' entry at index {idx} 'marks' must be a non-negative integer"
            )

        if not crit_desc:
            warnings.append(
                f"ERROR: [{element_id}] {label_prefix} 'rubric.criteria' entry at index {idx} missing required field 'description'"
            )


def _validate_rubric_dependencies(
    criteria: list,
    element_id: str,
    label_prefix: str,
    criteria_id_to_idx: dict[str, int],
    warnings: list[str]
) -> None:
    for idx, crit in enumerate(criteria):
        if not isinstance(crit, dict):
            continue
        crit_id = crit.get("id")
        if not crit_id:
            continue
        crit_id = str(crit_id).strip()
        depends_on = crit.get("depends_on")
        if depends_on is not None:
            depends_on = str(depends_on).strip()
            if depends_on == crit_id:
                warnings.append(
                    f"ERROR: [{element_id}] {label_prefix} rubric criterion '{crit_id}' depends on itself"
                )
            elif depends_on not in criteria_id_to_idx:
                warnings.append(
                    f"ERROR: [{element_id}] {label_prefix} rubric criterion '{crit_id}' depends on unknown criterion '{depends_on}'"
                )
            else:
                dep_idx = criteria_id_to_idx[depends_on]
                if dep_idx >= idx:
                    warnings.append(
                        f"ERROR: [{element_id}] {label_prefix} rubric criterion '{crit_id}' depends on '{depends_on}' which appears after or at the same position"
                    )


def _validate_rubric_block(
    rubric: Any,
    element_id: str,
    label_prefix: str,
    warnings: list[str]
) -> None:
    if rubric is None:
        return
    if not isinstance(rubric, dict):
        warnings.append(
            f"ERROR: [{element_id}] {label_prefix} 'rubric' must be a mapping"
        )
        return

    total_marks = rubric.get("total_marks")
    criteria = rubric.get("criteria")

    if total_marks is not None and not isinstance(total_marks, int):
        warnings.append(
            f"ERROR: [{element_id}] {label_prefix} 'rubric.total_marks' must be an integer"
        )

    if criteria is not None:
        if not isinstance(criteria, list):
            warnings.append(
                f"ERROR: [{element_id}] {label_prefix} 'rubric.criteria' must be a list"
            )
            return

        criteria_id_to_idx = {}
        _validate_rubric_criteria_items(criteria, element_id, label_prefix, criteria_id_to_idx, warnings)

        # Validate sum of marks matches total_marks
        if total_marks is not None and isinstance(total_marks, int):
            sum_marks = sum(
                crit.get("marks")
                for crit in criteria
                if isinstance(crit, dict) and isinstance(crit.get("marks"), int) and crit.get("marks") >= 0
            )
            if sum_marks != total_marks:
                warnings.append(
                    f"ERROR: [{element_id}] {label_prefix} rubric total_marks is {total_marks} but criteria marks sum to {sum_marks}"
                )

        _validate_rubric_dependencies(criteria, element_id, label_prefix, criteria_id_to_idx, warnings)


def _validate_diagnostic_block(
    block: dict,
    element_id: str,
    label_prefix: str,
    lesson_concepts: set[str],
    warnings: list[str]
) -> None:
    _validate_assesses_block(block.get("assesses"), element_id, label_prefix, lesson_concepts, warnings)
    _validate_rubric_block(block.get("rubric"), element_id, label_prefix, warnings)


def _validate_mcq_element(item: dict, warnings: list[str]) -> None:
    element_id = str(item.get("id", "<no-id>"))
    options = item.get("options")
    answer = item.get("answer")
    misconceptions = item.get("misconceptions")

    if not isinstance(options, dict):
        return

    if answer is not None:
        if str(answer) not in options:
            warnings.append(
                f"ERROR: [multiple_choice:answer] element '{element_id}' correct answer '{answer}' "
                f"is not a key in options dictionary"
            )

    if isinstance(misconceptions, dict):
        for opt in misconceptions:
            if opt not in options:
                warnings.append(
                    f"ERROR: [multiple_choice:misconceptions] element '{element_id}' maps misconception for option '{opt}' "
                    f"which is not a key in options dictionary"
                )


def _collect_part_ids(element_id: str, parts: list, warnings: list[str]) -> list[str]:
    part_ids = []
    seen = set()
    for idx, part in enumerate(parts):
        if not isinstance(part, dict):
            continue
        pid = part.get("id")
        if not pid:
            warnings.append(
                f"ERROR: [structured_response:parts] element '{element_id}' "
                f"part at index {idx} missing required 'id'"
            )
            continue
        pid = str(pid).strip()
        if pid in seen:
            warnings.append(
                f"ERROR: [structured_response:parts] element '{element_id}' "
                f"duplicate part id '{pid}'"
            )
        else:
            seen.add(pid)
            part_ids.append(pid)
    return part_ids


def _validate_part_dependencies(
    element_id: str, parts: list, part_ids: list[str], warnings: list[str]
) -> None:
    seen_part_ids = set(part_ids)
    for part in parts:
        if not isinstance(part, dict):
            continue
        pid = part.get("id")
        if not pid:
            continue
        pid = str(pid).strip()
        depends_on = part.get("depends_on")
        if depends_on is None:
            continue

        depends_on = str(depends_on).strip()
        if depends_on == pid:
            warnings.append(
                f"ERROR: [structured_response:parts] element '{element_id}' "
                f"part '{pid}' cannot depend on itself"
            )
        elif depends_on not in seen_part_ids:
            warnings.append(
                f"ERROR: [structured_response:parts] element '{element_id}' "
                f"part '{pid}' depends_on unknown part '{depends_on}'"
            )
        else:
            dep_idx = part_ids.index(depends_on)
            if dep_idx >= part_ids.index(pid):
                warnings.append(
                    f"ERROR: [structured_response:parts] element '{element_id}' "
                    f"part '{pid}' depends_on '{depends_on}' which appears after or at the same position"
                )


def _validate_structured_response_element(item: dict, warnings: list[str]) -> None:
    element_id = str(item.get("id", "<no-id>"))
    parts = item.get("parts")
    if not isinstance(parts, list):
        return

    if len(parts) < 2:
        warnings.append(
            f"ERROR: [structured_response:parts] element '{element_id}' must have at least 2 parts, got {len(parts)}"
        )

    part_ids = _collect_part_ids(element_id, parts, warnings)
    _validate_part_dependencies(element_id, parts, part_ids, warnings)


def _validate_element_actions_rels_concepts(item: dict, element_id: str, known_ids: set[str], warnings: list[str]) -> None:
    # Actions (optional)
    actions_data = item.get("actions")
    if actions_data is not None:
        for w in actions_schema.validate(element_id, actions_data):
            warnings.append(f"ERROR: {w}")

    # Relationships (optional) — exclude self from referential check
    rels = item.get("relationships")
    if rels is not None:
        ref_ids = known_ids - {element_id}
        for w in relationships_schema.validate(element_id, rels, ref_ids):
            warnings.append(f"ERROR: {w}")

    # Concepts (optional)
    element_concepts = item.get("concepts")
    if element_concepts is not None:
        if not isinstance(element_concepts, list):
            warnings.append(f"ERROR: [{element_id}] 'concepts' must be a list of strings")
        else:
            for c in element_concepts:
                if not isinstance(c, str):
                    warnings.append(f"ERROR: [{element_id}] 'concepts' entry must be a string, got {type(c).__name__}")
