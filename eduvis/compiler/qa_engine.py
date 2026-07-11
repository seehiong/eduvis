"""EduVis Compiler QA & Validation Engine (v1.0)"""

from typing import Any, Dict, List
from eduvis.core.curriculum import CurriculumGraph, validate_curriculum
from eduvis.core.validator import validate_lesson


class QAEngine:
    @staticmethod
    def validate_curriculum_document(curriculum_data: Dict[str, Any]) -> List[str]:
        """Validate the curriculum schema structure and consistency."""
        return validate_curriculum(curriculum_data)

    @staticmethod
    def validate_lesson_document(lesson_data: Dict[str, Any]) -> List[str]:
        """Validate the lesson schema structure, phase sequences, and pedagogical guidelines."""
        return validate_lesson(lesson_data)

    @staticmethod
    def _validate_element_concepts(item_id: str, item_concepts: Any, curriculum_concepts: set[str]) -> List[str]:
        errors = []
        if isinstance(item_concepts, list):
            for c in item_concepts:
                if c not in curriculum_concepts:
                    errors.append(f"ERROR: Element '{item_id}' references concept '{c}' which is missing from the curriculum graph.")
        elif isinstance(item_concepts, dict):
            for c in item_concepts:
                if c not in curriculum_concepts:
                    errors.append(f"ERROR: Element '{item_id}' mapping references concept '{c}' which is missing from the curriculum graph.")
        return errors

    @staticmethod
    def validate_concept_references(curriculum_graph: CurriculumGraph, lesson_data: Dict[str, Any]) -> List[str]:
        """
        Verify that all concepts declared in the lesson and tagged on content elements
        exist within the curriculum graph.
        """
        errors = []
        curriculum_concepts = set(curriculum_graph.concepts.keys())

        # Check lesson-declared concepts
        lesson = lesson_data.get("lesson") or {}
        lesson_concepts = lesson.get("concepts") or []
        for c in lesson_concepts:
            if c not in curriculum_concepts:
                errors.append(f"ERROR: Concept '{c}' declared in lesson metadata does not exist in the curriculum graph.")

        # Check content element concepts
        content = lesson_data.get("content") or []
        for idx, item in enumerate(content):
            if not isinstance(item, dict):
                continue
            item_id = item.get("id") or f"element_{idx}"
            item_concepts = item.get("concepts")
            errors.extend(QAEngine._validate_element_concepts(item_id, item_concepts, curriculum_concepts))

        return errors
