"""
EduVis Core Tool Wrappers for Agent Consumption.
"""

from .curriculum_tools import inspect_curriculum, check_prerequisites
from .paper_tools import assemble_paper_from_intent
from .validator_tools import validate_generated_spec

__all__ = [
    "inspect_curriculum",
    "check_prerequisites",
    "assemble_paper_from_intent",
    "validate_generated_spec",
]
