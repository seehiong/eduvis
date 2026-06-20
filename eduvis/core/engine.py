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
    Checks algebraic equivalence for mathematical expressions
    by substituting variable values and comparing outputs.
    """
    def _evaluate_at(expr_str: str, x_val: float) -> float:
        # Clean spacing and normalize variables to lowercase
        s = expr_str.replace(" ", "").lower()
        # Add implicit multiplication (e.g. 3x -> 3 * x)
        s = re.sub(r"(\d)([a-z])", r"\1*\2", s)
        # Replace variable with value (assuming single letter variables like x)
        s = re.sub(r"\b[a-z]\b", f"({x_val})", s)
        # Evaluate math expression safely
        # Allow only numbers, operators, decimals, and parentheses
        if not re.match(r"^[0-9\+\-\*\/\(\)\.]+$", s):
            raise ValueError("Unsafe characters in expression")
        return float(eval(s))  # pylint: disable=eval-used

    try:
        # Test at two different points to avoid accidental collisions
        for val in (2.0, 7.5):
            if abs(_evaluate_at(student, val) - _evaluate_at(correct, val)) > 1e-9:
                return False
        return True
    except Exception:  # pylint: disable=broad-exception-caught
        # Fallback to normalized string match if evaluation fails
        s_norm = student.replace(" ", "").replace("(", "").replace(")", "").lower()
        c_norm = correct.replace(" ", "").replace("(", "").replace(")", "").lower()
        return s_norm == c_norm



def _match_step_line(line_str: str, pattern: str, eval_mode: str) -> bool:
    """Helper to match a single step line against a pattern using the chosen mode."""
    if eval_mode == "numeric":
        return check_numeric_equivalence(line_str, pattern)
    if eval_mode == "algebraic":
        return check_algebraic_equivalence(line_str, pattern)
    return line_str.lower() == pattern.lower()


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

    for idx, rule in enumerate(marking_scheme):
        step_id = rule.get("step", idx)
        pattern = str(rule.get("pattern", "")).strip()
        mark_type = rule.get("mark_type", "M").upper()
        weight = int(rule.get("weight", 1))
        depends_on = rule.get("depends_on")
        description = rule.get("description", f"Step {step_id}")

        max_score += weight

        # Check if any student working line matches this step's pattern
        matched_line = None
        for line in student_working:
            line_str = str(line).strip()
            if line_str and _match_step_line(line_str, pattern, eval_mode):
                matched_line = line_str
                break

        correct = False
        blocked = False

        if matched_line is not None:
            # Check dependencies (e.g. A marks require M marks first)
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

    return {
        "total_score": total_score,
        "max_score": max_score,
        "steps": scored_steps
    }
