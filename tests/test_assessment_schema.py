"""Tests for assessment event schema."""

from eduvis.core.export_schema import assessment_event_schema

def _check_field_type(key: str, val: any, spec: dict, errors: list[str]) -> None:
    spec_type = spec.get("type")

    if spec_type == "string":
        if not isinstance(val, str):
            errors.append(f"Field {key} must be a string, got {type(val).__name__}")
    elif spec_type == "integer":
        if not isinstance(val, int) or isinstance(val, bool):
            errors.append(f"Field {key} must be an integer, got {type(val).__name__}")
        elif "minimum" in spec and val < spec["minimum"]:
            errors.append(f"Field {key} must be >= {spec['minimum']}, got {val}")
    elif spec_type == "number":
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            errors.append(f"Field {key} must be a number, got {type(val).__name__}")
        elif "minimum" in spec and val < spec["minimum"]:
            errors.append(f"Field {key} must be >= {spec['minimum']}, got {val}")
    elif spec_type == "boolean":
        if not isinstance(val, bool):
            errors.append(f"Field {key} must be a boolean, got {type(val).__name__}")
    elif isinstance(spec_type, list):
        is_valid = any(
            (t == "string" and isinstance(val, str)) or (t == "null" and val is None)
            for t in spec_type
        )
        if not is_valid:
            errors.append(f"Field {key} must be one of {spec_type}, got {type(val).__name__}")


def validate_event_against_schema(event: dict, schema: dict) -> list[str]:
    errors = []
    # Check required fields
    required = schema.get("required", [])
    for field in required:
        if field not in event:
            errors.append(f"Missing required field: {field}")

    # Check additional properties
    properties = schema.get("properties", {})
    for key, val in event.items():
        if key not in properties:
            errors.append(f"Additional property not allowed: {key}")
            continue

        _check_field_type(key, val, properties[key], errors)

    return errors

def test_assessment_event_schema_structure():
    schema = assessment_event_schema()
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert "student_id" in schema["properties"]
    assert "element_id" in schema["properties"]
    assert "attempt_number" in schema["properties"]
    assert "answer_submitted" in schema["properties"]
    assert "is_correct" in schema["properties"]
    assert "timestamp" in schema["properties"]

def test_valid_assessment_events():
    schema = assessment_event_schema()
    valid_event = {
        "student_id": "student_123",
        "element_id": "mcq_1",
        "attempt_number": 1,
        "answer_submitted": "A",
        "is_correct": True,
        "timestamp": "2026-06-20T10:00:00Z"
    }
    assert not validate_event_against_schema(valid_event, schema)

    # With optional fields
    valid_event_with_optionals = {
        "student_id": "student_123",
        "element_id": "mcq_1",
        "attempt_number": 2,
        "answer_submitted": "B",
        "is_correct": False,
        "misconception_detected": "digit-size",
        "time_taken_seconds": 15.5,
        "timestamp": "2026-06-20T10:01:30Z"
    }
    assert not validate_event_against_schema(valid_event_with_optionals, schema)

def test_invalid_assessment_events():
    schema = assessment_event_schema()
    # Missing required field
    invalid_event = {
        "student_id": "student_123",
        "element_id": "mcq_1",
        "attempt_number": 1,
        "answer_submitted": "A",
        # "is_correct" is missing
        "timestamp": "2026-06-20T10:00:00Z"
    }
    errors = validate_event_against_schema(invalid_event, schema)
    assert any("Missing required field: is_correct" in err for err in errors)

    # Invalid type
    invalid_event = {
        "student_id": "student_123",
        "element_id": "mcq_1",
        "attempt_number": "first", # must be integer
        "answer_submitted": "A",
        "is_correct": True,
        "timestamp": "2026-06-20T10:00:00Z"
    }
    errors = validate_event_against_schema(invalid_event, schema)
    assert any("must be an integer" in err for err in errors)

    # Out of bounds
    invalid_event = {
        "student_id": "student_123",
        "element_id": "mcq_1",
        "attempt_number": 0, # must be >= 1
        "answer_submitted": "A",
        "is_correct": True,
        "timestamp": "2026-06-20T10:00:00Z"
    }
    errors = validate_event_against_schema(invalid_event, schema)
    assert any("must be >= 1" in err for err in errors)

    # Additional property not allowed
    invalid_event = {
        "student_id": "student_123",
        "element_id": "mcq_1",
        "attempt_number": 1,
        "answer_submitted": "A",
        "is_correct": True,
        "timestamp": "2026-06-20T10:00:00Z",
        "extra_field": "not allowed"
    }
    errors = validate_event_against_schema(invalid_event, schema)
    assert any("Additional property not allowed: extra_field" in err for err in errors)
