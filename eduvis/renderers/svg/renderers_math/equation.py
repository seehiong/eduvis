"""Math renderers: fraction_equation (horizontal equations with vertical fractions)."""

import re
from ..primitives import (
    COLORS,
    _line, _rect, _resolve_color, _text, _get_font_size,
)

def parse_term(term_val: str):
    # Try mixed fraction: e.g. "2 1/5"
    m_mixed = re.match(r"^(\d+)\s+(\d+|\?)/(\d+|\?)$", term_val)
    if m_mixed:
        return {
            "type": "mixed_fraction",
            "whole": m_mixed.group(1),
            "num": m_mixed.group(2),
            "den": m_mixed.group(3)
        }
    
    # Try simple fraction: e.g. "3/5" or "?/5"
    m_frac = re.match(r"^(\d+|\?)/(\d+|\?)$", term_val)
    if m_frac:
        return {
            "type": "fraction",
            "num": m_frac.group(1),
            "den": m_frac.group(2)
        }
    
    # Try operator
    if term_val in ("+", "-", "×", "÷", "*", "=", "x"):
        return {
            "type": "operator",
            "val": term_val
        }
        
    # Standard number / placeholder / label
    return {
        "type": "number",
        "val": term_val
    }

def _render_fraction_equation(spec, zx, zy, zw, zh, posting_group="G1") -> tuple[list[str], int]:
    """Draw a horizontal mathematical equation featuring vertical fractions."""
    terms_spec = spec.get("terms", [])
    if not terms_spec:
        return [], 0

    body_sz = _get_font_size("body", posting_group)
    fsize_main = int(body_sz * 1.5)  # e.g., 24px
    fsize_frac = int(body_sz * 1.1)  # e.g., 18px

    parsed_terms = []
    
    # Gap between terms
    gap = 20
    
    # Measure widths of all terms
    for term in terms_spec:
        color_name = "body"
        bold = False
        placeholder = False
        
        if isinstance(term, dict):
            val_str = str(term.get("val", term.get("value", "")))
            color_name = term.get("color", "body")
            bold = term.get("bold", False)
            placeholder = term.get("placeholder", False)
        else:
            val_str = str(term)
            if val_str == "?":
                placeholder = True
        
        color = _resolve_color(color_name)
        parsed = parse_term(val_str)
        parsed["color"] = color
        parsed["bold"] = bold
        parsed["placeholder"] = placeholder
        
        # Calculate width of the parsed term
        if parsed["type"] == "operator":
            val = parsed["val"]
            parsed["width"] = max(16, int(len(val) * fsize_main * 0.6))
        elif parsed["type"] == "number":
            val = parsed["val"]
            parsed["width"] = int(len(val) * fsize_main * 0.6)
        elif parsed["type"] == "fraction":
            num = parsed["num"]
            den = parsed["den"]
            nw = int(len(num) * fsize_frac * 0.6)
            dw = int(len(den) * fsize_frac * 0.6)
            parsed["width"] = max(nw, dw) + 16
        elif parsed["type"] == "mixed_fraction":
            whole = parsed["whole"]
            num = parsed["num"]
            den = parsed["den"]
            ww = int(len(whole) * fsize_main * 0.6)
            nw = int(len(num) * fsize_frac * 0.6)
            dw = int(len(den) * fsize_frac * 0.6)
            parsed["width"] = ww + 4 + max(nw, dw) + 16
            
        parsed_terms.append(parsed)

    # Compute total width
    total_w = sum(t["width"] for t in parsed_terms) + gap * (len(parsed_terms) - 1)
    
    # Start coordinates
    cx = zx + (zw - total_w) // 2
    cy = zy + 40  # Vertically offset inside zone
    
    out = []
    
    for term in parsed_terms:
        tw = term["width"]
        color = term["color"]
        weight = "bold" if term["bold"] else "normal"
        
        # If placeholder is True, draw a light background box around the term
        if term["placeholder"]:
            bx = cx - 4
            by = cy - 24
            bw = tw + 8
            bh = 48
            out.append(_rect(bx, by, bw, bh, fill="none", stroke=COLORS["grey"], stroke_w=1, rx=4))

        if term["type"] == "operator":
            val = term["val"]
            # Draw vertically centered operator
            mid_x = cx + tw // 2
            mid_y = cy + int(fsize_main * 0.3)
            out.append(_text(mid_x, mid_y, val, size=fsize_main, color=color, anchor="middle", weight="bold"))
            
        elif term["type"] == "number":
            val = term["val"]
            mid_x = cx + tw // 2
            mid_y = cy + int(fsize_main * 0.3)
            out.append(_text(mid_x, mid_y, val, size=fsize_main, color=color, anchor="middle", weight=weight))
            
        elif term["type"] == "fraction":
            num = term["num"]
            den = term["den"]
            mid_x = cx + tw // 2
            
            # Fraction line
            out.append(_line(cx, cy, cx + tw, cy, color=COLORS["body"], stroke_w=2))
            
            # Numerator
            ny = cy - int(fsize_frac * 0.4)
            out.append(_text(mid_x, ny, num, size=fsize_frac, color=color, anchor="middle", weight=weight))
            
            # Denominator
            dy = cy + int(fsize_frac * 1.0)
            out.append(_text(mid_x, dy, den, size=fsize_frac, color=color, anchor="middle", weight=weight))
            
        elif term["type"] == "mixed_fraction":
            whole = term["whole"]
            num = term["num"]
            den = term["den"]
            ww = int(len(whole) * fsize_main * 0.6)
            
            # Whole number part
            mid_whole_x = cx + ww // 2
            mid_y = cy + int(fsize_main * 0.3)
            out.append(_text(mid_whole_x, mid_y, whole, size=fsize_main, color=color, anchor="middle", weight=weight))
            
            # Fraction part
            frac_cx = cx + ww + 4
            frac_w = tw - ww - 4
            mid_frac_x = frac_cx + frac_w // 2
            
            # Fraction line
            out.append(_line(frac_cx, cy, frac_cx + frac_w, cy, color=COLORS["body"], stroke_w=2))
            
            # Numerator
            ny = cy - int(fsize_frac * 0.4)
            out.append(_text(mid_frac_x, ny, num, size=fsize_frac, color=color, anchor="middle", weight=weight))
            
            # Denominator
            dy = cy + int(fsize_frac * 1.0)
            out.append(_text(mid_frac_x, dy, den, size=fsize_frac, color=color, anchor="middle", weight=weight))

        cx += tw + gap

    consumed_h = 80
    return out, consumed_h


RENDERERS = {
    "fraction_equation": _render_fraction_equation,
}

from ..element_registry import SVGElementSpec, SVGFieldSpec  # noqa: E402

ELEMENT_SPECS: list[SVGElementSpec] = [
    SVGElementSpec(
        name="fraction_equation",
        subjects=["math"],
        synopsis="terms: [strings|objects] — horizontal math equation featuring vertical fractions",
        fields=[
            SVGFieldSpec("terms", type="array", required=True,
                         description="List of terms in the equation. Each term can be a string (e.g. '1/5', '+', '3/5', '=', '4/5', '2 1/5') "
                                     "or an object with properties: val, color, bold, placeholder"),
        ],
        notes=[],
        render_fn=_render_fraction_equation,
    ),
]

