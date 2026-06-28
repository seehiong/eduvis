"""
EduVis Core — JSON Schema export.

JSON Schema export is a first-class API contract for external consumers to integrate
and validate content models downstream.

Derives all schemas from the same constants used by the Python validator so
they are always in sync. Call get_all_schemas() to get a name→dict mapping,
or each individual function for a single pillar.
"""

from __future__ import annotations

from .schemas.actions import VALID_CONCEPTUAL, VALID_PROCEDURAL
from .schemas.placement import (
    VALID_DIFFICULTY,
    VALID_LAYOUT_ZONES,
    VALID_MEMORY_ROLES,
    VALID_PHASES,
    VALID_PURPOSES,
    VALID_VISUAL_WEIGHTS,
    VALID_ASSESSMENT_OBJECTIVES,
    VALID_INTENTS,
    VALID_SCAFFOLDING_LEVELS,
)
from .schemas.progression import VALID_PATTERNS, VALID_PEDAGOGY_FLAGS
from .schemas.relationships import VALID_TYPES
from .schemas.presentation import VALID_ADVANCE_MODES, VALID_ACTIONS
from .constants import SCHEMA_VERSION

_BASE = "https://eduvis.dev/schemas"
_DRAFT = "https://json-schema.org/draft/2020-12/schema"


def placement_schema() -> dict:
    return {
        "$schema": _DRAFT,
        "$id": f"{_BASE}/placement.schema.json",
        "title": "EduVis Placement",
        "description": "Where an element lives in the lesson and in long-term memory.",
        "type": "object",
        "required": ["lesson_phase", "memory_role"],
        "properties": {
            "lesson_phase": {
                "type": "string",
                "enum": sorted(VALID_PHASES),
                "description": "Where in the instructional sequence this element sits.",
            },
            "memory_role": {
                "type": "string",
                "enum": sorted(VALID_MEMORY_ROLES),
                "description": "What role this element plays in long-term retention.",
            },
            "difficulty": {
                "type": "string",
                "enum": sorted(VALID_DIFFICULTY),
                "description": "Difficulty level; meaningful in practice and challenge phases.",
            },
            "purpose": {
                "type": "string",
                "enum": sorted(VALID_PURPOSES),
                "description": "Instructional purpose within the phase.",
            },
            "layout_zone": {
                "type": "string",
                "enum": sorted(VALID_LAYOUT_ZONES),
                "description": "Where on the rendered slide this element appears.",
            },
            "visual_weight": {
                "type": "string",
                "enum": sorted(VALID_VISUAL_WEIGHTS),
                "description": "Whether this element is the primary focal point.",
            },
            "assessment_objective": {
                "type": "string",
                "enum": sorted(VALID_ASSESSMENT_OBJECTIVES),
                "description": "The pedagogical skill target (only valid on assessment elements).",
            },
            "pedagogical_intent": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "enum": sorted(VALID_INTENTS),
                        "description": "The target pedagogical intent.",
                    },
                    "scaffolding_level": {
                        "type": "string",
                        "enum": sorted(VALID_SCAFFOLDING_LEVELS),
                        "description": "The level of instructional support.",
                    },
                },
                "additionalProperties": False,
                "description": "Pedagogical intent metadata to guide content generation and support.",
            },
        },
        "additionalProperties": False,
    }


def actions_schema() -> dict:
    action_item = {
        "oneOf": [
            {
                "type": "string",
                "description": "Bare action name (e.g. 'simplify').",
            },
            {
                "type": "object",
                "description": "Action with a parameter (e.g. {substitute: {from: x, to: 3}}).",
                "minProperties": 1,
                "maxProperties": 1,
            },
        ]
    }
    return {
        "$schema": _DRAFT,
        "$id": f"{_BASE}/actions.schema.json",
        "title": "EduVis Actions",
        "description": "What the element asks the student to do.",
        "type": "object",
        "properties": {
            "conceptual": {
                "type": "array",
                "description": "Cognitive actions (compare, predict, identify, retrieve, apply).",
                "items": action_item,
            },
            "procedural": {
                "type": "array",
                "description": "Step-by-step transformation actions (substitute, simplify, calculate, round).",
                "items": action_item,
            },
        },
        "additionalProperties": False,
        "$comment": (
            f"Valid conceptual actions: {', '.join(sorted(VALID_CONCEPTUAL))}. "
            f"Valid procedural actions: {', '.join(sorted(VALID_PROCEDURAL))}."
        ),
    }


