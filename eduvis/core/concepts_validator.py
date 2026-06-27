"""Concept validation rules for EduVis Core."""

from __future__ import annotations

import collections
import logging
from typing import Any

logger = logging.getLogger(__name__)


def is_assessment_element(element_type: str) -> bool:
    """Check if the element type is an assessment/practice input style element."""
    return element_type in ("multiple_choice", "short_answer", "structured_response")


def check_concept_coherence(lesson_doc: dict) -> list[str]:
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


def _collect_assesses_concepts(assesses_dict: Any) -> set[str]:
    res = set()
    if isinstance(assesses_dict, dict):
        for c in assesses_dict:
            if isinstance(c, str):
                res.add(c)
    return res


def _collect_item_concepts(item: dict, lesson_concepts: set[str], warnings: list[str]) -> set[str]:
    item_concepts = set()
    eid = item.get("id")
    if not eid:
        return item_concepts

    el_concepts = item.get("concepts")
    if isinstance(el_concepts, list):
        valid_concepts = [c for c in el_concepts if isinstance(c, str)]
        if valid_concepts:
            item_concepts.update(valid_concepts)
            if lesson_concepts:
                for c in valid_concepts:
                    if c not in lesson_concepts:
                        warnings.append(
                            f"ERROR: [content:concept] element '{eid}' tags concept '{c}' "
                            f"which is not declared in the lesson-level 'lesson.concepts'"
                        )

    assesses = item.get("assesses")
    item_concepts.update(_collect_assesses_concepts(assesses))

    parts = item.get("parts")
    if isinstance(parts, list):
        for part in parts:
            if isinstance(part, dict):
                item_concepts.update(_collect_assesses_concepts(part.get("assesses")))

    return item_concepts


def _collect_tagged_concepts(content: list, lesson_concepts: set[str], warnings: list[str]) -> tuple[dict[str, set[str]], set[str]]:
    element_to_concepts: dict[str, set[str]] = {}
    all_element_concepts: set[str] = set()

    for item in content:
        if not isinstance(item, dict):
            continue
        eid = item.get("id")
        if not eid:
            continue

        item_concepts = _collect_item_concepts(item, lesson_concepts, warnings)
        if item_concepts:
            element_to_concepts[eid] = item_concepts
            all_element_concepts.update(item_concepts)

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


def _collect_first_seen_concepts(content: list[dict]) -> dict[str, tuple[int, str]]:
    first_seen = {}
    for idx, item in enumerate(content):
        if not isinstance(item, dict):
            continue
        eid = item.get("id")
        if not eid:
            continue

        concepts = _collect_item_concepts(item, None, [])
        for c in concepts:
            if c not in first_seen:
                first_seen[c] = (idx, eid)
    return first_seen


def _build_transitive_prereqs(concept: str, requires: list[str], supports: list[str]) -> dict[str, set[str]]:
    prereqs = collections.defaultdict(set)
    for r in requires:
        prereqs[concept].add(r)
    for s in supports:
        prereqs[s].add(concept)
        for r in requires:
            prereqs[s].add(r)
    return prereqs


def check_concept_prerequisites(lesson_doc: dict, content: list[dict]) -> list[str]:
    """Verify that concepts are introduced/assessed in chronological order according to curriculum dependency graph."""
    warnings: list[str] = []
    curriculum = lesson_doc.get("curriculum")
    if not isinstance(curriculum, dict):
        return warnings

    concept = curriculum.get("concept")
    if not concept:
        return warnings
    concept = concept.strip()

    requires = [r.strip() for r in curriculum.get("requires") or [] if isinstance(r, str)]
    supports = [s.strip() for s in curriculum.get("supports") or [] if isinstance(s, str)]

    # Build transitive prerequisites mapping: prereqs[Y] = set of concepts required before Y
    prereqs = _build_transitive_prereqs(concept, requires, supports)

    # Find the first index in content where each concept is introduced or assessed
    first_seen = _collect_first_seen_concepts(content)

    # Check that any prerequisite X of Y appears before Y
    for y, x_set in prereqs.items():
        if y in first_seen:
            y_idx, y_eid = first_seen[y]
            for x in x_set:
                if x in first_seen:
                    x_idx, x_eid = first_seen[x]
                    if x_idx >= y_idx:
                        warnings.append(
                            f"ERROR: [curriculum:prerequisite] concept '{y}' (first seen at element '{y_eid}') "
                            f"cannot appear before or at the same element as its prerequisite concept '{x}' "
                            f"(first seen at element '{x_eid}')"
                        )

    return warnings
