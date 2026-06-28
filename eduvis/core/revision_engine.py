"""EduVis — Revision & Knowledge Condensation Engine.

Condenses a full curriculum graph + learner state into focused, time-bounded
revision plans.  Four public functions:

  get_top_concepts(mastery_view, n)
      Rank all concepts by a priority score combining exam importance,
      graph centrality, and mastery gap.  Returns the top-N highest-priority
      concepts to study next.

  get_top_misconceptions(state, curriculum, n)
      Return the top-N active misconceptions, ranked by remediation_weight.

  generate_study_plan(mastery_view, curriculum, hours, mode)
      Condenses the full concept graph into a prioritized, time-bounded
      study plan.  Four modes:

      lesson      — depth-first: prerequisites before targets
      revision    — focus on concepts with mastery gap (below threshold)
      exam_prep   — weight by exam_weight × gap; surface highest-value gaps
      crash_course — extreme compression: only critical bottleneck concepts

  StudyPlan / StudyTopic — lightweight result containers
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .curriculum import CurriculumGraph
from .mastery_projection import MasteryGraphView
from .learner_state import LearnerState

# Minutes of study assumed per concept depending on depth of gap
_MINUTES_PER_CONCEPT_WEAK = 15
_MINUTES_PER_CONCEPT_GAP = 25
_MINUTES_PER_MISCONCEPTION = 10

VALID_MODES = frozenset({"lesson", "revision", "exam_prep", "crash_course"})


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class StudyTopic:
    """A single entry in a study plan."""
    concept_code: str
    concept_name: str
    priority_score: float
    mastery: float
    status: str                       # mastered | weak | gap | locked
    active_misconceptions: list[str] = field(default_factory=list)
    prerequisite_of: list[str] = field(default_factory=list)
    estimated_minutes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept_code": self.concept_code,
            "concept_name": self.concept_name,
            "priority_score": round(self.priority_score, 4),
            "mastery": round(self.mastery, 4),
            "status": self.status,
            "active_misconceptions": self.active_misconceptions,
            "prerequisite_of": self.prerequisite_of,
            "estimated_minutes": self.estimated_minutes,
        }


@dataclass
class StudyPlan:
    """Output of generate_study_plan."""
    mode: str
    total_hours: float
    mastery_threshold: float
    topics: list[StudyTopic]
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "total_hours": self.total_hours,
            "mastery_threshold": self.mastery_threshold,
            "topics": [t.to_dict() for t in self.topics],
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_top_concepts(
    mastery_view: MasteryGraphView,
    n: int = 5,
) -> list[dict[str, Any]]:
    """Return the top-N highest-priority concepts to study.

    Priority = exam_weight × centrality_weight_normalised × (1 - mastery).
    Concepts already mastered (mastery >= threshold) are excluded.
    Returns a list of dicts with concept_code, concept_name, priority_score, mastery.
    """
    curriculum = mastery_view.curriculum
    threshold = mastery_view.mastery_threshold

    max_centrality = max(
        (c.centrality_weight for c in curriculum.concepts.values()),
        default=1.0,
    ) or 1.0

    results: list[dict[str, Any]] = []
    for code, info in mastery_view.concept_mastery.items():
        if info.is_mastered:
            continue
        node = curriculum.concepts.get(code)
        if not node:
            continue
        gap = max(0.0, threshold - info.mastery)
        norm_centrality = node.centrality_weight / max_centrality
        priority = node.exam_weight * (0.5 + 0.5 * norm_centrality) * gap
        results.append({
            "concept_code": code,
            "concept_name": info.name,
            "priority_score": round(priority, 4),
            "mastery": round(info.mastery, 4),
            "status": mastery_view.get_concept_status(code),
        })

    results.sort(key=lambda x: -x["priority_score"])
    return results[:n]


def get_top_misconceptions(
    state: LearnerState,
    curriculum: CurriculumGraph,
    n: int = 5,
) -> list[dict[str, Any]]:
    """Return the top-N active misconceptions ranked by remediation_weight.

    Only misconceptions with state == 'active' are included.
    """
    results: list[dict[str, Any]] = []
    for code, m_state in state.misconceptions.items():
        if m_state.state != "active":
            continue
        node = curriculum.misconceptions.get(code)
        remediation_weight = node.remediation_weight if node else 1.0
        concept_name = ""
        if node:
            c_node = curriculum.concepts.get(node.concept)
            concept_name = c_node.name if c_node else node.concept
        results.append({
            "misconception_code": code,
            "misconception_name": node.name if node else code,
            "concept": node.concept if node else "",
            "concept_name": concept_name,
            "remediation_weight": remediation_weight,
            "attempts": m_state.attempts,
        })

    results.sort(key=lambda x: (-x["remediation_weight"], -x["attempts"]))
    return results[:n]


def generate_study_plan(
    mastery_view: MasteryGraphView,
    curriculum: CurriculumGraph,
    hours: float = 2.0,
    mode: str = "revision",
) -> StudyPlan:
    """Condense the full concept graph into a time-bounded study plan.

    mode options:
      lesson      — prerequisite-first ordering; covers foundation before targets
      revision    — focus on concepts below mastery threshold, ordered by gap size
      exam_prep   — rank by exam_weight × gap; surfaces highest exam-value gaps
      crash_course — only critical bottleneck concepts (highest centrality + gap)
    """
    if mode not in VALID_MODES:
        mode = "revision"

    budget_minutes = int(hours * 60)

    all_topics = _build_all_topics(mastery_view, curriculum)

    if mode == "lesson":
        ranked = _rank_lesson(all_topics, curriculum)
    elif mode == "exam_prep":
        ranked = _rank_exam_prep(all_topics, curriculum)
    elif mode == "crash_course":
        ranked = _rank_crash_course(all_topics, curriculum)
    else:
        ranked = _rank_revision(all_topics)

    selected = _fit_to_budget(ranked, budget_minutes)

    summary = _build_summary(selected, mastery_view)

    return StudyPlan(
        mode=mode,
        total_hours=hours,
        mastery_threshold=mastery_view.mastery_threshold,
        topics=selected,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_all_topics(
    mastery_view: MasteryGraphView,
    curriculum: CurriculumGraph,
) -> list[StudyTopic]:
    """Build a StudyTopic for every non-mastered concept."""
    state = mastery_view.state
    threshold = mastery_view.mastery_threshold

    topics: list[StudyTopic] = []
    for code, info in mastery_view.concept_mastery.items():
        if info.is_mastered:
            continue

        node = curriculum.concepts.get(code)
        exam_w = node.exam_weight if node else 1.0
        centrality = node.centrality_weight if node else 0.0
        gap = max(0.0, threshold - info.mastery)

        # Active misconceptions linked to this concept
        active_m = [
            m_code for m_code, m_st in state.misconceptions.items()
            if m_st.state == "active"
            and curriculum.misconceptions.get(m_code) is not None
            and curriculum.misconceptions[m_code].concept == code
        ]

        # Concepts this concept is a prerequisite for
        prereq_of = curriculum.get_dependents(code, transitive=False)

        minutes = _estimate_minutes(info.mastery, threshold, len(active_m))

        topic = StudyTopic(
            concept_code=code,
            concept_name=info.name,
            priority_score=exam_w * centrality * gap,
            mastery=info.mastery,
            status=mastery_view.get_concept_status(code),
            active_misconceptions=active_m,
            prerequisite_of=prereq_of,
            estimated_minutes=minutes,
        )
        topics.append(topic)

    return topics


def _estimate_minutes(mastery: float, threshold: float, misconception_count: int) -> int:
    gap = threshold - mastery
    base = _MINUTES_PER_CONCEPT_GAP if gap > 0.4 else _MINUTES_PER_CONCEPT_WEAK
    return base + misconception_count * _MINUTES_PER_MISCONCEPTION


def _rank_revision(topics: list[StudyTopic]) -> list[StudyTopic]:
    return sorted(topics, key=lambda t: t.mastery)


def _rank_exam_prep(
    topics: list[StudyTopic],
    curriculum: CurriculumGraph,
) -> list[StudyTopic]:
    def score(t: StudyTopic) -> float:
        node = curriculum.concepts.get(t.concept_code)
        ew = node.exam_weight if node else 1.0
        return ew * (1.0 - t.mastery)

    return sorted(topics, key=lambda t: -score(t))


def _rank_crash_course(
    topics: list[StudyTopic],
    curriculum: CurriculumGraph,
) -> list[StudyTopic]:
    def score(t: StudyTopic) -> float:
        node = curriculum.concepts.get(t.concept_code)
        centrality = node.centrality_weight if node else 0.0
        ew = node.exam_weight if node else 1.0
        return (centrality + ew) * (1.0 - t.mastery)

    return sorted(topics, key=lambda t: -score(t))


def _rank_lesson(
    topics: list[StudyTopic],
    curriculum: CurriculumGraph,
) -> list[StudyTopic]:
    """Topological prerequisite-first ordering among non-mastered concepts."""
    topic_map = {t.concept_code: t for t in topics}
    codes = set(topic_map.keys())

    # Build adjacency restricted to non-mastered concepts
    adj: dict[str, list[str]] = {code: [] for code in codes}
    for dep in curriculum.dependencies:
        if dep.rel_type == "prerequisite" and dep.from_concept in codes and dep.to_concept in codes:
            adj[dep.from_concept].append(dep.to_concept)

    # Kahn's algorithm for topological sort
    in_degree: dict[str, int] = {code: 0 for code in codes}
    for code in codes:
        for child in adj[code]:
            in_degree[child] = in_degree.get(child, 0) + 1

    from collections import deque
    queue: deque[str] = deque(sorted(c for c in codes if in_degree[c] == 0))
    ordered: list[StudyTopic] = []

    while queue:
        code = queue.popleft()
        ordered.append(topic_map[code])
        for child in sorted(adj[code]):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    # Append any remaining (cycle-protected)
    seen = {t.concept_code for t in ordered}
    for t in topics:
        if t.concept_code not in seen:
            ordered.append(t)

    return ordered


def _fit_to_budget(topics: list[StudyTopic], budget_minutes: int) -> list[StudyTopic]:
    """Select topics until the time budget is filled."""
    selected: list[StudyTopic] = []
    remaining = budget_minutes

    for topic in topics:
        if topic.estimated_minutes <= remaining:
            selected.append(topic)
            remaining -= topic.estimated_minutes
        if remaining <= 0:
            break

    return selected


def _build_summary(
    selected: list[StudyTopic],
    mastery_view: MasteryGraphView,
) -> dict[str, Any]:
    total_minutes = sum(t.estimated_minutes for t in selected)
    total_concepts = len(mastery_view.concept_mastery)
    mastered_count = sum(1 for i in mastery_view.concept_mastery.values() if i.is_mastered)

    return {
        "concepts_covered": len(selected),
        "total_estimated_minutes": total_minutes,
        "total_concepts_in_graph": total_concepts,
        "already_mastered": mastered_count,
        "remaining_after_plan": total_concepts - mastered_count - len(selected),
    }
