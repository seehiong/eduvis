"""Tests for Diagnostic Assessment & Evidence Modeling validation rules."""

from eduvis.core import SCHEMA_VERSION, validate_lesson


def _lesson(**overrides):
    doc = {
      "schema_version": SCHEMA_VERSION,
      "curriculum": {"code": "test", "topic": "T1", "concept": "concept_a"},
      "lesson": {"title": "Test Lesson", "concepts": ["concept_a", "concept_b"]},
      "progression": {
          "pattern": "direct_instruction",
          "pedagogy": {},
          "phases": [{"phase": "explain"}],
      },
      "content": [],
    }
    doc.update(overrides)
    return doc


def test_valid_diagnostic_fields_mcq():
    doc = _lesson()
    doc["content"] = [
        {
            "id": "q1",
            "type": "multiple_choice",
            "placement": {"lesson_phase": "explain", "memory_role": "practice"},
            "question": "Q1?",
            "options": {"A": "1", "B": "2"},
            "answer": "A",
            "assesses": {
                "concept_a": 0.8,
                "concept_b": 0.2
            },
            "cognitive_skills": ["apply"],
            "challenge_factors": ["multi_step"],
            "evidence_targets": ["apply_formula"],
            "reasoning_path": ["identify", "calculate"],
            "evidence_strength": "high",
            "rubric": {
                "total_marks": 2,
                "criteria": [
                    {
                        "id": "step1",
                        "marks": 1,
                        "description": "Identify variables",
                    },
                    {
                        "id": "step2",
                        "marks": 1,
                        "description": "Perform calculation",
                        "depends_on": "step1"
                    }
                ]
            },
            "marking_policy": {
                "error_carry_forward": True,
                "partial_credit": True
            }
        }
    ]
    warnings = validate_lesson(doc)
    assert not warnings


def test_invalid_assesses_weights():
    doc = _lesson()
    doc["content"] = [
        {
            "id": "q1",
            "type": "multiple_choice",
            "placement": {"lesson_phase": "explain", "memory_role": "practice"},
            "question": "Q1?",
            "options": {"A": "1", "B": "2"},
            "answer": "A",
            "assesses": {
                "concept_a": 1.5,  # Weight > 1.0
            }
        }
    ]
    warnings = validate_lesson(doc)
    assert any("weight for concept 'concept_a' must be between 0.0 and 1.0" in w for w in warnings)

    doc = _lesson()
    doc["content"] = [
        {
            "id": "q1",
            "type": "multiple_choice",
            "placement": {"lesson_phase": "explain", "memory_role": "practice"},
            "question": "Q1?",
            "options": {"A": "1", "B": "2"},
            "answer": "A",
            "assesses": {
                "concept_a": "high",  # Weight not a number
            }
        }
    ]
    warnings = validate_lesson(doc)
    assert any("weight for concept 'concept_a' must be a number" in w for w in warnings)


def test_undeclared_concept_in_assesses():
    doc = _lesson()
    doc["content"] = [
        {
            "id": "q1",
            "type": "multiple_choice",
            "placement": {"lesson_phase": "explain", "memory_role": "practice"},
            "question": "Q1?",
            "options": {"A": "1", "B": "2"},
            "answer": "A",
            "assesses": {
                "undeclared_concept": 0.5,
            }
        }
    ]
    warnings = validate_lesson(doc)
    assert any("is not declared in the lesson-level 'lesson.concepts'" in w for w in warnings)


def test_rubric_total_marks_mismatch():
    doc = _lesson()
    doc["content"] = [
        {
            "id": "q1",
            "type": "multiple_choice",
            "placement": {"lesson_phase": "explain", "memory_role": "practice"},
            "question": "Q1?",
            "options": {"A": "1", "B": "2"},
            "answer": "A",
            "rubric": {
                "total_marks": 5,
                "criteria": [
                    {"id": "step1", "marks": 2, "description": "Step 1"},
                    {"id": "step2", "marks": 2, "description": "Step 2"}
                ]
            }
        }
    ]
    warnings = validate_lesson(doc)
    assert any("total_marks is 5 but criteria marks sum to 4" in w for w in warnings)


