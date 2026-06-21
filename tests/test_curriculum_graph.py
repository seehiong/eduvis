"""Tests for the EduVis Curriculum Graph and Knowledge Engine."""

from __future__ import annotations

import os
import pytest
import yaml

from eduvis.core.curriculum import (
    ConceptNode,
    SkillNode,
    MisconceptionNode,
    CurriculumGraph,
    validate_curriculum,
)

# Path to negative numbers lesson spec for testing coverage with real data
LESSON_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "docs", "showcase", "lessons", "negative-numbers-confidence-ladder-lesson.yaml"
)


def test_concept_node_creation():
    node = ConceptNode(code="neg_nums", name="Negative Numbers", description="Intro", exam_weight=0.9)
    assert node.code == "neg_nums"
    assert node.name == "Negative Numbers"
    assert node.description == "Intro"
    assert node.exam_weight == 0.9
    assert node.centrality_weight == 0.0

    d = node.to_dict()
    assert d["code"] == "neg_nums"
    assert d["exam_weight"] == 0.9
    assert d["centrality_weight"] == 0.0


def test_skill_and_misconception_creation():
    skill = SkillNode(code="add_neg", name="Add Negatives", concept="neg_nums", exam_weight=0.8)
    assert skill.code == "add_neg"
    assert skill.concept == "neg_nums"
    assert skill.exam_weight == 0.8

    misc = MisconceptionNode(code="size_err", name="Size Error", concept="neg_nums", remediation_weight=0.7)
    assert misc.code == "size_err"
    assert misc.concept == "neg_nums"
    assert misc.remediation_weight == 0.7


def test_curriculum_graph_loading_and_centrality():
    data = {
        "concepts": [
            {"code": "A", "name": "Concept A", "exam_weight": 0.5},
            {"code": "B", "name": "Concept B"},
            {"code": "C", "name": "Concept C"},
            {"code": "D", "name": "Concept D"},
        ],
        "skills": [
            {"code": "skill_1", "name": "Skill 1", "concept": "B", "exam_weight": 0.9},
        ],
        "misconceptions": [
            {"code": "misc_1", "name": "Misconception 1", "concept": "C", "remediation_weight": 0.8},
        ],
        "dependencies": [
            {"from": "A", "to": "B", "type": "prerequisite"},
            {"from": "B", "to": "C", "type": "prerequisite"},
            {"from": "D", "to": "C", "type": "prerequisite"},
        ]
    }
    graph = CurriculumGraph.from_dict(data)

    assert "A" in graph.concepts
    assert graph.concepts["A"].exam_weight == 0.5
    assert graph.concepts["B"].exam_weight == 1.0  # Default value
    assert "skill_1" in graph.skills
    assert "misc_1" in graph.misconceptions

    # Centrality weights:
    # Total nodes = 4. Denom = 3.
    # A is prerequisite for B, B is prerequisite for C. Descendants of A = {B, C} -> weight = 2/3 = 0.6667
    # B is prerequisite for C. Descendants of B = {C} -> weight = 1/3 = 0.3333
    # D is prerequisite for C. Descendants of D = {C} -> weight = 1/3 = 0.3333
    # C has no descendants -> weight = 0.0
    assert graph.concepts["A"].centrality_weight == pytest.approx(0.6667, abs=1e-4)
    assert graph.concepts["B"].centrality_weight == pytest.approx(0.3333, abs=1e-4)
    assert graph.concepts["D"].centrality_weight == pytest.approx(0.3333, abs=1e-4)
    assert graph.concepts["C"].centrality_weight == 0.0

    centrality_list = graph.analyze_centrality()
    assert centrality_list[0]["code"] == "A"
    assert centrality_list[0]["downstream_count"] == 2
    assert centrality_list[-1]["code"] == "C"
    assert centrality_list[-1]["downstream_count"] == 0


