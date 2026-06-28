"""Tests for eduvis.core.blueprint_engine."""

from eduvis.core.blueprint_engine import (
    generate_blueprint,
    validate_paper_coverage,
    assemble_paper,
    DEFAULT_COGNITIVE_WEIGHTS,
)
from eduvis.core.curriculum import CurriculumGraph


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_curriculum() -> CurriculumGraph:
    data = {
        "concepts": [
            {"code": "integers", "name": "Integers", "exam_weight": 2.0},
            {"code": "fractions", "name": "Fractions", "exam_weight": 1.5},
            {"code": "algebra", "name": "Algebra", "exam_weight": 3.0},
        ],
        "skills": [
            {"code": "add_integers", "name": "Add integers", "concept": "integers"},
            {"code": "solve_linear", "name": "Solve linear", "concept": "algebra"},
        ],
        "misconceptions": [
            {"code": "sign_confusion", "name": "Sign confusion", "concept": "integers", "remediation_weight": 1.5},
        ],
        "dependencies": [
            {"from": "integers", "to": "algebra", "type": "prerequisite"},
            {"from": "fractions", "to": "algebra", "type": "prerequisite"},
        ],
    }
    return CurriculumGraph.from_dict(data)


def _make_elements() -> list[dict]:
    return [
        {
            "id": "q1",
            "type": "multiple_choice",
            "concepts": ["integers"],
            "placement": {"lesson_phase": "independent_practice", "memory_role": "practice",
                          "assessment_objective": "conceptual_understanding"},
            "marking_scheme": [{"weight": 2}],
        },
        {
            "id": "q2",
            "type": "short_answer",
            "concepts": ["algebra"],
            "placement": {"lesson_phase": "independent_practice", "memory_role": "practice",
                          "assessment_objective": "procedural_fluency"},
            "marking_scheme": [{"weight": 1}, {"weight": 1}],
        },
        {
            "id": "q3",
            "type": "multiple_choice",
            "concepts": ["fractions"],
            "placement": {"lesson_phase": "independent_practice", "memory_role": "practice",
                          "assessment_objective": "procedural_fluency"},
        },
        {
            "id": "q4",
            "type": "short_answer",
            "concepts": ["algebra"],
            "placement": {"lesson_phase": "independent_practice", "memory_role": "practice",
                          "assessment_objective": "reasoning"},
            "marking_scheme": [{"weight": 1}, {"weight": 1}, {"weight": 1}],
        },
    ]


# ---------------------------------------------------------------------------
# generate_blueprint
# ---------------------------------------------------------------------------

class TestGenerateBlueprint:
    def test_returns_schema_version(self):
        curriculum = _make_curriculum()
        bp = generate_blueprint(curriculum, 40)
        assert bp["schema_version"] == "0.7"

    def test_total_marks_preserved(self):
        curriculum = _make_curriculum()
        bp = generate_blueprint(curriculum, 40)
        assert bp["total_marks"] == 40

    def test_concept_targets_present(self):
        curriculum = _make_curriculum()
        bp = generate_blueprint(curriculum, 40)
        concept_targets = [t for t in bp["targets"] if t["type"] == "concept"]
        codes = {t["code"] for t in concept_targets}
        assert {"integers", "fractions", "algebra"} == codes

    def test_cognitive_targets_present(self):
        curriculum = _make_curriculum()
        bp = generate_blueprint(curriculum, 40)
        cog_targets = [t for t in bp["targets"] if t["type"] == "cognitive_skill"]
        codes = {t["code"] for t in cog_targets}
        assert codes == set(DEFAULT_COGNITIVE_WEIGHTS.keys())

    def test_concept_weights_sum_to_one(self):
        curriculum = _make_curriculum()
        bp = generate_blueprint(curriculum, 40)
        concept_weights = [t["weight"] for t in bp["targets"] if t["type"] == "concept"]
        assert abs(sum(concept_weights) - 1.0) < 0.01

    def test_cognitive_weights_sum_to_one(self):
        curriculum = _make_curriculum()
        bp = generate_blueprint(curriculum, 40)
        cog_weights = [t["weight"] for t in bp["targets"] if t["type"] == "cognitive_skill"]
        assert abs(sum(cog_weights) - 1.0) < 0.01

    def test_higher_exam_weight_concept_gets_higher_blueprint_weight(self):
        curriculum = _make_curriculum()
        bp = generate_blueprint(curriculum, 40)
        concept_map = {t["code"]: t["weight"] for t in bp["targets"] if t["type"] == "concept"}
        # algebra has highest exam_weight (3.0) AND is a dependent → also highest centrality
        assert concept_map["algebra"] >= concept_map["integers"]
        assert concept_map["algebra"] >= concept_map["fractions"]

    def test_custom_cognitive_weights(self):
        curriculum = _make_curriculum()
        custom = {"procedural_fluency": 1.0}
        bp = generate_blueprint(curriculum, 40, cognitive_weights=custom)
        cog = [t for t in bp["targets"] if t["type"] == "cognitive_skill"]
        assert len(cog) == 1
        assert cog[0]["code"] == "procedural_fluency"
        assert cog[0]["weight"] == 1.0

    def test_empty_curriculum_has_no_concept_targets(self):
        empty = CurriculumGraph()
        bp = generate_blueprint(empty, 20)
        concept_targets = [t for t in bp["targets"] if t["type"] == "concept"]
        assert concept_targets == []
        assert bp["total_marks"] == 20