def test_rubric_dependencies_validation():
    # 1. Dependency on self
    doc = _lesson()
    doc["content"] = [
        {
            "id": "q1",
            "type": "multiple_choice",
            "placement": {"lesson_phase": "explain", "memory_role": "practice"},
            "question": "Q1?",
            "options": {"A": "1", "B": "2"},
            "answer": "A",
            "rubric": {
                "criteria": [
                    {"id": "step1", "marks": 1, "description": "Step 1", "depends_on": "step1"}
                ]
            }
        }
    ]
    warnings = validate_lesson(doc)
    assert any("rubric criterion 'step1' depends on itself" in w for w in warnings)

    # 2. Dependency on unknown criterion
    doc = _lesson()
    doc["content"] = [
        {
            "id": "q1",
            "type": "multiple_choice",
            "placement": {"lesson_phase": "explain", "memory_role": "practice"},
            "question": "Q1?",
            "options": {"A": "1", "B": "2"},
            "answer": "A",
            "rubric": {
                "criteria": [
                    {"id": "step1", "marks": 1, "description": "Step 1", "depends_on": "step2"}
                ]
            }
        }
    ]
    warnings = validate_lesson(doc)
    assert any("depends on unknown criterion 'step2'" in w for w in warnings)

    # 3. Forward dependency
    doc = _lesson()
    doc["content"] = [
        {
            "id": "q1",
            "type": "multiple_choice",
            "placement": {"lesson_phase": "explain", "memory_role": "practice"},
            "question": "Q1?",
            "options": {"A": "1", "B": "2"},
            "answer": "A",
            "rubric": {
                "criteria": [
                    {"id": "step1", "marks": 1, "description": "Step 1", "depends_on": "step2"},
                    {"id": "step2", "marks": 1, "description": "Step 2"}
                ]
            }
        }
    ]
    warnings = validate_lesson(doc)
    assert any("depends on 'step2' which appears after or at the same position" in w for w in warnings)


def test_structured_response_with_part_diagnostics():
    doc = _lesson()
    doc["content"] = [
        {
            "id": "q5",
            "type": "structured_response",
            "placement": {"lesson_phase": "explain", "memory_role": "practice"},
            "question": "Structured Question Context",
            "parts": [
                {
                    "id": "q5a",
                    "question": "Part a?",
                    "answer_type": "algebraic",
                    "answer": "x = 2",
                    "marks": 2,
                    "assesses": {"concept_a": 1.0},
                    "rubric": {
                        "total_marks": 2,
                        "criteria": [
                            {"id": "a_step1", "marks": 2, "description": "Solve Part a"}
                        ]
                    }
                },
                {
                    "id": "q5b",
                    "question": "Part b?",
                    "answer_type": "numeric",
                    "answer": "4",
                    "marks": 3,
                    "depends_on": "q5a",
                    "assesses": {"concept_b": 1.0},
                    "rubric": {
                        "total_marks": 3,
                        "criteria": [
                            {"id": "b_step1", "marks": 3, "description": "Solve Part b"}
                        ]
                    }
                }
            ],
        }
    ]
    warnings = validate_lesson(doc)
    assert not warnings


def test_invalid_evidence_strength():
    doc = _lesson()
    doc["content"] = [
        {
            "id": "q1",
            "type": "multiple_choice",
            "placement": {"lesson_phase": "explain", "memory_role": "practice"},
            "question": "Q1?",
            "options": {"A": "1", "B": "2"},
            "answer": "A",
            "evidence_strength": "invalid_strength"
        }
    ]
    warnings = validate_lesson(doc)
    # The registry validates the enum constraints
    assert any("field 'evidence_strength': expected string" in w or "evidence_strength" in w for w in warnings)