def relationships_schema() -> dict:
    id_list = {"type": "array", "items": {"type": "string"}, "description": "Element IDs."}
    return {
        "$schema": _DRAFT,
        "$id": f"{_BASE}/relationships.schema.json",
        "title": "EduVis Relationships",
        "description": "How an element relates to other elements within a lesson.",
        "type": "object",
        "properties": {rel: id_list for rel in sorted(VALID_TYPES)},
        "additionalProperties": False,
    }


def progression_schema() -> dict:
    phase_entry = {
        "type": "object",
        "required": ["phase"],
        "properties": {
            "phase": {"type": "string", "enum": sorted(VALID_PHASES)},
            "difficulty": {"type": "string", "enum": sorted(VALID_DIFFICULTY)},
            "purpose": {"type": "string", "enum": sorted(VALID_PURPOSES)},
            "count": {"type": "integer", "minimum": 1},
        },
        "additionalProperties": False,
    }
    pedagogy_props = {flag: {"type": "boolean"} for flag in sorted(VALID_PEDAGOGY_FLAGS)}
    return {
        "$schema": _DRAFT,
        "$id": f"{_BASE}/progression.schema.json",
        "title": "EduVis Progression",
        "description": "The named instructional flow of the whole lesson.",
        "type": "object",
        "required": ["pattern"],
        "properties": {
            "pattern": {
                "type": "string",
                "enum": sorted(VALID_PATTERNS),
                "description": "Named teaching pattern governing phase sequence.",
            },
            "pedagogy": {
                "type": "object",
                "description": "Pedagogy flags that the validator enforces.",
                "properties": pedagogy_props,
                "additionalProperties": False,
            },
            "phases": {
                "type": "array",
                "description": "Ordered sequence of instructional phases.",
                "items": phase_entry,
            },
        },
        "additionalProperties": False,
    }


