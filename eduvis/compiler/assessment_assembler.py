"""EduVis Assessment Assembler Compiler Stage (v1.0)"""

from typing import Any, Dict, List, Optional
from eduvis.compiler.pipeline import CompilerStage, CompilationContext
from eduvis.core.blueprint_engine import generate_blueprint, assemble_paper


class AssessmentAssembler(CompilerStage):
    def __init__(
        self,
        total_marks: int = 20,
        title: str = "Assembled Test Paper",
        cognitive_weights: Optional[Dict[str, float]] = None,
        available_elements: Optional[List[Dict[str, Any]]] = None,
    ):
        self.total_marks = total_marks
        self.title = title
        self.cognitive_weights = cognitive_weights
        self.available_elements = available_elements or []

    @property
    def name(self) -> str:
        return "AssessmentAssembler"

    @property
    def description(self) -> str:
        return "Blueprints exam specifications and selects questions aligning to skills"

    def run(self, context: CompilationContext) -> None:
        if not context.curriculum_graph:
            raise ValueError("CurriculumGraph must be compiled before running AssessmentAssembler.")

        context.log(f"Generating assessment blueprint for {self.total_marks} marks...")
        blueprint = generate_blueprint(context.curriculum_graph, self.total_marks, self.cognitive_weights)
        context.assessment_blueprints[self.title] = blueprint

        # Use explicitly provided pool, or fall back to extracting elements from compiled lessons
        pool = list(self.available_elements)
        for lesson in context.lessons.values():
            content = lesson.get("content") or []
            for item in content:
                if isinstance(item, dict) and item not in pool:
                    pool.append(item)

        if pool:
            context.log(f"Assembling paper '{self.title}' from a pool of {len(pool)} elements...")
            paper = assemble_paper(blueprint, pool, self.title)
            context.assessment_papers[self.title] = paper
            context.log(f"Assessment paper '{self.title}' compiled successfully.")
        else:
            context.log("No element pool available for assessment assembly; blueprint compiled only.")