def test_traversal_apis():
    data = {
        "concepts": [
            {"code": "A", "name": "Concept A"},
            {"code": "B", "name": "Concept B"},
            {"code": "C", "name": "Concept C"},
            {"code": "D", "name": "Concept D"},
        ],
        "skills": [
            {"code": "skill_1", "name": "Skill 1", "concept": "A"},
            {"code": "skill_2", "name": "Skill 2", "concept": "A"},
        ],
        "misconceptions": [
            {"code": "misc_1", "name": "Misconception 1", "concept": "B"},
        ],
        "dependencies": [
            {"from": "A", "to": "B"},
            {"from": "B", "to": "C"},
            {"from": "A", "to": "D"},
        ]
    }
    graph = CurriculumGraph.from_dict(data)

    # get_prerequisites
    assert graph.get_prerequisites("C", transitive=False) == ["B"]
    assert graph.get_prerequisites("C", transitive=True) == ["A", "B"]
    assert graph.get_prerequisites("A", transitive=True) == []

    # get_dependents
    assert graph.get_dependents("A", transitive=False) == ["B", "D"]
    assert graph.get_dependents("A", transitive=True) == ["B", "C", "D"]

    # get_skills & misconceptions
    assert graph.get_skills("A") == ["skill_1", "skill_2"]
    assert graph.get_misconceptions("B") == ["misc_1"]

    # find_path
    assert graph.find_path("A", "C") == ["A", "B", "C"]
    assert graph.find_path("A", "A") == ["A"]
    assert graph.find_path("D", "C") is None


def test_completeness_validation_and_cycles():
    # 1. Valid graph
    valid_data = {
        "concepts": [{"code": "A", "name": "A"}, {"code": "B", "name": "B"}],
        "skills": [{"code": "s1", "name": "s1", "concept": "A"}],
        "misconceptions": [{"code": "m1", "name": "m1", "concept": "B"}],
        "dependencies": [{"from": "A", "to": "B"}]
    }
    graph = CurriculumGraph.from_dict(valid_data)
    assert len(graph.validate_completeness()) == 0

    # 2. Undefined references
    invalid_data = {
        "concepts": [{"code": "A", "name": "A"}],
        "skills": [{"code": "s1", "name": "s1", "concept": "B"}],
        "misconceptions": [{"code": "m1", "name": "m1", "concept": "C"}],
        "dependencies": [{"from": "A", "to": "D"}, {"from": "E", "to": "A"}]
    }
    graph = CurriculumGraph.from_dict(invalid_data)
    errors = graph.validate_completeness()
    assert len(errors) == 4
    assert any("Skill 's1' refers to undefined concept 'B'" in e for e in errors)
    assert any("Misconception 'm1' refers to undefined concept 'C'" in e for e in errors)
    assert any("Dependency references undefined target concept 'D'" in e for e in errors)
    assert any("Dependency references undefined source concept 'E'" in e for e in errors)

    # 3. Cycle detection
    cycle_data = {
        "concepts": [{"code": "A", "name": "A"}, {"code": "B", "name": "B"}, {"code": "C", "name": "C"}],
        "dependencies": [
            {"from": "A", "to": "B"},
            {"from": "B", "to": "C"},
            {"from": "C", "to": "A"},
        ]
    }
    graph = CurriculumGraph.from_dict(cycle_data)
    errors = graph.validate_completeness()
    assert len(errors) > 0
    assert any("Dependency cycle detected" in e for e in errors)


def test_coverage_and_gap_analytics():
    data = {
        "concepts": [
            {"code": "negative_numbers", "name": "Negative Numbers"},
            {"code": "rational_numbers", "name": "Rational Numbers"},
            {"code": "real_numbers", "name": "Real Numbers"},
        ],
        "skills": [
            {"code": "order_integers", "name": "Order Integers", "concept": "negative_numbers"},
            {"code": "add_negatives", "name": "Add Negatives", "concept": "negative_numbers"},
            {"code": "order_rational", "name": "Order Rational", "concept": "rational_numbers"},
        ],
        "misconceptions": [
            {"code": "digit_size_magnitude_error", "name": "Size Error", "concept": "negative_numbers"},
            {"code": "other_error", "name": "Other Error", "concept": "rational_numbers"},
        ],
        "dependencies": [
            {"from": "negative_numbers", "to": "rational_numbers"},
            {"from": "rational_numbers", "to": "real_numbers"},
        ]
    }
    graph = CurriculumGraph.from_dict(data)

    mock_lessons = [{
        "curriculum": {
            "code": "SEC-math",
            "topic": "Chapter-2",
            "concept": "negative_numbers"
        },
        "lesson": {
            "title": "Mock Lesson",
            "concepts": ["negative_numbers"]
        },
        "content": [
            {
                "id": "q1",
                "type": "multiple_choice",
                "concepts": ["negative_numbers"],
                "skills": ["order_integers"],
                "placement": {"lesson_phase": "practice", "memory_role": "practice"},
                "misconceptions": {"A": "digit_size_magnitude_error"}
            }
        ]
    }]

    coverage = graph.analyze_coverage(mock_lessons)
    assert coverage["covered_concepts"] == ["negative_numbers"]
    assert coverage["uncovered_concepts"] == ["rational_numbers", "real_numbers"]
    assert coverage["covered_skills"] == ["order_integers"]
    assert coverage["uncovered_skills"] == ["add_negatives", "order_rational"]
    assert coverage["covered_misconceptions"] == ["digit_size_magnitude_error"]
    assert coverage["uncovered_misconceptions"] == ["other_error"]

    # Dependency Gaps
    # If rational_numbers is covered, it requires negative_numbers.
    # If rational_numbers is covered, but negative_numbers is NOT, that's a gap.
    gaps = graph.detect_dependency_gaps(["rational_numbers"])
    assert len(gaps) == 1
    assert gaps[0]["concept"] == "rational_numbers"
    assert gaps[0]["missing_prerequisite"] == "negative_numbers"

    # No gaps if both are covered
    assert len(graph.detect_dependency_gaps(["negative_numbers", "rational_numbers"])) == 0


