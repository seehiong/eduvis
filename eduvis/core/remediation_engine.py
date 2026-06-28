"""EduVis — Adaptive Remediation & Path Engine.

Three public functions:

  trace_prerequisite_failure_root(mastery_view, concept_code)
      Walk the prerequisite dependency graph backward from a weak concept to
      find the deepest unmastered root that must be remediated first.
      Returns an ordered remediation path from root → target.

  select_next_element(mastery_view, available_elements, curriculum)
      Given learner state, score and rank available lesson elements to pick the
      single best next element to present.  Scoring favours:
        - elements that address unmastered concepts the learner needs
        - elements targeting active misconceptions
        - prerequisite concepts before dependents
        - lower difficulty when mastery is low

  generate_hint(element, failed_answer)
      Derive a targeted hint from an element's misconceptions mapping and
      solution_steps, matched to the student's submitted wrong answer.
      Returns a HintResult with a misconception code (if detected) and steps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .curriculum import CurriculumGraph
from .mastery_projection import MasteryGraphView

# Weight applied to a concept when the learner has an active misconception for it
_MISCONCEPTION_BOOST = 0.3

# Difficulty ordering (lower index = easier = preferred when mastery is low)
_DIFFICULTY_RANK = {"starter": 0, "routine": 1, "challenge": 2, "": 1}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class RemediationPath:
    """Ordered prerequisite path that must be mastered before the target concept."""
    target_concept: str
    root_concept: str
    path: list[str]           # root → ... → target, all unmastered
    path_names: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_concept": self.target_concept,
            "root_concept": self.root_concept,
            "path": self.path,
            "path_names": self.path_names,
        }


@dataclass
class HintResult:
    """Hint derived from an element's metadata after a wrong answer."""
    misconception_code: str | None
    misconception_detected: bool
    hint_steps: list[str]
    final_hint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "misconception_code": self.misconception_code,
            "misconception_detected": self.misconception_detected,
            "hint_steps": self.hint_steps,
            "final_hint": self.final_hint,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _is_unmastered(code: str, mastery_view: MasteryGraphView) -> bool:
    info = mastery_view.concept_mastery.get(code)
    if info is None:
        return True
    return not info.is_mastered


def _find_root_path(start: str, rev_adj: dict[str, list[str]], mastery_view: MasteryGraphView) -> list[str]:
    best_path: list[str] = [start]
    stack: list[list[str]] = [[start]]

    while stack:
        path = stack.pop()
        curr = path[-1]
        prereqs = [p for p in rev_adj.get(curr, []) if _is_unmastered(p, mastery_view)]

        if not prereqs:
            if len(path) > len(best_path):
                best_path = path
        else:
            for prereq in prereqs:
                if prereq not in path:  # cycle guard
                    stack.append(path + [prereq])

    return list(reversed(best_path))  # root → target


def trace_prerequisite_failure_root(
    mastery_view: MasteryGraphView,
    concept_code: str,
) -> RemediationPath:
    """Find the deepest unmastered prerequisite root for a concept.

    Walks the prerequisite graph backward from concept_code, following only
    unmastered concepts.  Returns an ordered path [root, ..., concept_code]
    so the caller knows where to begin remediation.

    If no unmastered prerequisites exist, the path contains only concept_code.
    """
    curriculum = mastery_view.curriculum

    # BFS backward through prerequisite edges to find all unmastered ancestors
    # Build reverse adjacency: concept → its direct prerequisites
    rev_adj: dict[str, list[str]] = {}
    for dep in curriculum.dependencies:
        if dep.rel_type == "prerequisite":
            rev_adj.setdefault(dep.to_concept, []).append(dep.from_concept)

    path = _find_root_path(concept_code, rev_adj, mastery_view)
    root = path[0]

    path_names = [
        curriculum.concepts[c].name if c in curriculum.concepts else c
        for c in path
    ]

    return RemediationPath(
        target_concept=concept_code,
        root_concept=root,
        path=path,
        path_names=path_names,
    )


