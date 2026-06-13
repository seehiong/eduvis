"""
EduVis SVG Renderer - deterministic svg_spec YAML to SVG translator.

Renders educational content specifications to pixel-perfect SVG with zero LLM involvement.
"""

import re
import yaml

from .primitives import (
    CANVAS_H,
    CANVAS_W,
    COLORS,
    HEADER_H,
    MARGIN,
    CONTENT_Y,
    _line,
    _text,
    _wrap,
    _get_font_size,
)
from .renderers_base import RENDERERS as _R_BASE
from .renderers_math import RENDERERS as _R_MATH

# Merged renderer registry: type name → render function
_RENDERERS: dict = {**_R_BASE, **_R_MATH}

_ROLE_THEME: dict[str, dict[str, str]] = {
    "anchor":           {"bg": "#fef3c7", "text": "#78350f", "border": "#fde047"},
    "example":          {"bg": "#ecfeff", "text": "#083344", "border": "#a5f3fc"},
    "practice":         {"bg": "#f0fdf4", "text": "#14532d", "border": "#bbf7d0"},
    "misconception_fix":{"bg": "#fef2f2", "text": "#7f1d1d", "border": "#fecaca"},
    "retrieval":        {"bg": "#fff7ed", "text": "#7c2d12", "border": "#fed7aa"},
    "review":           {"bg": "#f1f5f9", "text": "#0f172a", "border": "#cbd5e1"},
}


class UnitTracker:
    def __init__(self, group_elements: bool, ref: str, el_type: str, start_order: int):
        self.group_elements = group_elements
        self.ref = ref
        self.el_type = el_type
        self.order = start_order
        self.units: list[dict] = []
        self.active = False

    def open_unit(self, out: list[str], sub_type: str = "") -> None:
        if self.active:
            self.close_unit(out, sub_type)
        if self.group_elements:
            out.append(
                f'  <g id="u{self.order}" data-reveal-order="{self.order}" '
                f'data-ref="{self.ref}" data-type="{sub_type or self.el_type}">'
            )
        self.active = True

    def close_unit(self, out: list[str], sub_type: str = "") -> None:
        if not self.active:
            return
        if self.group_elements:
            out.append("  </g>")
        self.units.append(
            {
                "id": f"u{self.order}",
                "order": self.order,
                "ref": self.ref,
                "type": sub_type or self.el_type,
            }
        )
        self.order += 1
        self.active = False