def test_coverage_analysis_with_real_lesson():
    """Verify that we can load and analyze coverage using the actual negative-numbers.yaml lesson file."""
    assert os.path.exists(LESSON_FILE)

    with open(LESSON_FILE, "r", encoding="utf-8") as f:
        lesson_data = yaml.safe_load(f)

    # Construct a curriculum graph corresponding to Chapter 2 taxonomy
    graph_data = {
        "concepts": [
            {"code": "negative_numbers", "name": "Negative Numbers"}
        ],
        "skills": [
            {"code": "order_integers", "name": "Order Integers", "concept": "negative_numbers"},
            {"code": "add_negative_numbers", "name": "Add Negatives", "concept": "negative_numbers"},
            {"code": "subtract_negative_numbers", "name": "Subtract Negatives", "concept": "negative_numbers"},
            {"code": "simplify_expressions", "name": "Simplify Expressions", "concept": "negative_numbers"}
        ],
        "misconceptions": [
            {"code": "digit_size_magnitude_error", "name": "Size Error", "concept": "negative_numbers"},
            {"code": "difference_confusion", "name": "Diff Confusion", "concept": "negative_numbers"},
            {"code": "double_negative_addition_confusion", "name": "Double Neg Add", "concept": "negative_numbers"},
            {"code": "subtract_negative_minus_negative", "name": "Sub Neg Minus", "concept": "negative_numbers"}
        ],
        "dependencies": []
    }
    graph = CurriculumGraph.from_dict(graph_data)

    coverage = graph.analyze_coverage([lesson_data])
    assert coverage["covered_concepts"] == ["negative_numbers"]
    assert "order_integers" in coverage["covered_skills"]
    assert "add_negative_numbers" in coverage["covered_skills"]
    assert "subtract_negative_numbers" in coverage["covered_skills"]
    assert "simplify_expressions" in coverage["covered_skills"]
    assert "digit_size_magnitude_error" in coverage["covered_misconceptions"]
    assert "double_negative_addition_confusion" in coverage["covered_misconceptions"]
    assert "subtract_negative_minus_negative" in coverage["covered_misconceptions"]


def test_validate_curriculum_schema():
    # 1. Valid curriculum dict
    valid_data = {
        "schema_version": "0.5",
        "concepts": [
            {"code": "neg_nums", "name": "Negative Numbers", "description": "Intro", "exam_weight": 0.9}
        ],
        "skills": [
            {"code": "add_neg", "name": "Add Negatives", "concept": "neg_nums", "exam_weight": 0.8}
        ],
        "misconceptions": [
            {"code": "size_err", "name": "Size Error", "concept": "neg_nums", "remediation_weight": 0.7}
        ],
        "dependencies": [
            {"from": "neg_nums", "to": "neg_nums", "type": "prerequisite"}
        ]
    }
    warnings = validate_curriculum(valid_data)
    assert len(warnings) == 1
    assert "Dependency cycle detected" in warnings[0]

    # 2. Schema errors
    invalid_data = {
        "schema_version": "0.4",
        "unexpected_field": "hello",
        "concepts": [
            {"code": "neg_nums", "name": "Negative Numbers", "exam_weight": "not-a-number"}
        ],
        "skills": [
            {"code": "add_neg", "name": "Add Negatives"}
        ]
    }
    warnings2 = validate_curriculum(invalid_data)
    assert len(warnings2) > 0
    assert any("unsupported schema version" in w for w in warnings2)
    assert any("unexpected key 'unexpected_field'" in w for w in warnings2)
    assert any("exam_weight' must be a number" in w for w in warnings2)
    assert any("missing required 'concept'" in w for w in warnings2)
