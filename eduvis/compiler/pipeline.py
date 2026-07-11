"""EduVis Compiler Pipeline Core (v1.0)"""

import time
from typing import Any, Dict, List, Optional
from eduvis.core.curriculum import CurriculumGraph


class CompilationContext:
    def __init__(self):
        self.syllabus_text: Optional[str] = None
        self.curriculum_file: Optional[str] = None
        self.curriculum_graph: Optional[CurriculumGraph] = None
        self.lessons: Dict[str, Dict[str, Any]] = {}  # lesson_id -> lesson YAML data dict
        self.assessment_blueprints: Dict[str, Dict[str, Any]] = {}
        self.assessment_papers: Dict[str, Dict[str, Any]] = {}
        self.presentations: Dict[str, Dict[str, Any]] = {}  # lesson_id -> presentation data dict

        self.logs: List[str] = []
        self.errors: List[str] = []
        self.stages_executed: List[str] = []

    def log(self, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")

    def add_error(self, error: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.errors.append(f"[{timestamp}] ERROR: {error}")


class CompilerStage:
    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def description(self) -> str:
        raise NotImplementedError

    def run(self, context: CompilationContext) -> None:
        raise NotImplementedError


class CompilerPipeline:
    def __init__(self):
        self.stages: List[CompilerStage] = []

    def add_stage(self, stage: CompilerStage) -> None:
        self.stages.append(stage)

    def run(self, context: CompilationContext) -> CompilationContext:
        context.log("Initiating EduVis v1.0 Curriculum Compiler Pipeline...")

        for stage in self.stages:
            context.log(f"Running stage: {stage.name} - {stage.description}")
            start_time = time.perf_counter()
            try:
                stage.run(context)
                context.stages_executed.append(stage.name)
                elapsed = time.perf_counter() - start_time
                context.log(f"Stage {stage.name} completed successfully in {elapsed:.4f}s.")
            except Exception as e:  # pylint: disable=broad-exception-caught
                elapsed = time.perf_counter() - start_time
                err_msg = f"Stage {stage.name} failed after {elapsed:.4f}s: {e}"
                context.add_error(err_msg)
                context.log(err_msg)
                # Fail fast on compilation error
                break

        if context.errors:
            context.log("Compilation FAILED.")
        else:
            context.log("Compilation completed successfully.")

        return context
