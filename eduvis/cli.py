"""
EduVis CLI — validate and render EduVis lesson YAML files.

Usage:
  python -m eduvis validate lesson.yaml
  python -m eduvis render lesson.yaml -o slides/
"""

from __future__ import annotations

import sys
from pathlib import Path

import json

import click
import yaml

# ── EduVis Core import ────────────────────────────────────────────────────────
# Allow running from any directory: resolve the eduvis package root.
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent   # project root
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

from eduvis.core import validate_lesson, format_prompt_docs, get_all_schemas, validate_curriculum  # noqa: E402
from eduvis.core.schemas.placement import VALID_MEMORY_ROLES, VALID_PHASES, VALID_DIFFICULTY  # noqa: E402

# ── EduVis SVG renderer ──────────────────────────────────────────────────────

# ── Constants ─────────────────────────────────────────────────────────────────
_EDUVIS_META = frozenset({"id", "placement", "actions", "relationships"})

# Layout zone mapping: EduVis layout_zone → svg_spec zone key.
_ZONE_MAP = {
    "center": "center",
    "left":   "left",
    "right":  "right",
    "full":   "full",
    "bottom": "bottom",
}

_LAYOUT_FOR_ZONE = {
    "left":   "two-column",
    "right":  "two-column",
    "center": "visual + full-width",
    "full":   "header + full-width",
    "bottom": "visual + full-width",
}

# Phase → header background color + badge label.
# Colors are dark enough for white title text.
_PHASE_STYLE: dict[str, dict] = {
    "hook":                 {"color": "#BF360C", "label": "HOOK"},
    "explore":              {"color": "#00695C", "label": "EXPLORE"},
    "explain":              {"color": "#1565C0", "label": "EXPLAIN"},
    "guided_practice":      {"color": "#4A148C", "label": "GUIDED"},
    "independent_practice": {"color": "#1B5E20", "label": "PRACTICE"},
    "challenge":            {"color": "#B71C1C", "label": "CHALLENGE"},
    "reflect":              {"color": "#37474F", "label": "REFLECT"},
    "recall":               {"color": "#4E342E", "label": "RECALL"},
}

# Difficulty overrides for independent_practice (color + label).
_DIFFICULTY_STYLE: dict[str, dict] = {
    "starter":   {"color": "#1B5E20", "label": "STARTER"},
    "routine":   {"color": "#004D40", "label": "ROUTINE"},
    "challenge": {"color": "#B71C1C", "label": "CHALLENGE"},
}

# Memory role → accent color for the divider line and dot.
_ROLE_COLOR: dict[str, str] = {
    "anchor":           "#FFD700",
    "example":          "#00BCD4",
    "practice":         "#66BB6A",
    "misconception_fix":"#EF5350",
    "retrieval":        "#FFA726",
    "review":           "#9E9E9E",
}


# Validate CLI style mappings cover all placement schema enum values.
missing_roles = VALID_MEMORY_ROLES - set(_ROLE_COLOR.keys())
if missing_roles:
    raise RuntimeError(
        f"Developer Error: CLI _ROLE_COLOR mapping is incomplete. "
        f"Missing roles: {', '.join(sorted(missing_roles))}"
    )

missing_phases = VALID_PHASES - set(_PHASE_STYLE.keys())
if missing_phases:
    raise RuntimeError(
        f"Developer Error: CLI _PHASE_STYLE mapping is incomplete. "
        f"Missing phases: {', '.join(sorted(missing_phases))}"
    )

missing_difficulties = VALID_DIFFICULTY - set(_DIFFICULTY_STYLE.keys())
if missing_difficulties:
    raise RuntimeError(
        f"Developer Error: CLI _DIFFICULTY_STYLE mapping is incomplete. "
        f"Missing difficulties: {', '.join(sorted(missing_difficulties))}"
    )


# ── Bridge helpers ────────────────────────────────────────────────────────────


def _element_to_spec(element: dict) -> dict:
    """Strip EduVis meta-fields; return only fields the SVG renderer needs."""
    return {k: v for k, v in element.items() if k not in _EDUVIS_META}


