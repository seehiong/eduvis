import yaml
from eduvis.core.curriculum import CurriculumGraph
from eduvis.core.constants import SCHEMA_VERSION

class GraphLessonGenerator:
    # pylint: disable=too-few-public-methods
    def __init__(self, curriculum: CurriculumGraph):
        self.curriculum = curriculum

    def generate(self, concept_codes: list[str]) -> str:
        """
        Generates a basic lesson YAML skeleton based on the given concepts.
        """

        doc = {
            "schema_version": SCHEMA_VERSION,
            "curriculum": {
                "code": "generated",
                "topic": "generated_topic",
                "objectives": concept_codes
            },
            "lesson": {
                "title": f"Generated Lesson for {', '.join(concept_codes)}",
                "concepts": concept_codes
            },
            "progression": {
                "pattern": "direct_instruction",
                "pedagogy": {
                    "confidence_first": False,
                    "explain_why": False,
                    "no_skipped_steps": False
                },
                "phases": [
                    {"phase": "hook"},
                    {"phase": "explain", "purpose": "conceptual_model"},
                    {"phase": "guided_practice"}
                ]
            },
            "content": []
        }

        # For each concept, generate a standard sequence
        for code in concept_codes:
            node = self.curriculum.concepts.get(code)
            if not node:
                continue

            # Hook phase
            doc["content"].append({
                "type": "fact_boxes",
                "id": f"hook_{code}",
                "phase": "hook",
                "memory_role": "anchor",
                "concepts": [code],
                "placement": {
                    "lesson_phase": "hook",
                    "memory_role": "anchor"
                },
                "items": [
                    {"text": f"Let's explore {node.name}.", "border_color": "blue"}
                ]
            })

            # Explain phase
            doc["content"].append({
                "type": "fact_boxes",
                "id": f"explain_{code}",
                "phase": "explain",
                "memory_role": "fact",
                "concepts": [code],
                "placement": {
                    "lesson_phase": "explain",
                    "memory_role": "example",
                    "purpose": "conceptual_model"
                },
                "items": [
                    {"text": node.description, "border_color": "cyan"}
                ]
            })

            # Guided practice
            doc["content"].append({
                "type": "short_answer",
                "id": f"guided_practice_{code}",
                "phase": "guided_practice",
                "concepts": [code],
                "placement": {
                    "lesson_phase": "guided_practice",
                    "memory_role": "example",
                    "purpose": "worked_example"
                },
                "actions": {
                    "conceptual": ["apply"]
                },
                "question": f"What is a key feature of {node.name}?",
                "concept": code,
                "answer": f"key feature of {node.name}",
                "marking_scheme": [
                    {"step": "1", "type": "M", "pattern": ".*", "marks": 1}
                ]
            })

        return yaml.dump(doc, sort_keys=False, default_flow_style=False, allow_unicode=True)
