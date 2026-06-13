"""EduVis — educational content schema."""

__version__ = "0.1.1"

from .core import ElementRegistry, ElementSpec, FieldSpec, validate_lesson, format_prompt_docs, get_all_schemas

__all__ = [
    "__version__",
    "ElementRegistry",
    "ElementSpec",
    "FieldSpec",
    "validate_lesson",
    "format_prompt_docs",
    "get_all_schemas",
]

