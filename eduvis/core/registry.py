"""
EduVis Core — Element Registry.

Each element module declares an ELEMENT_SPECS list alongside element definitions.
Every entry is an ElementSpec that carries:
  • A JSON Schema (subset) describing the expected content fields
  • The subjects this element is available for ("*" = all)
  • LLM guidance notes (IMPORTANT / PREFER constraints)

The registry is the single source of truth for:
  1. Prompt vocabulary   — format_prompt_docs()
  2. Field-level schema  — get_json_schemas()
  3. Field validation    — validate_fields()

Adding a new element:
  1. Write the ElementSpec in the appropriate elements/*.py file
  2. Add it to that file's ELEMENT_SPECS list
  That's it — prompt docs and validation update automatically.

render_fn is intentionally absent from ElementSpec: renderers are separate from the schema.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_COLOR_VALUES = "red|green|blue|yellow|cyan|orange|purple|grey|white"


# ── Field descriptor ──────────────────────────────────────────────────────────

@dataclass
class FieldSpec:
    """Describes one field in an element's content schema."""

    name: str
    type: str                          # "string"|"number"|"integer"|"boolean"|"array"|"object"|"color"
    required: bool = True
    description: str = ""
    constraint: str = ""               # Extra LLM guidance, e.g. "MUST be numeric, not '$5.00'"
    default: Any = None
    enum: list[str] = field(default_factory=list)
    items: "FieldSpec | None" = None             # schema for array items
    properties: list["FieldSpec"] = field(default_factory=list)  # schema for object properties

    def to_schema_dict(self) -> dict:
        d: dict = {"type": self.type if self.type != "color" else "string"}
        if self.description:
            d["description"] = self.description
        if self.constraint:
            d["x-constraint"] = self.constraint
        if self.enum:
            d["enum"] = self.enum
        if self.default is not None:
            d["default"] = self.default
        if self.type == "array" and self.items:
            d["items"] = self.items.to_schema_dict()
        if self.type == "object" and self.properties:
            d["properties"] = {p.name: p.to_schema_dict() for p in self.properties}
            d["required"] = [p.name for p in self.properties if p.required]
        return d

    def to_prompt_line(self, indent: int = 6) -> str:
        pad = " " * indent
        req = "" if self.required else " (optional)"
        typ = self.type
        if self.enum:
            typ = "|".join(self.enum)
        elif self.type == "color":
            typ = _COLOR_VALUES
        elif self.type == "array" and self.items:
            item_typ = self.items.type if self.items.type != "color" else _COLOR_VALUES
            typ = f"array of {item_typ}"
        default_str = f"  # default: {self.default}" if self.default is not None else ""
        desc_str = f"  # {self.description}" if self.description else ""
        constraint_str = f"  [!]{self.constraint}" if self.constraint else ""
        return f"{pad}{self.name}{req}: {typ}{default_str}{desc_str}{constraint_str}"


# ── Element spec ──────────────────────────────────────────────────────────────

@dataclass
class ElementSpec:
    """
    Full descriptor for one EduVis content element type.

    Co-locate one of these with every element definition — the registry reads
    ELEMENT_SPECS lists from element modules at import time.

    render_fn is intentionally absent — renderers define their own mappings
    separately from the content schema.
    """

    name: str                          # "bar_model"
    subjects: list[str]               # ["math"] | ["*"] for all subjects
    synopsis: str                      # one-line description shown in element list
    fields: list[FieldSpec]           # typed field descriptors
    notes: list[str] = field(default_factory=list)  # IMPORTANT / PREFER guidance for LLMs

    def json_schema(self) -> dict:
        props = {f.name: f.to_schema_dict() for f in self.fields}
        required = [f.name for f in self.fields if f.required]
        schema: dict = {
            "$schema": "https://json-schema.org/draft-07/schema",
            "title": self.name,
            "description": self.synopsis,
            "type": "object",
            "properties": props,
        }
        if required:
            schema["required"] = required
        return schema

    def to_prompt_block(self) -> str:
        name_col = 16
        pad_name = max(1, name_col - len(self.name))
        lines = [f"  {self.name}{' ' * pad_name}{self.synopsis}"]

        for f in self.fields:
            req_str = "required" if f.required else "optional"
            default_str = f", default: {f.default}" if f.default is not None else ""
            constraint_str = f"  [!]{f.constraint}" if f.constraint else ""
            desc_str = f"  # {f.description}" if f.description else ""

            if f.type == "array" and f.items and f.items.properties:
                lines.append(f"                  {f.name} ({req_str}, array):{constraint_str}{desc_str}")
                for prop in f.items.properties:
                    prop_req = "" if prop.required else " (optional)"
                    prop_typ = "|".join(prop.enum) if prop.enum else (
                        _COLOR_VALUES if prop.type == "color" else prop.type
                    )
                    prop_constraint = f"  [!]{prop.constraint}" if prop.constraint else ""
                    prop_desc = f"  # {prop.description}" if prop.description else ""
                    lines.append(f"                    - {prop.name}{prop_req}: {prop_typ}{prop_constraint}{prop_desc}")
            elif f.type == "object" and f.properties:
                lines.append(f"                  {f.name} ({req_str}, object):{constraint_str}{desc_str}")
                for prop in f.properties:
                    prop_req = "" if prop.required else " (optional)"
                    prop_typ = "|".join(prop.enum) if prop.enum else (
                        _COLOR_VALUES if prop.type == "color" else prop.type
                    )
                    lines.append(f"                    {prop.name}{prop_req}: {prop_typ}")
            else:
                typ = "|".join(f.enum) if f.enum else (
                    _COLOR_VALUES if f.type == "color" else f.type
                )
                lines.append(
                    f"                  {f.name} ({req_str}): {typ}{default_str}"
                    f"{constraint_str}{desc_str}"
                )

        for note in self.notes:
            lines.append(f"                  {note}")

        return "\n".join(lines)


