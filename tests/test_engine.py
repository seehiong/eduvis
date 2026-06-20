"""Tests for the EduVis Answer Checking and Validation Engine."""

from eduvis.core.engine import check_answer, check_numeric_equivalence, check_algebraic_equivalence

def test_check_answer_mcq():
    element = {
        "id": "q1",
        "type": "multiple_choice",
        "question": "What is 1/2 of 100?",
        "options": {
            "A": "25",
            "B": "50",
            "C": "200"
        },
        "answer": "B",
        "misconceptions": {
            "A": "half-concept-doubled",
            "C": "doubled-instead-of-halved"
        }
    }

    # Correct answer
    res = check_answer(element, "B")
    assert res["is_correct"] is True
    assert res["misconception_detected"] is None

    # Correct answer with lowercase / whitespace
    res = check_answer(element, " b ")
    assert res["is_correct"] is True
    assert res["misconception_detected"] is None

    # Incorrect answer with misconception A
    res = check_answer(element, "A")
    assert res["is_correct"] is False
    assert res["misconception_detected"] == "half-concept-doubled"

    # Incorrect answer with misconception C
    res = check_answer(element, "C")
    assert res["is_correct"] is False
    assert res["misconception_detected"] == "doubled-instead-of-halved"

    # Incorrect answer with no misconception
    res = check_answer(element, "D")
    assert res["is_correct"] is False
    assert res["misconception_detected"] is None

def test_check_numeric_equivalence():
    # Simple integer / decimal match
    assert check_numeric_equivalence("50", "50.0") is True
    assert check_numeric_equivalence("50.00", "50") is True
    assert check_numeric_equivalence("+50", "50") is True
    assert check_numeric_equivalence("-50", "-50") is True

    # Whitespace and units matching
    assert check_numeric_equivalence("50 deg", "50deg") is True
    assert check_numeric_equivalence("50 deg", "50.0deg") is True
    assert check_numeric_equivalence("50 °", "50 deg") is True
    assert check_numeric_equivalence("50 degrees", "50 degree") is True

    # Correct has no unit, student has unit: accepted
    assert check_numeric_equivalence("50 deg", "50") is True
    # Student has no unit, correct has unit: accepted
    assert check_numeric_equivalence("50", "50 deg") is True

    # Mismatched units
    assert check_numeric_equivalence("50 m", "50 s") is False

    # Close floats
    assert check_numeric_equivalence("50.0000000001", "50") is True
    assert check_numeric_equivalence("50.1", "50") is False

    # Non-numeric fallback
    assert check_numeric_equivalence("hello", "hello") is True
    assert check_numeric_equivalence("hello", "world") is False

def test_check_algebraic_equivalence():
    # Commutative addition
    assert check_algebraic_equivalence("x + 2", "2 + x") is True
    assert check_algebraic_equivalence("x + 2", "2+x") is True
    assert check_algebraic_equivalence("a + b + c", "c + b + a") is True

    # Implicit multiplication
    assert check_algebraic_equivalence("3x", "3*x") is True
    assert check_algebraic_equivalence("3x", "x*3") is True
    assert check_algebraic_equivalence("x*y", "y*x") is True

    # Double signs normalization
    assert check_algebraic_equivalence("x - y", "x + -y") is True
    assert check_algebraic_equivalence("x -- 2", "x + 2") is True
    assert check_algebraic_equivalence("x +- y", "x - y") is True

    # Mismatches
    assert check_algebraic_equivalence("x + 3", "x + 2") is False
    assert check_algebraic_equivalence("x * 2", "x + 2") is False
