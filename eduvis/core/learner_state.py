"""EduVis — Learner State Model.

Represents a transient student learning state, mapping concepts, skills,
and misconceptions to their respective mastery metrics, with validation support.
"""

from __future__ import annotations

import datetime
from typing import Any


class ConceptState:  # pylint: disable=too-few-public-methods
    """Represents the mastery and confidence state of a single concept."""

    def __init__(self, mastery: float, confidence: float | None = None) -> None:
        self.mastery = float(mastery)
        self.confidence = float(confidence) if confidence is not None else None

    def to_dict(self) -> dict[str, Any]:
        res: dict[str, Any] = {"mastery": self.mastery}
        if self.confidence is not None:
            res["confidence"] = self.confidence
        return res


class SkillState:  # pylint: disable=too-few-public-methods
    """Represents the mastery state of a single skill."""

    def __init__(self, mastery: float) -> None:
        self.mastery = float(mastery)

    def to_dict(self) -> dict[str, Any]:
        return {"mastery": self.mastery}


class MisconceptionState:  # pylint: disable=too-few-public-methods
    """Represents the active status of a single misconception."""

    def __init__(self, state: str, attempts: int = 0) -> None:
        self.state = str(state).strip().lower()
        self.attempts = int(attempts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "attempts": self.attempts,
        }


class LearnerState:
    """Manages the transient learner state with validation."""

    def __init__(
        self,
        learner_id: str,
        schema_version: str = "0.7",
        last_updated: str | None = None,
    ) -> None:
        self.learner_id = str(learner_id).strip()
        self.schema_version = str(schema_version).strip()
        self.last_updated = last_updated or datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.concepts: dict[str, ConceptState] = {}
        self.skills: dict[str, SkillState] = {}
        self.misconceptions: dict[str, MisconceptionState] = {}

    def to_dict(self) -> dict[str, Any]:
        res: dict[str, Any] = {
            "schema_version": self.schema_version,
            "learner_id": self.learner_id,
            "last_updated": self.last_updated,
            "concepts": {code: state.to_dict() for code, state in self.concepts.items()},
        }
        if self.skills:
            res["skills"] = {code: state.to_dict() for code, state in self.skills.items()}
        if self.misconceptions:
            res["misconceptions"] = {code: state.to_dict() for code, state in self.misconceptions.items()}
        return res

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LearnerState:
        """Construct a LearnerState instance from a dictionary."""
        version = data.get("schema_version", "0.7")
        state = cls(
            learner_id=data.get("learner_id", "anonymous"),
            schema_version=version,
            last_updated=data.get("last_updated"),
        )

        concepts_data = data.get("concepts") or {}
        if isinstance(concepts_data, dict):
            for code, c_val in concepts_data.items():
                if isinstance(c_val, dict) and "mastery" in c_val:
                    state.concepts[code] = ConceptState(
                        mastery=c_val["mastery"],
                        confidence=c_val.get("confidence"),
                    )

        skills_data = data.get("skills") or {}
        if isinstance(skills_data, dict):
            for code, s_val in skills_data.items():
                if isinstance(s_val, dict) and "mastery" in s_val:
                    state.skills[code] = SkillState(mastery=s_val["mastery"])

        mis_data = data.get("misconceptions") or {}
        if isinstance(mis_data, dict):
            for code, m_val in mis_data.items():
                if isinstance(m_val, dict) and "state" in m_val:
                    state.misconceptions[code] = MisconceptionState(
                        state=m_val["state"],
                        attempts=m_val.get("attempts", 0),
                    )

        return state


def _validate_learner_concepts(concepts: Any, warnings: list[str]) -> None:
    if concepts is None:
        warnings.append("ERROR: [learner_state] missing 'concepts' map")
    elif not isinstance(concepts, dict):
        warnings.append("ERROR: [learner_state] 'concepts' must be a dictionary mapping concept codes")
    else:
        for code, c_val in concepts.items():
            if not isinstance(c_val, dict):
                warnings.append(f"ERROR: [learner_state:concepts] value for '{code}' must be a dictionary")
                continue
            if "mastery" not in c_val:
                warnings.append(f"ERROR: [learner_state:concepts] concept '{code}' missing 'mastery'")
            else:
                m = c_val["mastery"]
                if not isinstance(m, (int, float)) or not 0.0 <= m <= 1.0:
                    warnings.append(f"ERROR: [learner_state:concepts] concept '{code}' mastery must be a float between 0.0 and 1.0")
            if "confidence" in c_val:
                conf = c_val["confidence"]
                if conf is not None and (not isinstance(conf, (int, float)) or not 0.0 <= conf <= 1.0):
                    warnings.append(f"ERROR: [learner_state:concepts] concept '{code}' confidence must be a float between 0.0 and 1.0")


def _validate_learner_skills(skills: Any, warnings: list[str]) -> None:
    if skills is not None:
        if not isinstance(skills, dict):
            warnings.append("ERROR: [learner_state] 'skills' must be a dictionary")
        else:
            for code, s_val in skills.items():
                if not isinstance(s_val, dict):
                    warnings.append(f"ERROR: [learner_state:skills] value for '{code}' must be a dictionary")
                    continue
                if "mastery" not in s_val:
                    warnings.append(f"ERROR: [learner_state:skills] skill '{code}' missing 'mastery'")
                else:
                    m = s_val["mastery"]
                    if not isinstance(m, (int, float)) or not 0.0 <= m <= 1.0:
                        warnings.append(f"ERROR: [learner_state:skills] skill '{code}' mastery must be a float between 0.0 and 1.0")


def _validate_learner_misconceptions(misconceptions: Any, warnings: list[str]) -> None:
    if misconceptions is not None:
        if not isinstance(misconceptions, dict):
            warnings.append("ERROR: [learner_state] 'misconceptions' must be a dictionary")
        else:
            for code, m_val in misconceptions.items():
                if not isinstance(m_val, dict):
                    warnings.append(f"ERROR: [learner_state:misconceptions] value for '{code}' must be a dictionary")
                    continue
                if "state" not in m_val:
                    warnings.append(f"ERROR: [learner_state:misconceptions] misconception '{code}' missing 'state'")
                else:
                    state = m_val["state"]
                    if state not in ("active", "remediated"):
                        warnings.append(f"ERROR: [learner_state:misconceptions] misconception '{code}' state must be 'active' or 'remediated'")
                if "attempts" in m_val:
                    att = m_val["attempts"]
                    if not isinstance(att, int) or att < 0:
                        warnings.append(f"ERROR: [learner_state:misconceptions] misconception '{code}' attempts must be a non-negative integer")


def validate_learner_state(data: dict[str, Any]) -> list[str]:
    """Validate a learner state dictionary, returning warnings/errors."""
    warnings: list[str] = []

    if not isinstance(data, dict):
        warnings.append("ERROR: [learner_state] must be a dictionary")
        return warnings

    # learner_id
    if "learner_id" not in data:
        warnings.append("ERROR: [learner_state] missing 'learner_id'")
    elif not isinstance(data["learner_id"], str) or not data["learner_id"].strip():
        warnings.append("ERROR: [learner_state] 'learner_id' must be a non-empty string")

    # concepts
    _validate_learner_concepts(data.get("concepts"), warnings)

    # skills
    _validate_learner_skills(data.get("skills"), warnings)

    # misconceptions
    _validate_learner_misconceptions(data.get("misconceptions"), warnings)

    return warnings