def _element_title(element: dict) -> str:
    """Build a human-readable slide title from an element's id and lesson_phase."""
    if element.get("title"):
        return str(element["title"])
    eid = element.get("id", "")
    placement = element.get("placement") or {}
    phase = placement.get("lesson_phase", "")
    if phase and eid:
        return f"{phase.replace('_', ' ').title()}: {eid.replace('_', ' ')}"
    return (eid or "slide").replace("_", " ").title()


def _build_svg_spec_yaml(element: dict, elements_by_id: dict[str, dict] | None = None) -> str:
    """Convert one EduVis element dict to an svg_spec YAML string for rendering."""
    # Resolve remediation_block question references if elements_by_id is provided
    if element.get("type") == "remediation_block" and elements_by_id:
        element = element.copy()
        review = element.get("review", {})
        if isinstance(review, dict):
            review = review.copy()
            q_id = review.get("source_question")
            if q_id and q_id in elements_by_id:
                review["question_spec"] = elements_by_id[q_id]
            element["review"] = review

    placement = element.get("placement") or {}
    if "zones" in element:
        zones = {}
        for z_name, z_elements in element["zones"].items():
            if isinstance(z_elements, list):
                zones[z_name] = [_element_to_spec(el) for el in z_elements]
            else:
                zones[z_name] = [_element_to_spec(z_elements)]
        layout = element.get("layout", "two-column")
    else:
        zone = _ZONE_MAP.get(placement.get("layout_zone", "full"), "full")
        layout = _LAYOUT_FOR_ZONE.get(zone, "header + full-width")
        zones = {zone: [_element_to_spec(element)]}

    phase = placement.get("lesson_phase", "")
    difficulty = placement.get("difficulty", "")
    memory_role = placement.get("memory_role", "")

    phase_style = _PHASE_STYLE.get(phase, {})
    header_color = phase_style.get("color", "#111111")
    phase_label = phase_style.get("label", "")

    # Differentiate starter / routine within independent_practice
    if phase == "independent_practice" and difficulty in _DIFFICULTY_STYLE:
        diff_style = _DIFFICULTY_STYLE[difficulty]
        header_color = diff_style["color"]
        phase_label = diff_style["label"]

    role_color = _ROLE_COLOR.get(memory_role, "")

    spec_dict = {
        "layout": layout,
        "header_color": header_color,
        "phase_label": phase_label,
        "role_color": role_color,
        "memory_role": memory_role,
        "zones": zones,
    }
    return yaml.dump(spec_dict, allow_unicode=True, default_flow_style=False)


def _load_renderer():
    """Load the standalone EduVis SVG renderer."""
    try:
        from .renderers.svg import SVGSpecRenderer  # noqa: PLC0415
        return SVGSpecRenderer()
    except ImportError as exc:
        raise click.ClickException(
            f"Cannot import EduVis SVG renderer: {exc}"
        ) from exc


def _get_sidecar_path(lesson_path: Path) -> Path:
    """Determine the sidecar presentation file path based on suffix pattern matching."""
    stem = lesson_path.stem
    has_suffix = False
    for suffix in ["-lesson", "-content"]:
        if stem.endswith(suffix):
            stem = stem[:-len(suffix)]
            has_suffix = True
            break

    # 1. Check if <prefix>-presentation.yaml exists
    prefix_pres = lesson_path.parent / f"{stem}-presentation.yaml"
    if prefix_pres.is_file():
        return prefix_pres

    # 2. Check if <lesson_stem>-presentation.yaml exists
    stem_pres = lesson_path.parent / f"{lesson_path.stem}-presentation.yaml"
    if stem_pres.is_file():
        return stem_pres

    # 3. Check if presentation.yaml exists
    default_pres = lesson_path.parent / "presentation.yaml"
    if default_pres.is_file():
        return default_pres

    # Fallback for creation
    if has_suffix:
        return prefix_pres
    return default_pres


# ── Sidecar presentation.yaml helpers ───────────────────────────────────────


