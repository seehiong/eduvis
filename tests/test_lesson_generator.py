import yaml
from eduvis.core.curriculum import CurriculumGraph
from eduvis.core.generator import GraphLessonGenerator
from eduvis.core import SCHEMA_VERSION, validate_lesson

def test_graph_lesson_generator():
    cg = CurriculumGraph()
    cg.concepts = {
        "test_concept": type("MockConcept", (), {"name": "Test Concept", "description": "A test description", "code": "test_concept"})()
    }
    generator = GraphLessonGenerator(cg)
    yaml_str = generator.generate(["test_concept"])

    data = yaml.safe_load(yaml_str)

    assert data["schema_version"] == SCHEMA_VERSION
    assert data["curriculum"]["code"] == "generated"

    content = data["content"]
    assert len(content) == 3

    assert content[0]["id"] == "hook_test_concept"
    assert content[0]["phase"] == "hook"
    assert content[1]["id"] == "explain_test_concept"
    assert content[2]["id"] == "guided_practice_test_concept"

    # Validate output lesson
    warnings = validate_lesson(data)
    assert not warnings, f"Validation warnings in generated lesson: {warnings}"
