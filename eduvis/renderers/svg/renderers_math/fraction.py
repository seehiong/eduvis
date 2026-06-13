"""Math renderers: fraction_model (circle/bar/grid) and bar_model (comparison bars)."""

import math

from ..primitives import (
    COLORS,
    _line, _rect, _resolve_color, _text, _get_font_size,
)


def _render_fraction_model(spec, zx, zy, zw, zh, posting_group="G1") -> tuple[list[str], int]:
    shape  = spec.get("shape", "circle")
    total  = max(1, int(spec.get("total_parts", 4)))
    shaded = min(total, int(spec.get("shaded_parts", 1)))
    color  = _resolve_color(spec.get("color", "green"))
    label  = spec.get("label", f"{shaded}/{total}")

    size_lbl = _get_font_size("body", posting_group) - 1

    out = []

    if shape == "circle":
        r   = min(spec.get("max_r", 70), min(zw, zh) // 2 - 10)
        ccx = zx + zw // 2
        ccy = zy + r + 10
        out.append(
            f'  <circle cx="{ccx}" cy="{ccy}" r="{r}" '
            f'fill="{COLORS["panel"]}" stroke="{color}" stroke-width="1.5" />'
        )
        angle_per = 2 * math.pi / total
        if shaded == total:
            out.append(
                f'  <circle cx="{ccx}" cy="{ccy}" r="{r}" '
                f'fill="{color}" opacity="0.6" />'
            )
        else:
            for i in range(shaded):
                a1 = -math.pi / 2 + i * angle_per
                a2 = a1 + angle_per
                x1 = round(ccx + r * math.cos(a1), 1)
                y1 = round(ccy + r * math.sin(a1), 1)
                x2 = round(ccx + r * math.cos(a2), 1)
                y2 = round(ccy + r * math.sin(a2), 1)
                out.append(
                    f'  <path d="M {ccx},{ccy} L {x1},{y1} A {r},{r} 0 0,1 {x2},{y2} Z" '
                    f'fill="{color}" opacity="0.7" />'
                )
        for i in range(total):
            a  = -math.pi / 2 + i * angle_per
            lx = round(ccx + r * math.cos(a), 1)
            ly = round(ccy + r * math.sin(a), 1)
            out.append(_line(ccx, ccy, lx, ly, color=COLORS["panel"], stroke_w=1.5))
        ly_label = ccy + r + 22
        out.append(_text(ccx, ly_label, label, size=size_lbl, color=color, anchor="middle"))
        return out, ly_label - zy + 10

    if shape == "bar":
        bw = zw - 20
        bh = 36
        out.append(_rect(zx + 10, zy + 8, bw, bh,
                          fill=COLORS["panel"], stroke=color, stroke_w=1.5, rx=4))
        sw = round(bw * shaded / total, 1)
        out.append(_rect(zx + 10, zy + 8, sw, bh, fill=color, stroke="none", rx=4))
        for i in range(1, total):
            dx = round(zx + 10 + bw * i / total, 1)
            out.append(_line(dx, zy + 8, dx, zy + 8 + bh,
                              color=COLORS["background"], stroke_w=1.5))
        out.append(_text(zx + zw // 2, zy + bh + 28, label, size=size_lbl,
                          color=color, anchor="middle"))
        return out, bh + 40

    # grid shape
    mult = spec.get("multiply")
    if mult and len(mult) == 4:
        num1, den1, num2, den2 = [int(v) for v in mult]
        rows = den1
        cols = den2
    else:
        best_diff = float("inf")
        rows, cols = 1, total
        limit = int(math.isqrt(total))
        for r_try in range(1, limit + 1):
            if total % r_try == 0:
                c_try = total // r_try
                if c_try - r_try < best_diff:
                    best_diff = c_try - r_try
                    rows = r_try
                    cols = c_try
    cell = min(28, (zw - 20) // max(1, cols), (zh - 30) // max(1, rows))
    gw   = cols * cell
    gh   = rows * cell
    gx   = zx + (zw - gw) // 2
    for row in range(rows):
        for col in range(cols):
            cx   = gx + col * cell
            cy   = zy + 8 + row * cell
            if mult and len(mult) == 4:
                is_row = row < num1
                is_col = col < num2
                if is_row and is_col:
                    fill = COLORS["green"]
                elif is_row:
                    fill = COLORS["blue"]
                elif is_col:
                    fill = COLORS["yellow"]
                else:
                    fill = COLORS["panel"]
            else:
                fill = color if (row * cols + col) < shaded else COLORS["panel"]
            out.append(_rect(cx, cy, cell - 2, cell - 2,
                               fill=fill, stroke=color, stroke_w=1, rx=2))
    out.append(_text(zx + zw // 2, zy + gh + 28, label, size=size_lbl,
                      color=color, anchor="middle"))
    return out, gh + 40


def _render_bar_model(spec, zx, zy, zw, zh, posting_group="G1") -> tuple[list[str], int]:
    bars     = spec.get("bars", [])
    diff     = spec.get("difference", {})
    style    = spec.get("style", "comparison")
    if not bars:
        return [], 0

    BAR_H    = 32
    GAP      = 14
    label_w  = 110
    bar_area = zw - label_w - 20
    max_val  = max((b.get("value", 1) for b in bars), default=1)
    try:
        max_val = float(max_val)
    except (TypeError, ValueError):
        max_val = 1.0

    size_lbl = _get_font_size("body", posting_group) - 2

    out       = []
    bar_rects = []  # (bar_x, bar_y, bar_w, bar_h) per bar
    cy        = zy + 8

    for bar in bars:
        label = bar.get("label", "")
        try:
            value = float(bar.get("value", 0))
        except (TypeError, ValueError):
            value = 0.0
        color = _resolve_color(bar.get("color", "cyan"))
        bw    = round(bar_area * value / max_val, 1)
        out.append(_text(zx, cy + BAR_H // 2 + 5, label, size=size_lbl, color=COLORS["body"]))
        out.append(_rect(zx + label_w, cy, bw, BAR_H,
                          fill=color, stroke=color, stroke_w=1, rx=3))
        out.append(_text(zx + label_w + bw + 8, cy + BAR_H // 2 + 5,
                          str(value), size=size_lbl, color=color))
        bar_rects.append((zx + label_w, cy, bw, BAR_H))
        cy += BAR_H + GAP

    if diff and len(bars) >= 2 and style == "comparison":
        lo_i     = 0 if bars[0].get("value", 0) <= bars[1].get("value", 0) else 1
        hi_i     = 1 - lo_i
        lo_bw    = bar_rects[lo_i][2]
        hi_bw    = bar_rects[hi_i][2]
        dcol     = _resolve_color(diff.get("color", "red"))
        brace_y  = bar_rects[lo_i][1] + BAR_H
        brace_x1 = zx + label_w + lo_bw
        brace_x2 = zx + label_w + hi_bw
        mid_x    = round((brace_x1 + brace_x2) / 2, 1)
        out.append(_line(brace_x1, brace_y - 6, brace_x1, brace_y + 6,
                          color=dcol, stroke_w=2))
        out.append(_line(brace_x1, brace_y, brace_x2, brace_y, color=dcol, stroke_w=2))
        out.append(_line(brace_x2, brace_y - 6, brace_x2, brace_y + 6,
                          color=dcol, stroke_w=2))
        out.append(_text(mid_x, brace_y - 12, diff.get("label", ""),
                          size=size_lbl, color=dcol, anchor="middle"))

    return out, cy - zy


RENDERERS = {
    "fraction_model": _render_fraction_model,
    "bar_model":      _render_bar_model,
}

from ..element_registry import SVGElementSpec, SVGFieldSpec  # noqa: E402

ELEMENT_SPECS: list[SVGElementSpec] = [
    SVGElementSpec(
        name="fraction_model",
        subjects=["math"],
        synopsis="shape: circle|bar|grid, total_parts, shaded_parts, color, label",
        fields=[
            SVGFieldSpec("shape", type="string", required=False, default="circle",
                         enum=["circle", "bar", "grid"],
                         description="Visual representation style"),
            SVGFieldSpec("total_parts", type="integer", required=True,
                         description="Total number of equal parts"),
            SVGFieldSpec("shaded_parts", type="integer", required=True,
                         description="Number of shaded (coloured) parts"),
            SVGFieldSpec("color", type="color", required=False, default="green"),
            SVGFieldSpec("label", type="string", required=False,
                         description="Caption below the model; defaults to 'shaded/total'"),
        ],
        notes=[],
        render_fn=_render_fraction_model,
    ),
    SVGElementSpec(
        name="bar_model",
        subjects=["math"],
        synopsis="bars: [{label, value, color}], difference: {label, color} (optional)",
        fields=[
            SVGFieldSpec(
                "bars", type="array", required=True,
                description="Comparison bars — list of bar dicts",
                items=SVGFieldSpec("bar", type="object", properties=[
                    SVGFieldSpec("label", type="string",
                                 description="Bar label; include units here e.g. 'Friend A = $5.00'"),
                    SVGFieldSpec("value", type="number",
                                 constraint="MUST be a plain number — WRONG: \"$5.00\"  RIGHT: 5"),
                    SVGFieldSpec("color", type="color"),
                ]),
            ),
            SVGFieldSpec("difference", type="object", required=False,
                         description="Bracket showing the gap between two bars",
                         properties=[
                             SVGFieldSpec("label", type="string"),
                             SVGFieldSpec("color", type="color"),
                         ]),
            SVGFieldSpec("style", type="string", required=False, default="comparison",
                         enum=["comparison"],
                         description="Rendering style"),
        ],
        notes=[
            "IMPORTANT: `value` MUST be a plain number (integer or float), NOT a formatted string.",
            "WRONG: value: \"$5.00\"  RIGHT: value: 5",
            "Dollar amounts and units belong in the `label` field.",
        ],
        render_fn=_render_bar_model,
    ),
]

