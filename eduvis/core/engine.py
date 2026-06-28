"""
EduVis Answer Checking and Validation Engine.

Provides numeric and symbolic algebraic equivalence checking, MCQ validation,
and telemetry event verification helper functions.
"""

from __future__ import annotations

import re


def check_answer(element: dict, student_answer: str) -> dict:
    """
    Check student answer against MCQ or short_answer element correct answer.

    Returns:
      {
        "is_correct": bool,
        "misconception_detected": str | None
      }
    """
    if not isinstance(element, dict):
        return {"is_correct": False, "misconception_detected": None}

    el_type = element.get("type")
    correct_answer = element.get("answer")

    if el_type == "short_answer":
        eval_mode = element.get("evaluation_mode", "string")
        student_str = str(student_answer).strip()
        correct_str = str(correct_answer).strip()

        if eval_mode == "numeric":
            is_correct = check_numeric_equivalence(student_str, correct_str)
        elif eval_mode == "algebraic":
            is_correct = check_algebraic_equivalence(student_str, correct_str)
        else:
            is_correct = student_str.lower() == correct_str.lower()

        return {
            "is_correct": is_correct,
            "misconception_detected": None
        }

    # Default MCQ checking
    misconceptions = element.get("misconceptions") or {}
    norm_student = str(student_answer).strip().upper()
    norm_correct = str(correct_answer).strip().upper()

    is_correct = norm_student == norm_correct

    misconception_detected = None
    if not is_correct:
        # Check if the student answer matches one of the misconception keys
        misconception_detected = misconceptions.get(student_answer) or misconceptions.get(norm_student)

    return {
        "is_correct": is_correct,
        "misconception_detected": misconception_detected
    }


def check_numeric_equivalence(student: str, correct: str) -> bool:
    """
    Checks if student answer is numerically equivalent to correct answer.
    Handles decimals, integers, trailing whitespace, and units (e.g. '50 deg' == '50deg' == '50.0').
    """
    def _parse_numeric(val: str) -> tuple[float | None, str]:
        cleaned = val.strip().lower()
        # Regex to extract float/integer at start and optional units
        match = re.match(r"^([\+\-]?\d+(?:\.\d+)?)\s*(.*)$", cleaned)
        if match:
            num_part, unit_part = match.groups()
            try:
                return float(num_part), unit_part.strip()
            except ValueError:
                pass
        return None, cleaned

    s_num, s_unit = _parse_numeric(student)
    c_num, c_unit = _parse_numeric(correct)

    if s_num is None or c_num is None:
        # Fallback to simple normalized string check
        return student.strip().lower() == correct.strip().lower()

    def _normalize_unit(u: str) -> str:
        u = u.replace(" ", "")
        if u in ("deg", "degree", "degrees", "°"):
            return "deg"
        return u

    norm_s_unit = _normalize_unit(s_unit)
    norm_c_unit = _normalize_unit(c_unit)

    # If correct has no unit, we can accept student having unit or not.
    # Otherwise, require units to match.
    unit_matches = (norm_s_unit == norm_c_unit or not norm_c_unit or not norm_s_unit)

    return abs(s_num - c_num) < 1e-9 and unit_matches


def check_algebraic_equivalence(student: str, correct: str) -> bool:
    """
    Checks algebraic equivalence via the AnyEquivalentMatcher (SymPy).
    Kept as a public convenience function used by check_answer.
    """
    from eduvis.core.step_matchers import AnyEquivalentMatcher  # pylint: disable=import-outside-toplevel
    return AnyEquivalentMatcher().matches(student, correct)


def _match_step_line(line_str: str, pattern: str, eval_mode: str,
                     step_type: str | None = None) -> bool:
    """Match a student line against a pattern using the chosen mode and step_type strategy."""
    if eval_mode == "numeric":
        return check_numeric_equivalence(line_str, pattern)
    if eval_mode == "algebraic":
        from eduvis.core.step_matchers import get_step_matcher  # pylint: disable=import-outside-toplevel
        return get_step_matcher(step_type).matches(line_str, pattern)
    return line_str.lower() == pattern.lower()


