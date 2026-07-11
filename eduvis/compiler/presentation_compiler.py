"""EduVis Presentation Compiler Stage (v1.0)"""

from typing import Any, Dict, List
from eduvis.compiler.pipeline import CompilerStage, CompilationContext
from eduvis.core.constants import SCHEMA_VERSION


class PresentationCompiler(CompilerStage):
    @property
    def name(self) -> str:
        return "PresentationCompiler"

    @property
    def description(self) -> str:
        return "Compiles educational meaning with viewport definitions, timings, and narration sidecars"

    def run(self, context: CompilationContext) -> None:
        if not context.lessons:
            raise ValueError("No compiled lessons found. Run LessonPlanner before PresentationCompiler.")

        for lesson_id, lesson in context.lessons.items():
            context.log(f"Compiling presentation layout for lesson '{lesson_id}'...")

            content = lesson.get("content") or []
            slides: List[Dict[str, Any]] = []

            for idx, item in enumerate(content):
                if not isinstance(item, dict):
                    continue
                item_id = item.get("id") or f"element_{idx}"
                item_type = item.get("type") or "unknown"

                # Derive narration from text fields
                narration = ""
                if "caption" in item and isinstance(item["caption"], str):
                    narration = item["caption"]
                elif "text" in item and isinstance(item["text"], str):
                    narration = item["text"]
                elif "question" in item and isinstance(item["question"], str):
                    narration = item["question"]
                elif "items" in item and isinstance(item["items"], list) and item["items"]:
                    first_item = item["items"][0]
                    if isinstance(first_item, dict) and "text" in first_item:
                        narration = first_item["text"]

                slide = {
                    "id": f"slide_{item_id}",
                    "visible_items": [item_id],
                    "viewport": {
                        "center": [0, 0],
                        "zoom": 1.0
                    },
                    "duration": 5.0,
                    "narration": narration or f"This slide presents the {item_type} element."
                }
                slides.append(slide)

            presentation_data = {
                "schema_version": SCHEMA_VERSION,
                "slides": slides
            }

            # Embed the presentation inline in the lesson document
            lesson["presentation"] = presentation_data
            context.presentations[lesson_id] = presentation_data
            context.log(f"Presentation layout compiled inline for lesson '{lesson_id}'.")
