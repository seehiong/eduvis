"""Tests for eduvis.core.revision_engine."""

from eduvis.core.curriculum import CurriculumGraph
from eduvis.core.learner_state import LearnerState, ConceptState, MisconceptionState
from eduvis.core.mastery_projection import MasteryGraphView
from eduvis.core.revision_engine import (
    get_top_concepts,
    get_top_misconceptions,
    generate_study_plan,
    StudyPlan,
    StudyTopic,
    VALID_MODES,
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
            {"code": "geometry", "name": "Geometry", "exam_weight": 2.5},
        ],
        "skills": [],
        "misconceptions": [
            {"code": "sign_err", "name": "Sign error", "concept": "integers", "remediation_weight": 2.0},
            {"code": "frac_add", "name": "Fraction add error", "concept": "fractions", "remediation_weight": 1.0},
        ],
        "dependencies": [
            {"from": "integers", "to": "algebra", "type": "prerequisite"},
            {"from": "fractions", "to": "algebra", "type": "prerequisite"},
        ],
    }
    return CurriculumGraph.from_dict(data)


def _make_state_with_gaps(learner_id: str = "stu_01") -> LearnerState:
    state = LearnerState(learner_id=learner_id)
    state.concepts["integers"] = ConceptState(mastery=0.3)
    state.concepts["fractions"] = ConceptState(mastery=0.6)
    state.concepts["algebra"] = ConceptState(mastery=0.1)
    # geometry: not in state → mastery=0.0
    state.misconceptions["sign_err"] = MisconceptionState(state="active", attempts=2)
    return state


def _make_mastery_view(
    state: LearnerState | None = None,
    curriculum: CurriculumGraph | None = None,
    threshold: float = 0.8,
) -> MasteryGraphView:
    if state is None:
        state = _make_state_with_gaps()
    if curriculum is None:
        curriculum = _make_curriculum()
    return MasteryGraphView(curriculum, state, mastery_threshold=threshold)


# ---------------------------------------------------------------------------
# get_top_concepts
# ---------------------------------------------------------------------------

class TestGetTopConcepts:
    def test_returns_list(self):
        view = _make_mastery_view()
        result = get_top_concepts(view, n=3)
        assert isinstance(result, list)

    def test_respects_n_limit(self):
        view = _make_mastery_view()
        result = get_top_concepts(view, n=2)
        assert len(result) <= 2

    def test_excludes_mastered_concepts(self):
        state = _make_state_with_gaps()
        state.concepts["integers"] = ConceptState(mastery=1.0)
        view = _make_mastery_view(state=state)
        codes = [r["concept_code"] for r in get_top_concepts(view, n=10)]
        assert "integers" not in codes

    def test_result_has_required_keys(self):
        view = _make_mastery_view()
        result = get_top_concepts(view, n=1)
        assert result
        keys = result[0].keys()
        for k in ("concept_code", "concept_name", "priority_score", "mastery", "status"):
            assert k in keys

    def test_higher_exam_weight_ranks_higher_when_same_gap(self):
        # algebra has exam_weight=3.0 and lowest mastery → should rank highest
        view = _make_mastery_view()
        top = get_top_concepts(view, n=4)
        top_codes = [r["concept_code"] for r in top]
        assert top_codes[0] == "algebra"

    def test_priority_scores_are_non_negative(self):
        view = _make_mastery_view()
        for r in get_top_concepts(view, n=10):
            assert r["priority_score"] >= 0

    def test_all_mastered_returns_empty(self):
        state = LearnerState("s")
        curriculum = _make_curriculum()
        for code in curriculum.concepts:
            state.concepts[code] = ConceptState(mastery=1.0)
        view = MasteryGraphView(curriculum, state, mastery_threshold=0.8)
        assert not get_top_concepts(view)


# ---------------------------------------------------------------------------
# get_top_misconceptions
# ---------------------------------------------------------------------------

class TestGetTopMisconceptions:
    def test_returns_only_active(self):
        state = _make_state_with_gaps()
        state.misconceptions["frac_add"] = MisconceptionState(state="remediated", attempts=1)
        curriculum = _make_curriculum()
        result = get_top_misconceptions(state, curriculum, n=10)
        codes = [r["misconception_code"] for r in result]
        assert "frac_add" not in codes
        assert "sign_err" in codes

    def test_respects_n_limit(self):
        state = _make_state_with_gaps()
        state.misconceptions["frac_add"] = MisconceptionState(state="active", attempts=1)
        curriculum = _make_curriculum()
        result = get_top_misconceptions(state, curriculum, n=1)
        assert len(result) == 1

    def test_higher_remediation_weight_ranks_first(self):
        state = _make_state_with_gaps()
        state.misconceptions["frac_add"] = MisconceptionState(state="active", attempts=1)
        curriculum = _make_curriculum()
        result = get_top_misconceptions(state, curriculum, n=10)
        # sign_err has remediation_weight=2.0 > frac_add=1.0
        assert result[0]["misconception_code"] == "sign_err"

    def test_result_has_required_keys(self):
        state = _make_state_with_gaps()
        curriculum = _make_curriculum()
        result = get_top_misconceptions(state, curriculum, n=5)
        if result:
            for k in ("misconception_code", "misconception_name", "concept", "remediation_weight", "attempts"):
                assert k in result[0]

    def test_empty_when_no_active_misconceptions(self):
        state = LearnerState("s")
        curriculum = _make_curriculum()
        assert not get_top_misconceptions(state, curriculum)


