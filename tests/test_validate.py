"""Smoke tests for the EduVis lesson validator."""

import pytest
from eduvis.core import validate_lesson


def _lesson(**overrides):
    doc = {
        "lesson": {"syllabus": "test", "topic": "T1", "title": "Test Lesson"},
        "progression": {
            "pattern": "direct_instruction",
            "pedagogy": {},
            "phases": [{"phase": "explain"}],
        },
        "content": [
            {
                "id": "slide_1",
                "type": "text_list",
                "placement": {"lesson_phase": "explain", "memory_role": "example"},
                "items": ["Point one", "Point two"],
            }
        ],
    }
    doc.update(overrides)
    return doc


def test_valid_lesson_no_warnings():
    assert validate_lesson(_lesson()) == []


def test_missing_lesson_block():
    doc = _lesson()
    del doc["lesson"]
    warnings = validate_lesson(doc)
    assert any("lesson" in w for w in warnings)


def test_missing_progression_block():
    doc = _lesson()
    del doc["progression"]
    warnings = validate_lesson(doc)
    assert any("progression" in w for w in warnings)


def test_missing_content_block():
    doc = _lesson()
    del doc["content"]
    warnings = validate_lesson(doc)
    assert any("content" in w for w in warnings)


def test_invalid_lesson_phase():
    doc = _lesson()
    doc["content"][0]["placement"]["lesson_phase"] = "not_a_phase"
    warnings = validate_lesson(doc)
    assert any("lesson_phase" in w for w in warnings)


def test_invalid_memory_role():
    doc = _lesson()
    doc["content"][0]["placement"]["memory_role"] = "bad_role"
    warnings = validate_lesson(doc)
    assert any("memory_role" in w for w in warnings)


def test_invalid_progression_pattern():
    doc = _lesson()
    doc["progression"]["pattern"] = "bad_pattern"
    warnings = validate_lesson(doc)
    assert any("pattern" in w for w in warnings)


def test_duplicate_element_ids():
    doc = _lesson()
    doc["content"].append(dict(doc["content"][0]))
    warnings = validate_lesson(doc)
    assert any("duplicate" in w for w in warnings)


def test_missing_element_id():
    doc = _lesson()
    del doc["content"][0]["id"]
    warnings = validate_lesson(doc)
    assert any("id" in w for w in warnings)


def test_missing_element_placement():
    doc = _lesson()
    del doc["content"][0]["placement"]
    warnings = validate_lesson(doc)
    assert any("placement" in w for w in warnings)


def test_confidence_first_pedagogy():
    """confidence_first: routine before starter should warn."""
    doc = _lesson()
    doc["progression"]["pattern"] = "confidence_ladder"
    doc["progression"]["pedagogy"] = {"confidence_first": True}
    doc["content"] = [
        {
            "id": "routine_1",
            "type": "text_list",
            "placement": {
                "lesson_phase": "independent_practice",
                "memory_role": "practice",
                "difficulty": "routine",
            },
            "items": ["Q1"],
        },
        {
            "id": "starter_1",
            "type": "text_list",
            "placement": {
                "lesson_phase": "independent_practice",
                "memory_role": "practice",
                "difficulty": "starter",
            },
            "items": ["Q2"],
        },
    ]
    warnings = validate_lesson(doc)
    assert any("confidence_first" in w for w in warnings)
