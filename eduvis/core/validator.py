"""
EduVis Core — Full lesson validator.

Validates a complete EduVis lesson document against all five pillars:
  Elements · Actions · Relationships · Placement · Progression
"""

from __future__ import annotations

import logging
from typing import Any

from .registry import ElementRegistry
from .schemas import actions as actions_schema
from .schemas import placement as placement_schema
from .schemas import progression as progression_schema
from .schemas import relationships as relationships_schema
from .schemas import presentation as presentation_schema

logger = logging.getLogger(__name__)

# Configurable anchor density warning limit
ANCHOR_DENSITY_LIMIT = 2


def is_assessment_element(element_type: str) -> bool:
    """Check if the element type is an assessment/practice input style element."""
    return element_type in ("multiple_choice", "short_answer")


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
            "WARN: [lesson:version] missing 'schema_version' field. Assuming default \"0.5\"."
        )
    elif not isinstance(version, str):
        warnings.append(
            f"ERROR: [lesson:version] 'schema_version' must be a string, got {type(version).__name__}"
        )
    elif version != "0.5":
        warnings.append(
            f"ERROR: [lesson:version] unsupported schema version \"{version}\". Expected \"0.5\"."
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
            _validate_element_fields(item, known_ids, warnings)

    # ── phase sequence & coverage validation ──────────────────────────────────
    if progression and isinstance(progression, dict):
        progression_phases = progression.get("phases", [])
        if isinstance(progression_phases, list):
            warnings.extend(_check_phase_sequence(progression_phases, content))

    # ── pedagogy coherence checks ─────────────────────────────────────────────
    if progression:
        warnings.extend(_check_pedagogy_coherence(progression, content))

    # ── anchor density checks ─────────────────────────────────────────────────
    warnings.extend(_check_anchor_density(content))

    # ── remediation checks ────────────────────────────────────────────────────
    warnings.extend(_check_remediations(content))

    # ── concept coherence checks ──────────────────────────────────────────────
    warnings.extend(_check_concept_coherence(lesson_doc))


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


def _validate_element_fields(item: dict, known_ids: set[str], warnings: list[str]) -> None:
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

    _validate_element_actions_rels_concepts(item, element_id, known_ids, warnings)

    if element_type == "multiple_choice":
        _validate_mcq_element(item, warnings)


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


# ── Phase Sequence & Coverage ─────────────────────────────────────────────────

def _check_phase_sequence(progression_phases: list[dict], content: list[dict]) -> list[str]:
    """Verify chronological phase order and progression coverage (unused/undeclared phases)."""
    warnings: list[str] = []
    if not progression_phases or not content:
        return warnings

    element_phases = _collect_element_phases(content)

    # 1. Progression Coverage: Undeclared Phases Check (ERROR)
    declared_phases_list = [p.get("phase") for p in progression_phases if isinstance(p, dict) and p.get("phase")]
    declared_phases_set = set(declared_phases_list)

    for el in element_phases:
        if el["phase"] not in declared_phases_set:
            warnings.append(
                f"ERROR: [progression:sequence] element '{el['id']}' has phase '{el['phase']}' "
                f"which is not declared in the progression phases list"
            )

    # 2. Progression Coverage: Unused Phases Check (WARN)
    content_phases_set = {el["phase"] for el in element_phases if el["phase"]}
    for dp in declared_phases_list:
        if dp not in content_phases_set:
            warnings.append(
                f"WARN: [progression:coverage] phase '{dp}' is declared in the progression but not used by any content elements"
            )

    # 3. Monotonic Phase Sequence Matching (ERROR)
    _validate_phase_monotonicity(element_phases, progression_phases, declared_phases_set, warnings)

    return warnings


def _collect_element_phases(content: list[dict]) -> list[dict]:
    element_phases = []
    for item in content:
        if not isinstance(item, dict):
            continue
        eid = item.get("id", "<no-id>")
        placement = item.get("placement")
        if not isinstance(placement, dict):
            continue
        phase = placement.get("lesson_phase")
        purpose = placement.get("purpose")
        difficulty = placement.get("difficulty")
        element_phases.append({
            "id": eid,
            "phase": phase,
            "purpose": purpose,
            "difficulty": difficulty
        })
    return element_phases


def _validate_phase_monotonicity(
    element_phases: list[dict], progression_phases: list[dict], declared_phases_set: set[str], warnings: list[str]
) -> None:
    curr_prog_idx = 0
    num_prog = len(progression_phases)

    for el in element_phases:
        # Skip sequence matching if the phase is completely undeclared
        if el["phase"] not in declared_phases_set:
            continue

        # Try to match greedily starting from curr_prog_idx
        matched_idx = -1
        for p_idx in range(curr_prog_idx, num_prog):
            p_phase = progression_phases[p_idx]
            if el["phase"] == p_phase.get("phase"):
                p_purpose = p_phase.get("purpose")
                p_difficulty = p_phase.get("difficulty")

                if p_purpose is not None and el["purpose"] != p_purpose:
                    continue
                if p_difficulty is not None and el["difficulty"] != p_difficulty:
                    continue

                matched_idx = p_idx
                break

        if matched_idx != -1:
            curr_prog_idx = matched_idx
        else:
            # Sequence error: phase appears out of order
            _handle_phase_sequence_error(el, curr_prog_idx, progression_phases, warnings)


def _handle_phase_sequence_error(el: dict, curr_prog_idx: int, progression_phases: list[dict], warnings: list[str]) -> None:
    matched_behind = False
    for p_idx in range(0, curr_prog_idx):
        p_phase = progression_phases[p_idx]
        if el["phase"] == p_phase.get("phase"):
            p_purpose = p_phase.get("purpose")
            p_difficulty = p_phase.get("difficulty")
            if (
                (p_purpose is None or el["purpose"] == p_purpose)
                and (p_difficulty is None or el["difficulty"] == p_difficulty)
            ):
                matched_behind = True
                break

    if matched_behind:
        warnings.append(
            f"ERROR: [progression:sequence] element '{el['id']}' has phase '{el['phase']}' "
            f"which appears out of order (this phase was already completed in the progression)"
        )
    else:
        warnings.append(
            f"ERROR: [progression:sequence] element '{el['id']}' has phase '{el['phase']}' "
            f"which does not match the constraints of progression phases"
        )


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
            "ERROR: [pedagogy:confidence_first] no starter-difficulty independent_practice "
            "elements found; add at least one starter element before routine practice"
        )
    elif starter_indices and routine_indices:
        last_starter = max(starter_indices)
        first_routine = min(routine_indices)
        if first_routine < last_starter:
            offending_id = practice[first_routine][1]
            warnings.append(
                f"ERROR: [pedagogy:confidence_first] routine element '{offending_id}' "
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
            "ERROR: [pedagogy:explain_why] explain phase has a 'procedure' element but no "
            "'conceptual_model' element; add a conceptual_model before the procedure"
        )
    elif conceptual_indices and procedure_indices:
        last_conceptual = max(conceptual_indices)
        first_procedure = min(procedure_indices)
        if first_procedure < last_conceptual:
            offending_id = explain[first_procedure][1]
            warnings.append(
                f"ERROR: [pedagogy:explain_why] procedure element '{offending_id}' appears "
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
                f"ERROR: [pedagogy:no_skipped_steps] guided_practice element '{element_id}' "
                f"has no actions block; every guided example must document its steps"
            )
            continue

        conceptual = actions.get("conceptual") or []
        procedural = actions.get("procedural") or []
        total_actions = (len(conceptual) if isinstance(conceptual, list) else 0) + \
                        (len(procedural) if isinstance(procedural, list) else 0)

        if total_actions == 0:
            warnings.append(
                f"ERROR: [pedagogy:no_skipped_steps] guided_practice element '{element_id}' "
                f"has an empty actions block; every step must be an explicit action "
                f"(use procedural for computation steps, conceptual for reasoning steps)"
            )

    return warnings