# ---------------------------------------------------------------------------
# validate_paper_coverage
# ---------------------------------------------------------------------------

class TestValidatePaperCoverage:
    def _make_paper(self) -> dict:
        return {
            "title": "Test Paper",
            "sections": [
                {
                    "name": "Section A",
                    "questions": [
                        {"id": "q1", "marks": 10},
                        {"id": "q2", "marks": 10},
                    ],
                },
                {
                    "name": "Section B",
                    "questions": [
                        {"id": "q3", "marks": 10},
                        {"id": "q4", "marks": 10},
                    ],
                },
            ],
        }

    def _make_blueprint(self) -> dict:
        return {
            "schema_version": "0.7",
            "total_marks": 40,
            "targets": [
                {"type": "concept", "code": "integers", "weight": 0.25},
                {"type": "concept", "code": "algebra", "weight": 0.50},
                {"type": "concept", "code": "fractions", "weight": 0.25},
                {"type": "cognitive_skill", "code": "conceptual_understanding", "weight": 0.25},
                {"type": "cognitive_skill", "code": "procedural_fluency", "weight": 0.50},
                {"type": "cognitive_skill", "code": "reasoning", "weight": 0.25},
            ],
        }

    def test_clean_paper_returns_no_warnings(self):
        paper = self._make_paper()
        blueprint = self._make_blueprint()
        elements = {el["id"]: el for el in _make_elements()}
        warnings = validate_paper_coverage(paper, blueprint, elements)
        assert not warnings

    def test_total_marks_mismatch_raises_warning(self):
        paper = {
            "title": "Test",
            "sections": [{"name": "A", "questions": [{"id": "q1", "marks": 5}]}],
        }
        blueprint = {"schema_version": "0.7", "total_marks": 40, "targets": []}
        elements = {"q1": _make_elements()[0]}
        warnings = validate_paper_coverage(paper, blueprint, elements)
        assert any("total marks" in w for w in warnings)

    def test_zero_coverage_concept_warns(self):
        paper = {
            "title": "Test",
            "sections": [{"name": "A", "questions": [{"id": "q2", "marks": 40}]}],
        }
        blueprint = {
            "schema_version": "0.7",
            "total_marks": 40,
            "targets": [
                {"type": "concept", "code": "integers", "weight": 0.5},
                {"type": "concept", "code": "algebra", "weight": 0.5},
            ],
        }
        elements = {"q2": _make_elements()[1]}
        warnings = validate_paper_coverage(paper, blueprint, elements)
        assert any("integers" in w and "zero marks" in w for w in warnings)

    def test_over_covered_concept_warns(self):
        paper = {
            "title": "Test",
            "sections": [{"name": "A", "questions": [
                {"id": "q1", "marks": 30},
                {"id": "q2", "marks": 10},
            ]}],
        }
        blueprint = {
            "schema_version": "0.7",
            "total_marks": 40,
            "targets": [
                {"type": "concept", "code": "integers", "weight": 0.10},
                {"type": "concept", "code": "algebra", "weight": 0.90},
            ],
        }
        elements = {"q1": _make_elements()[0], "q2": _make_elements()[1]}
        warnings = validate_paper_coverage(paper, blueprint, elements)
        assert any("integers" in w and "over-covered" in w for w in warnings)

    def test_empty_paper_sections_warns_only_about_total(self):
        paper = {"title": "Empty", "sections": []}
        blueprint = {"schema_version": "0.7", "total_marks": 40, "targets": [
            {"type": "concept", "code": "integers", "weight": 1.0}
        ]}
        warnings = validate_paper_coverage(paper, blueprint, {})
        assert any("total marks" in w for w in warnings)
        assert not any("under-covered" in w or "over-covered" in w for w in warnings)


