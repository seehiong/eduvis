"""EduVis — Stateless Transition Engine.

Processes telemetry events to update student learner state statelessly
and applies decay functions.
"""

from __future__ import annotations

import datetime
from typing import Any, Callable

from .learner_state import LearnerState, ConceptState, SkillState, MisconceptionState
from .curriculum import CurriculumGraph


DEFAULT_ENGINE_CONFIG = {
    "learning_rate": 0.1,
    "misconception_penalty": 0.15,
    "decay_rate": 0.05,  # proportional decay per day (e.g. 5% decay)
}


def default_decay_fn(state: LearnerState, time_delta_seconds: float, config: dict[str, Any]) -> LearnerState:
    """Proportionally decay concept and skill mastery over time."""
    decay_rate = config.get("decay_rate", 0.05)
    # Convert seconds to days (86400 seconds in a day)
    days = time_delta_seconds / 86400.0
    if days <= 0:
        return state

    decay_factor = (1.0 - decay_rate) ** days

    for c_state in state.concepts.values():
        c_state.mastery = max(0.0, min(1.0, c_state.mastery * decay_factor))

    for s_state in state.skills.values():
        s_state.mastery = max(0.0, min(1.0, s_state.mastery * decay_factor))

    return state


def _handle_misconception_update(
    new_state: LearnerState,
    misconception: Any,
    assessed_concepts: list[str],
    assesses: dict[str, float],
    *,
    curriculum: CurriculumGraph | None,
    engine_config: dict[str, Any],
) -> None:
    if not misconception:
        return
    mis_code = str(misconception).strip()
    # Find concept mapping if curriculum graph is present
    linked_concept = None
    if curriculum and mis_code in curriculum.misconceptions:
        linked_concept = curriculum.misconceptions[mis_code].concept
        if linked_concept not in assessed_concepts:
            assessed_concepts.append(linked_concept)

    if mis_code in new_state.misconceptions:
        m_state = new_state.misconceptions[mis_code]
        m_state.state = "active"
        m_state.attempts += 1
    else:
        new_state.misconceptions[mis_code] = MisconceptionState(state="active", attempts=1)

    # Apply misconception penalty to assessed concepts
    penalty = engine_config["misconception_penalty"]
    for concept in assessed_concepts:
        weight = assesses.get(concept, 1.0)
        if concept in new_state.concepts:
            c_state = new_state.concepts[concept]
            c_state.mastery = max(0.0, c_state.mastery - penalty * weight)
        else:
            new_state.concepts[concept] = ConceptState(mastery=0.0)


def _handle_correct_attempt(
    new_state: LearnerState,
    assessed_concepts: list[str],
    assesses: dict[str, float],
    assesses_skills: dict[str, float],
    *,
    curriculum: CurriculumGraph | None,
    engine_config: dict[str, Any],
) -> None:
    lr = engine_config["learning_rate"]
    # Set triggered misconceptions for these concepts to remediated
    for m_code, m_state in list(new_state.misconceptions.items()):
        if m_state.state == "active":
            # Check if misconception is linked to assessed concepts
            is_linked = False
            if curriculum and m_code in curriculum.misconceptions:
                if curriculum.misconceptions[m_code].concept in assessed_concepts:
                    is_linked = True
            if is_linked:
                m_state.state = "remediated"

    # Increment concept mastery
    for concept in assessed_concepts:
        weight = assesses.get(concept, 1.0)
        if concept in new_state.concepts:
            c_state = new_state.concepts[concept]
            c_state.mastery = min(1.0, c_state.mastery + lr * weight * (1.0 - c_state.mastery))
        else:
            new_state.concepts[concept] = ConceptState(mastery=lr * weight)

    # Increment skill mastery
    for skill in assesses_skills:
        weight = assesses_skills.get(skill, 1.0)
        if skill in new_state.skills:
            s_state = new_state.skills[skill]
            s_state.mastery = min(1.0, s_state.mastery + lr * weight * (1.0 - s_state.mastery))
        else:
            new_state.skills[skill] = SkillState(mastery=lr * weight)


