"""Pedagogy validation rules for EduVis Core."""

from __future__ import annotations

from .concepts_validator import is_assessment_element

# Configurable anchor density warning limit
ANCHOR_DENSITY_LIMIT = 2


def check_phase_sequence(progression_phases: list[dict], content: list[dict]) -> list[str]:
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


def check_pedagogy_coherence(progression: dict, content: list[dict]) -> list[str]:
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
    action (conceptual or procedural).
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


def check_anchor_density(content: list[dict]) -> list[str]:
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


def check_remediations(content: list[dict]) -> list[str]:
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
