from eduvis.core.scaffolding import ReasoningScaffoldEngine
from eduvis.core import SCHEMA_VERSION, validate_lesson

def test_reasoning_scaffold_engine():
    engine = ReasoningScaffoldEngine()

    reasoning_path = [
        "identify variable",
        {"milestone": "isolate x", "hint_triggers": ["Check both sides."]}
    ]

    scaffolds = engine.scaffold(reasoning_path, "algebra")

    assert len(scaffolds) == 2

    assert scaffolds[0]["id"] == "scaffold_algebra_0"
    assert "Hint for identify variable" in scaffolds[0]["items"][0]["text"]

    assert scaffolds[1]["id"] == "scaffold_algebra_1"
    assert "Hint for isolate x: Check both sides." in scaffolds[1]["items"][0]["text"]

    # Wrap the generated elements in a minimal valid lesson and validate it
    lesson_doc = {
        "schema_version": SCHEMA_VERSION,
        "curriculum": {
            "code": "generated",
            "topic": "generated_topic",
        },
        "lesson": {
            "title": "Test Scaffolding",
        },
        "progression": {
            "pattern": "direct_instruction",
            "pedagogy": {
                "confidence_first": False,
                "explain_why": False,
                "no_skipped_steps": False
            },
            "phases": [
                {"phase": "explain", "purpose": "conceptual_model"}
            ]
        },
        "content": scaffolds
    }

    warnings = validate_lesson(lesson_doc)
    assert not warnings, f"Validation warnings in scaffolded lesson: {warnings}"