# ── Anchor Density ────────────────────────────────────────────────────────────

def _check_anchor_density(content: list[dict]) -> list[str]:
    """Check anchor counts and warn if they exceed density limits."""
    warnings: list[str] = []
    anchor_count = 0
    for item in content:
        if isinstance(item, dict):
            placement = item.get("placement")
            if isinstance(placement, dict):
                if placement.get("memory_role") == "anchor":
                    anchor_count += 1

    if anchor_count > ANCHOR_DENSITY_LIMIT:
        warnings.append(
            f"WARN: [pedagogy:anchor] lesson contains {anchor_count} anchor elements; "
            f"consider identifying a primary anchor to avoid cognitive overload"
        )
    return warnings


# ── Remediation target & sequence ─────────────────────────────────────────────

def _check_remediations(content: list[dict]) -> list[str]:
    """Ensure remediation targets are valid assessment types and do not target future slides."""
    warnings: list[str] = []
    id_to_index = {}
    id_to_type = {}
    for idx, item in enumerate(content):
        if isinstance(item, dict):
            eid = item.get("id")
            if eid:
                id_to_index[eid] = idx
                id_to_type[eid] = item.get("type")

    for idx, item in enumerate(content):
        if not isinstance(item, dict):
            continue
        _validate_element_remediations(idx, item, id_to_index, id_to_type, warnings)
        if item.get("type") == "remediation_block":
            _validate_remediation_block_targets(idx, item, id_to_index, id_to_type, warnings)

    return warnings