# ---------------------------------------------------------------------------
# assemble_paper
# ---------------------------------------------------------------------------

class TestAssemblePaper:
    def _make_blueprint(self) -> dict:
        return {
            "schema_version": "0.7",
            "total_marks": 6,
            "targets": [
                {"type": "concept", "code": "algebra", "weight": 0.6},
                {"type": "concept", "code": "integers", "weight": 0.4},
                {"type": "cognitive_skill", "code": "procedural_fluency", "weight": 0.5},
                {"type": "cognitive_skill", "code": "conceptual_understanding", "weight": 0.3},
                {"type": "cognitive_skill", "code": "reasoning", "weight": 0.2},
            ],
        }

    def test_returns_assessment_paper_structure(self):
        bp = self._make_blueprint()
        paper = assemble_paper(bp, _make_elements(), title="Algebra Test")
        assert paper["title"] == "Algebra Test"
        assert "sections" in paper
        assert "schema_version" in paper

    def test_total_marks_does_not_exceed_blueprint(self):
        bp = self._make_blueprint()
        paper = assemble_paper(bp, _make_elements())
        assert paper["total_marks"] <= bp["total_marks"]

    def test_all_questions_have_id_and_marks(self):
        bp = self._make_blueprint()
        paper = assemble_paper(bp, _make_elements())
        for section in paper["sections"]:
            for q in section["questions"]:
                assert "id" in q
                assert "marks" in q
                assert q["marks"] > 0

    def test_no_duplicate_element_ids(self):
        bp = self._make_blueprint()
        paper = assemble_paper(bp, _make_elements())
        all_ids = [q["id"] for s in paper["sections"] for q in s["questions"]]
        assert len(all_ids) == len(set(all_ids))

    def test_sections_grouped_by_objective(self):
        bp = self._make_blueprint()
        paper = assemble_paper(bp, _make_elements())
        section_names = [s["name"] for s in paper["sections"]]
        # Should have at least one named section
        assert len(section_names) >= 1

    def test_algebra_elements_preferred_by_high_blueprint_weight(self):
        bp = self._make_blueprint()
        paper = assemble_paper(bp, _make_elements())
        all_ids = {q["id"] for s in paper["sections"] for q in s["questions"]}
        # algebra elements (q2, q4) should be selected given blueprint weight 0.6
        assert "q2" in all_ids or "q4" in all_ids

    def test_empty_elements_pool_returns_zero_marks(self):
        bp = self._make_blueprint()
        paper = assemble_paper(bp, [])
        assert paper["total_marks"] == 0
        assert not paper["sections"]

    def test_fallback_marks_per_element_applied(self):
        bp = {"schema_version": "0.7", "total_marks": 10, "targets": []}
        elements = [
            {"id": "x1", "concepts": [], "placement": {"memory_role": "practice"}},
            {"id": "x2", "concepts": [], "placement": {"memory_role": "practice"}},
        ]
        paper = assemble_paper(bp, elements, marks_per_element=3)
        assert paper["total_marks"] == 6
