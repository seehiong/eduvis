"""
State definitions for LangGraph educational generation graph.
"""

from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
from .intent import GenerationIntent


class AgentGraphState(TypedDict, total=False):
    """
    State object passed between nodes in the Educational Generation Graph.
    """
    # Raw user request
    user_prompt: str
    curriculum_yaml: str

    # Parsed Intent IR
    intent: Optional[GenerationIntent]

    # EduVis Core enriched context
    resolved_concepts: List[Dict[str, Any]]
    resolved_prerequisites: List[str]
    curriculum_graph_context: Dict[str, Any]

    # Generated candidate items & assembled specification
    candidate_questions: List[Dict[str, Any]]
    assembled_yaml: str

    # Validation status & feedback loop
    is_valid: bool
    validation_errors: List[str]
    critique_history: List[str]
    retry_count: int

    # LLM call diagnostics (preserved across retries)
    raw_llm_response: Optional[str]
    llm_error: Optional[str]

    # Final output status
    status: str  # "success", "retry", "failed"