def _validate_element_remediations(
    idx: int, item: dict, id_to_index: dict[str, int], id_to_type: dict[str, str], warnings: list[str]
) -> None:
    eid = item.get("id", "<no-id>")
    rels = item.get("relationships")
    if not isinstance(rels, dict):
        return
    remediations = rels.get("remediation_for")
    if not isinstance(remediations, list):
        return

    for target in remediations:
        if not isinstance(target, str) or target not in id_to_index:
            continue

        target_idx = id_to_index[target]
        if target_idx >= idx:
            warnings.append(
                f"ERROR: [relationships:remediation_for] element '{eid}' is a remediation for '{target}' "
                f"which appears after it in the lesson; a hint cannot remediate a future question"
            )

        target_type = id_to_type.get(target)
        if target_type and not is_assessment_element(target_type):
            warnings.append(
                f"ERROR: [relationships:remediation_for] element '{eid}' is a remediation but targets "
                f"element '{target}' of type '{target_type}'; remediation must target an assessment element"
            )


def _validate_remediation_block_targets(
    idx: int, item: dict, id_to_index: dict[str, int], id_to_type: dict[str, str], warnings: list[str]
) -> None:
    eid = item.get("id", "<no-id>")
    review = item.get("review")
    if not isinstance(review, dict):
        return
    source_question = review.get("source_question")
    if not isinstance(source_question, str):
        return

    if source_question not in id_to_index:
        warnings.append(
            f"ERROR: [remediation_block:review] element '{eid}' references source_question '{source_question}' "
            f"which does not exist in the lesson content"
        )
        return

    target_idx = id_to_index[source_question]
    if target_idx >= idx:
        warnings.append(
            f"ERROR: [remediation_block:review] element '{eid}' references source_question '{source_question}' "
            f"which appears after it in the lesson; a remediation block cannot target a future question"
        )

    target_type = id_to_type.get(source_question)
    if target_type and not is_assessment_element(target_type):
        warnings.append(
            f"ERROR: [remediation_block:review] element '{eid}' references source_question '{source_question}' "
            f"of type '{target_type}'; source_question must be an assessment element"
        )


# ── Concept coherence ─────────────────────────────────────────────────────────

def _check_concept_coherence(lesson_doc: dict) -> list[str]:
    """Check that elements tag valid concepts and do not contain unrelated concept clusters."""
    warnings: list[str] = []

    lesson = lesson_doc.get("lesson") or {}
    content = lesson_doc.get("content") or []

    lesson_concepts = set(lesson.get("concepts", []))

    # 1. Collect all concepts tagged on elements
    element_to_concepts, all_element_concepts = _collect_tagged_concepts(content, lesson_concepts, warnings)

    # Check 2: Warning if a lesson-declared concept is completely unused by any element
    if lesson_concepts:
        unused_concepts = lesson_concepts - all_element_concepts
        if unused_concepts:
            warnings.append(
                f"WARN: [lesson:concept] the following declared concepts are not tagged on any content elements: "
                f"{', '.join(sorted(unused_concepts))}"
            )

    # Check 3: Check for disconnected concept clusters (Concept Connectivity Check)
    if len(all_element_concepts) > 1:
        _check_concept_connectivity(content, element_to_concepts, all_element_concepts, warnings)

    return warnings


