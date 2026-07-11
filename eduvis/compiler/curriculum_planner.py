"""EduVis Curriculum Planner Compiler Stage (v1.0)"""

from typing import Any, Dict
import yaml
from eduvis.compiler.pipeline import CompilerStage, CompilationContext
from eduvis.compiler.qa_engine import QAEngine
from eduvis.core.curriculum import CurriculumGraph
from eduvis.core.constants import SCHEMA_VERSION


class CurriculumPlanner(CompilerStage):
    @property
    def name(self) -> str:
        return "CurriculumPlanner"

    @property
    def description(self) -> str:
        return "Compiles standard syllabus structures into a validated CurriculumGraph"

    def run(self, context: CompilationContext) -> None:
        data: Dict[str, Any] = {}

        if context.curriculum_file:
            context.log(f"Loading curriculum graph from file: {context.curriculum_file}")
            with open(context.curriculum_file, "r", encoding="utf-8") as f:
                raw_data = yaml.safe_load(f)
                if isinstance(raw_data, dict):
                    data = raw_data
        elif context.syllabus_text:
            context.log("Parsing syllabus text...")
            raw_data = yaml.safe_load(context.syllabus_text)
            if isinstance(raw_data, dict):
                data = raw_data
        else:
            raise ValueError("No syllabus_text or curriculum_file provided in CompilationContext.")

        if not data:
            raise ValueError("Curriculum data is empty or invalid.")

        # Set default schema version if missing
        if "schema_version" not in data:
            data["schema_version"] = SCHEMA_VERSION

        # Validate with QAEngine
        errors = QAEngine.validate_curriculum_document(data)
        if errors:
            raise ValueError(f"Curriculum validation errors found: {errors}")

        # Build CurriculumGraph object
        graph = CurriculumGraph.from_dict(data)
        context.curriculum_graph = graph
        context.log("CurriculumGraph successfully compiled and validated.")
