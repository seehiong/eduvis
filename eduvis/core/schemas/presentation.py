"""Presentation schema validation for EduVis Core."""

from __future__ import annotations

from typing import Any

VALID_ADVANCE_MODES = frozenset({"manual", "auto"})
VALID_ACTIONS = frozenset({"pause", "resume"})


def validate(presentation: dict, known_ids: set[str]) -> list[str]:
    """
    Validate the presentation block.

    known_ids: all element IDs declared in the lesson (for referential integrity).
    Returns warning/error strings.
    """
    warnings: list[str] = []

    if not isinstance(presentation, dict):
        warnings.append("ERROR: [presentation] 'presentation' must be a mapping")
        return warnings

    # Validate schema version
    version = presentation.get("schema_version")
    if version is not None:
        if not isinstance(version, str):
            warnings.append(
                f"ERROR: [presentation:version] 'schema_version' must be a string, got {type(version).__name__}"
            )
        elif version != "0.5":
            warnings.append(
                f"ERROR: [presentation:version] unsupported schema version \"{version}\". Expected \"0.5\"."
            )

    # Validate top-level keys
    allowed_keys = {"schema_version", "slides"}
    for key in presentation:
        if key not in allowed_keys:
            warnings.append(
                f"ERROR: [presentation] unexpected key '{key}' in presentation block"
            )

    slides = presentation.get("slides")
    if slides is None:
        warnings.append("ERROR: [presentation] missing required 'slides' list")
        return warnings

    if not isinstance(slides, list):
        warnings.append("ERROR: [presentation] 'slides' must be a list")
        return warnings

    for slide_idx, slide in enumerate(slides):
        _validate_slide(slide_idx, slide, known_ids, warnings)

    return warnings


def _validate_slide(slide_idx: int, slide: dict, known_ids: set[str], warnings: list[str]) -> None:
    if not isinstance(slide, dict):
        warnings.append(f"ERROR: [presentation] slides[{slide_idx}] must be a mapping")
        return

    slide_id = slide.get("id")
    if not isinstance(slide_id, str) or not slide_id.strip():
        warnings.append(f"ERROR: [presentation] slides[{slide_idx}] missing required non-empty 'id' string")
        return

    if slide_id not in known_ids:
        warnings.append(
            f"ERROR: [presentation:slide_{slide_id}] slide ID '{slide_id}' references unknown content element ID"
        )

    # Optional slide-level fields
    advance = slide.get("advance")
    if advance is not None and advance not in VALID_ADVANCE_MODES:
        warnings.append(
            f"ERROR: [presentation:slide_{slide_id}] 'advance' must be one of "
            f"{sorted(VALID_ADVANCE_MODES)}, got {repr(advance)}"
        )

    duration = slide.get("duration")
    if duration is not None:
        if not isinstance(duration, (int, float)) or duration < 0:
            warnings.append(
                f"ERROR: [presentation:slide_{slide_id}] 'duration' must be a non-negative number, got {repr(duration)}"
            )

    reveals = slide.get("reveals")
    if reveals is not None:
        if not isinstance(reveals, list):
            warnings.append(f"ERROR: [presentation:slide_{slide_id}] 'reveals' must be a list")
        else:
            for reveal_idx, reveal in enumerate(reveals):
                _validate_reveal(slide_id, reveal_idx, reveal, known_ids, warnings)

    _validate_slide_svg(slide_id, slide, warnings)


def _validate_slide_svg(slide_id: str, slide: dict, warnings: list[str]) -> None:
    """Validate optional svg_ref and svg_inline fields on a slide."""
    svg_ref = slide.get("svg_ref")
    svg_inline = slide.get("svg_inline")

    if svg_ref is not None:
        if not isinstance(svg_ref, str) or not svg_ref.strip():
            warnings.append(
                f"ERROR: [presentation:slide_{slide_id}] 'svg_ref' must be a non-empty string path"
            )

    if svg_inline is not None:
        if not isinstance(svg_inline, str) or not svg_inline.strip():
            warnings.append(
                f"ERROR: [presentation:slide_{slide_id}] 'svg_inline' must be a non-empty string"
            )
        elif not svg_inline.strip().startswith("<svg"):
            warnings.append(
                f"WARN: [presentation:slide_{slide_id}] 'svg_inline' does not appear to start with '<svg'; "
                f"ensure it is valid SVG markup"
            )

    if svg_ref is not None and svg_inline is not None:
        if isinstance(svg_ref, str) and svg_ref.strip() and isinstance(svg_inline, str) and svg_inline.strip():
            warnings.append(
                f"WARN: [presentation:slide_{slide_id}] both 'svg_inline' and 'svg_ref' are set; "
                f"'svg_inline' takes precedence"
            )


def _validate_reveal(slide_id: str, reveal_idx: int, reveal: dict, known_ids: set[str], warnings: list[str]) -> None:
    if not isinstance(reveal, dict):
        warnings.append(f"ERROR: [presentation:slide_{slide_id}] reveals[{reveal_idx}] must be a mapping")
        return

    target = reveal.get("target")
    if not isinstance(target, str) or not target.strip():
        warnings.append(
            f"ERROR: [presentation:slide_{slide_id}] reveals[{reveal_idx}] missing required non-empty 'target' string"
        )
        return

    # Validate target refers to a known element
    if target not in known_ids and not any(target.startswith(k + "_") for k in known_ids):
        # Allow targets that reference nested parts
        pass

    steps = reveal.get("steps")
    if steps is None:
        warnings.append(
            f"ERROR: [presentation:slide_{slide_id}] reveal target '{target}' missing required 'steps' list"
        )
        return

    if not isinstance(steps, list):
        warnings.append(
            f"ERROR: [presentation:slide_{slide_id}] reveal target '{target}' 'steps' must be a list"
        )
        return

    for step_idx, step in enumerate(steps):
        _validate_step(slide_id, target, step_idx, step, warnings)


