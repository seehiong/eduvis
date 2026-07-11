"""EduVis Lesson Planner Compiler Stage (v1.0)"""

from typing import List, Optional
import yaml
from eduvis.compiler.pipeline import CompilerStage, CompilationContext
from eduvis.compiler.qa_engine import QAEngine
from eduvis.core.generator import GraphLessonGenerator


class LessonPlanner(CompilerStage):
    def __init__(self, concept_codes: Optional[List[str]] = None):
        self.concept_codes = concept_codes

    @property
    def name(self) -> str:
        return "LessonPlanner"

    @property
    def description(self) -> str:
        return "Generates progressive lesson steps and selects scaffolding depth from CurriculumGraph"

    def run(self, context: CompilationContext) -> None:
        if not context.curriculum_graph:
            raise ValueError("CurriculumGraph must be compiled before running LessonPlanner.")

        target_concepts = self.concept_codes
        if not target_concepts:
            target_concepts = getattr(context, "lesson_concepts", None)

        if not target_concepts:
            # Fallback to all concepts in the graph
            target_concepts = list(context.curriculum_graph.concepts.keys())

        if not target_concepts:
            raise ValueError("No target concept codes specified for lesson generation.")

        context.log(f"Generating lesson for concepts: {', '.join(target_concepts)}")

        generator = GraphLessonGenerator(context.curriculum_graph)
        lesson_yaml_str = generator.generate(target_concepts)
        lesson_data = yaml.safe_load(lesson_yaml_str)

        # Validate using QAEngine
        errors = QAEngine.validate_lesson_document(lesson_data)
        if errors:
            context.log(f"Lesson validation details: {errors}")
            critical_errors = [e for e in errors if e.startswith("ERROR")]
            if critical_errors:
                raise ValueError(f"Lesson validation failed with critical errors: {critical_errors}")

        lesson_id = lesson_data.get("lesson", {}).get("title", "generated_lesson").lower().replace(" ", "_")
        context.lessons[lesson_id] = lesson_data
        context.log(f"Lesson '{lesson_id}' successfully generated and validated.")