def _update_presentation_svg(
    sidecar_path: Path,
    element_id: str,
    embed_mode: str,
    svg_text: str,
    svg_rel_path: str,
) -> None:
    """
    Auto-write SVG data into the sidecar presentation.yaml for the matching slide.

    embed_mode='ref'    → sets svg_ref to svg_rel_path, removes svg_inline.
    embed_mode='inline' → sets svg_inline to svg_text,  removes svg_ref.

    Only updates slides that already have a matching 'id' entry in the sidecar.
    If no matching slide entry exists, the file is left unchanged.
    """
    if sidecar_path.is_file():
        try:
            with open(sidecar_path, encoding="utf-8") as f:
                doc = yaml.safe_load(f) or {}
        except yaml.YAMLError:
            return  # Don't corrupt a broken sidecar
    else:
        doc = {}

    slides = doc.get("slides")
    if not isinstance(slides, list):
        return  # No slides list — nothing to update

    matched = False
    for slide in slides:
        if isinstance(slide, dict) and slide.get("id") == element_id:
            if embed_mode == "inline":
                slide["svg_inline"] = svg_text
                slide.pop("svg_ref", None)
            else:  # ref (default)
                slide["svg_ref"] = svg_rel_path
                slide.pop("svg_inline", None)
            matched = True
            break

    if matched:
        sidecar_path.write_text(
            yaml.dump(doc, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )


# ── CLI ───────────────────────────────────────────────────────────────────────

@click.group()
def cli() -> None:
    """EduVis - educational content schema tools."""


@cli.command()
@click.option(
    "--subjects",
    default="math",
    show_default=True,
    help="Comma-separated subject tags to include (e.g. math,science). Use '*' for all.",
)
@click.option(
    "--output", "-o",
    default=None,
    help="Write vocabulary to this file instead of stdout.",
)
def docs(subjects: str, output: str | None) -> None:
    """Print the full EduVis vocabulary for use in an LLM system prompt."""
    subject_list = [s.strip() for s in subjects.split(",")]
    vocab = format_prompt_docs(subject_list)
    if output:
        Path(output).write_text(vocab, encoding="utf-8")
        click.echo(f"Vocabulary written to {output}")
    else:
        click.echo(vocab)


@cli.command()
@click.option(
    "-o", "--output",
    default="schemas",
    show_default=True,
    help="Directory to write JSON Schema files into.",
)
def schema(output: str) -> None:
    """Export all EduVis JSON Schemas to a directory."""
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)

    schemas = get_all_schemas()
    for name, schema_dict in schemas.items():
        out_path = out_dir / f"{name}.schema.json"
        out_path.write_text(json.dumps(schema_dict, indent=2), encoding="utf-8")
        click.echo(f"   OK {out_path}")

    click.secho(f"\nDone -- {len(schemas)} schema(s) written to {out_dir}/", fg="green")


@cli.command()
@click.argument("lesson_file", type=click.Path(exists=True, dir_okay=False))
def validate(lesson_file: str) -> None:
    """Validate an EduVis lesson or curriculum YAML file."""
    with open(lesson_file, encoding="utf-8") as f:
        try:
            doc = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise click.ClickException(f"YAML parse error: {exc}") from exc

    if not isinstance(doc, dict):
        raise click.ClickException("File must be a YAML mapping at the top level.")

    if "concepts" in doc and "content" not in doc:
        # Standalone curriculum validation
        warnings = validate_curriculum(doc)
        is_curriculum = True
    else:
        # Lesson validation
        is_curriculum = False
        lesson_path = Path(lesson_file)
        sidecar_path = _get_sidecar_path(lesson_path)
        if sidecar_path.is_file():
            try:
                with open(sidecar_path, encoding="utf-8") as f_sidecar:
                    presentation_doc = yaml.safe_load(f_sidecar)
                    if isinstance(presentation_doc, dict):
                        doc["presentation"] = presentation_doc
            except yaml.YAMLError as exc:
                raise click.ClickException(f"Sidecar presentation.yaml parse error: {exc}") from exc

        warnings = validate_lesson(doc)

    if not warnings:
        click.secho(f"OK  {lesson_file} -- valid, no warnings", fg="green")
    else:
        file_type = "curriculum" if is_curriculum else "lesson"
        click.secho(f"WARN  {lesson_file} ({file_type}) -- {len(warnings)} warning(s):", fg="yellow")
        for w in warnings:
            click.echo(f"   {w}")
        sys.exit(1)


