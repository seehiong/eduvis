"""EduVis — educational content schema."""

__version__ = "0.6.0"

from .core import (
    ElementRegistry,
    ElementSpec,
    FieldSpec,
    validate_lesson,
    format_prompt_docs,
    get_all_schemas,
    CurriculumGraph,
    ConceptNode,
    SkillNode,
    MisconceptionNode,
    validate_curriculum,
    SCHEMA_VERSION,
)

__all__ = [
    "__version__",
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
    "SCHEMA_VERSION",
]
