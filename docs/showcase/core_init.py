"""
EduVis Core — renderer-agnostic educational content schema.

Public API:
  ElementRegistry        — query element specs, generate prompt docs, validate fields
  validate_lesson()      — validate a complete lesson document (all five pillars)
  format_prompt_docs()   — full five-pillar vocabulary for LLM system prompts
"""

from .registry import ElementRegistry, ElementSpec, FieldSpec
from .validator import validate_lesson
from .prompt import format_prompt_docs
from .export_schema import get_all_schemas
from .curriculum import CurriculumGraph, ConceptNode, SkillNode, MisconceptionNode, validate_curriculum

__all__ = [
    "ElementRegistry",
    "ElementSpec",
    "FieldSpec",
    "validate_lesson",
    "format_prompt_docs",
    "get_all_schemas",
    "CurriculumGraph",
    "ConceptNode",
    "SkillNode",
    "MisconceptionNode",
    "validate_curriculum",
]