def presentation_schema() -> dict:
    step_item = {
        "type": "object",
        "required": ["index"],
        "properties": {
            "index": {"type": "integer", "minimum": 0},
            "visible_items": {
                "type": "array",
                "items": {"type": "integer", "minimum": 0},
                "description": "Subset of element items index to reveal.",
            },
            "auto_advance_after": {
                "type": "number",
                "minimum": 0,
                "description": "Seconds to wait before auto-advancing to next step.",
            },
            "caption": {
                "type": "string",
                "description": "Accessibility subtitle or narration text for this step.",
            },
            "audio_offset": {
                "type": "number",
                "minimum": 0,
                "description": "Seconds offset into the single slide audio file.",
            },
            "audio_file": {
                "type": ["string", "null"],
                "description": "Override audio file reference per step.",
            },
            "highlight": {
                "type": "object",
                "required": ["target", "style"],
                "properties": {
                    "target": {"type": "string"},
                    "style": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "viewport": {
                "type": "object",
                "properties": {
                    "zoom": {"type": "number", "minimum": 0},
                    "center": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2,
                    },
                },
                "additionalProperties": False,
            },
            "action": {
                "type": "string",
                "enum": sorted(VALID_ACTIONS),
            },
        },
        "additionalProperties": False,
    }

    reveal_entry = {
        "type": "object",
        "required": ["target", "steps"],
        "properties": {
            "target": {"type": "string", "description": "Element ID being revealed."},
            "steps": {"type": "array", "items": step_item},
        },
        "additionalProperties": False,
    }

    slide_entry = {
        "type": "object",
        "required": ["id"],
        "properties": {
            "id": {"type": "string", "description": "Slide ID mapping to content element ID."},
            "advance": {"type": "string", "enum": sorted(VALID_ADVANCE_MODES)},
            "duration": {"type": "number", "minimum": 0},
            "reveals": {"type": "array", "items": reveal_entry},
        },
        "additionalProperties": False,
    }

    return {
        "$schema": _DRAFT,
        "$id": f"{_BASE}/presentation.schema.json",
        "title": "EduVis Presentation",
        "description": "Visual sequencing, narration timing, and camera commands for presentation renderers.",
        "type": "object",
        "required": ["slides"],
        "properties": {
            "schema_version": {
                "type": "string",
                "enum": [SCHEMA_VERSION],
                "description": "The version of the EduVis schema used by this document.",
            },
            "slides": {"type": "array", "items": slide_entry},
        },
        "additionalProperties": False,
    }


def lesson_schema() -> dict:
    """Top-level lesson document schema. Element content fields are open (additionalProperties: true)
    because they vary by type; the Python validator handles element-level field checking."""
    element = {
        "type": "object",
        "required": ["id", "type", "placement"],
        "properties": {
            "id": {"type": "string", "description": "Unique identifier within the lesson."},
            "type": {"type": "string", "description": "EduVis element type (e.g. number_line)."},
            "placement": {"$ref": "placement.schema.json"},
            "actions": {"$ref": "actions.schema.json"},
            "relationships": {"$ref": "relationships.schema.json"},
            "concepts": {"type": "array", "items": {"type": "string"}, "description": "Concepts taught by this element."},
        },
        "additionalProperties": True,
    }
    return {
        "$schema": _DRAFT,
        "$id": f"{_BASE}/lesson.schema.json",
        "title": "EduVis Lesson",
        "description": "A complete EduVis lesson document.",
        "type": "object",
        "required": ["lesson", "progression", "content"],
        "properties": {
            "schema_version": {
                "type": "string",
                "enum": [SCHEMA_VERSION],
                "description": "The version of the EduVis schema used by this document.",
            },
            "curriculum": {
                "type": "object",
                "required": ["code", "topic"],
                "properties": {
                    "code": {"type": "string", "description": "Curriculum code (e.g. SEC-math-2027)."},
                    "topic": {"type": "string", "description": "Topic code (e.g. N1.6)."},
                    "concept": {"type": "string", "description": "Primary concept code or title."},
                    "learning_outcomes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Learning outcomes mapped to this lesson."
                    },
                    "requires": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Prerequisite concept or topic codes."
                    },
                    "supports": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Concept or topic codes supported by this lesson."
                    },
                    "remediated_by": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Concept or topic codes recommended to remediate gaps."
                    },
                    "assessment_targets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Assessment objectives/targets mapping."
                    },
                    "assessment_objectives": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Assessment objectives/targets mapping."
                    },
                },
                "additionalProperties": False,
            },
            "lesson": {
                "type": "object",
                "required": ["title"],
                "properties": {
                    "title": {"type": "string"},
                    "concepts": {"type": "array", "items": {"type": "string"}, "description": "Target concepts for the lesson."},
                },
                "additionalProperties": True,
            },
            "progression": {"$ref": "progression.schema.json"},
            "presentation": {"$ref": "presentation.schema.json"},
            "content": {
                "type": "array",
                "items": element,
                "minItems": 1,
            },
        },
        "additionalProperties": False,
    }


def assessment_event_schema() -> dict:
    return {
        "$schema": _DRAFT,
        "$id": f"{_BASE}/assessment_event.schema.json",
        "title": "EduVis Assessment Event",
        "description": "Telemetry event for tracking student attempts on assessment elements.",
        "type": "object",
        "required": [
            "student_id",
            "element_id",
            "attempt_number",
            "answer_submitted",
            "is_correct",
            "timestamp"
        ],
        "properties": {
            "student_id": {
                "type": "string",
                "description": "Unique identifier for the student."
            },
            "element_id": {
                "type": "string",
                "description": "Identifier of the assessment element."
            },
            "attempt_number": {
                "type": "integer",
                "minimum": 1,
                "description": "The 1-based attempt count for this student on this element."
            },
            "answer_submitted": {
                "type": "string",
                "description": "The raw option key or free-text response submitted by the student."
            },
            "is_correct": {
                "type": "boolean",
                "description": "Whether the student's answer was correct."
            },
            "misconception_detected": {
                "type": ["string", "null"],
                "description": "Code representing the detected misconception, if any."
            },
            "time_taken_seconds": {
                "type": "number",
                "minimum": 0,
                "description": "Time spent by the student on this attempt in seconds."
            },
            "timestamp": {
                "type": "string",
                "format": "date-time",
                "description": "ISO 8601 formatted timestamp of the event."
            }
        },
        "additionalProperties": False,
    }