def _validate_step(slide_id: str, target: str, step_idx: int, step: dict, warnings: list[str]) -> None:
    if not isinstance(step, dict):
        warnings.append(
            f"ERROR: [presentation:slide_{slide_id}] reveal target '{target}' steps[{step_idx}] must be a mapping"
        )
        return

    index = step.get("index")
    if index is None or not isinstance(index, int) or index < 0:
        warnings.append(
            f"ERROR: [presentation:slide_{slide_id}] reveal target '{target}' steps[{step_idx}] missing required non-negative integer 'index'"
        )

    _validate_step_properties(slide_id, target, index, step, warnings)

    highlight = step.get("highlight")
    if highlight is not None:
        _validate_highlight(slide_id, target, index, highlight, warnings)

    viewport = step.get("viewport")
    if viewport is not None:
        _validate_viewport(slide_id, target, index, viewport, warnings)


def _validate_step_properties(slide_id: str, target: str, index: Any, step: dict, warnings: list[str]) -> None:
    visible_items = step.get("visible_items")
    if visible_items is not None:
        if not isinstance(visible_items, list):
            warnings.append(
                f"ERROR: [presentation:slide_{slide_id}] reveal target '{target}' step {index} 'visible_items' must be a list of integers"
            )
        else:
            for item in visible_items:
                if not isinstance(item, int) or item < 0:
                    warnings.append(
                        f"ERROR: [presentation:slide_{slide_id}] reveal target '{target}' step {index} 'visible_items' entry must be a non-negative integer, got {repr(item)}"
                    )

    _validate_step_audio_and_action(slide_id, target, index, step, warnings)


def _validate_step_audio_and_action(slide_id: str, target: str, index: Any, step: dict, warnings: list[str]) -> None:
    auto_advance_after = step.get("auto_advance_after")
    if auto_advance_after is not None:
        if not isinstance(auto_advance_after, (int, float)) or auto_advance_after < 0:
            warnings.append(
                f"ERROR: [presentation:slide_{slide_id}] reveal target '{target}' step {index} 'auto_advance_after' must be a non-negative number"
            )

    caption = step.get("caption")
    if caption is not None and not isinstance(caption, str):
        warnings.append(
            f"ERROR: [presentation:slide_{slide_id}] reveal target '{target}' step {index} 'caption' must be a string"
        )

    audio_offset = step.get("audio_offset")
    if audio_offset is not None:
        if not isinstance(audio_offset, (int, float)) or audio_offset < 0:
            warnings.append(
                f"ERROR: [presentation:slide_{slide_id}] reveal target '{target}' step {index} 'audio_offset' must be a non-negative number"
            )

    audio_file = step.get("audio_file")
    if audio_file is not None and not isinstance(audio_file, str):
        warnings.append(
            f"ERROR: [presentation:slide_{slide_id}] reveal target '{target}' step {index} 'audio_file' must be a string"
        )

    action = step.get("action")
    if action is not None and action not in VALID_ACTIONS:
        warnings.append(
            f"ERROR: [presentation:slide_{slide_id}] reveal target '{target}' step {index} 'action' must be one of {sorted(VALID_ACTIONS)}, got {repr(action)}"
        )


def _validate_highlight(slide_id: str, target: str, index: Any, highlight: dict, warnings: list[str]) -> None:
    if not isinstance(highlight, dict):
        warnings.append(
            f"ERROR: [presentation:slide_{slide_id}] reveal target '{target}' step {index} 'highlight' must be a mapping"
        )
    else:
        h_target = highlight.get("target")
        h_style = highlight.get("style")
        if not isinstance(h_target, str) or not h_target.strip():
            warnings.append(
                f"ERROR: [presentation:slide_{slide_id}] reveal target '{target}' step {index} 'highlight' missing required 'target' string"
            )
        if not isinstance(h_style, str) or not h_style.strip():
            warnings.append(
                f"ERROR: [presentation:slide_{slide_id}] reveal target '{target}' step {index} 'highlight' missing required 'style' string"
            )


def _validate_viewport(slide_id: str, target: str, index: Any, viewport: dict, warnings: list[str]) -> None:
    if not isinstance(viewport, dict):
        warnings.append(
            f"ERROR: [presentation:slide_{slide_id}] reveal target '{target}' step {index} 'viewport' must be a mapping"
        )
    else:
        zoom = viewport.get("zoom")
        center = viewport.get("center")
        if zoom is not None and (not isinstance(zoom, (int, float)) or zoom <= 0):
            warnings.append(
                f"ERROR: [presentation:slide_{slide_id}] reveal target '{target}' step {index} 'viewport.zoom' must be a positive number"
            )
        if center is not None:
            if not isinstance(center, list) or len(center) != 2 or not all(isinstance(coord, (int, float)) for coord in center):
                warnings.append(
                    f"ERROR: [presentation:slide_{slide_id}] reveal target '{target}' step {index} 'viewport.center' must be a list of 2 numbers"
                )