# ---------------------------------------------------------------------------
# generate_study_plan
# ---------------------------------------------------------------------------

class TestGenerateStudyPlan:
    def test_returns_study_plan(self):
        view = _make_mastery_view()
        plan = generate_study_plan(view, _make_curriculum(), hours=2.0, mode="revision")
        assert isinstance(plan, StudyPlan)

    def test_plan_to_dict_has_keys(self):
        view = _make_mastery_view()
        plan = generate_study_plan(view, _make_curriculum(), hours=2.0)
        d = plan.to_dict()
        for k in ("mode", "total_hours", "mastery_threshold", "topics", "summary"):
            assert k in d

    def test_topics_are_study_topic_instances(self):
        view = _make_mastery_view()
        plan = generate_study_plan(view, _make_curriculum(), hours=2.0)
        for t in plan.topics:
            assert isinstance(t, StudyTopic)

    def test_topics_fit_within_budget(self):
        view = _make_mastery_view()
        plan = generate_study_plan(view, _make_curriculum(), hours=1.0, mode="revision")
        total_minutes = sum(t.estimated_minutes for t in plan.topics)
        assert total_minutes <= 60

    def test_all_modes_run_without_error(self):
        curriculum = _make_curriculum()
        view = _make_mastery_view(curriculum=curriculum)
        for mode in VALID_MODES:
            plan = generate_study_plan(view, curriculum, hours=2.0, mode=mode)
            assert plan.mode == mode

    def test_invalid_mode_falls_back_to_revision(self):
        view = _make_mastery_view()
        plan = generate_study_plan(view, _make_curriculum(), hours=2.0, mode="unknown_mode")
        assert plan.mode == "revision"

    def test_lesson_mode_puts_prerequisites_first(self):
        view = _make_mastery_view()
        plan = generate_study_plan(view, _make_curriculum(), hours=10.0, mode="lesson")
        codes = [t.concept_code for t in plan.topics]
        if "integers" in codes and "algebra" in codes:
            assert codes.index("integers") < codes.index("algebra")

    def test_exam_prep_ranks_by_exam_weight_times_gap(self):
        view = _make_mastery_view()
        plan = generate_study_plan(view, _make_curriculum(), hours=10.0, mode="exam_prep")
        # algebra: exam_weight=3.0, mastery=0.1 → gap=0.7 → score=2.1
        # geometry: exam_weight=2.5, mastery=0.0 → gap=0.8 → score=2.0
        # algebra should rank first
        if plan.topics:
            assert plan.topics[0].concept_code == "algebra"

    def test_crash_course_selects_high_centrality_concepts(self):
        view = _make_mastery_view()
        plan = generate_study_plan(view, _make_curriculum(), hours=10.0, mode="crash_course")
        # integers and fractions have centrality (prerequisites of algebra)
        codes = {t.concept_code for t in plan.topics}
        assert "integers" in codes or "fractions" in codes

    def test_summary_has_expected_keys(self):
        view = _make_mastery_view()
        plan = generate_study_plan(view, _make_curriculum(), hours=2.0)
        for k in ("concepts_covered", "total_estimated_minutes", "total_concepts_in_graph",
                  "already_mastered", "remaining_after_plan"):
            assert k in plan.summary

    def test_fully_mastered_state_returns_empty_plan(self):
        state = LearnerState("s")
        curriculum = _make_curriculum()
        for code in curriculum.concepts:
            state.concepts[code] = ConceptState(mastery=1.0)
        view = MasteryGraphView(curriculum, state)
        plan = generate_study_plan(view, curriculum, hours=2.0)
        assert not plan.topics

    def test_topic_contains_active_misconceptions(self):
        view = _make_mastery_view()
        plan = generate_study_plan(view, _make_curriculum(), hours=10.0)
        integers_topic = next((t for t in plan.topics if t.concept_code == "integers"), None)
        if integers_topic:
            assert "sign_err" in integers_topic.active_misconceptions
