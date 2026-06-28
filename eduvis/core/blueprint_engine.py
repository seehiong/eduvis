"""EduVis — Assessment Blueprint Engine.

Three complementary tools for assessment paper construction and validation:

  generate_blueprint(curriculum, total_marks, cognitive_weights)
      Produces a paper_blueprint dict from a CurriculumGraph, distributing
      mark weights proportionally by blended exam_weight and centrality_weight.

  validate_paper_coverage(paper, blueprint, elements)
      Audits an assessment_paper against a paper_blueprint and returns a list
      of coverage warnings (empty = paper satisfies blueprint).

  assemble_paper(blueprint, available_elements, title, marks_per_element)
      Greedy assembler: scores and selects elements from a pool to satisfy
      blueprint concept and cognitive-skill targets; returns a valid
      assessment_paper dict grouped into sections by assessment_objective.
"""

from __future__ import annotations

from typing import Any

from .curriculum import CurriculumGraph
from .constants import SCHEMA_VERSION

# Blend ratio exam_weight vs centrality_weight when computing concept importance
_EXAM_BLEND = 0.70
_CENTRALITY_BLEND = 0.30

# Tolerance (±) before a coverage deviation triggers a warning
_COVERAGE_TOLERANCE = 0.05

# Default cognitive distribution when caller does not supply cognitive_weights
DEFAULT_COGNITIVE_WEIGHTS: dict[str, float] = {
    "conceptual_understanding": 0.30,
    "procedural_fluency": 0.50,
    "application": 0.10,
    "reasoning": 0.10,
}

# Canonical section ordering in assembled papers
_SECTION_ORDER = [
    "conceptual_understanding",
    "procedural_fluency",
    "application",
    "reasoning",
    "general",
]


# ---------------------------------------------------------------------------
# 1. Blueprint generation
# ---------------------------------------------------------------------------

