"""
Pydantic Intermediate Representation (IR) models for generation requests.
"""

from typing import List, Dict
from pydantic import BaseModel, Field


class AssessmentObjectiveAlloc(BaseModel):
    """Distribution of assessment objectives across the paper."""
    AO1_recall: float = Field(0.4, description="Weight for direct recall and basic application")
    AO2_analysis: float = Field(0.4, description="Weight for mathematical reasoning and multi-step problem solving")
    AO3_synthesis: float = Field(0.2, description="Weight for novel context synthesis and proof")


class GenerationIntent(BaseModel):
    """
    Intermediate Representation (IR) produced by LLM intent interpretation.
    EduVis deterministic engines use this IR to validate constraints, check prerequisites,
    and assemble complete EduVis specifications.
    """
    subject: str = Field("mathematics", description="Subject name (e.g. mathematics, physics)")
    level: str = Field("Secondary 1", description="Grade or educational level")
    topic: str = Field("negative_numbers", description="Primary topic identifier")

    target_concepts: List[str] = Field(default_factory=list, description="Target curriculum concept codes")
    prerequisites: List[str] = Field(default_factory=list, description="Explicit prerequisite concept codes")
    misconceptions: List[str] = Field(default_factory=list, description="Misconception codes to address or test")

    difficulty_target: str = Field("medium", description="Target difficulty level (easy, medium, hard, adaptive)")
    total_marks: int = Field(60, description="Total paper mark budget")
    question_count: int = Field(10, description="Target number of questions")

    objective_distribution: AssessmentObjectiveAlloc = Field(default_factory=AssessmentObjectiveAlloc)
    diagnostic_ratio: float = Field(0.2, description="Percentage of questions reserved for misconception diagnostics")

    constraints: Dict[str, str] = Field(default_factory=dict, description="Additional custom constraints")