def curriculum_schema() -> dict:
    concept_item = {
        "type": "object",
        "required": ["code", "name"],
        "properties": {
            "code": {"type": "string"},
            "name": {"type": "string"},
            "description": {"type": "string"},
            "exam_weight": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
        "additionalProperties": False,
    }
    skill_item = {
        "type": "object",
        "required": ["code", "name", "concept"],
        "properties": {
            "code": {"type": "string"},
            "name": {"type": "string"},
            "concept": {"type": "string"},
            "exam_weight": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
        "additionalProperties": False,
    }
    misconception_item = {
        "type": "object",
        "required": ["code", "name", "concept"],
        "properties": {
            "code": {"type": "string"},
            "name": {"type": "string"},
            "concept": {"type": "string"},
            "remediation_weight": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
        "additionalProperties": False,
    }
    dependency_item = {
        "type": "object",
        "required": ["from", "to"],
        "properties": {
            "from": {"type": "string"},
            "to": {"type": "string"},
            "type": {"type": "string", "enum": ["prerequisite", "support"]},
        },
        "additionalProperties": False,
    }
    return {
        "$schema": _DRAFT,
        "$id": f"{_BASE}/curriculum.schema.json",
        "title": "EduVis Curriculum Graph",
        "description": "A standalone master curriculum graph representing subject concepts, skills, misconceptions, and dependencies.",
        "type": "object",
        "required": ["concepts"],
        "properties": {
            "schema_version": {
                "type": "string",
                "enum": [SCHEMA_VERSION],
                "description": "The version of the EduVis schema used by this document.",
            },
            "concepts": {"type": "array", "items": concept_item},
            "skills": {"type": "array", "items": skill_item},
            "misconceptions": {"type": "array", "items": misconception_item},
            "dependencies": {"type": "array", "items": dependency_item},
        },
        "additionalProperties": False,
    }


def learner_state_schema() -> dict:
    return {
        "$schema": _DRAFT,
        "$id": f"{_BASE}/learner_state.schema.json",
        "title": "EduVis Learner State",
        "description": "Transient learner state mapping concept, skill, and misconception mastery levels.",
        "type": "object",
        "required": ["learner_id", "concepts"],
        "properties": {
            "schema_version": {
                "type": "string",
                "enum": [SCHEMA_VERSION],
                "description": "The version of the EduVis schema used by this document."
            },
            "learner_id": {
                "type": "string",
                "description": "Unique identifier for the student."
            },
            "last_updated": {
                "type": "string",
                "format": "date-time",
                "description": "ISO timestamp indicating when the state was last calculated."
            },
            "concepts": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "required": ["mastery"],
                    "properties": {
                        "mastery": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "Current mastery level of the concept."
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "Self-reported or student confidence."
                        }
                    },
                    "additionalProperties": False
                },
                "description": "Map of concept codes to mastery objects."
            },
            "skills": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "required": ["mastery"],
                    "properties": {
                        "mastery": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "Current mastery level of the skill."
                        }
                    },
                    "additionalProperties": False
                },
                "description": "Map of skill codes to mastery objects."
            },
            "misconceptions": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "required": ["state"],
                    "properties": {
                        "state": {
                            "type": "string",
                            "enum": ["active", "remediated"],
                            "description": "Status of the misconception."
                        },
                        "attempts": {
                            "type": "integer",
                            "minimum": 0,
                            "description": "Number of times this misconception was triggered."
                        }
                    },
                    "additionalProperties": False
                },
                "description": "Map of misconception codes to active/remediated states."
            }
        },
        "additionalProperties": False
    }


