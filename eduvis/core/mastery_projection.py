"""EduVis — Mastery Graph Projection.

Combines the static CurriculumGraph with dynamic LearnerState
to construct a MasteryGraphView that exposes active gaps, bottlenecks,
and concept states.
"""

from __future__ import annotations

from typing import Any

from .constants import DEFAULT_MASTERY_THRESHOLD
from .curriculum import CurriculumGraph
from .learner_state import LearnerState


class ConceptMasteryInfo:  # pylint: disable=too-few-public-methods
    """Combines concept details with current student mastery metrics."""

    def __init__(
        self,
        code: str,
        name: str,
        mastery: float,
        *,
        confidence: float | None = None,
        is_mastered: bool = False,
        has_gaps: bool = False,
        gaps: list[str] | None = None,
    ) -> None:
        self.code = code
        self.name = name
        self.mastery = mastery
        self.confidence = confidence
        self.is_mastered = is_mastered
        self.has_gaps = has_gaps
        self.gaps = gaps or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "mastery": self.mastery,
            "confidence": self.confidence,
            "is_mastered": self.is_mastered,
            "has_gaps": self.has_gaps,
            "gaps": self.gaps,
        }


class MasteryGraphView:
    """Provides a projected view combining static curriculum graph and dynamic state."""

    def __init__(
        self,
        curriculum: CurriculumGraph,
        state: LearnerState,
        mastery_threshold: float = DEFAULT_MASTERY_THRESHOLD,
    ) -> None:
        self.curriculum = curriculum
        self.state = state
        self.mastery_threshold = mastery_threshold

        self.concept_mastery: dict[str, ConceptMasteryInfo] = {}
        self.prerequisite_gaps: list[dict[str, Any]] = []
        self._project()

    def _project(self) -> None:
        # Build concept mastery map
        for c_code, concept in self.curriculum.concepts.items():
            state_c = self.state.concepts.get(c_code)
            mastery = state_c.mastery if state_c else 0.0
            confidence = state_c.confidence if state_c else None
            is_mastered = mastery >= self.mastery_threshold

            self.concept_mastery[c_code] = ConceptMasteryInfo(
                code=c_code,
                name=concept.name,
                mastery=mastery,
                confidence=confidence,
                is_mastered=is_mastered,
            )

        # Detect gaps by traversing dependencies
        # Direct dependencies mapping
        for dep in self.curriculum.dependencies:
            if dep.rel_type == "prerequisite":
                from_c = dep.from_concept
                to_c = dep.to_concept

                # Check if from_c is mastered
                from_info = self.concept_mastery.get(from_c)
                from_mastery = from_info.mastery if from_info else 0.0

                if from_mastery < self.mastery_threshold:
                    # Target concept to_c has a prerequisite gap
                    to_info = self.concept_mastery.get(to_c)
                    if to_info:
                        to_info.has_gaps = True
                        if from_c not in to_info.gaps:
                            to_info.gaps.append(from_c)

                    self.prerequisite_gaps.append({
                        "concept": to_c,
                        "missing_prerequisite": from_c,
                        "current_mastery": from_mastery,
                    })

    def get_concept_status(self, code: str) -> str:
        """Get the status of a concept node: 'mastered', 'gap', 'weak', or 'locked'."""
        info = self.concept_mastery.get(code)
        if not info:
            return "unknown"
        if info.is_mastered:
            return "mastered"
        if info.has_gaps:
            return "gap"
        if info.mastery > 0.0:
            return "weak"
        return "locked"

    def to_dict(self) -> dict[str, Any]:
        return {
            "learner_id": self.state.learner_id,
            "mastery_threshold": self.mastery_threshold,
            "concepts": {code: info.to_dict() for code, info in self.concept_mastery.items()},
            "gaps": self.prerequisite_gaps,
        }
