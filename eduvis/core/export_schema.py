"""
EduVis Core — JSON Schema export.

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
)
from .schemas.progression import VALID_PATTERNS, VALID_PEDAGOGY_FLAGS
from .schemas.relationships import VALID_TYPES

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
            "lesson": {
                "type": "object",
                "required": ["title"],
                "properties": {
                    "syllabus": {"type": "string"},
                    "topic": {"type": "string"},
                    "title": {"type": "string"},
                    "concepts": {"type": "array", "items": {"type": "string"}, "description": "Target concepts for the lesson."},
                },
                "additionalProperties": True,
            },
            "progression": {"$ref": "progression.schema.json"},
            "content": {
                "type": "array",
                "items": element,
                "minItems": 1,
            },
        },
        "additionalProperties": False,
    }


def get_all_schemas() -> dict[str, dict]:
    """Return all EduVis JSON Schemas keyed by pillar name."""
    return {
        "placement": placement_schema(),
        "actions": actions_schema(),
        "relationships": relationships_schema(),
        "progression": progression_schema(),
        "lesson": lesson_schema(),
    }
