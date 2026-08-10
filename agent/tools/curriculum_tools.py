"""
Curriculum Graph inspection tools for agent orchestration.
Wraps EduVis Core curriculum engines.
"""

from typing import Dict, List, Any
from eduvis.core.curriculum import CurriculumGraph


def inspect_curriculum(curriculum_yaml: str) -> Dict[str, Any]:
    """
    Parses a curriculum specification YAML and extracts concepts, skills,
    misconceptions, and dependency DAG relationships.
    """
    try:
        graph = CurriculumGraph.from_yaml(curriculum_yaml)
        concepts = []
        for code, node in graph.concepts.items():
            concepts.append({
                "code": code,
                "name": getattr(node, "name", code),
                "description": getattr(node, "description", ""),
                "prerequisites": list(graph.get_prerequisites(code)),
                "dependents": list(graph.get_dependents(code)),
            })
        return {
            "status": "success",
            "concept_count": len(concepts),
            "concepts": concepts,
        }
    except Exception as err:
        return {
            "status": "error",
            "message": str(err),
            "concepts": [],
        }


def check_prerequisites(curriculum_yaml: str, target_concept_codes: List[str]) -> Dict[str, Any]:
    """
    Checks that all prerequisites for a list of target concepts are satisfied
    within the curriculum graph.
    """
    try:
        graph = CurriculumGraph.from_yaml(curriculum_yaml)
        prereqs = set()
        missing = set()

        for code in target_concept_codes:
            if code in graph.concepts:
                for p in graph.get_prerequisites(code):
                    prereqs.add(p)
            else:
                missing.add(code)

        return {
            "status": "success",
            "target_concepts": target_concept_codes,
            "required_prerequisites": sorted(list(prereqs)),
            "unknown_concepts": sorted(list(missing)),
        }
    except Exception as err:
        return {
            "status": "error",
            "message": str(err),
            "required_prerequisites": [],
        }
