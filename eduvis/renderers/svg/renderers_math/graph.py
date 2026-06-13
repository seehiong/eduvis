"""Math renderer: coordinate_plane (Cartesian grid with line/point plots)."""

import re

from ..primitives import (
    COLORS,
    _line, _resolve_color, _text, _get_font_size,
)


def _parse_linear_eq(equation: str) -> tuple[float, float]:
    """Parse 'y = mx + b' into (m, b). Handles y=x, y=2x-1, y=-x+3."""
    rhs     = equation.replace(" ", "").lower().split("=", 1)[-1]
    m_match = re.search(r"(-?\d*\.?\d*)x", rhs)
    if m_match:
        m_str = m_match.group(1)
        m = float(m_str) if m_str not in ("", "-", "+") else (-1.0 if m_str == "-" else 1.0)
    else:
        m = 0.0
    b_match = re.search(r"x([+-]\d+\.?\d*)$", rhs) or re.search(r"^(-?\d+\.?\d*)$", rhs)
    b = float(b_match.group(1)) if b_match else 0.0
    return m, b


def _render_coordinate_plane(spec, zx, zy, zw, zh, posting_group="G1") -> tuple[list[str], int]:
    x_range   = spec.get("x_range", [-5, 5])
    y_range   = spec.get("y_range", [-5, 5])
    grid_step = spec.get("grid_step", 1)
    plots     = spec.get("plots", [])

    x_lo, x_hi = int(x_range[0]), int(x_range[1])
    y_lo, y_hi = int(y_range[0]), int(y_range[1])
    pad    = 28
    x_span = max(1, x_hi - x_lo)
    y_span = max(1, y_hi - y_lo)
    # Square grid sized from width (max 300px), never from zh — avoids dynamic-height explosion
    MAX_SIDE = min(zw - 2 * pad, 300)
    s    = MAX_SIDE / max(x_span, y_span)
    pw   = round(s * x_span, 1)
    ph   = round(s * y_span, 1)
    gx0  = zx + (zw - pw) / 2          # left edge of grid (centred)
    ox   = round(gx0 + (-x_lo) * s, 1) # canvas x for x=0
    oy   = round(zy + pad + y_hi * s, 1) # canvas y for y=0

    size_ann = _get_font_size("annotation", posting_group)

    out = []

    # Grid lines and tick labels
    for v in range(x_lo, x_hi + 1, grid_step):
        gx  = round(gx0 + (v - x_lo) * s, 1)
        col = COLORS["body"] if v == 0 else "#cbd5e1"
        sw  = 1.5 if v == 0 else 0.5
        out.append(_line(gx, zy + pad, gx, zy + pad + ph, color=col, stroke_w=sw))
        out.append(_text(gx, zy + pad + ph + 14, str(v), size=size_ann,
                          color=COLORS["body"], anchor="middle"))

    for v in range(y_lo, y_hi + 1, grid_step):
        gy  = round(zy + pad + (y_hi - v) * s, 1)
        col = COLORS["body"] if v == 0 else "#cbd5e1"
        sw  = 1.5 if v == 0 else 0.5
        out.append(_line(gx0, gy, gx0 + pw, gy, color=col, stroke_w=sw))
        if v != 0:
            out.append(_text(gx0 - 6, gy + 4, str(v), size=size_ann,
                               color=COLORS["body"], anchor="end"))

    # Axis arrowheads (tiny filled triangles)
    def _arrowhead(tip_x, tip_y, direction: str) -> str:
        a = 5.0
        if direction == "right":
            pts = f"{tip_x},{tip_y} {tip_x-a},{tip_y-a/2} {tip_x-a},{tip_y+a/2}"
        else:  # up
            pts = f"{tip_x},{tip_y} {tip_x-a/2},{tip_y+a} {tip_x+a/2},{tip_y+a}"
        return f'  <polygon points="{pts}" fill="{COLORS["body"]}" />'

    out.append(_arrowhead(gx0 + pw + 7, oy, "right"))
    out.append(_arrowhead(ox, zy + pad - 7, "up"))

    # Plots
    for plot in plots:
        ptype = plot.get("type", "")
        color = _resolve_color(plot.get("color", "cyan"))

        if ptype == "line":
            m, b = _parse_linear_eq(plot.get("equation", "y = x"))
            pts = [
                (round(gx0 + (xv - x_lo) * s, 1),
                 round(zy + pad + (y_hi - (m * xv + b)) * s, 1))
                for xv in (x_lo, x_hi)
                if y_lo <= m * xv + b <= y_hi
            ]
            if len(pts) == 2:
                out.append(_line(pts[0][0], pts[0][1], pts[1][0], pts[1][1],
                                  color=color, stroke_w=2))

        elif ptype == "point":
            coord = plot.get("coord", [0, 0])
            label = plot.get("label", "")
            px    = round(gx0 + (coord[0] - x_lo) * s, 1)
            py    = round(zy + pad + (y_hi - coord[1]) * s, 1)
            out.append(f'  <circle cx="{px}" cy="{py}" r="4" fill="{color}" />')
            if label:
                out.append(_text(px + 8, py - 6, label, size=size_ann + 1, color=color))

    return out, int(ph + 2 * pad)


RENDERERS = {
    "coordinate_plane": _render_coordinate_plane,
}

from ..element_registry import SVGElementSpec, SVGFieldSpec  # noqa: E402

ELEMENT_SPECS: list[SVGElementSpec] = [
    SVGElementSpec(
        name="coordinate_plane",
        subjects=["math"],
        synopsis="x_range, y_range, grid_step, plots: [{type, equation|coord, color}]",
        fields=[
            SVGFieldSpec("x_range", type="array", required=True,
                         description="[min, max] for the x-axis"),
            SVGFieldSpec("y_range", type="array", required=True,
                         description="[min, max] for the y-axis"),
            SVGFieldSpec("grid_step", type="integer", required=False, default=1,
                         description="Grid line interval"),
            SVGFieldSpec("plots", type="array", required=False,
                         description="List of line or point plot specs",
                         items=SVGFieldSpec("plot", type="object", properties=[
                             SVGFieldSpec("type", type="string", enum=["line", "point"]),
                             SVGFieldSpec("equation", type="string", required=False,
                                          description="Linear equation e.g. 'y=2x+1' (line only)"),
                             SVGFieldSpec("coord", type="array", required=False,
                                          description="[x, y] coordinate (point only)"),
                             SVGFieldSpec("label", type="string", required=False),
                             SVGFieldSpec("color", type="color", required=False),
                         ])),
        ],
        notes=[],
        render_fn=_render_coordinate_plane,
    ),
]

