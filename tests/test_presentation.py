"""Tests for the EduVis presentation block validation."""

from __future__ import annotations

from eduvis.core import SCHEMA_VERSION, validate_lesson


def _lesson_with_presentation(presentation_doc: dict) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "curriculum": {"code": "test", "topic": "T1"},
        "lesson": {"title": "Test Lesson"},
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
        "presentation": presentation_doc,
    }


def test_valid_presentation():
    pres = {
        "slides": [
            {
                "id": "slide_1",
                "advance": "manual",
                "duration": 5.0,
                "reveals": [
                    {
                        "target": "slide_1",
                        "steps": [
                            {
                                "index": 0,
                                "visible_items": [0],
                                "auto_advance_after": 2.5,
                                "caption": "Hello",
                                "audio_offset": 0.0,
                                "audio_file": "step1.mp3",
                                "highlight": {"target": "item_0", "style": "pulse"},
                                "viewport": {"zoom": 1.5, "center": [100.0, 150.0]},
                                "action": "pause",
                            }
                        ],
                    }
                ],
            }
        ]
    }
    warnings = validate_lesson(_lesson_with_presentation(pres))
    assert not warnings


def test_presentation_invalid_mapping():
    warnings = validate_lesson(_lesson_with_presentation("not_a_dict"))
    assert any("must be a mapping" in w for w in warnings)


def test_presentation_missing_slides():
    warnings = validate_lesson(_lesson_with_presentation({}))
    assert any("missing required 'slides'" in w for w in warnings)


def test_presentation_unknown_slide_id():
    pres = {"slides": [{"id": "slide_unknown"}]}
    warnings = validate_lesson(_lesson_with_presentation(pres))
    assert any("slide ID 'slide_unknown' references unknown content element ID" in w for w in warnings)


def test_presentation_invalid_advance():
    pres = {"slides": [{"id": "slide_1", "advance": "invalid_mode"}]}
    warnings = validate_lesson(_lesson_with_presentation(pres))
    assert any("'advance' must be one of" in w for w in warnings)


def test_presentation_invalid_duration():
    pres = {"slides": [{"id": "slide_1", "duration": -1}]}
    warnings = validate_lesson(_lesson_with_presentation(pres))
    assert any("'duration' must be a non-negative number" in w for w in warnings)


def test_presentation_invalid_visible_items():
    pres = {
        "slides": [
            {
                "id": "slide_1",
                "reveals": [
                    {
                        "target": "slide_1",
                        "steps": [{"index": 0, "visible_items": "not_a_list"}],
                    }
                ],
            }
        ]
    }
    warnings = validate_lesson(_lesson_with_presentation(pres))
    assert any("'visible_items' must be a list" in w for w in warnings)


def test_presentation_invalid_visible_items_entry():
    pres = {
        "slides": [
            {
                "id": "slide_1",
                "reveals": [
                    {
                        "target": "slide_1",
                        "steps": [{"index": 0, "visible_items": [-1]}],
                    }
                ],
            }
        ]
    }
    warnings = validate_lesson(_lesson_with_presentation(pres))
    assert any("must be a non-negative integer" in w for w in warnings)


def test_presentation_invalid_viewport_center():
    pres = {
        "slides": [
            {
                "id": "slide_1",
                "reveals": [
                    {
                        "target": "slide_1",
                        "steps": [{"index": 0, "viewport": {"center": [100]}}],
                    }
                ],
            }
        ]
    }
    warnings = validate_lesson(_lesson_with_presentation(pres))
    assert any("viewport.center' must be a list of 2 numbers" in w for w in warnings)


def test_presentation_invalid_action():
    pres = {
        "slides": [
            {
                "id": "slide_1",
                "reveals": [
                    {
                        "target": "slide_1",
                        "steps": [{"index": 0, "action": "invalid_action"}],
                    }
                ],
            }
        ]
    }
    warnings = validate_lesson(_lesson_with_presentation(pres))
    assert any("'action' must be one of" in w for w in warnings)
