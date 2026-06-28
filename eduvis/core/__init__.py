"""
EduVis Core — renderer-agnostic educational content schema.

Public API:
  ElementRegistry        — query element specs, generate prompt docs, validate fields
  validate_lesson()      — validate a complete lesson document (all five pillars)
  format_prompt_docs()   — full five-pillar vocabulary for LLM system prompts
  get_all_schemas()      — export JSON schemas for external consumer integrations

  Assessment Paper Tooling (v0.7):
  generate_blueprint()         — build a paper_blueprint from a CurriculumGraph
  validate_paper_coverage()    — audit an assessment_paper against a blueprint
  assemble_paper()             — greedy element selector satisfying a blueprint

  Revision & Knowledge Condensation (v0.7):
  get_top_concepts()           — rank concepts by priority for revision
  get_top_misconceptions()     — rank active misconceptions by remediation weight
  generate_study_plan()        — time-bounded study plan from mastery view
  StudyPlan / StudyTopic       — result containers

  Adaptive Remediation & Paths (v0.7):
  trace_prerequisite_failure_root() — find root cause of a prerequisite gap
  select_next_element()             — pick the best next element for a learner
  generate_hint()                   — derive a targeted hint from element metadata
  RemediationPath / HintResult      — result containers

  Spaced Repetition (v0.7 — SM-2):
  update_review_schedule()     — SM-2 update after a review event
  get_due_elements()           — elements due for review on a given date
  get_schedule_summary()       — aggregate stats across the schedule
  SpacedRepetitionSchedule / SpacedRepetitionRecord — state containers
"""

from .registry import ElementRegistry, ElementSpec, FieldSpec
from .validator import validate_lesson
from .prompt import format_prompt_docs
from .export_schema import get_all_schemas
from .curriculum import CurriculumGraph, ConceptNode, SkillNode, MisconceptionNode, validate_curriculum
from .learner_state import LearnerState, ConceptState, SkillState, MisconceptionState, validate_learner_state
from .transition_engine import apply_telemetry_event, default_decay_fn, DEFAULT_ENGINE_CONFIG
from .mastery_projection import MasteryGraphView, ConceptMasteryInfo
from .blueprint_engine import (
    generate_blueprint,
    validate_paper_coverage,
    assemble_paper,
    DEFAULT_COGNITIVE_WEIGHTS,
)
from .revision_engine import (
    get_top_concepts,
    get_top_misconceptions,
    generate_study_plan,
    StudyPlan,
    StudyTopic,
    VALID_MODES as VALID_REVISION_MODES,
)
from .remediation_engine import (
    trace_prerequisite_failure_root,
    select_next_element,
    generate_hint,
    RemediationPath,
    HintResult,
)
from .spaced_repetition import (
    update_review_schedule,
    get_due_elements,
    get_schedule_summary,
    SpacedRepetitionSchedule,
    SpacedRepetitionRecord,
)
from .constants import SCHEMA_VERSION, DEFAULT_MASTERY_THRESHOLD

__all__ = [
    # Core schema
    "ElementRegistry",
    "ElementSpec",
    "FieldSpec",
    "validate_lesson",
    "format_prompt_docs",
    "get_all_schemas",
    # Curriculum
    "CurriculumGraph",
    "ConceptNode",
    "SkillNode",
    "MisconceptionNode",
    "validate_curriculum",
    # Learner state
    "LearnerState",
    "ConceptState",
    "SkillState",
    "MisconceptionState",
    "validate_learner_state",
    # Transition engine
    "apply_telemetry_event",
    "default_decay_fn",
    "DEFAULT_ENGINE_CONFIG",
    # Mastery projection
    "MasteryGraphView",
    "ConceptMasteryInfo",
    # Assessment paper tooling
    "generate_blueprint",
    "validate_paper_coverage",
    "assemble_paper",
    "DEFAULT_COGNITIVE_WEIGHTS",
    # Revision engine
    "get_top_concepts",
    "get_top_misconceptions",
    "generate_study_plan",
    "StudyPlan",
    "StudyTopic",
    "VALID_REVISION_MODES",
    # Remediation engine
    "trace_prerequisite_failure_root",
    "select_next_element",
    "generate_hint",
    "RemediationPath",
    "HintResult",
    # Spaced repetition
    "update_review_schedule",
    "get_due_elements",
    "get_schedule_summary",
    "SpacedRepetitionSchedule",
    "SpacedRepetitionRecord",
    # Constants
    "SCHEMA_VERSION",
    "DEFAULT_MASTERY_THRESHOLD",
]