def _award_parent_if_needed(step: dict, scored_steps: list[dict], marking_scheme: list[dict], earned_steps: set[int]) -> float:
    """Awards the parent step of a dependent step if it hasn't been earned yet."""
    rule = next((r for r in marking_scheme if r.get("step") == step["step"]), None)
    if rule:
        dep_id = rule.get("depends_on")
        if dep_id is not None and dep_id not in earned_steps:
            parent = next((s for s in scored_steps if s["step"] == dep_id), None)
            if parent and not parent["correct"]:
                parent["correct"] = True
                earned_steps.add(dep_id)
                return float(parent["weight"])
    return 0.0


def _apply_retroactive_sweep(scored_steps: list[dict], marking_scheme: list[dict], earned_steps: set[int]) -> float:
    """Applies retroactive step awarding and returns the additional score earned."""
    additional_score = 0.0
    changed = True
    while changed:
        changed = False
        for step in scored_steps:
            # Phase 1 & 3: if this step is correct OR it matched but is blocked,
            # try to grant its parent retroactively.
            if (step["blocked"] and step["matched_line"] is not None) or step["correct"]:
                score_delta = _award_parent_if_needed(step, scored_steps, marking_scheme, earned_steps)
                if score_delta > 0:
                    additional_score += score_delta
                    changed = True

            # Phase 2: if this step is blocked and its parent has now been earned,
            # un-block it and award its marks.
            if step["blocked"] and step["matched_line"] is not None:
                rule = next((r for r in marking_scheme if r.get("step") == step["step"]), None)
                if rule and rule.get("depends_on") in earned_steps:
                    step["blocked"] = False
                    step["correct"] = True
                    additional_score += step["weight"]
                    earned_steps.add(step["step"])
                    changed = True
    return additional_score


def evaluate_steps(element: dict, student_working: list[str]) -> dict:
    """
    Evaluates step-by-step student working based on Method/Accuracy rules.

    Returns:
      {
        "total_score": float,
        "max_score": float,
        "steps": [
          {
            "step": str/int,
            "description": str,
            "mark_type": "M" | "A" | "B",
            "weight": int,
            "correct": bool,
            "blocked": bool,
            "matched_line": str | None
          }
        ]
      }
    """
    if not isinstance(element, dict):
        return {"total_score": 0.0, "max_score": 0.0, "steps": []}

    marking_scheme = element.get("marking_scheme") or []
    eval_mode = element.get("evaluation_mode", "algebraic")

    scored_steps = []
    total_score = 0.0
    max_score = 0.0

    # Track earned status of parent steps
    earned_steps = set()
    matched_student_lines = set()

    for idx, rule in enumerate(marking_scheme):
        step_id = rule.get("step", idx)
        pattern = str(rule.get("pattern", "")).strip()
        mark_type = rule.get("mark_type", "M").upper()
        weight = int(rule.get("weight", 1))
        depends_on = rule.get("depends_on")
        step_type = rule.get("step_type")  # strategy selector
        description = rule.get("description", f"Step {step_id}")

        max_score += weight

        # Each student line can match at most one marking step (consumed once)
        matched_line = None
        for line in student_working:
            line_str = str(line).strip()
            if line_str and line_str not in matched_student_lines:
                if _match_step_line(line_str, pattern, eval_mode, step_type):
                    matched_line = line_str
                    break

        correct = False
        blocked = False

        if matched_line is not None:
            matched_student_lines.add(matched_line)
            if depends_on is not None:
                if depends_on in earned_steps:
                    correct = True
                    total_score += weight
                    earned_steps.add(step_id)
                else:
                    blocked = True
            else:
                correct = True
                total_score += weight
                earned_steps.add(step_id)

        scored_steps.append({
            "step": step_id,
            "description": description,
            "mark_type": mark_type,
            "weight": weight,
            "correct": correct,
            "blocked": blocked,
            "matched_line": matched_line
        })

    # Retroactively award parent steps when the student skipped writing them
    # but demonstrated mastery via a correct or blocked-but-matched dependent step.
    # Only applies when the student wrote NO lines that were completely unrecognised.
    all_lines = {str(working_line).strip() for working_line in student_working if str(working_line).strip()}
    has_wrong_lines = bool(all_lines - matched_student_lines)

    if not has_wrong_lines:
        total_score += _apply_retroactive_sweep(scored_steps, marking_scheme, earned_steps)

    return {
        "total_score": total_score,
        "max_score": max_score,
        "steps": scored_steps
    }
