"""Tests and demonstration of the v0.4 Assessment Evidence & Mastery Bridge.

This demonstrates the end-to-end flow:
1. Negative numbers subtraction question configuration
2. Assessment engine execution (checking student answer and detecting misconception)
3. Evidence bridge (aggregating telemetry events to structured concept/skill/misconception evidence)
4. Mastery bridge (updating learner state confidence and active misconceptions)
"""

from __future__ import annotations
import datetime
from eduvis.core.engine import check_answer


def test_end_to_end_mastery_bridge():
    # 1. Negative numbers subtraction question configuration
    element = {
        "id": "neg_sub_1",
        "type": "multiple_choice",
        "question": "Evaluate: -5 - (-3)",
        "options": {
            "A": "-8",
            "B": "-2",
            "C": "-15",
            "D": "2"
        },
        "answer": "B",
        "misconceptions": {
            "A": "subtract_negative_minus_negative"  # Student computed -5 - 3 = -8
        },
        "concepts": ["negative_numbers"],
        "skills": ["subtract_negative_numbers"]
    }

    # 2. Mock Learner State (initial baseline)
    learner_state = {
        "student_id": "student_123",
        "concept_mastery": {
            "negative_numbers": {"confidence": 0.5, "last_seen": "2026-06-19T00:00:00Z"}
        },
        "skill_mastery": {
            "subtract_negative_numbers": {"confidence": 0.5, "last_seen": "2026-06-19T00:00:00Z"}
        },
        "active_misconceptions": {}
    }

    # Helper: Evidence Bridge
    def build_evidence(element_cfg: dict, check_res: dict, student_answer: str, attempt: int) -> dict:
        """Transforms a raw telemetry check result into a structured evidence package."""
        return {
            "student_id": "student_123",
            "element_id": element_cfg["id"],
            "attempt_number": attempt,
            "answer_submitted": student_answer,
            "is_correct": check_res["is_correct"],
            "misconception_detected": check_res["misconception_detected"],
            "resolved_misconceptions": list(element_cfg.get("misconceptions", {}).values()),
            "concepts": element_cfg.get("concepts", []),
            "skills": element_cfg.get("skills", []),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

    # Helper: Mastery Bridge / Update
    def update_learner_state(state: dict, evidence: dict) -> dict:
        """Applies evidence to update student confidence and active misconceptions."""
        updated = {
            "student_id": state["student_id"],
            "concept_mastery": {k: dict(v) for k, v in state["concept_mastery"].items()},
            "skill_mastery": {k: dict(v) for k, v in state["skill_mastery"].items()},
            "active_misconceptions": dict(state["active_misconceptions"])
        }
        timestamp = evidence["timestamp"]

        # 1. Update misconception tracking
        misconception = evidence["misconception_detected"]
        if misconception:
            updated["active_misconceptions"][misconception] = {
                "active": True,
                "detected_at": timestamp
            }

        # If student answered correctly, clear related misconceptions tested by this element
        if evidence["is_correct"]:
            for resolved in evidence.get("resolved_misconceptions", []):
                if resolved in updated["active_misconceptions"]:
                    del updated["active_misconceptions"][resolved]

        # 2. Adjust skill and concept confidence
        is_correct = evidence["is_correct"]
        for skill in evidence["skills"]:
            current_conf = updated["skill_mastery"].get(skill, {}).get("confidence", 0.5)
            if is_correct:
                new_conf = min(1.0, current_conf + 0.15)
            else:
                new_conf = max(0.0, current_conf - 0.2)

            updated["skill_mastery"][skill] = {
                "confidence": round(new_conf, 2),
                "last_seen": timestamp
            }

        for concept in evidence["concepts"]:
            current_conf = updated["concept_mastery"].get(concept, {}).get("confidence", 0.5)
            if is_correct:
                new_conf = min(1.0, current_conf + 0.1)
            else:
                new_conf = max(0.0, current_conf - 0.1)

            updated["concept_mastery"][concept] = {
                "confidence": round(new_conf, 2),
                "last_seen": timestamp
            }

        return updated

    # --- Scenario A: Student commits the subtraction misconception (answers 'A') ---
    res_incorrect = check_answer(element, "A")
    assert res_incorrect["is_correct"] is False
    assert res_incorrect["misconception_detected"] == "subtract_negative_minus_negative"

    evidence_incorrect = build_evidence(element, res_incorrect, "A", 1)
    state_after_incorrect = update_learner_state(learner_state, evidence_incorrect)

    # Assert state adjustments
    assert state_after_incorrect["active_misconceptions"]["subtract_negative_minus_negative"]["active"] is True
    # Confidence in specific skill goes down from 0.5 to 0.3
    assert state_after_incorrect["skill_mastery"]["subtract_negative_numbers"]["confidence"] == 0.3
    # Confidence in general concept goes down from 0.5 to 0.4
    assert state_after_incorrect["concept_mastery"]["negative_numbers"]["confidence"] == 0.4

    # --- Scenario B: Student retries and gets it correct (answers 'B') ---
    res_correct = check_answer(element, "B")
    assert res_correct["is_correct"] is True
    assert res_correct["misconception_detected"] is None

    evidence_correct = build_evidence(element, res_correct, "B", 2)
    state_after_correct = update_learner_state(state_after_incorrect, evidence_correct)

    # Assert state recovery
    # Misconception is cleared/deactivated because they resolved it
    assert "subtract_negative_minus_negative" not in state_after_correct["active_misconceptions"]
    # Confidence in specific skill goes up from 0.3 to 0.45
    assert state_after_correct["skill_mastery"]["subtract_negative_numbers"]["confidence"] == 0.45
    # Confidence in general concept goes up from 0.4 to 0.5
    assert state_after_correct["concept_mastery"]["negative_numbers"]["confidence"] == 0.5