def _collect_tagged_concepts(content: list, lesson_concepts: set[str], warnings: list[str]) -> tuple[dict[str, set[str]], set[str]]:
    element_to_concepts: dict[str, set[str]] = {}
    all_element_concepts: set[str] = set()

    for item in content:
        if not isinstance(item, dict):
            continue
        eid = item.get("id")
        if not eid:
            continue
        el_concepts = item.get("concepts")
        if el_concepts is not None and isinstance(el_concepts, list):
            valid_concepts = [c for c in el_concepts if isinstance(c, str)]
            if valid_concepts:
                element_to_concepts[eid] = set(valid_concepts)
                all_element_concepts.update(valid_concepts)

                # Check 1: Error if element concept is not declared in lesson-level concepts
                if lesson_concepts:
                    for c in valid_concepts:
                        if c not in lesson_concepts:
                            warnings.append(
                                f"ERROR: [content:concept] element '{eid}' tags concept '{c}' "
                                f"which is not declared in the lesson-level 'lesson.concepts'"
                            )
    return element_to_concepts, all_element_concepts


def _check_concept_connectivity(
    content: list[dict], element_to_concepts: dict[str, set[str]], all_element_concepts: set[str], warnings: list[str]
) -> None:
    adj = _build_concept_connectivity_graph(content)

    # For each concept, find the elements that tag it
    concept_elements = {c: set() for c in all_element_concepts}
    for eid, concepts in element_to_concepts.items():
        for c in concepts:
            concept_elements[c].add(eid)

    components = _find_concept_components(adj)

    _verify_concept_unrelated_pairs(all_element_concepts, concept_elements, components, warnings)


def _build_concept_connectivity_graph(content: list[dict]) -> dict[str, set[str]]:
    # Build relationship adjacency graph (ignoring direction)
    adj: dict[str, set[str]] = {
        item.get("id"): set()
        for item in content
        if isinstance(item, dict) and item.get("id")
    }
    for item in content:
        if not isinstance(item, dict):
            continue
        eid = item.get("id")
        if not eid:
            continue
        rels = item.get("relationships") or {}
        if isinstance(rels, dict):
            for _, targets in rels.items():
                if isinstance(targets, list):
                    for t in targets:
                        if isinstance(t, str) and t in adj:
                            adj[eid].add(t)
                            adj[t].add(eid)
    return adj


def _find_concept_components(adj: dict[str, set[str]]) -> list[set[str]]:
    visited = set()
    components = []
    for eid in adj:
        if eid not in visited:
            comp = set()
            q = [eid]
            visited.add(eid)
            while q:
                curr = q.pop(0)
                comp.add(curr)
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        q.append(neighbor)
            components.append(comp)
    return components


def _verify_concept_unrelated_pairs(
    all_element_concepts: set[str], concept_elements: dict[str, set[str]], components: list[set[str]], warnings: list[str]
) -> None:
    unrelated_pairs = []
    concepts_list = list(all_element_concepts)
    for i, c1 in enumerate(concepts_list):
        for c2 in concepts_list[i + 1:]:

            # Check 1: Are there any elements tagging both?
            sharing_elements = concept_elements[c1] & concept_elements[c2]
            if sharing_elements:
                continue  # they share elements, so they are related

            # Check 2: Is there any path between any element of c1 and any element of c2?
            connected = False
            for comp in components:
                if (concept_elements[c1] & comp) and (concept_elements[c2] & comp):
                    connected = True
                    break

            if not connected:
                unrelated_pairs.append((c1, c2))

    if unrelated_pairs:
        warnings.append(
            "WARN: [coherence:concept] Multiple concept groups detected with no relationships connecting them."
        )
