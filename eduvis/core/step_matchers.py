# pylint: disable=import-error, too-few-public-methods
"""
EduVis Step Matcher Strategies.

Each StepMatcher subclass validates one specific kind of algebraic transformation
that a student may be expected to produce at a given marking-scheme step.

Supported step_type values
--------------------------
any_equivalent   -- Any form algebraically equal to the pattern (default fallback).
extract_factor   -- Student identifies a factor (sub-expression divides pattern).
fully_factorised -- Expression must itself already be its own fully-factored form.
expanded         -- Expression must be the distributed / multiplied-out form.
collected        -- Expression must be the simplified polynomial form (like terms collected).

Usage
-----
    from eduvis.core.step_matchers import get_step_matcher
    matcher = get_step_matcher("fully_factorised")
    ok = matcher.matches("3x(2x+3)", "3x(2x+3)")   # True
    ok = matcher.matches("x(6x+9)", "3x(2x+3)")    # False -- not fully factored
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sympify_expr(expr_str: str):
    """
    Parse a plain-text algebra string into a SymPy expression.
    Handles implicit multiplication (3x -> 3*x, x( -> x*(, )x -> )*x)
    and common exponent notations (^, squared, cubed).
    """
    from sympy import sympify  # pylint: disable=import-outside-toplevel

    s = expr_str.strip().replace(" ", "").lower()
    s = s.replace("^", "**")
    s = s.replace("\u00b2", "**2").replace("\u00b3", "**3")
    s = re.sub(r"(\d)([a-z])", r"\1*\2", s)
    s = re.sub(r"([a-z\d])\(", r"\1*(", s)
    s = re.sub(r"\)([a-z\d(])", r")*\1", s)
    return sympify(s)


def _are_equivalent(student_str: str, pattern_str: str) -> bool:
    """Return True if both expressions are algebraically equivalent."""
    from sympy import simplify  # pylint: disable=import-outside-toplevel
    try:
        s = _sympify_expr(student_str)
        p = _sympify_expr(pattern_str)
        return simplify(s - p) == 0
    except Exception:  # pylint: disable=broad-exception-caught
        def norm(t: str) -> str:
            return t.replace(" ", "").replace("(", "").replace(")", "").lower()
        return norm(student_str) == norm(pattern_str)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class StepMatcher(ABC):
    """Base class for all algebraic step matchers."""

    @abstractmethod
    def matches(self, student: str, pattern: str) -> bool:
        """Return True if the student expression satisfies this step."""


# ---------------------------------------------------------------------------
# Concrete matchers
# ---------------------------------------------------------------------------

class AnyEquivalentMatcher(StepMatcher):
    """
    Default matcher. Accepts any expression that is algebraically equivalent
    to the pattern, regardless of form.
    """

    def matches(self, student: str, pattern: str) -> bool:
        return _are_equivalent(student, pattern)


class ExtractFactorMatcher(StepMatcher):
    """
    M-mark: student must have written the correct common factor.
    The student expression needs to be algebraically equivalent to the pattern.
    """

    def matches(self, student: str, pattern: str) -> bool:
        return _are_equivalent(student, pattern)


class FullyFactorisedMatcher(StepMatcher):
    """
    A-mark: expression must be fully factorised AND equivalent to the pattern.

    Fully factorised means SymPy factor() of the student expression equals
    the student expression itself (no further factorisation is possible).
    """

    def matches(self, student: str, pattern: str) -> bool:
        from sympy import factor, simplify  # pylint: disable=import-outside-toplevel
        try:
            s = _sympify_expr(student)
            p = _sympify_expr(pattern)
            if simplify(s - p) != 0:
                return False
            return factor(s) == s
        except Exception:  # pylint: disable=broad-exception-caught
            return False


class ExpandedMatcher(StepMatcher):
    """
    M-mark: expression must be the expanded (distributed) form.

    Expanded means expand(student) == student.
    e.g. 6x + 8 + x is expanded; x(6x+9) is not.
    """

    def matches(self, student: str, pattern: str) -> bool:
        from sympy import expand, simplify  # pylint: disable=import-outside-toplevel
        try:
            s = _sympify_expr(student)
            p = _sympify_expr(pattern)
            if simplify(s - p) != 0:
                return False
            return expand(s) == s
        except Exception:  # pylint: disable=broad-exception-caught
            return False


class CollectedMatcher(StepMatcher):
    """
    A-mark: expression must be a fully collected / simplified polynomial form.

    Collected means Poly(student).as_expr() == student (no like terms remain).
    e.g. 7x + 8 is collected; 6x + 8 + x is not.
    """

    def matches(self, student: str, pattern: str) -> bool:
        from sympy import Poly, simplify, symbols, expand  # pylint: disable=import-outside-toplevel
        try:
            x = symbols("x")
            s = _sympify_expr(student)
            p = _sympify_expr(pattern)
            if simplify(s - p) != 0:
                return False
            poly_s = Poly(s, x).as_expr()
            return expand(poly_s - s) == 0
        except Exception:  # pylint: disable=broad-exception-caught
            return False


# ---------------------------------------------------------------------------
# Registry and factory
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, StepMatcher] = {
    "any_equivalent":   AnyEquivalentMatcher(),
    "extract_factor":   ExtractFactorMatcher(),
    "fully_factorised": FullyFactorisedMatcher(),
    "expanded":         ExpandedMatcher(),
    "collected":        CollectedMatcher(),
}


def get_step_matcher(step_type: str | None) -> StepMatcher:
    """
    Factory: return the appropriate StepMatcher for the given step_type.
    Unknown or missing step_type falls back to AnyEquivalentMatcher.
    """
    return _REGISTRY.get(step_type or "any_equivalent", AnyEquivalentMatcher())
