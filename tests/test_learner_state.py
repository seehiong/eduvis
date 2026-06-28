"""Tests for the EduVis Learner State representation and validation."""

from eduvis.core.learner_state import LearnerState, validate_learner_state


def test_learner_state_basic_instantiation():
    state = LearnerState(learner_id="student_123")
    assert state.learner_id == "student_123"
    assert state.schema_version == "0.7"
    assert not state.concepts
    assert not state.skills
    assert not state.misconceptions
    assert state.last_updated is not None


def test_learner_state_to_and_from_dict():
    data = {
        "schema_version": "0.7",
        "learner_id": "student_abc",
        "last_updated": "2026-06-27T00:00:00Z",
        "concepts": {
            "concept_1": {"mastery": 0.8, "confidence": 0.9},
            "concept_2": {"mastery": 0.4}
        },
        "skills": {
            "skill_a": {"mastery": 0.7}
        },
        "misconceptions": {
            "mis_x": {"state": "active", "attempts": 2}
        }
    }

    # Check validation passes
    warnings = validate_learner_state(data)
    assert not warnings

    # Parse state
    state = LearnerState.from_dict(data)
    assert state.learner_id == "student_abc"
    assert state.concepts["concept_1"].mastery == 0.8
    assert state.concepts["concept_1"].confidence == 0.9
    assert state.concepts["concept_2"].mastery == 0.4
    assert state.concepts["concept_2"].confidence is None
    assert state.skills["skill_a"].mastery == 0.7
    assert state.misconceptions["mis_x"].state == "active"
    assert state.misconceptions["mis_x"].attempts == 2

    # Serialize back
    serialized = state.to_dict()
    assert serialized["learner_id"] == "student_abc"
    assert serialized["concepts"]["concept_1"]["mastery"] == 0.8
    assert serialized["concepts"]["concept_1"]["confidence"] == 0.9
    assert serialized["skills"]["skill_a"]["mastery"] == 0.7
    assert serialized["misconceptions"]["mis_x"]["state"] == "active"
    assert serialized["misconceptions"]["mis_x"]["attempts"] == 2


def test_validate_learner_state_failures():
    # Empty dictionary
    assert any("missing 'learner_id'" in w for w in validate_learner_state({}))

    # Invalid learner_id type
    assert any("must be a non-empty string" in w for w in validate_learner_state({"learner_id": 123}))

    # Missing concepts map
    assert any("missing 'concepts' map" in w for w in validate_learner_state({"learner_id": "std"}))

    # Invalid concept mastery
    bad_data = {
        "learner_id": "std",
        "concepts": {
            "c1": {"mastery": 1.5}  # Too large
        }
    }
    assert any("mastery must be a float between 0.0 and 1.0" in w for w in validate_learner_state(bad_data))

    # Invalid misconception state
    bad_mis = {
        "learner_id": "std",
        "concepts": {"c1": {"mastery": 0.5}},
        "misconceptions": {
            "m1": {"state": "unknown_state"}
        }
    }
    assert any("state must be 'active' or 'remediated'" in w for w in validate_learner_state(bad_mis))
