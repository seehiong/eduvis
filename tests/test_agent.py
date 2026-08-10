"""
Unit tests for EduVis Agent v1.3 components.
"""

import pytest
from agent.schemas.intent import GenerationIntent, AssessmentObjectiveAlloc
from agent.tools.curriculum_tools import inspect_curriculum, check_prerequisites
from agent.tools.validator_tools import validate_generated_spec
from agent.graph.workflow import build_educational_generation_graph


SAMPLE_CURRICULUM_YAML = """
schema_version: "1.0"
concepts:
  - code: "concept_1"
    name: "Negative Numbers Intro"
    description: "Understanding integers below zero"
    exam_weight: 1.0
skills:
  - code: "skill_1"
    name: "Subtracting Integers"
    concept: "concept_1"
    exam_weight: 1.0
misconceptions: []
dependencies: []
"""


def test_generation_intent_schema():
    """Verify GenerationIntent Pydantic IR instantiation and defaults."""
    intent = GenerationIntent(
        topic="negative_numbers",
        target_concepts=["concept_1"],
        total_marks=50,
        objective_distribution=AssessmentObjectiveAlloc(AO1_recall=0.5, AO2_analysis=0.3, AO3_synthesis=0.2)
    )
    assert intent.topic == "negative_numbers"
    assert intent.total_marks == 50
    assert intent.objective_distribution.AO1_recall == 0.5


def test_agent_curriculum_tools():
    """Verify EduVis curriculum tool wrappers for agent consumption."""
    info = inspect_curriculum(SAMPLE_CURRICULUM_YAML)
    assert info["status"] == "success"
    assert info["concept_count"] == 1
    assert info["concepts"][0]["code"] == "concept_1"

    prereqs = check_prerequisites(SAMPLE_CURRICULUM_YAML, ["concept_1"])
    assert prereqs["status"] == "success"
    assert prereqs["required_prerequisites"] == []


def test_agent_validator_tools():
    """Verify deterministic validator tool wrapper."""
    res = validate_generated_spec(SAMPLE_CURRICULUM_YAML, spec_type="curriculum")
    assert res["is_valid"] is True
    assert len(res["errors"]) == 0


def test_educational_generation_graph():
    """Verify Educational Generation Graph execution loop."""
    graph = build_educational_generation_graph()
    initial_state = {
        "user_prompt": "Create a Secondary 1 paper on negative numbers",
        "curriculum_yaml": SAMPLE_CURRICULUM_YAML,
        "retry_count": 0,
        "critique_history": []
    }
    result = graph.invoke(initial_state)
    assert result["status"] in ["success", "validated", "failed", "critiqued"]
    assert result["intent"] is not None
    assert len(result["candidate_questions"]) > 0


def test_agent_fastapi_server_endpoints():
    """Verify Agent FastAPI REST server endpoints (/health, /api/validate, /api/generate/paper)."""
    try:
        from fastapi.testclient import TestClient
        from agent.server import app
        if app is None:
            return

        client = TestClient(app)

        # 1. GET /health
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.3.0"

        # 2. POST /api/validate
        val_response = client.post(
            "/api/validate",
            json={"yaml_text": SAMPLE_CURRICULUM_YAML, "spec_type": "curriculum"}
        )
        assert val_response.status_code == 200
        val_data = val_response.json()
        assert val_data["is_valid"] is True

        # 3. POST /api/generate/paper
        gen_response = client.post(
            "/api/generate/paper",
            json={
                "prompt": "Create a practice paper on negative numbers",
                "curriculum_yaml": SAMPLE_CURRICULUM_YAML,
                "target_marks": 50
            }
        )
        assert gen_response.status_code == 200
        gen_data = gen_response.json()
        assert gen_data["status"] in ["success", "validated", "failed", "critiqued"]
        assert gen_data["intent"] is not None

    except ImportError:
        pytest.skip("FastAPI / TestClient is not installed in current environment.")