def select_next_element(
    mastery_view: MasteryGraphView,
    available_elements: list[dict[str, Any]],
    curriculum: CurriculumGraph | None = None,
) -> dict[str, Any] | None:
    """Score and select the best next element to present to the learner.

    Scoring criteria (additive):
      +concept_relevance  — element covers concepts the learner needs (not mastered)
      +prerequisite_bonus — element covers a concept that unblocks a dependent gap
      +misconception_boost — element targets a concept with active misconceptions
      -difficulty_penalty  — harder difficulty gets a small penalty when mastery is low

    Returns the highest-scoring element dict, or None if no elements provided.
    """
    if not available_elements:
        return None

    curriculum = curriculum or mastery_view.curriculum
    scored = [
        (el, _score_element(el, mastery_view, curriculum))
        for el in available_elements
    ]
    scored.sort(key=lambda x: -x[1])
    return scored[0][0]


def generate_hint(
    element: dict[str, Any],
    failed_answer: str,
) -> HintResult:
    """Derive a targeted hint for a wrong answer.

    Checks the element's misconceptions dict for the failed_answer key.
    Falls back to the element's solution_steps if no misconception match.
    Returns a HintResult with the detected misconception code and hint steps.
    """
    misconceptions: dict[str, Any] = element.get("misconceptions") or {}
    solution_steps: list[str] = element.get("solution_steps") or []

    # Normalise: keys may be option letters (A, B, C …) or free text
    misconception_code: str | None = None
    detected = False

    if failed_answer and failed_answer in misconceptions:
        raw = misconceptions[failed_answer]
        if isinstance(raw, str):
            misconception_code = raw
        detected = True

    # Build hint steps: use solution_steps as the scaffold
    hint_steps = list(solution_steps)

    # Prepend a targeted misconception note when detected
    if detected and misconception_code:
        note = f"You selected an answer linked to a common mistake: '{misconception_code}'. "
        note += "Work through the solution steps below carefully."
        hint_steps = [note] + hint_steps

    final_hint = hint_steps[-1] if hint_steps else "Review the worked example and try again."

    return HintResult(
        misconception_code=misconception_code,
        misconception_detected=detected,
        hint_steps=hint_steps,
        final_hint=final_hint,
    )


# ---------------------------------------------------------------------------
# Internal scoring
# ---------------------------------------------------------------------------

def _score_element(
    el: dict[str, Any],
    mastery_view: MasteryGraphView,
    curriculum: CurriculumGraph,
) -> float:
    score = 0.0
    state = mastery_view.state
    threshold = mastery_view.mastery_threshold

    el_concepts: list[str] = el.get("concepts") or []
    placement: dict[str, Any] = el.get("placement") or {}
    difficulty = placement.get("difficulty") or ""

    for concept_code in el_concepts:
        info = mastery_view.concept_mastery.get(concept_code)
        if info is None:
            mastery = 0.0
            is_mastered = False
        else:
            mastery = info.mastery
            is_mastered = info.is_mastered

        if is_mastered:
            continue

        gap = threshold - mastery
        node = curriculum.concepts.get(concept_code)
        exam_w = node.exam_weight if node else 1.0

        # Concept relevance: weighted by exam importance and mastery gap
        score += exam_w * gap

        # Prerequisite bonus: this concept unblocks other weak concepts
        dependents = curriculum.get_dependents(concept_code, transitive=False)
        for dep in dependents:
            dep_info = mastery_view.concept_mastery.get(dep)
            if dep_info and not dep_info.is_mastered:
                score += 0.2  # bonus per unblocked dependent

        # Misconception boost: learner has active misconceptions on this concept
        active_m = [
            m_code for m_code, m_st in state.misconceptions.items()
            if m_st.state == "active"
            and curriculum.misconceptions.get(m_code) is not None
            and curriculum.misconceptions[m_code].concept == concept_code
        ]
        score += len(active_m) * _MISCONCEPTION_BOOST

        # Difficulty penalty: harder elements score lower when learner is weak
        diff_rank = _DIFFICULTY_RANK.get(difficulty, 1)
        if mastery < 0.4:
            score -= diff_rank * 0.15

    return score