class SVGSpecRenderer:
    """Deterministic svg_spec YAML to SVG renderer. No LLM calls."""

    @staticmethod
    def _sanitize_yaml(raw: str) -> str:
        """Strip non-rendering presentation keys (such as narration blocks) before YAML parsing."""
        # Translate LaTeX math symbols to Unicode equivalents to prevent YAML escape sequence corruption
        latex_map = {
            "to": "→",
            "rightarrow": "→",
            "leftarrow": "←",
            "times": "×",
            "approx": "≈",
            "leq": "≤",
            "geq": "≥",
            "le": "≤",
            "ge": "≥",
            "div": "÷",
            "pm": "±",
            "neq": "≠",
            "ne": "≠",
            "cdot": "·",
        }
        def repl(match):
            return latex_map[match.group(1)]
        raw = re.sub(
            r'\\(approx|times|rightarrow|leftarrow|leq|geq|neq|div|to|le|ge|pm|ne|cdot)(?![a-zA-Z])',
            repl,
            raw
        )
        # Match standalone unescaped command names (where the leading backslash is omitted)
        raw = re.sub(
            r'\b(geq|leq|ge|le|div)\b',
            repl,
            raw
        )

        # Map LaTeX/plain superscripts and subscripts to their Unicode equivalents
        superscripts = {
            "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
            "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
            "+": "⁺", "-": "⁻", "=": "⁼", "(": "⁽", ")": "⁾",
            "n": "ⁿ", "i": "ⁱ", "x": "ˣ", "y": "ʸ"
        }
        subscripts = {
            "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄",
            "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉",
            "+": "₊", "-": "₋", "=": "₌", "(": "₍", ")": "₎",
            "a": "ₐ", "e": "ₑ", "i": "ᵢ", "o": "ₒ", "x": "ₓ",
            "h": "ₕ", "k": "ₖ", "l": "ₗ", "m": "ₘ", "n": "ₙ",
            "p": "ₚ", "s": "ₛ", "t": "ₜ"
        }

        def make_super(match):
            chars = match.group(1) or match.group(2)
            return "".join(superscripts.get(c, c) for c in chars)

        def make_sub(match):
            chars = match.group(1) or match.group(2)
            return "".join(subscripts.get(c, c) for c in chars)

        # Match ^{characters} or ^character
        raw = re.sub(r'\^\{([0-9+\-=()nixy]+)\}|\^([0-9nixy])', make_super, raw)
        # Match _{characters} or _character (only when not mid-identifier, e.g. bar_model)
        raw = re.sub(r'\_\{([0-9+\-=()aeixhklmnpst]+)\}|\_([0-9aeixhklmnpst])(?![a-zA-Z0-9_])', make_sub, raw)

        lines = raw.splitlines(keepends=True)
        result: list[str] = []
        in_ignored_block = False

        for line in lines:
            stripped = line.lstrip()
            # Strip key-value blocks that are not used in rendering and may contain invalid YAML indentation
            if re.match(r"^(voiceover|narration|script|audio)\s*:", line):
                in_ignored_block = True
                continue
            if in_ignored_block:
                if not stripped or line[0] in (" ", "\t") or stripped.startswith("|"):
                    continue
                in_ignored_block = False
            result.append(line)

        return "".join(result)

    def render(
        self,
        svg_spec_yaml: str,
        title: str = "",
        width: int = CANVAS_W,
        height: int = CANVAS_H,
        posting_group: str = "G1",
        group_elements: bool = False,
        dynamic_height: bool = True,
    ) -> str:
        """Render svg_spec YAML to SVG string."""
        svg_str, _units = self.render_with_units(
            svg_spec_yaml,
            title=title,
            width=width,
            height=height,
            posting_group=posting_group,
            group_elements=group_elements,
            dynamic_height=dynamic_height,
        )
        return svg_str

    def render_with_units(
        self,
        svg_spec_yaml: str,
        title: str = "",
        width: int = CANVAS_W,
        height: int = CANVAS_H,
        posting_group: str = "G1",
        group_elements: bool = False,
        dynamic_height: bool = True,
    ) -> tuple[str, list[dict]]:
        """Render svg_spec YAML and return (svg_string, ordered_unit_list)."""
        spec = yaml.safe_load(self._sanitize_yaml(svg_spec_yaml))
        layout = spec.get("layout", "header + full-width")
        zones_spec = spec.get("zones", {})

        header_color = spec.get("header_color", "#ffffff")
        phase_label  = spec.get("phase_label", "")
        role_color   = spec.get("role_color", "")
        memory_role  = spec.get("memory_role", "")

        # Use theme title color on light headers, white on dark headers
        title_color = COLORS["title"] if header_color.lower() in ("#ffffff", "#f8fafc", "#f1f5f9", "white") else "#FFFFFF"

        # Reserve right-side space so the title doesn't run under the phase badge
        badge_w = len(phase_label) * 7 + 20 if phase_label else 0
        title_max_w = width - 2 * MARGIN - badge_w - (12 if badge_w else 0)

        out = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            f'  <rect width="{width}" height="{height}" fill="{COLORS["background"]}" />',
            f'  <rect width="{width}" height="{HEADER_H}" fill="{header_color}" />',
        ]

        units: list[dict] = []
        order = 0

        def _open(ref: str, el_type: str) -> None:
            if group_elements:
                out.append(
                    f'  <g id="u{order}" data-reveal-order="{order}" '
                    f'data-ref="{ref}" data-type="{el_type}">'
                )

        def _close(ref: str, el_type: str) -> None:
            nonlocal order
            if group_elements:
                out.append("  </g>")
            units.append(
                {"id": f"u{order}", "order": order, "ref": ref, "type": el_type}
            )
            order += 1

        if title:
            title_size = _get_font_size("title", posting_group)
            title_lines = _wrap(title, title_max_w, title_size)
            ty = 44 - (len(title_lines) - 1) * 20
            _open("title", "title")
            for tl in title_lines:
                out.append(
                    _text(
                        MARGIN,
                        ty,
                        tl,
                        size=title_size,
                        color=title_color,
                        weight="bold",
                    )
                )
                ty += 20
            _close("title", "title")

        # Phase badge — pill in top-right corner of header
        if phase_label:
            badge_h  = 18
            badge_x  = width - MARGIN - badge_w
            badge_y  = (HEADER_H - badge_h) // 2
            out.append(
                f'  <rect x="{badge_x}" y="{badge_y}" width="{badge_w}" '
                f'height="{badge_h}" rx="4" fill="#000000" opacity="0.35" />'
            )
            out.append(
                f'  <text x="{badge_x + badge_w // 2}" y="{badge_y + 13}" '
                f'font-family="Arial, sans-serif" font-size="10" font-weight="bold" '
                f'fill="#FFFFFF" text-anchor="middle">{phase_label}</text>'
            )

        # Divider line — colored by memory_role; default separator color
        theme = _ROLE_THEME.get(memory_role, {"bg": "#f1f5f9", "text": "#0f172a", "border": COLORS["separator"]})
        line_c = theme["border"]
        out.append(_line(MARGIN, HEADER_H, width - MARGIN, HEADER_H, color=line_c))

        # Memory-role horizontal pill directly flush with the divider line
        if memory_role:
            role_label = memory_role.replace("_", " ").upper()
            badge_h = 16
            badge_w = len(role_label) * 6 + 16
            badge_x = MARGIN
            badge_y = HEADER_H
            
            out.append(
                f'  <rect x="{badge_x}" y="{badge_y}" width="{badge_w}" '
                f'height="{badge_h}" rx="3" fill="{theme["bg"]}" stroke="{theme["border"]}" stroke-width="1.2" />'
            )
            out.append(
                f'  <text x="{badge_x + badge_w // 2}" y="{badge_y + 11.5}" '
                f'font-family="Arial, sans-serif" font-size="8.5" font-weight="bold" '
                f'fill="{theme["text"]}" text-anchor="middle">{role_label}</text>'
            )

        # Determine physical rendering and spacing order dynamically
        layout_lower = layout.lower().replace(" ", "").replace("-", "")
        if "twocolumn" in layout_lower:
            zone_order = ["left", "right", "bottom"]
        elif "visual" in layout_lower:
            zone_order = ["center", "full", "bottom"]
        else:
            zone_order = ["full"]

        has_bot = "bottom" in zones_spec

        def _simulate_layout(config):
            start_y = config.get("start_y", CONTENT_Y)
            el_gap = config.get("el_gap", 8)
            z_gap = config.get("z_gap", 10)
            use_min = config.get("use_min", True)

            current_y_visual = start_y
            left_right_max_y = start_y

            zone_coords = {}
            for zone_name in zone_order:
                if zone_name not in zones_spec or not zones_spec[zone_name]:
                    continue

                elements = zones_spec[zone_name]

                if "twocolumn" in layout_lower:
                    col_w = 315
                    col_h = 230 if has_bot else 340
                    if zone_name == "left":
                        zx, zy, zw = MARGIN, start_y, col_w
                        zh = height - start_y - 10
                    elif zone_name == "right":
                        zx, zy, zw = MARGIN + col_w + 10, start_y, col_w
                        zh = height - start_y - 10
                    elif zone_name == "bottom":
                        zy = (
                            left_right_max_y + z_gap
                            if left_right_max_y > start_y
                            else start_y
                        )
                        zx, zw = MARGIN, width - 2 * MARGIN
                        zh = height - zy - 10
                elif "visual" in layout_lower:
                    zw = width - 2 * MARGIN
                    zx = MARGIN
                    if zone_name == "center":
                        zy = start_y
                        zh = height - zy - 10
                    elif zone_name == "full":
                        zy = (
                            current_y_visual + z_gap
                            if current_y_visual > start_y
                            else start_y
                        )
                        zh = height - zy - 10
                    elif zone_name == "bottom":
                        zy = (
                            current_y_visual + z_gap
                            if current_y_visual > start_y
                            else start_y
                        )
                        zx, zw = MARGIN, width - 2 * MARGIN
                        zh = height - zy - 10
                else:
                    zx, zy, zw = MARGIN, start_y, width - 2 * MARGIN
                    zh = height - start_y - 10

                cy = zy
                el_heights = []
                for el_spec in elements:
                    el_type = el_spec.get("type", "")
                    renderer = _RENDERERS.get(el_type)
                    if not renderer:
                        continue

                    if "max_circle_r" in config and el_type == "fraction_model":
                        el_spec = el_spec.copy()
                        el_spec["max_r"] = config["max_circle_r"]

                    remaining = zh - (cy - zy)
                    if remaining < 10:
                        remaining = 10

                    import inspect
                    sig = inspect.signature(renderer)
                    kwargs = {}
                    if "posting_group" in sig.parameters:
                        kwargs["posting_group"] = posting_group
                    if "tracker" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                        kwargs["tracker"] = None

                    try:
                        _, consumed = renderer(
                            el_spec, zx, cy, zw, 9999, **kwargs
                        )
                    except Exception:
                        consumed = 90

                    el_heights.append(consumed)
                    cy += consumed + el_gap

                actual_cy = cy - el_gap if el_heights else cy

                if "twocolumn" in layout_lower:
                    if zone_name in ("left", "right"):
                        col_h_enforced = col_h if use_min else 0
                        left_right_max_y = max(
                            left_right_max_y, actual_cy, start_y + col_h_enforced
                        )
                elif "visual" in layout_lower:
                    if zone_name == "center":
                        min_y = start_y + 150 if use_min else start_y
                        current_y_visual = max(actual_cy, min_y)
                    elif zone_name == "full":
                        min_h = 100 if (has_bot and use_min) else (height - zy - 10 if use_min else 0)
                        current_y_visual = max(actual_cy, zy + min_h)

                zone_coords[zone_name] = {
                    "zx": zx,
                    "zy": zy,
                    "zw": zw,
                    "zh": zh,
                    "actual_cy": actual_cy,
                    "el_heights": el_heights,
                }

            max_y = start_y
            for z_name, z_c in zone_coords.items():
                max_y = max(max_y, z_c["actual_cy"])

            return zone_coords, max_y

        configs = [
            {"start_y": CONTENT_Y, "el_gap": 8, "z_gap": 10, "use_min": True, "max_circle_r": 70},
            {"start_y": CONTENT_Y, "el_gap": 8, "z_gap": 10, "use_min": False, "max_circle_r": 70},
            {"start_y": CONTENT_Y - 10, "el_gap": 4, "z_gap": 6, "use_min": False, "max_circle_r": 50},
            {"start_y": CONTENT_Y - 15, "el_gap": 2, "z_gap": 4, "use_min": False, "max_circle_r": 35},
        ]

        fits = False
        selected_config = configs[0]
        zone_coords, max_y = _simulate_layout(selected_config)
        for cfg in configs[1:]:
            if max_y + 10 <= height:
                fits = True
                break
            selected_config = cfg
            zone_coords, max_y = _simulate_layout(selected_config)

        if max_y + 10 <= height:
            fits = True

        if not fits and dynamic_height:
            selected_config = configs[0]
            height = 9999
            zone_coords, max_y = _simulate_layout(selected_config)
            
            height = int(max_y + 16)
            zone_coords, max_y = _simulate_layout(selected_config)
            
            out[1] = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
            out[2] = f'  <rect width="{width}" height="{height}" fill="{COLORS["background"]}" />'

        el_gap = selected_config["el_gap"]

        for zone_name in zone_order:
            if zone_name not in zones_spec or not zones_spec[zone_name]:
                continue

            elements = zones_spec[zone_name]
            z_c = zone_coords[zone_name]
            zx, zy, zw, zh = z_c["zx"], z_c["zy"], z_c["zw"], z_c["zh"]

            cy = zy
            for j, el_spec in enumerate(elements):
                el_type = el_spec.get("type", "")
                renderer = _RENDERERS.get(el_type)
                if not renderer:
                    continue

                if "max_circle_r" in selected_config and el_type == "fraction_model":
                    el_spec = el_spec.copy()
                    el_spec["max_r"] = selected_config["max_circle_r"]

                remaining = zh - (cy - zy)
                if remaining < 10:
                    break

                import inspect

                sig = inspect.signature(renderer)
                has_tracker = "tracker" in sig.parameters or any(
                    p.kind == inspect.Parameter.VAR_KEYWORD
                    for p in sig.parameters.values()
                )

                if has_tracker:
                    tracker = UnitTracker(group_elements, zone_name, el_type, order)
                    el_lines, consumed = renderer(
                        el_spec,
                        zx,
                        cy,
                        zw,
                        remaining,
                        posting_group=posting_group,
                        tracker=tracker,
                    )
                    if tracker.active:
                        tracker.close_unit(el_lines)
                    if tracker.units:
                        out.extend(el_lines)
                        units.extend(tracker.units)
                        order = tracker.order
                    else:
                        _open(zone_name, el_type)
                        out.extend(el_lines)
                        _close(zone_name, el_type)
                else:
                    el_lines, consumed = renderer(
                        el_spec, zx, cy, zw, remaining, posting_group=posting_group
                    )
                    _open(zone_name, el_type)
                    out.extend(el_lines)
                    _close(zone_name, el_type)

                if j < len(z_c["el_heights"]):
                    consumed = z_c["el_heights"][j]

                cy += consumed + el_gap

        out.append("</svg>")
        return "\n".join(out), units
