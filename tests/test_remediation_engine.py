"""Tests for eduvis.core.remediation_engine."""

from eduvis.core.curriculum import CurriculumGraph
from eduvis.core.learner_state import LearnerState, ConceptState, MisconceptionState
from eduvis.core.mastery_projection import MasteryGraphView
from eduvis.core.remediation_engine import (
    trace_prerequisite_failure_root,
    select_next_element,
    generate_hint,
    RemediationPath,
    HintResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_curriculum() -> CurriculumGraph:
    data = {
        "concepts": [
            {"code": "integers", "name": "Integers", "exam_weight": 2.0},
            {"code": "fractions", "name": "Fractions", "exam_weight": 1.5},
            {"code": "algebra", "name": "Algebra", "exam_weight": 3.0},
            {"code": "geometry", "name": "Geometry", "exam_weight": 2.0},
        ],
        "skills": [],
        "misconceptions": [
            {"code": "sign_err", "name": "Sign error", "concept": "integers", "remediation_weight": 2.0},
        ],
        "dependencies": [
            {"from": "integers", "to": "algebra", "type": "prerequisite"},
            {"from": "fractions", "to": "algebra", "type": "prerequisite"},
        ],
    }
    return CurriculumGraph.from_dict(data)


def _make_view(mastery_map: dict[str, float] | None = None) -> MasteryGraphView:
    state = LearnerState("stu")
    if mastery_map:
        for code, m in mastery_map.items():
            state.concepts[code] = ConceptState(mastery=m)
    return MasteryGraphView(_make_curriculum(), state, mastery_threshold=0.8)


# ---------------------------------------------------------------------------
# trace_prerequisite_failure_root
# ---------------------------------------------------------------------------

class TestTracePrerequisiteFailureRoot:
    def test_returns_remediation_path(self):
        view = _make_view({"integers": 0.2, "fractions": 0.3, "algebra": 0.1})
        result = trace_prerequisite_failure_root(view, "algebra")
        assert isinstance(result, RemediationPath)

    def test_path_ends_with_target(self):
        view = _make_view({"integers": 0.2, "fractions": 0.3, "algebra": 0.1})
        result = trace_prerequisite_failure_root(view, "algebra")
        assert result.path[-1] == "algebra"

    def test_path_starts_with_root(self):
        view = _make_view({"integers": 0.2, "fractions": 0.3, "algebra": 0.1})
        result = trace_prerequisite_failure_root(view, "algebra")
        assert result.root_concept == result.path[0]

    def test_mastered_prerequisites_not_in_path(self):
        view = _make_view({"integers": 1.0, "fractions": 0.2, "algebra": 0.1})
        result = trace_prerequisite_failure_root(view, "algebra")
        # integers is mastered so should not be in path
        assert "integers" not in result.path

    def test_concept_with_no_prerequisites_returns_self(self):
        view = _make_view({"geometry": 0.1})
        result = trace_prerequisite_failure_root(view, "geometry")
        assert result.path == ["geometry"]
        assert result.root_concept == "geometry"

    def test_path_names_same_length_as_path(self):
        view = _make_view({"integers": 0.2, "fractions": 0.3, "algebra": 0.1})
        result = trace_prerequisite_failure_root(view, "algebra")
        assert len(result.path) == len(result.path_names)

    def test_to_dict_has_expected_keys(self):
        view = _make_view({"algebra": 0.1})
        result = trace_prerequisite_failure_root(view, "algebra")
        d = result.to_dict()
        for k in ("target_concept", "root_concept", "path", "path_names"):
            assert k in d


# ---------------------------------------------------------------------------
# select_next_element
# ---------------------------------------------------------------------------

class TestSelectNextElement:
    def _elements(self) -> list[dict]:
        return [
            {
                "id": "integers_starter",
                "concepts": ["integers"],
                "placement": {"lesson_phase": "independent_practice", "difficulty": "starter",
                              "memory_role": "practice"},
            },
            {
                "id": "algebra_routine",
                "concepts": ["algebra"],
                "placement": {"lesson_phase": "independent_practice", "difficulty": "routine",
                              "memory_role": "practice"},
            },
            {
                "id": "geometry_challenge",
                "concepts": ["geometry"],
                "placement": {"lesson_phase": "independent_practice", "difficulty": "challenge",
                              "memory_role": "practice"},
            },
        ]

    def test_returns_element_dict_or_none(self):
        view = _make_view({"integers": 0.2})
        result = select_next_element(view, self._elements())
        assert result is None or isinstance(result, dict)

    def test_returns_none_for_empty_pool(self):
        view = _make_view()
        assert select_next_element(view, []) is None

    def test_prefers_unmastered_concepts(self):
        # integers (mastery=0.2) and algebra (mastery=0.1) — both weak
        # algebra has exam_weight=3.0 so algebra_routine should score higher
        view = _make_view({"integers": 0.2, "fractions": 0.3, "algebra": 0.1, "geometry": 0.0})
        result = select_next_element(view, self._elements())
        assert result is not None
        assert "algebra" in result["concepts"] or "integers" in result["concepts"]

    def test_mastered_concept_elements_rank_lower(self):
        # geometry is mastered; integers is weak
        view = _make_view({"integers": 0.2, "fractions": 0.3, "algebra": 0.1, "geometry": 1.0})
        result = select_next_element(view, self._elements())
        assert result is not None
        assert result.get("id") != "geometry_challenge"

    def test_misconception_boost_applied(self):
        state = LearnerState("s")
        state.concepts["integers"] = ConceptState(mastery=0.3)
        state.concepts["algebra"] = ConceptState(mastery=0.5)
        state.misconceptions["sign_err"] = MisconceptionState(state="active", attempts=2)
        view = MasteryGraphView(_make_curriculum(), state)
        result = select_next_element(view, self._elements())
        # integers_starter targets integers which has active sign_err
        assert result is not None
        assert result["id"] == "integers_starter"

    def test_single_element_always_selected(self):
        view = _make_view({"integers": 0.2})
        elements = [{"id": "only", "concepts": ["integers"],
                     "placement": {"memory_role": "practice"}}]
        result = select_next_element(view, elements)
        assert result["id"] == "only"


# ---------------------------------------------------------------------------
# generate_hint
# ---------------------------------------------------------------------------

class TestGenerateHint:
    def _element(self) -> dict:
        return {
            "id": "check_negative",
            "type": "multiple_choice",
            "question": "Which is larger: -7 or -2?",
            "options": {
                "A": "-7",
                "B": "-2",
                "C": "They are equal",
                "D": "Cannot tell",
            },
            "answer": "B",
            "misconceptions": {
                "A": "digit_size_magnitude_error",
            },
            "solution_steps": [
                "Plot both on a number line.",
                "-2 is to the right of -7.",
                "The number further right is larger.",
                "Answer: -2 > -7.",
            ],
        }

    def test_returns_hint_result(self):
        result = generate_hint(self._element(), "A")
        assert isinstance(result, HintResult)

    def test_detects_misconception_for_known_wrong_answer(self):
        result = generate_hint(self._element(), "A")
        assert result.misconception_detected is True
        assert result.misconception_code == "digit_size_magnitude_error"

    def test_no_misconception_for_unknown_wrong_answer(self):
        result = generate_hint(self._element(), "C")
        assert result.misconception_detected is False
        assert result.misconception_code is None

    def test_hint_steps_include_solution_steps(self):
        result = generate_hint(self._element(), "A")
        # solution steps should appear in hint_steps
        assert any("number line" in s for s in result.hint_steps)

    def test_misconception_note_prepended_when_detected(self):
        result = generate_hint(self._element(), "A")
        assert "digit_size_magnitude_error" in result.hint_steps[0]

    def test_final_hint_is_last_step(self):
        result = generate_hint(self._element(), "A")
        assert result.final_hint == result.hint_steps[-1]

    def test_empty_failed_answer_returns_generic_hint(self):
        element = {"id": "q1", "type": "multiple_choice"}
        result = generate_hint(element, "")
        assert result.misconception_detected is False
        assert "Review" in result.final_hint or result.final_hint != ""

    def test_element_with_no_metadata_returns_fallback(self):
        result = generate_hint({}, "A")
        assert result.misconception_detected is False
        assert isinstance(result.hint_steps, list)

    def test_to_dict_has_expected_keys(self):
        result = generate_hint(self._element(), "A")
        d = result.to_dict()
        for k in ("misconception_code", "misconception_detected", "hint_steps", "final_hint"):
            assert k in d