@cli.command()
@click.argument("lesson_file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "-o", "--output",
    default="output",
    show_default=True,
    help="Directory to write SVG files into.",
)
@click.option(
    "--posting-group",
    default="G1",
    show_default=True,
    help="Grade level for font sizing (G1, G2, or G3).",
)
@click.option(
    "--skip-validation",
    is_flag=True,
    default=False,
    help="Skip EduVis validation before rendering.",
)
@click.option(
    "--embed-mode",
    type=click.Choice(["ref", "inline"], case_sensitive=False),
    default="ref",
    show_default=True,
    help=(
        "How to record the rendered SVG in presentation.yaml. "
        "'ref' writes a relative file path (svg_ref). "
        "'inline' embeds the full SVG markup (svg_inline)."
    ),
)
def render(lesson_file: str, output: str, posting_group: str, skip_validation: bool, embed_mode: str) -> None:
    """Render an EduVis lesson YAML to one SVG per element."""
    with open(lesson_file, encoding="utf-8") as f:
        try:
            doc = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise click.ClickException(f"YAML parse error: {exc}") from exc

    if not isinstance(doc, dict):
        raise click.ClickException("Lesson file must be a YAML mapping at the top level.")

    # Load optional sidecar presentation.yaml
    lesson_path = Path(lesson_file)
    sidecar_path = _get_sidecar_path(lesson_path)
    if sidecar_path.is_file():
        try:
            with open(sidecar_path, encoding="utf-8") as f_sidecar:
                presentation_doc = yaml.safe_load(f_sidecar)
                if isinstance(presentation_doc, dict):
                    doc["presentation"] = presentation_doc
        except yaml.YAMLError as exc:
            raise click.ClickException(f"Sidecar presentation.yaml parse error: {exc}") from exc

    # ── Validate first ────────────────────────────────────────────────────────
    if not skip_validation:
        warnings = validate_lesson(doc)
        if warnings:
            click.secho(f"WARN  {len(warnings)} validation warning(s):", fg="yellow")
            for w in warnings:
                click.echo(f"   {w}")
            click.echo()

    # ── Load renderer ─────────────────────────────────────────────────────────
    renderer = _load_renderer()

    # ── Render ────────────────────────────────────────────────────────────────
    content = doc.get("content")
    if not isinstance(content, list) or not content:
        raise click.ClickException("No 'content' list found in the lesson file.")

    elements_by_id = {el["id"]: el for el in content if isinstance(el, dict) and "id" in el}

    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)

    lesson_title = (doc.get("lesson") or {}).get("title", "")
    rendered = 0
    skipped = 0
    first_dict_idx = next((i for i, el in enumerate(content) if isinstance(el, dict)), None)

    for idx, element in enumerate(content):
        if not isinstance(element, dict):
            continue

        element_id = element.get("id", f"element_{rendered + skipped + 1}")
        if lesson_title and idx == first_dict_idx:
            title = f"{lesson_title} - {_element_title(element)}"
        else:
            title = _element_title(element)

        svg_spec_yaml = _build_svg_spec_yaml(element, elements_by_id)

        try:
            svg_text = renderer.render(
                svg_spec_yaml,
                title=title,
                posting_group=posting_group,
            )
        except Exception as exc:
            click.secho(f"   FAIL {element_id}: render error -- {exc}", fg="red")
            skipped += 1
            continue

        out_path = out_dir / f"{element_id}.svg"
        out_path.write_text(svg_text, encoding="utf-8")
        click.echo(f"   OK {out_path}")
        rendered += 1

        # Auto-update sidecar presentation.yaml (mode: ref or inline)
        try:
            svg_rel = out_path.relative_to(lesson_path.parent).as_posix()
        except ValueError:
            svg_rel = str(out_path)  # Fallback: absolute path if not relative
        _update_presentation_svg(sidecar_path, element_id, embed_mode, svg_text, svg_rel)

    click.echo()
    click.secho(
        f"Done -- {rendered} SVG(s) written to {out_dir}/",
        fg="green" if not skipped else "yellow",
    )
    if skipped:
        click.secho(f"       {skipped} element(s) skipped due to render errors.", fg="yellow")
