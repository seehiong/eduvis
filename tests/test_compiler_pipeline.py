"""Unit tests for EduVis Compiler Pipeline (v1.0)"""

import pytest
import yaml
from eduvis.compiler import (
    CompilerPipeline,
    CompilationContext,
    CurriculumPlanner,
    LessonPlanner,
    AssessmentAssembler,
    PresentationCompiler,
)
from eduvis.compiler.qa_engine import QAEngine

# Valid test syllabus / curriculum structure matching the 1.0 schema
TEST_SYLLABUS = {
    "schema_version": "1.0",
    "concepts": [
        {
            "code": "integers",
            "name": "Integers & Number Line",
            "description": "Understanding positive and negative whole numbers",
            "exam_weight": 0.9
        },
        {
            "code": "negative_numbers",
            "name": "Negative Numbers",
            "description": "Operations and ordering of signed values",
            "exam_weight": 0.95
        }
    ],
    "skills": [],
    "misconceptions": [],
    "dependencies": []
}


def test_compilation_context_logging():
    context = CompilationContext()
    context.log("Stage 1 started")
    context.add_error("Invalid schema format")

    assert len(context.logs) == 1
    assert "Stage 1 started" in context.logs[0]
    assert len(context.errors) == 1
    assert "ERROR: Invalid schema format" in context.errors[0]


def test_curriculum_planner_success():
    context = CompilationContext()
    context.syllabus_text = yaml.dump(TEST_SYLLABUS)

    planner = CurriculumPlanner()
    planner.run(context)

    assert context.curriculum_graph is not None
    assert "integers" in context.curriculum_graph.concepts
    assert "negative_numbers" in context.curriculum_graph.concepts
    assert not context.errors


def test_curriculum_planner_invalid_data():
    context = CompilationContext()
    # Invalid: concepts is not a list
    invalid_syllabus = dict(TEST_SYLLABUS)
    invalid_syllabus["concepts"] = "not-a-list"
    context.syllabus_text = yaml.dump(invalid_syllabus)

    planner = CurriculumPlanner()
    with pytest.raises(ValueError):
        planner.run(context)


def test_lesson_planner_success():
    context = CompilationContext()
    context.syllabus_text = yaml.dump(TEST_SYLLABUS)

    pipeline = CompilerPipeline()
    pipeline.add_stage(CurriculumPlanner())
    pipeline.add_stage(LessonPlanner(concept_codes=["integers"]))
    pipeline.run(context)

    assert not context.errors
    assert len(context.lessons) == 1
    lesson_id = list(context.lessons.keys())[0]
    lesson_data = context.lessons[lesson_id]

    assert "lesson" in lesson_data
    assert "content" in lesson_data
    # Content must have generated elements for integers
    content = lesson_data["content"]
    assert any(item.get("id") == "hook_integers" for item in content)


def test_assessment_assembler_success():
    context = CompilationContext()
    context.syllabus_text = yaml.dump(TEST_SYLLABUS)

    pipeline = CompilerPipeline()
    pipeline.add_stage(CurriculumPlanner())
    pipeline.add_stage(LessonPlanner(concept_codes=["integers", "negative_numbers"]))
    pipeline.add_stage(AssessmentAssembler(total_marks=10, title="Unit Quiz"))
    pipeline.run(context)

    assert not context.errors
    assert "Unit Quiz" in context.assessment_blueprints
    assert "Unit Quiz" in context.assessment_papers
    paper = context.assessment_papers["Unit Quiz"]
    assert "total_marks" in paper
    assert "sections" in paper


def test_presentation_compiler_success():
    context = CompilationContext()
    context.syllabus_text = yaml.dump(TEST_SYLLABUS)

    pipeline = CompilerPipeline()
    pipeline.add_stage(CurriculumPlanner())
    pipeline.add_stage(LessonPlanner(concept_codes=["integers"]))
    pipeline.add_stage(PresentationCompiler())
    pipeline.run(context)

    assert not context.errors
    assert len(context.presentations) == 1

    # Grab the inline modified lesson
    lesson_id = list(context.lessons.keys())[0]
    lesson_data = context.lessons[lesson_id]
    assert "presentation" in lesson_data
    assert "slides" in lesson_data["presentation"]
    slides = lesson_data["presentation"]["slides"]
    assert len(slides) > 0
    assert slides[0]["visible_items"] == ["hook_integers"]


def test_qa_engine_validation():
    context = CompilationContext()
    context.syllabus_text = yaml.dump(TEST_SYLLABUS)

    CurriculumPlanner().run(context)
    graph = context.curriculum_graph

    # Valid check
    valid_lesson = {
        "schema_version": "0.9",
        "curriculum": {
            "code": "integers",
            "topic": "integers",
            "objectives": ["integers"]
        },
        "lesson": {
            "title": "Integers lesson",
            "concepts": ["integers"]
        },
        "content": []
    }

    errors = QAEngine.validate_concept_references(graph, valid_lesson)
    assert not errors

    # Invalid concept check
    invalid_lesson = {
        "schema_version": "0.9",
        "curriculum": {
            "code": "integers",
            "topic": "integers",
            "objectives": ["nonexistent_concept"]
        },
        "lesson": {
            "title": "Integers lesson",
            "concepts": ["nonexistent_concept"]
        },
        "content": []
    }
    errors = QAEngine.validate_concept_references(graph, invalid_lesson)
    assert errors
    assert any("nonexistent_concept" in err for err in errors)