# ── Registry singleton ────────────────────────────────────────────────────────

class _ElementRegistry:
    """
    Singleton registry for all EduVis element specs.

    Populated by register_all() from element modules.
    _ensure_registered() triggers lazy auto-discovery if the registry
    is queried before any module has explicitly registered its specs.
    """

    def __init__(self) -> None:
        self._specs: dict[str, ElementSpec] = {}
        self._registered = False

    def _ensure_registered(self) -> None:
        if self._registered or self._specs:
            self._registered = True
            return
        try:
            from .elements import generic, math as math_elements  # noqa: PLC0415
            self.register_all(generic.ELEMENT_SPECS)
            self.register_all(math_elements.ELEMENT_SPECS)
            self._registered = True
            logger.debug(
                "EduVis ElementRegistry: auto-registered %d element specs.", len(self._specs)
            )
        except ImportError as exc:
            logger.warning(
                "EduVis ElementRegistry: auto-registration incomplete — %s.", exc
            )

    def register(self, spec: ElementSpec) -> None:
        self._specs[spec.name] = spec

    def register_all(self, specs: list[ElementSpec]) -> None:
        for spec in specs:
            self.register(spec)

    def get(self, name: str) -> ElementSpec | None:
        self._ensure_registered()
        return self._specs.get(name)

    def known_names(self) -> list[str]:
        self._ensure_registered()
        return sorted(self._specs.keys())

    def all_specs(self) -> dict[str, ElementSpec]:
        self._ensure_registered()
        return dict(self._specs)

    # ── Prompt generation ─────────────────────────────────────────────────────

    def format_prompt_docs(self, subjects: list[str]) -> str:
        """Generate element vocabulary for an LLM prompt."""
        self._ensure_registered()
        subject_set = set(subjects) | {"*"}
        blocks = [
            spec.to_prompt_block()
            for spec in self._specs.values()
            if any(s in subject_set for s in spec.subjects)
        ]
        return "\n".join(blocks)

    def get_json_schemas(self, subjects: list[str]) -> dict[str, dict]:
        self._ensure_registered()
        subject_set = set(subjects) | {"*"}
        return {
            name: spec.json_schema()
            for name, spec in self._specs.items()
            if any(s in subject_set for s in spec.subjects)
        }

    # ── Field validation ──────────────────────────────────────────────────────

    def validate_fields(self, element_name: str, content_data: dict) -> list[str]:
        """
        Validate content_data against the registered field schema for element_name.

        Returns a list of warning strings (empty = valid).
        Logs each warning at WARNING level. Does NOT raise — callers should
        let the renderer try anyway for graceful degradation.
        """
        self._ensure_registered()
        warnings: list[str] = []
        spec = self._specs.get(element_name)
        if not spec:
            return warnings  # unknown element — renderer will handle it

        for field_spec in spec.fields:
            value = content_data.get(field_spec.name)

            if value is None:
                if field_spec.required:
                    msg = f"[{element_name}] missing required field '{field_spec.name}'"
                    warnings.append(msg)
                    logger.warning(msg)
                continue

            if not _check_type(field_spec, value):
                msg = (
                    f"[{element_name}] field '{field_spec.name}': "
                    f"expected {field_spec.type}, got {type(value).__name__} {value!r}"
                )
                if field_spec.constraint:
                    msg += f" — {field_spec.constraint}"
                warnings.append(msg)
                logger.warning(msg)

            # Array-of-object item validation
            if (
                field_spec.type == "array"
                and field_spec.items
                and field_spec.items.properties
                and isinstance(value, list)
            ):
                for i, item in enumerate(value):
                    if not isinstance(item, dict):
                        continue
                    for prop in field_spec.items.properties:
                        item_val = item.get(prop.name)
                        if item_val is None:
                            if prop.required:
                                msg = (
                                    f"[{element_name}] {field_spec.name}[{i}] "
                                    f"missing required property '{prop.name}'"
                                )
                                warnings.append(msg)
                                logger.warning(msg)
                        elif not _check_type(prop, item_val):
                            msg = (
                                f"[{element_name}] {field_spec.name}[{i}].{prop.name}: "
                                f"expected {prop.type}, got {type(item_val).__name__} {item_val!r}"
                            )
                            if prop.constraint:
                                msg += f" — {prop.constraint}"
                            warnings.append(msg)
                            logger.warning(msg)

        return warnings


def _check_type(field_spec: FieldSpec, value: Any) -> bool:
    t = field_spec.type
    if t == "string":
        return isinstance(value, str)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "array":
        return isinstance(value, list)
    if t in ("object", "dict"):
        return isinstance(value, dict)
    if t == "color":
        return isinstance(value, str)
    return True


# ── Public singleton ──────────────────────────────────────────────────────────

ElementRegistry = _ElementRegistry()