def _handle_incorrect_attempt(
    new_state: LearnerState,
    misconception: Any,
    assessed_concepts: list[str],
    assesses: dict[str, float],
    *,
    assesses_skills: dict[str, float],
    engine_config: dict[str, Any],
) -> None:
    if misconception:
        return
    lr = engine_config["learning_rate"]
    # Slight penalty for incorrect
    penalty = lr * 0.5
    for concept in assessed_concepts:
        weight = assesses.get(concept, 1.0)
        if concept in new_state.concepts:
            c_state = new_state.concepts[concept]
            c_state.mastery = max(0.0, c_state.mastery - penalty * weight)
        else:
            new_state.concepts[concept] = ConceptState(mastery=0.0)

    for skill in assesses_skills:
        weight = assesses_skills.get(skill, 1.0)
        if skill in new_state.skills:
            s_state = new_state.skills[skill]
            s_state.mastery = max(0.0, s_state.mastery - penalty * weight)
        else:
            new_state.skills[skill] = SkillState(mastery=0.0)


def _apply_assessment_attempt(
    new_state: LearnerState,
    payload: dict[str, Any],
    curriculum: CurriculumGraph | None,
    engine_config: dict[str, Any],
) -> None:
    is_correct = payload.get("is_correct", False)
    misconception = payload.get("misconception_detected")
    assesses = payload.get("assesses") or {}
    assesses_skills = payload.get("assesses_skills") or {}

    assessed_concepts = list(assesses.keys())

    _handle_misconception_update(
        new_state, misconception, assessed_concepts, assesses,
        curriculum=curriculum, engine_config=engine_config
    )

    if is_correct:
        _handle_correct_attempt(
            new_state, assessed_concepts, assesses, assesses_skills,
            curriculum=curriculum, engine_config=engine_config
        )
    else:
        _handle_incorrect_attempt(
            new_state, misconception, assessed_concepts, assesses,
            assesses_skills=assesses_skills, engine_config=engine_config
        )


def apply_telemetry_event(
    current_state: LearnerState,
    event: dict[str, Any],
    curriculum: CurriculumGraph | None = None,
    config: dict[str, Any] | None = None,
    decay_fn: Callable[[LearnerState, float, dict[str, Any]], LearnerState] | None = None,
) -> LearnerState:
    """
    Statelessly process a telemetry event to calculate the new student LearnerState.

    current_state: The current LearnerState instance.
    event: A telemetry event dictionary conforming to telemetry_event.schema.json.
    curriculum: Optional static CurriculumGraph to resolve node mappings.
    config: Optional config dict to override learning rates/penalties.
    decay_fn: Optional custom decay function. If None, default_decay_fn is used.
    """
    # 1. Clone state to keep the transition pure and stateless
    new_state = LearnerState.from_dict(current_state.to_dict())

    # Merge config
    engine_config = DEFAULT_ENGINE_CONFIG.copy()
    if config:
        engine_config.update(config)

    # 2. Handle Temporal Decay first
    event_time_str = event.get("timestamp")
    if event_time_str and current_state.last_updated:
        try:
            event_time = datetime.datetime.fromisoformat(event_time_str.replace("Z", "+00:00"))
            state_time = datetime.datetime.fromisoformat(current_state.last_updated.replace("Z", "+00:00"))
            delta_seconds = (event_time - state_time).total_seconds()
            if delta_seconds > 0:
                active_decay_fn = decay_fn or default_decay_fn
                new_state = active_decay_fn(new_state, delta_seconds, engine_config)
        except (ValueError, TypeError, KeyError):
            # If datetime parsing fails, skip decay step and proceed
            pass

    # Update last updated timestamp
    if event_time_str:
        new_state.last_updated = event_time_str

    # 3. Process Payload
    event_type = event.get("event_type")
    payload = event.get("payload") or {}

    if event_type == "assessment_attempt":
        _apply_assessment_attempt(new_state, payload, curriculum, engine_config)

    return new_state
