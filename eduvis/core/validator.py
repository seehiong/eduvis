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
    else:
        # Validate lesson-level concepts
        concepts = lesson.get("concepts")
        if concepts is not None:
            if not isinstance(concepts, list):
                warnings.append("[lesson] 'concepts' must be a list of strings")
            else:
                for c in concepts:
                    if not isinstance(c, str):
                        warnings.append(f"[lesson] 'concepts' entry must be a string, got {type(c).__name__}")

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

        # Concepts (optional)
        element_concepts = item.get("concepts")
        if element_concepts is not None:
            if not isinstance(element_concepts, list):
                warnings.append(f"[{element_id}] 'concepts' must be a list of strings")
            else:
                for c in element_concepts:
                    if not isinstance(c, str):
                        warnings.append(f"[{element_id}] 'concepts' entry must be a string, got {type(c).__name__}")

    # ── pedagogy coherence checks ─────────────────────────────────────────────
    if progression:
        warnings.extend(_check_pedagogy_coherence(progression, content))

    # ── concept coherence checks ──────────────────────────────────────────────
    warnings.extend(_check_concept_coherence(lesson_doc))

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


# ── Concept coherence ─────────────────────────────────────────────────────────

def _check_concept_coherence(lesson_doc: dict) -> list[str]:
    """Check that elements tag valid concepts and do not contain unrelated concept clusters."""
    warnings: list[str] = []
    
    lesson = lesson_doc.get("lesson") or {}
    content = lesson_doc.get("content") or []
    
    lesson_concepts = set(lesson.get("concepts", []))
    
    # 1. Collect all concepts tagged on elements
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
                
                # Check 1: Warning if element concept is not declared in lesson-level concepts
                if lesson_concepts:
                    for c in valid_concepts:
                        if c not in lesson_concepts:
                            warnings.append(
                                f"[content:concept] element '{eid}' tags concept '{c}' "
                                f"which is not declared in the lesson-level 'lesson.concepts'"
                            )
                            
    # Check 2: Warning if a lesson-declared concept is completely unused by any element
    if lesson_concepts:
        unused_concepts = lesson_concepts - all_element_concepts
        if unused_concepts:
            warnings.append(
                f"[lesson:concept] the following declared concepts are not tagged on any content elements: "
                f"{', '.join(sorted(unused_concepts))}"
            )
            
    # Check 3: Check for disjoint concept clusters (unrelated concepts in the same lesson)
    if len(all_element_concepts) > 1:
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
                for rel_type, targets in rels.items():
                    if isinstance(targets, list):
                        for t in targets:
                            if isinstance(t, str) and t in adj:
                                adj[eid].add(t)
                                adj[t].add(eid)
                                
        # For each concept, find the elements that tag it
        concept_elements = {c: set() for c in all_element_concepts}
        for eid, concepts in element_to_concepts.items():
            for c in concepts:
                concept_elements[c].add(eid)
                
        # Find connected components in the element graph
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
                
        # Find unrelated pairs of concepts
        unrelated_pairs = []
        concepts_list = list(all_element_concepts)
        for i in range(len(concepts_list)):
            for j in range(i + 1, len(concepts_list)):
                c1, c2 = concepts_list[i], concepts_list[j]
                
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
                    
        for c1, c2 in unrelated_pairs:
            warnings.append(
                f"[coherence:concept] lesson contains two unrelated concept clusters: "
                f"'{c1}' and '{c2}' are taught in disjoint sections of the lesson with no bridging relationships"
            )
            
    return warnings
