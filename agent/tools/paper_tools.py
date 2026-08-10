"""
Paper Assembly and Assessment Blueprint tool wrappers for Agent consumption.
Wraps EduVis Core blueprint engine.
"""

from typing import Dict, Any, List
from eduvis.core.blueprint_engine import generate_blueprint, assemble_paper, validate_paper_coverage
from eduvis.core.curriculum import CurriculumGraph
from agent.schemas.intent import GenerationIntent


def assemble_paper_from_intent(
    curriculum_yaml: str,
    intent: GenerationIntent,
    candidate_elements: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Takes a GenerationIntent, generates a paper blueprint via EduVis Core,
    and runs greedy paper assembly over candidate question elements.
    """
    try:
        graph = CurriculumGraph.from_yaml(curriculum_yaml)

        # Convert intent objective distribution to cognitive weights
        cognitive_weights = {
            "conceptual_understanding": intent.objective_distribution.AO1_recall,
            "procedural_fluency": intent.objective_distribution.AO2_analysis,
            "application": intent.objective_distribution.AO3_synthesis,
            "reasoning": 0.0,
        }

        # 1. Generate EduVis paper blueprint
        blueprint = generate_blueprint(
            curriculum=graph,
            total_marks=intent.total_marks,
            cognitive_weights=cognitive_weights
        )

        # 2. Assemble paper using EduVis Core greedy assembler
        marks_per_item = intent.total_marks // intent.question_count if (intent and intent.question_count > 0) else 5
        assembled_paper = assemble_paper(
            blueprint=blueprint,
            available_elements=candidate_elements,
            title=f"{intent.topic.title()} Assessment Paper",
            marks_per_element=marks_per_item
        )

        # 3. Audit paper coverage against blueprint
        # validate_paper_coverage expects a {element_id: element_dict} mapping, not a list
        elements_by_id = {str(el.get("id", idx)): el for idx, el in enumerate(candidate_elements)}
        warnings = validate_paper_coverage(assembled_paper, blueprint, elements_by_id)

        return {
            "status": "success",
            "assembled_paper": assembled_paper,
            "blueprint": blueprint,
            "coverage_warnings": warnings,
            "is_valid": len(warnings) == 0
        }
    except Exception as err:
        return {
            "status": "error",
            "message": str(err),
            "assembled_paper": None,
            "is_valid": False
        }
