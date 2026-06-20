"""Smoke tests for the EduVis JSON Schema export."""

import json

import pytest
from eduvis.core.export_schema import (
    actions_schema,
    get_all_schemas,
    lesson_schema,
    placement_schema,
    progression_schema,
    relationships_schema,
    assessment_event_schema,
)


def test_get_all_schemas_returns_all_pillars():
    schemas = get_all_schemas()
    assert set(schemas.keys()) == {
        "placement",
        "actions",
        "relationships",
        "progression",
        "lesson",
        "presentation",
        "assessment_event",
    }


def test_all_schemas_are_json_serialisable():
    for name, schema in get_all_schemas().items():
        try:
            json.dumps(schema)
        except TypeError as exc:
            pytest.fail(f"{name} schema is not JSON-serialisable: {exc}")


def test_placement_has_required_fields():
    s = placement_schema()
    assert "lesson_phase" in s["properties"]
    assert "memory_role" in s["properties"]
    assert "lesson_phase" in s["required"]
    assert "memory_role" in s["required"]


def test_placement_enums_are_non_empty():
    s = placement_schema()
    assert len(s["properties"]["lesson_phase"]["enum"]) > 0
    assert len(s["properties"]["memory_role"]["enum"]) > 0


def test_actions_has_conceptual_and_procedural():
    s = actions_schema()
    assert "conceptual" in s["properties"]
    assert "procedural" in s["properties"]


def test_relationships_properties_match_valid_types():
    from eduvis.core.schemas.relationships import VALID_TYPES
    s = relationships_schema()
    assert set(s["properties"].keys()) == VALID_TYPES


def test_progression_pattern_enum_non_empty():
    s = progression_schema()
    assert len(s["properties"]["pattern"]["enum"]) > 0
    assert "pattern" in s["required"]


def test_lesson_requires_top_level_keys():
    s = lesson_schema()
    assert set(s["required"]) == {"lesson", "progression", "content"}


def test_schemas_have_draft_2020_12():
    for s in get_all_schemas().values():
        assert s["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_assessment_event_schema_has_required_fields():
    s = assessment_event_schema()
    expected_req = {
        "student_id",
        "element_id",
        "attempt_number",
        "answer_submitted",
        "is_correct",
        "timestamp"
    }
    assert set(s["required"]) == expected_req
    assert "misconception_detected" in s["properties"]
    assert "time_taken_seconds" in s["properties"]
