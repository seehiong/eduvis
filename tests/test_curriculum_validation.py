"""Tests for Singapore MOE Secondary 1 Mathematics Chapter 2 validation loop.

Verifies the end-to-end flow by parsing the actual production lesson YAML:
1. Static Curriculum Graph & progression structure parsing
2. MCQ answer checking and misconception identification on real question elements
3. Evidence bridge mapping
4. Dynamic learner state updates and mastery projections
"""

from __future__ import annotations
import os
import datetime
import yaml
from eduvis.core.engine import check_answer


# Path to the actual negative numbers lesson spec
LESSON_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "docs", "showcase", "lessons", "negative-numbers-confidence-ladder-lesson.yaml"
)


def test_load_and_validate_lesson_spec():
    """Verify the physical lesson YAML is valid, contains required elements, and conforms to progression rules."""
    assert os.path.exists(LESSON_FILE), f"Missing lesson file at {LESSON_FILE}"

    with open(LESSON_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # 1. Verify Curriculum Metadata
    assert data["curriculum"]["code"] == "SEC-math-2027"
    assert data["curriculum"]["topic"] == "Chapter-2-Negative-Numbers"
    assert "negative_numbers" in data["lesson"]["concepts"]

    # 2. Verify progression matches confidence ladder
    assert data["progression"]["pattern"] == "confidence_ladder"
    phases = [p["phase"] for p in data["progression"]["phases"]]
    assert "hook" in phases
    assert "explore" in phases
    assert "explain" in phases
    assert "independent_practice" in phases

    # 3. Verify content contains all required elements
    content_map = {item["id"]: item for item in data["content"]}
    assert "hook_real_world" in content_map
    assert "explore_temperature_scale" in content_map
    assert "check_negative_ordering" in content_map
    assert "check_negative_addition" in content_map
    assert "check_negative_subtraction" in content_map
    assert "simplify_expression" in content_map


def test_real_lesson_assessment_to_mastery_loop():
    """Simulate student interactions with the actual parsed lesson questions to verify telemetry and learner state update bridge."""
    with open(LESSON_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    content_map = {item["id"]: item for item in data["content"]}

    # Initialize dynamic learner state (starting baseline)
    learner_state = {
        "student_id": "student_999",
        "concept_mastery": {
            "negative_numbers": {"confidence": 0.5, "last_seen": "Never"}
        },
        "skill_mastery": {
            "order_integers": {"confidence": 0.5, "last_seen": "Never"},
            "add_negative_numbers": {"confidence": 0.5, "last_seen": "Never"},
            "subtract_negative_numbers": {"confidence": 0.5, "last_seen": "Never"}
        },
        "active_misconceptions": {}
    }

    # Evidence Bridge
    def build_evidence(element_cfg: dict, check_res: dict, _answer: str) -> dict:
        return {
            "student_id": "student_999",
            "element_id": element_cfg["id"],
            "is_correct": check_res["is_correct"],
            "misconception_detected": check_res["misconception_detected"],
            "resolved_misconceptions": list(element_cfg.get("misconceptions", {}).values()),
            "concepts": element_cfg.get("concepts", []),
            "skills": element_cfg.get("skills", []),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

    # Mastery Bridge
    def update_learner_state(state: dict, evidence: dict) -> dict:
        updated = {
            "student_id": state["student_id"],
            "concept_mastery": {k: dict(v) for k, v in state["concept_mastery"].items()},
            "skill_mastery": {k: dict(v) for k, v in state["skill_mastery"].items()},
            "active_misconceptions": dict(state["active_misconceptions"])
        }
        timestamp = evidence["timestamp"]

        # Track misconception
        m = evidence["misconception_detected"]
        if m:
            updated["active_misconceptions"][m] = {"active": True, "detected_at": timestamp}

        # Clear misconceptions if correct
        if evidence["is_correct"]:
            for resolved in evidence.get("resolved_misconceptions", []):
                if resolved in updated["active_misconceptions"]:
                    del updated["active_misconceptions"][resolved]

        # Adjust skill confidence
        is_correct = evidence["is_correct"]
        for skill in evidence["skills"]:
            curr = updated["skill_mastery"].get(skill, {}).get("confidence", 0.5)
            new_val = min(1.0, curr + 0.15) if is_correct else max(0.0, curr - 0.2)
            updated["skill_mastery"][skill] = {"confidence": round(new_val, 2), "last_seen": timestamp}

        # Adjust concept confidence
        for concept in evidence["concepts"]:
            curr = updated["concept_mastery"].get(concept, {}).get("confidence", 0.5)
            new_val = min(1.0, curr + 0.1) if is_correct else max(0.0, curr - 0.1)
            updated["concept_mastery"][concept] = {"confidence": round(new_val, 2), "last_seen": timestamp}

        return updated

    # --- Step 1: Student answers 'A' (Incorrect) on ordering ---
    elem_ordering = content_map["check_negative_ordering"]
    res_1 = check_answer(elem_ordering, "A")
    assert res_1["is_correct"] is False
    assert res_1["misconception_detected"] == "digit_size_magnitude_error"

    ev_1 = build_evidence(elem_ordering, res_1, "A")
    learner_state = update_learner_state(learner_state, ev_1)

    assert learner_state["active_misconceptions"]["digit_size_magnitude_error"]["active"] is True
    assert learner_state["skill_mastery"]["order_integers"]["confidence"] == 0.3
    assert learner_state["concept_mastery"]["negative_numbers"]["confidence"] == 0.4

    # --- Step 2: Student answers 'C' (Incorrect) on addition ---
    elem_addition = content_map["check_negative_addition"]
    res_2 = check_answer(elem_addition, "C")
    assert res_2["is_correct"] is False
    assert res_2["misconception_detected"] == "double_negative_addition_confusion"

    ev_2 = build_evidence(elem_addition, res_2, "C")
    learner_state = update_learner_state(learner_state, ev_2)

    assert "digit_size_magnitude_error" in learner_state["active_misconceptions"]
    assert "double_negative_addition_confusion" in learner_state["active_misconceptions"]
    assert learner_state["skill_mastery"]["add_negative_numbers"]["confidence"] == 0.3

    # --- Step 3: Student answers 'B' (Correct) on ordering retry ---
    res_3 = check_answer(elem_ordering, "B")
    assert res_3["is_correct"] is True

    ev_3 = build_evidence(elem_ordering, res_3, "B")
    learner_state = update_learner_state(learner_state, ev_3)

    # Ordering misconception must be resolved/removed, addition misconception remains active
    assert "digit_size_magnitude_error" not in learner_state["active_misconceptions"]
    assert "double_negative_addition_confusion" in learner_state["active_misconceptions"]
    assert learner_state["skill_mastery"]["order_integers"]["confidence"] == 0.45