def telemetry_event_schema() -> dict:
    return {
        "$schema": _DRAFT,
        "$id": f"{_BASE}/telemetry_event.schema.json",
        "title": "EduVis Telemetry Event",
        "description": "Interaction telemetry event from the student player interface.",
        "type": "object",
        "required": ["event_id", "timestamp", "learner_id", "event_type", "payload"],
        "properties": {
            "event_id": {
                "type": "string",
                "description": "Unique identifier for this event."
            },
            "timestamp": {
                "type": "string",
                "format": "date-time",
                "description": "ISO timestamp indicating when the event occurred."
            },
            "learner_id": {
                "type": "string",
                "description": "Unique identifier for the student."
            },
            "event_type": {
                "type": "string",
                "enum": ["assessment_attempt", "lesson_reveal", "help_request"],
                "description": "Category of student interaction."
            },
            "payload": {
                "type": "object",
                "required": ["element_id"],
                "properties": {
                    "element_id": {
                        "type": "string",
                        "description": "The lesson element ID related to the action."
                    },
                    "answer_submitted": {
                        "type": "string",
                        "description": "Option key or text submitted."
                    },
                    "is_correct": {
                        "type": "boolean",
                        "description": "Correctness flag."
                    },
                    "misconception_detected": {
                        "type": ["string", "null"],
                        "description": "Detected misconception code, if any."
                    },
                    "time_taken_seconds": {
                        "type": "number",
                        "minimum": 0.0,
                        "description": "Duration spent on interaction."
                    }
                },
                "additionalProperties": True,
                "description": "Payload containing event-specific properties."
            }
        },
        "additionalProperties": False
    }


def assessment_paper_schema() -> dict:
    return {
        "$schema": _DRAFT,
        "$id": f"{_BASE}/assessment_paper.schema.json",
        "title": "EduVis Assessment Paper",
        "description": "Structure of an exam or formal quiz containing multiple assessment elements.",
        "type": "object",
        "required": ["title", "sections"],
        "properties": {
            "schema_version": {
                "type": "string",
                "enum": [SCHEMA_VERSION],
                "description": "The schema version used."
            },
            "title": {
                "type": "string",
                "description": "Title of the assessment paper."
            },
            "instructions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Student-facing instructions."
            },
            "time_limit_minutes": {
                "type": "integer",
                "minimum": 0,
                "description": "Duration of the exam in minutes."
            },
            "calculator": {
                "type": "string",
                "enum": ["allowed", "prohibited", "scientific_only"],
                "description": "Calculator usage policy."
            },
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "questions"],
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the section (e.g., Section A)."
                        },
                        "instructions": {
                            "type": "string",
                            "description": "Section-specific instructions."
                        },
                        "questions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["id"],
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "Reference to the element ID in lesson content or standalone content."
                                    },
                                    "marks": {
                                        "type": "integer",
                                        "minimum": 1,
                                        "description": "Allocated mark weight for this item."
                                    }
                                },
                                "additionalProperties": False
                            }
                        }
                    },
                    "additionalProperties": False
                }
            }
        },
        "additionalProperties": False
    }


def paper_blueprint_schema() -> dict:
    return {
        "$schema": _DRAFT,
        "$id": f"{_BASE}/paper_blueprint.schema.json",
        "title": "EduVis Assessment Blueprint",
        "description": "Assessment specifications targeting concept mastery and cognitive dimensions.",
        "type": "object",
        "required": ["total_marks", "targets"],
        "properties": {
            "schema_version": {
                "type": "string",
                "enum": [SCHEMA_VERSION]
            },
            "total_marks": {
                "type": "integer",
                "minimum": 1
            },
            "targets": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["type", "code", "weight"],
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["concept", "cognitive_skill"],
                            "description": "Dimension being targeted."
                        },
                        "code": {
                            "type": "string",
                            "description": "Concept code or cognitive skill name (e.g., reasoning)."
                        },
                        "weight": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "Proportional mark weight target."
                        }
                    },
                    "additionalProperties": False
                }
            }
        },
        "additionalProperties": False
    }


def get_all_schemas() -> dict[str, dict]:
    """
    Return all active EduVis JSON Schemas keyed by pillar name.

    This is a first-class API representing the core schemas for placement,
    actions, relationships, progression, lesson, presentation,
    assessment_event, curriculum, learner_state, telemetry_event,
    assessment_paper, and paper_blueprint.
    """
    return {
        "placement": placement_schema(),
        "actions": actions_schema(),
        "relationships": relationships_schema(),
        "progression": progression_schema(),
        "lesson": lesson_schema(),
        "presentation": presentation_schema(),
        "assessment_event": assessment_event_schema(),
        "curriculum": curriculum_schema(),
        "learner_state": learner_state_schema(),
        "telemetry_event": telemetry_event_schema(),
        "assessment_paper": assessment_paper_schema(),
        "paper_blueprint": paper_blueprint_schema(),
    }