def generate_blueprint(
    curriculum: CurriculumGraph,
    total_marks: int,
    cognitive_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Build a paper_blueprint dict from a CurriculumGraph.

    Concept weights blend each node's exam_weight (70 %) and centrality_weight
    (30 %), then normalise to sum to 1.0.  cognitive_weights follows the same
    normalisation and defaults to DEFAULT_COGNITIVE_WEIGHTS when omitted.
    """
    concept_targets = _build_concept_targets(curriculum)
    cognitive_targets = _build_cognitive_targets(cognitive_weights or DEFAULT_COGNITIVE_WEIGHTS)

    return {
        "schema_version": SCHEMA_VERSION,
        "total_marks": total_marks,
        "targets": concept_targets + cognitive_targets,
    }


def _build_concept_targets(curriculum: CurriculumGraph) -> list[dict[str, Any]]:
    raw: dict[str, float] = {}
    for code, node in curriculum.concepts.items():
        score = node.exam_weight * _EXAM_BLEND + node.centrality_weight * _CENTRALITY_BLEND
        raw[code] = max(0.0, score)

    total = sum(raw.values())
    if total == 0:
        return []

    return [
        {"type": "concept", "code": code, "weight": round(score / total, 4)}
        for code, score in sorted(raw.items(), key=lambda x: -x[1])
        if score > 0
    ]


def _build_cognitive_targets(weights: dict[str, float]) -> list[dict[str, Any]]:
    total = sum(v for v in weights.values() if v > 0)
    if total == 0:
        return []

    return [
        {"type": "cognitive_skill", "code": skill, "weight": round(w / total, 4)}
        for skill, w in sorted(weights.items(), key=lambda x: -x[1])
        if w > 0
    ]


# ---------------------------------------------------------------------------
# 2. Coverage validation
# ---------------------------------------------------------------------------

def validate_paper_coverage(
    paper: dict[str, Any],
    blueprint: dict[str, Any],
    elements: dict[str, dict[str, Any]],
) -> list[str]:
    """Audit an assessment_paper against a paper_blueprint.

    Returns a list of warning strings.  An empty list means the paper
    satisfies all blueprint targets within the tolerance threshold.

    paper     — assessment_paper dict (sections → questions → {id, marks})
    blueprint — paper_blueprint dict (total_marks, targets)
    elements  — {element_id: element_content_dict} for concept/objective lookup
    """
    warnings: list[str] = []

    blueprint_total = int(blueprint.get("total_marks", 0))
    targets: list[dict[str, Any]] = blueprint.get("targets", [])

    concept_marks, cognitive_marks, paper_total = _tally_paper_marks(paper, elements)

    if blueprint_total > 0 and paper_total != blueprint_total:
        warnings.append(
            f"WARN: paper total marks ({paper_total}) does not match "
            f"blueprint total_marks ({blueprint_total})"
        )

    if paper_total == 0:
        return warnings

    for target in targets:
        t_type = target.get("type")
        t_code = str(target.get("code", ""))
        t_weight = float(target.get("weight", 0))

        if t_type == "concept":
            actual_marks = concept_marks.get(t_code, 0)
        elif t_type == "cognitive_skill":
            actual_marks = cognitive_marks.get(t_code, 0)
        else:
            continue

        actual_weight = actual_marks / paper_total
        deviation = actual_weight - t_weight

        if actual_marks == 0 and t_weight > 0:
            warnings.append(
                f"WARN: {t_type} '{t_code}' has zero marks in paper "
                f"but blueprint targets {t_weight:.0%}"
            )
        elif abs(deviation) > _COVERAGE_TOLERANCE:
            direction = "over" if deviation > 0 else "under"
            warnings.append(
                f"WARN: {t_type} '{t_code}' is {direction}-covered — "
                f"actual {actual_weight:.1%} vs target {t_weight:.1%} "
                f"(Δ {abs(deviation):.1%})"
            )

    return warnings


def _tally_paper_marks(
    paper: dict[str, Any],
    elements: dict[str, dict[str, Any]],
) -> tuple[dict[str, int], dict[str, int], int]:
    """Return (concept_marks, cognitive_marks, total) tallied from a paper."""
    concept_marks: dict[str, int] = {}
    cognitive_marks: dict[str, int] = {}
    paper_total = 0

    for section in paper.get("sections", []):
        for q in section.get("questions", []):
            el_id = str(q.get("id", ""))
            marks = int(q.get("marks", 0))
            paper_total += marks

            el = elements.get(el_id, {})
            for concept in el.get("concepts") or []:
                concept_marks[concept] = concept_marks.get(concept, 0) + marks

            placement = el.get("placement") or {}
            obj = placement.get("assessment_objective")
            if obj:
                cognitive_marks[obj] = cognitive_marks.get(obj, 0) + marks

    return concept_marks, cognitive_marks, paper_total


# ---------------------------------------------------------------------------
# 3. Automated exam assembly
# ---------------------------------------------------------------------------

def assemble_paper(
    blueprint: dict[str, Any],
    available_elements: list[dict[str, Any]],
    title: str = "Assessment Paper",
    marks_per_element: int = 2,
) -> dict[str, Any]:
    """Greedy assembler: build an assessment_paper from a pool of elements.

    Each element is scored by how well its concepts and assessment_objective
    align with blueprint targets.  Elements are selected highest-score-first
    until the mark budget is filled.  Sections are grouped by
    assessment_objective in canonical order.

    available_elements — list of element content dicts; each should carry:
        id, concepts (list[str]), placement.assessment_objective (str),
        marking_scheme (list, optional — used to derive marks)
    marks_per_element  — fallback mark value when an element has no
                         marking_scheme; defaults to 2
    """
    blueprint_total = int(blueprint.get("total_marks", 0))
    targets: list[dict[str, Any]] = blueprint.get("targets", [])

    concept_targets: dict[str, float] = {}
    cognitive_targets: dict[str, float] = {}
    for t in targets:
        if t.get("type") == "concept":
            concept_targets[str(t["code"])] = float(t.get("weight", 0))
        elif t.get("type") == "cognitive_skill":
            cognitive_targets[str(t["code"])] = float(t.get("weight", 0))

    scored = sorted(
        available_elements,
        key=lambda el: _score_element(el, concept_targets, cognitive_targets),
        reverse=True,
    )

    selected: list[tuple[dict[str, Any], int]] = []
    remaining = blueprint_total
    seen_ids: set[str] = set()

    for el in scored:
        el_id = str(el.get("id", ""))
        if not el_id or el_id in seen_ids:
            continue
        m = _element_marks(el, marks_per_element)
        if 0 < m <= remaining:
            selected.append((el, m))
            seen_ids.add(el_id)
            remaining -= m
        if remaining <= 0:
            break

    sections = _group_into_sections(selected)
    actual_total = blueprint_total - remaining

    return {
        "schema_version": SCHEMA_VERSION,
        "title": title,
        "total_marks": actual_total,
        "sections": sections,
    }


def _score_element(
    el: dict[str, Any],
    concept_targets: dict[str, float],
    cognitive_targets: dict[str, float],
) -> float:
    score = 0.0
    for concept in el.get("concepts") or []:
        score += concept_targets.get(concept, 0.0)
    placement = el.get("placement") or {}
    obj = placement.get("assessment_objective")
    if obj:
        score += cognitive_targets.get(obj, 0.0)
    return score


def _element_marks(el: dict[str, Any], default: int) -> int:
    scheme = el.get("marking_scheme")
    if isinstance(scheme, list) and scheme:
        return sum(int(step.get("weight", 1)) for step in scheme)
    return default


def _group_into_sections(
    selected: list[tuple[dict[str, Any], int]],
) -> list[dict[str, Any]]:
    sections_map: dict[str, list[dict[str, Any]]] = {}
    for el, m in selected:
        obj = (el.get("placement") or {}).get("assessment_objective") or "general"
        sections_map.setdefault(obj, []).append({"id": el["id"], "marks": m})

    sections: list[dict[str, Any]] = []
    for key in _SECTION_ORDER:
        if key in sections_map:
            label = key.replace("_", " ").title()
            sections.append({"name": f"Section — {label}", "questions": sections_map.pop(key)})

    # Any non-standard objectives appended at the end
    for key, qs in sections_map.items():
        sections.append({"name": key.replace("_", " ").title(), "questions": qs})

    return sections
