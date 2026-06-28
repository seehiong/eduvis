"""Tests for the EduVis Stateless Transition Engine and Mastery Projection."""

import pytest
from eduvis.core.learner_state import LearnerState, ConceptState
from eduvis.core.curriculum import CurriculumGraph, ConceptNode, MisconceptionNode
from eduvis.core.transition_engine import apply_telemetry_event
from eduvis.core.mastery_projection import MasteryGraphView


def _setup_curriculum() -> CurriculumGraph:
    curr = CurriculumGraph()
    # Concepts
    curr.concepts["concept_a"] = ConceptNode("concept_a", "Concept A")
    curr.concepts["concept_b"] = ConceptNode("concept_b", "Concept B")
    # Misconceptions
    curr.misconceptions["mis_a"] = MisconceptionNode("mis_a", "Misconception A", "concept_a")
    return curr


def test_transition_correct_attempt():
    curr = _setup_curriculum()
    state = LearnerState(learner_id="learner_1")
    state.concepts["concept_a"] = ConceptState(mastery=0.5)
    # Build standard state dict
    state_dict = {
        "schema_version": "0.7",
        "learner_id": "learner_1",
        "concepts": {
            "concept_a": {"mastery": 0.5}
        }
    }
    learner_state = LearnerState.from_dict(state_dict)

    # Correct assessment attempt event
    event = {
        "event_id": "evt_1",
        "timestamp": "2026-06-27T00:00:00Z",
        "learner_id": "learner_1",
        "event_type": "assessment_attempt",
        "payload": {
            "element_id": "q1",
            "is_correct": True,
            "assesses": {"concept_a": 1.0}
        }
    }

    # Apply event
    next_state = apply_telemetry_event(learner_state, event, curriculum=curr)

    # Mastery should increase: 0.5 + 0.1 * 1.0 * (1.0 - 0.5) = 0.55
    assert next_state.concepts["concept_a"].mastery == pytest.approx(0.55)


def test_transition_incorrect_attempt_with_misconception():
    curr = _setup_curriculum()
    state_dict = {
        "schema_version": "0.7",
        "learner_id": "learner_2",
        "concepts": {
            "concept_a": {"mastery": 0.5}
        }
    }
    learner_state = LearnerState.from_dict(state_dict)

    # Incorrect attempt triggering misconception 'mis_a'
    event = {
        "event_id": "evt_2",
        "timestamp": "2026-06-27T00:00:00Z",
        "learner_id": "learner_2",
        "event_type": "assessment_attempt",
        "payload": {
            "element_id": "q2",
            "is_correct": False,
            "misconception_detected": "mis_a",
            "assesses": {"concept_a": 1.0}
        }
    }

    next_state = apply_telemetry_event(learner_state, event, curriculum=curr)

    # Misconception 'mis_a' should be flagged as active
    assert next_state.misconceptions["mis_a"].state == "active"
    assert next_state.misconceptions["mis_a"].attempts == 1

    # Mastery should be penalized: 0.5 - 0.15 * 1.0 = 0.35
    assert next_state.concepts["concept_a"].mastery == pytest.approx(0.35)


def test_transition_remediation_on_correct():
    curr = _setup_curriculum()
    state_dict = {
        "schema_version": "0.7",
        "learner_id": "learner_3",
        "concepts": {
            "concept_a": {"mastery": 0.3}
        },
        "misconceptions": {
            "mis_a": {"state": "active", "attempts": 1}
        }
    }
    learner_state = LearnerState.from_dict(state_dict)

    # Correct attempt assesses concept_a
    event = {
        "event_id": "evt_3",
        "timestamp": "2026-06-27T00:00:00Z",
        "learner_id": "learner_3",
        "event_type": "assessment_attempt",
        "payload": {
            "element_id": "q3",
            "is_correct": True,
            "assesses": {"concept_a": 1.0}
        }
    }

    next_state = apply_telemetry_event(learner_state, event, curriculum=curr)

    # Misconception 'mis_a' associated with concept_a should be set to remediated
    assert next_state.misconceptions["mis_a"].state == "remediated"


def test_temporal_decay():
    state_dict = {
        "schema_version": "0.7",
        "learner_id": "learner_4",
        "last_updated": "2026-06-27T00:00:00Z",
        "concepts": {
            "concept_a": {"mastery": 1.0}
        }
    }
    learner_state = LearnerState.from_dict(state_dict)

    # Event occurring 1 day (86400 seconds) later
    event = {
        "event_id": "evt_4",
        "timestamp": "2026-06-28T00:00:00Z",
        "learner_id": "learner_4",
        "event_type": "lesson_reveal",
        "payload": {"element_id": "card_1"}
    }

    # Proportional decay of 5% per day (decay_rate: 0.05)
    # Next state mastery should be 1.0 * (1.0 - 0.05) = 0.95
    next_state = apply_telemetry_event(learner_state, event, config={"decay_rate": 0.05})
    assert next_state.concepts["concept_a"].mastery == pytest.approx(0.95)
    assert next_state.last_updated == "2026-06-28T00:00:00Z"


def test_mastery_graph_projection():
    curr = _setup_curriculum()
    # Add dependency concept_a (prereq) -> concept_b
    from eduvis.core.curriculum import DependencyEdge
    curr.dependencies.append(DependencyEdge("concept_a", "concept_b", "prerequisite"))

    # State where concept_a (prereq) is weak (mastery = 0.5, under default threshold of 0.8)
    state_dict = {
        "schema_version": "0.7",
        "learner_id": "learner_5",
        "concepts": {
            "concept_a": {"mastery": 0.5},
            "concept_b": {"mastery": 0.2}
        }
    }
    learner_state = LearnerState.from_dict(state_dict)

    view = MasteryGraphView(curr, learner_state)

    # Gap check: concept_b has prerequisite gap because concept_a is not mastered
    assert view.concept_mastery["concept_b"].has_gaps is True
    assert "concept_a" in view.concept_mastery["concept_b"].gaps

    # Prerequisite gaps list length
    assert len(view.prerequisite_gaps) == 1
    assert view.prerequisite_gaps[0]["concept"] == "concept_b"
    assert view.prerequisite_gaps[0]["missing_prerequisite"] == "concept_a"

    # Status check
    assert view.get_concept_status("concept_a") == "weak"
    assert view.get_concept_status("concept_b") == "gap"

    # State with prereq mastered
    state_dict_ok = {
        "schema_version": "0.7",
        "learner_id": "learner_5",
        "concepts": {
            "concept_a": {"mastery": 0.9},
            "concept_b": {"mastery": 0.2}
        }
    }
    learner_state_ok = LearnerState.from_dict(state_dict_ok)
    view_ok = MasteryGraphView(curr, learner_state_ok)
    assert view_ok.concept_mastery["concept_b"].has_gaps is False
    assert view_ok.get_concept_status("concept_b") == "weak"
    assert view_ok.get_concept_status("concept_a") == "mastered"
