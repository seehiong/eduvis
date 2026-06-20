"""
Base element renderers — original eight types.
Each renderer returns (list[svg_line_str], height_consumed_px).
"""

from .primitives import (
    COLORS, LEAD,
    _line, _rect, _resolve_color, _text, _wrap, _get_font_size,
)

_NUMBER_LINE_H = 90  # fixed vertical allocation for number_line


def _render_ribbon_box(zx, zy, zw, h, ribbon_type, label=None) -> list[str]:
    """
    Renders a premium flat card at (zx, zy) with width zw, height h.
    The card has a vertical ribbon on the left with text `label` (defaults to ribbon_type).
    Uses Material 3 / Tailwind container colors for maximum contrast.
    """
    themes = {
        "review":   {"bg": "#dcfce7", "border": "#86efac", "text": "#166534"},
        "remember": {"bg": "#dbeafe", "border": "#93c5fd", "text": "#1e40af"},
        "solve":    {"bg": "#ffedd5", "border": "#fdba74", "text": "#9a3412"},
    }
    theme = themes.get(ribbon_type, themes["solve"])
    text_label = (label or ribbon_type).upper()
    
    # Outer Card rounded rectangle
    out = [
        # Card Background (white) and border
        f'  <rect x="{zx}" y="{zy}" width="{zw}" height="{h}" rx="8" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.2" />',
    ]
    
    # Custom left-rounded ribbon shape sitting flush inside the card
    path_d = (
        f"M {zx+25} {zy+1} "
        f"L {zx+8} {zy+1} "
        f"A 7 7 0 0 0 {zx+1} {zy+8} "
        f"L {zx+1} {zy+h-8} "
        f"A 7 7 0 0 0 {zx+8} {zy+h-1} "
        f"L {zx+25} {zy+h-1} Z"
    )
    
    out.append(
        f'  <path d="{path_d}" fill="{theme["bg"]}" />'
    )
    
    # Thin divider line between ribbon and card content
    out.append(
        f'  <line x1="{zx+25}" y1="{zy+1}" x2="{zx+25}" y2="{zy+h-1}" stroke="{theme["border"]}" stroke-width="1" />'
    )
    
    # Vertical text inside the ribbon using dark theme text color
    tx = zx + 13
    ty = zy + h / 2
    out.append(
        f'  <text x="{tx}" y="{ty}" font-family="Arial, sans-serif" font-size="9.5" font-weight="bold" '
        f'fill="{theme["text"]}" text-anchor="middle" transform="rotate(-90, {tx}, {ty})">{text_label}</text>'
    )
    
    return out



def _render_number_line(spec, zx, zy, zw, zh, posting_group="G1", tracker=None) -> tuple[list[str], int]:
    rng    = spec.get("range", [-10, 10])
    lo     = float(rng[0])
    hi     = float(rng[1])
    diff   = hi - lo
    if diff <= 0.0:
        diff = 1.0
        hi = lo + 1.0

    hls    = spec.get("highlight", {})
    # highlight may be a single dict or a list of dicts (multiple points).
    if isinstance(hls, dict):
        hls = [hls] if hls else []
    elif not isinstance(hls, list):
        hls = []
    dlabs   = spec.get("direction_labels", {})
    # Optional caption titles the line so two stacked number_lines on one slide
    # (e.g. two contrasting worked examples) are each self-labelling.
    caption = spec.get("caption", "")
    cap_h   = 22 if caption else 0

    size_lbl = _get_font_size("annotation", posting_group)

    axis_y = zy + cap_h + _NUMBER_LINE_H // 2
    lx     = zx + 40
    rx     = zx + zw - 40
    pxp    = (rx - lx) / diff

    out  = []
    if tracker:
        tracker.open_unit(out, sub_type="number_line_base")

    if caption:
        out.append(_text(zx + zw / 2, zy + 14, caption,
                          size=size_lbl + 1, color=COLORS["heading"],
                          anchor="middle", weight="bold"))

    out.append(_line(lx, axis_y, rx, axis_y, color=COLORS["body"]))

    # Determine optimal step and tick values
    lo = float(lo)
    hi = float(hi)
    is_int_range = lo.is_integer() and hi.is_integer()
    if is_int_range and diff >= 1.0:
        int_candidates = [100, 50, 20, 10, 5, 2, 1]
        int_candidates = [c for c in int_candidates if c <= diff]
        if int_candidates:
            step = min(int_candidates, key=lambda c: abs(diff / c - 10))
        else:
            step = 1.0
    else:
        import math
        power = 10.0 ** math.floor(math.log10(diff))
        candidates = [power * 2, power, power / 2, power / 5, power / 10, power / 20, power / 50, power / 100]
        step = min(candidates, key=lambda c: abs(diff / c - 10))

    # Count decimals for formatting labels
    step = float(step)
    if step.is_integer() and lo.is_integer() and hi.is_integer():
        decimals = 0
    else:
        step_str = f"{step:.10f}".rstrip('0')
        if '.' in step_str:
            decimals = len(step_str.split('.')[1])
        else:
            decimals = 0

    # Generate ticks list safely
    ticks = []
    v = lo
    epsilon = step * 0.01
    while v <= hi + epsilon:
        ticks.append(round(v, decimals + 2))
        v += step

    for v in ticks:
        tx  = round(lx + (v - lo) * pxp, 1)
        col = COLORS["heading"] if abs(v) < 1e-9 else COLORS["body"]
        out.append(_line(tx, axis_y - 5, tx, axis_y + 5, color=col))
        lbl_str = f"{v:.{decimals}f}" if decimals > 0 else str(int(round(v)))
        out.append(_text(tx, axis_y + 18, lbl_str, size=size_lbl, color=col, anchor="middle"))

    if dlabs.get("left"):
        out.append(_text(lx, axis_y - 14, dlabs["left"],
                          size=size_lbl, color=COLORS["body"], anchor="middle"))
    if dlabs.get("right"):
        out.append(_text(rx, axis_y - 14, dlabs["right"],
                          size=size_lbl, color=COLORS["body"], anchor="middle"))

    if tracker:
        tracker.close_unit(out, sub_type="number_line_base")

    normal_hls = []
    jump_hls = []
    for hl in hls:
        if not isinstance(hl, dict):
            continue
        if hl.get("type") == "jump" or "step" in str(hl.get("label", "")).lower():
            jump_hls.append(hl)
        else:
            normal_hls.append(hl)

    # Sort highlights by value so left-to-right spacing checks are consistent
    sorted_normal_hls = sorted([hl for hl in normal_hls if isinstance(hl, dict)], key=lambda x: x.get("value", 0))
    # Map vertical level -> rightmost X boundary of the last placed label
    level_rights = {}
    if dlabs.get("left"):
        w_left = len(dlabs["left"]) * size_lbl * 0.55
        level_rights[0] = lx + w_left / 2

    # Colored band connecting the two outermost highlighted values
    band_str = ""
    if len(sorted_normal_hls) >= 2:
        v_band_lo = sorted_normal_hls[0].get("value", 0)
        v_band_hi = sorted_normal_hls[-1].get("value", 0)
        bx_lo = round(lx + (v_band_lo - lo) * pxp, 1)
        bx_hi = round(lx + (v_band_hi - lo) * pxp, 1)
        if bx_hi > bx_lo:
            band_str = (
                f'  <rect x="{bx_lo}" y="{axis_y - 6}" width="{round(bx_hi - bx_lo, 1)}" height="12" '
                f'rx="3" fill="#FFFFFF" opacity="0.12" />'
            )

    band_rendered = False
    for hl in sorted_normal_hls:
        if tracker:
            tracker.open_unit(out, sub_type="number_line_highlight")
        if band_str and not band_rendered:
            out.append(band_str)
            band_rendered = True
        hv   = hl.get("value", 0)
        hx   = round(lx + (hv - lo) * pxp, 1)
        hcol = _resolve_color(hl.get("color", "red"))
        
        label = hl.get("label", "")
        if label:
            lines = [ln.strip() for ln in str(label).split('\n') if ln.strip()]
            N = len(lines)
            max_ln_len = max(len(ln) for ln in lines)
            w = max_ln_len * (size_lbl + 1) * 0.55
            left_x = hx - w / 2
            right_x = hx + w / 2
            
            level = 0
            while True:
                collision = False
                for l in range(level, level + N):
                    if l in level_rights and level_rights[l] + 5 > left_x:
                        collision = True
                        break
                    if l == 0 and dlabs.get("right"):
                        w_right = len(dlabs["right"]) * size_lbl * 0.55
                        if right_x + 5 > rx - w_right / 2:
                            collision = True
                            break
                if not collision:
                    break
                level += 1
            
            for l in range(level, level + N):
                level_rights[l] = right_x
                
            y_offset = -20 - level * 14
            line_top = axis_y - 14 - level * 14
        else:
            lines = []
            N = 0
            y_offset = -20
            line_top = axis_y - 14

        out.append(_line(hx, line_top, hx, axis_y, color=hcol, stroke_w=2.5))
        if lines:
            lead_lbl = size_lbl + 4
            for idx, ln in enumerate(lines):
                ly = axis_y + y_offset - (N - 1 - idx) * lead_lbl
                out.append(_text(hx, ly, ln,
                                  size=size_lbl + 1, color=hcol, anchor="middle"))
        if tracker:
            tracker.close_unit(out, sub_type="number_line_highlight")

    current_start = normal_hls[0].get("value", 0) if normal_hls else lo
    has_single_jump = len(jump_hls) == 1

    for hl in jump_hls:
        if tracker:
            tracker.open_unit(out, sub_type="number_line_jump")
        hcol = _resolve_color(hl.get("color", "red"))
        
        val = hl.get("value", 0)
        
        if has_single_jump and len(normal_hls) >= 2:
            start_val = None
            end_val = None
            for nhl in normal_hls:
                lbl = str(nhl.get("label", "")).lower()
                if "start" in lbl:
                    start_val = nhl.get("value", 0)
                elif "end" in lbl:
                    end_val = nhl.get("value", 0)
            if start_val is None or end_val is None:
                v0 = normal_hls[0].get("value", 0)
                v1 = normal_hls[1].get("value", 0)
                if val >= 0:
                    start_val = min(v0, v1)
                    end_val = max(v0, v1)
                else:
                    start_val = max(v0, v1)
                    end_val = min(v0, v1)
        else:
            is_absolute = (lo <= val <= hi)
            if is_absolute:
                start_val = current_start
                end_val = val
                current_start = val
            elif len(normal_hls) >= 2:
                start_val = normal_hls[0].get("value", 0)
                end_val = normal_hls[1].get("value", 0)
            else:
                start_val = current_start
                end_val = val
            
        hx_start = round(lx + (start_val - lo) * pxp, 1)
        hx_end = round(lx + (end_val - lo) * pxp, 1)
        
        if hx_start != hx_end:
            hx_mid = round((hx_start + hx_end) / 2, 1)
            
            # Draw curved path from start to end
            out.append(
                f'  <path d="M {hx_start} {axis_y - 4} Q {hx_mid} {axis_y - 28} {hx_end} {axis_y - 4}" '
                f'fill="none" stroke="{hcol}" stroke-width="2" />'
            )
            # Draw arrowhead pointing in the correct direction with tangent alignment
            import math
            dx = hx_end - hx_start
            dy = 24.0 * 2.0  # tangent slope component (2 * vertical offset)
            L = math.sqrt(dx*dx + dy*dy)
            ux = dx / L
            uy = dy / L
            
            # Back of the arrow (8 pixels back along the tangent)
            bx = hx_end - 8.0 * ux
            by = (axis_y - 4) - 8.0 * uy
            
            # Normal vector to tangent
            px = -uy
            py = ux
            
            # Wings (4 pixels out)
            w1x = bx + 4.0 * px
            w1y = by + 4.0 * py
            w2x = bx - 4.0 * px
            w2y = by - 4.0 * py
            
            out.append(
                f'  <polygon points="{hx_end},{axis_y-4} {w1x:.1f},{w1y:.1f} {w2x:.1f},{w2y:.1f}" '
                f'fill="{hcol}" />'
            )
            # Draw the label above the apex of the curve
            if hl.get("label"):
                out.append(_text(hx_mid, axis_y - 34, hl["label"],
                                  size=size_lbl + 1, color=hcol, anchor="middle"))
        else:
            # Fallback to standard tick line if start and end are identical
            hx   = round(lx + (val - lo) * pxp, 1)
            out.append(_line(hx, axis_y - 14, hx, axis_y + 14, color=hcol, stroke_w=2.5))
            if hl.get("label"):
                out.append(_text(hx, axis_y - 20, hl["label"],
                                  size=size_lbl + 1, color=hcol, anchor="middle"))
        if tracker:
            tracker.close_unit(out, sub_type="number_line_jump")

    return out, _NUMBER_LINE_H + cap_h


def _render_text_list(spec, zx, zy, zw, zh, posting_group="G1", tracker=None) -> tuple[list[str], int]:
    items        = spec.get("items", [])
    out          = []
    size         = _get_font_size("body", posting_group)
    lead         = int(size * 1.5)
    cy           = zy + 16
    anchor       = spec.get("anchor", "start")
    custom_color = spec.get("color")

    dot_r   = 3
    dot_ox  = zx + dot_r + 2
    text_x  = zx + dot_r * 2 + 12
    text_bw = zw - dot_r * 2 - 16
    text_fw = zw - 10

    for item in items:
        if tracker:
            tracker.open_unit(out, sub_type="text_list_item")

        has_bullet   = True
        display_text = item
        math_operators = ("+", "=", "-", "*", "/", "×", "÷", "≠", "≈", "≄", "<", ">", "≤", "≥")
        if item.startswith("no-bullet:"):
            has_bullet   = False
            display_text = item[len("no-bullet:"):].strip()
        elif item.strip() in math_operators:
            has_bullet = False

        text_color   = COLORS["body"]
        bullet_color = COLORS["bullet"]
        if custom_color:
            c            = _resolve_color(custom_color)
            text_color   = c
            bullet_color = c

        is_operator = not has_bullet and display_text.strip() in math_operators
        item_size   = size + 6 if is_operator else size
        item_lead   = int(item_size * 1.4) if is_operator else lead

        # Extra breathing room before a no-bullet note line
        if not has_bullet and not is_operator:
            cy += size // 2

        lines = _wrap(display_text, text_bw if has_bullet else text_fw, item_size)

        for j, ln in enumerate(lines):
            if cy > zy + zh - 4:
                break
            if is_operator or anchor in ("middle", "center"):
                out.append(_text(zx + zw // 2, cy, ln, size=item_size, color=text_color,
                                  anchor="middle", weight="bold" if is_operator else "normal"))
            elif has_bullet:
                if j == 0:
                    dot_cy = cy - item_size // 2 + 1
                    out.append(f'  <circle cx="{dot_ox}" cy="{dot_cy}" r="{dot_r}" fill="{bullet_color}" />')
                out.append(_text(text_x, cy, ln, size=item_size, color=text_color))
            else:
                # no-bullet: same indent as bullet text, muted colour
                note_color = _resolve_color(custom_color) if custom_color else COLORS["grey"]
                out.append(_text(text_x, cy, ln, size=item_size, color=note_color))
            cy += item_lead

        if tracker:
            tracker.close_unit(out, sub_type="text_list_item")

    # Subtle left accent rail framing the entire list
    content_h = cy - zy - 8
    is_pure_operator = all(str(item).strip() in ("+", "=", "-", "*", "/", "×", "÷", "≠", "≈", "≄", "<", ">", "≤", "≥") for item in items)
    if content_h > 0 and not (anchor in ("middle", "center")) and not is_pure_operator:
        rail_color = _resolve_color(custom_color) if custom_color else COLORS["bullet"]
        rail_str = (
            f'  <rect x="{zx}" y="{zy + 8}" width="2" height="{content_h}" '
            f'rx="1" fill="{rail_color}" opacity="0.35" />'
        )
        if tracker and tracker.group_elements and len(out) > 0:
            out.insert(1, rail_str)
        else:
            out.insert(0, rail_str)

    return out, cy - zy


def _render_fact_boxes(spec, zx, zy, zw, zh, posting_group="G1", tracker=None) -> tuple[list[str], int]:
    items = spec.get("items", [])
    if not items:
        return [], 0

    gap      = 12
    box_h    = min(90, max(55, (zh - gap * (len(items) - 1)) // len(items)))
    stripe_w = 5
    text_x   = zx + stripe_w + 14
    text_w   = zw - stripe_w - 28

    # Two candidate sizes: large for short facts, body for longer text
    size_lg = _get_font_size("body", posting_group) + 8
    size_sm = _get_font_size("body", posting_group)
    lead_lg = int(size_lg * 1.35)
    lead_sm = int(size_sm * 1.35)

    out = []
    cy  = zy

    for item in items:
        if tracker:
            tracker.open_unit(out, sub_type="fact_box_item")

        # Accept both 'color' and 'border_color' field names
        color_name = item.get("color") or item.get("border_color") or "cyan"
        accent = _resolve_color(color_name)
        text   = item.get("text", "")

        # Use large size when text fits on one line, fall back to body size
        lines_lg = _wrap(text, text_w, size_lg)
        if len(lines_lg) == 1:
            lines, size, lead = lines_lg, size_lg, lead_lg
        else:
            lines, size, lead = _wrap(text, text_w, size_sm), size_sm, lead_sm

        # Tinted background
        out.append(
            f'  <rect x="{zx}" y="{cy}" width="{zw}" height="{box_h}" '
            f'rx="8" fill="{accent}" opacity="0.07" />'
        )
        # Hairline border
        out.append(
            f'  <rect x="{zx}" y="{cy}" width="{zw}" height="{box_h}" '
            f'rx="8" fill="none" stroke="{accent}" stroke-width="1" opacity="0.3" />'
        )
        # Left accent stripe — inset slightly for breathing room
        out.append(
            f'  <rect x="{zx}" y="{cy + 8}" width="{stripe_w}" height="{box_h - 16}" '
            f'rx="2" fill="{accent}" />'
        )

        # Text vertically centred in the box
        total_h = len(lines) * lead
        ty = cy + (box_h - total_h) // 2 + size - 2
        for ln in lines:
            if ty > cy + box_h - 4:
                break
            out.append(_text(text_x, ty, ln, size=size, color=accent, weight="bold"))
            ty += lead

        if tracker:
            tracker.close_unit(out, sub_type="fact_box_item")
        cy += box_h + gap

    return out, cy - zy


def _render_example_panel(spec, zx, zy, zw, zh, posting_group="G1", tracker=None) -> tuple[list[str], int]:
    items = spec.get("items", [])
    if not items:
        return [], 0
    n   = len(items)
    gap = 16
    bw  = (zw - gap * (n - 1)) // n
    out = []
    cx  = zx
    size_body = _get_font_size("body", posting_group)
    size_head = _get_font_size("label", posting_group)
    lead      = int(size_body * 1.4)
    
    # Calculate required height dynamically based on the text contents
    max_h = 50
    for item in items:
        body = str(item.get("body", ""))
        segments = body.split("\n")
        total_lines = 0
        for seg in segments:
            total_lines += len(_wrap(seg, bw - 32, size_body))
        extra_gaps = max(0, len(segments) - 1) * int(lead * 0.5)
        item_h = 46 + total_lines * lead + extra_gaps + 16
        if item_h > max_h:
            max_h = item_h
    h = min(zh, max_h)

    for item in items:
        if tracker:
            tracker.open_unit(out, sub_type="example_panel_item")
            
        # Determine accent color based on content
        heading_lower = str(item.get("heading", "")).lower()
        body_lower = str(item.get("body", "")).lower()
        if "mistake" in heading_lower or "wrong" in heading_lower or "mistake" in body_lower or "wrong" in body_lower:
            accent_color = COLORS["red"]
        elif "correct" in heading_lower or "right" in heading_lower or "think" in heading_lower or "correct" in body_lower:
            accent_color = COLORS["green"]
        else:
            accent_color = COLORS["blue"]

        # Main panel container with a visible grey border
        out.append(
            f'  <rect x="{cx}" y="{zy}" width="{bw}" height="{h}" rx="8" fill="#ffffff" stroke="#cbd5e1" stroke-width="1.2" />'
        )
        # Top colored accent bar cap conforming to the rounded corners
        out.append(
            f'  <path d="M {cx+1} {zy+4} A 3 3 0 0 1 {cx+4} {zy+1} L {cx+bw-4} {zy+1} A 3 3 0 0 1 {cx+bw-4} {zy+1} A 3 3 0 0 1 {cx+bw-1} {zy+4} L {cx+bw-1} {zy+6} L {cx+1} {zy+6} Z" fill="{accent_color}" />'
        )
        
        # Panel header text
        out.append(_text(cx + 16, zy + 26, item.get("heading", ""),
                          size=size_head, color=COLORS["heading"], weight="bold"))
        
        ty = zy + 46
        # Honor explicit line breaks (\n) between worked-example steps; wrap each
        # segment independently so a multi-line body renders as separate lines.
        body = str(item.get("body", ""))
        segments = body.split("\n")
        for idx, seg in enumerate(segments):
            lines = _wrap(seg, bw - 32, size_body)
            for ln in lines:
                if ty > zy + h - 6:
                    break
                out.append(_text(cx + 16, ty, ln, size=size_body, color=COLORS["body"]))
                ty += lead
            # Add an extra 0.5 * lead space between segments/sentences to simulate a 1.5 line spacing
            if idx < len(segments) - 1:
                ty += int(lead * 0.5)
            
        if tracker:
            tracker.close_unit(out, sub_type="example_panel_item")
        cx += bw + gap
    return out, h


def _render_callout_box(spec, zx, zy, zw, zh, posting_group="G1") -> tuple[list[str], int]:
    title   = spec.get("title", "")
    lines   = spec.get("lines", [])

    size_body  = _get_font_size("body", posting_group)
    size_title = size_body + 2
    lead       = int(size_body * 1.5)
    pad        = 36
    text_w     = zw - pad - 16

    # Determine ribbon type (default to remember for callout boxes)
    ribbon_type = "remember"
    
    n_wrapped = sum(len(_wrap(ln, text_w, size_body)) for ln in lines)
    h = min(zh, max(60, (size_title + 14 if title else 0) + n_wrapped * lead + 24))

    out = _render_ribbon_box(zx, zy, zw, h, ribbon_type, label=spec.get("ribbon_label", "remember"))

    ty = zy + size_title + 12
    if title:
        out.append(_text(zx + pad, ty, title,
                          size=size_title, color=COLORS["title"], weight="bold"))
        ty += lead + 4

    for ln_text in lines:
        for ln in _wrap(ln_text, text_w, size_body):
            if ty > zy + h - 6:
                break
            out.append(_text(zx + pad, ty, ln, size=size_body, color=COLORS["body"]))
            ty += lead

    return out, h



def _render_summary_list(spec, zx, zy, zw, zh, posting_group="G1") -> tuple[list[str], int]:
    return _render_text_list(spec, zx, zy, zw, zh, posting_group=posting_group)


def _render_multiple_choice(spec, zx, zy, zw, zh, posting_group="G1") -> tuple[list[str], int]:
    question = spec.get("question", "")
    options  = spec.get("options", {})
    
    # Check placement for ribbon type
    placement = spec.get("placement", {})
    phase = str(placement.get("lesson_phase", "")).lower()
    role = str(placement.get("memory_role", "")).lower()
    
    if phase == "recall" or role in ("retrieval", "review"):
        ribbon_type = "review"
    else:
        ribbon_type = "solve"
        
    size_q   = _get_font_size("label", posting_group) + 1
    size_opt = _get_font_size("body", posting_group)
    lead_q   = int(size_q * 1.4)
    lead_opt = int(size_opt * 1.4)
    
    pad = 36
    inner_w = zw - pad - 16
    
    # Calculate question height
    q_lines = _wrap(question, inner_w, size_q)
    q_h = len(q_lines) * lead_q
    
    labels = sorted(options.keys()) if isinstance(options, dict) else []
    is_tf = len(labels) == 2 and set(l.lower() for l in labels) == {"true", "false"}
    
    if is_tf:
        # Side-by-side buttons for True and False
        tf_order = []
        if "True" in options and "False" in options:
            tf_order = ["True", "False"]
        elif "true" in options and "false" in options:
            tf_order = ["true", "false"]
        else:
            tf_order = sorted(labels, key=lambda x: x.lower() == "false")

        btn_w = (inner_w - 16) // 2
        btn_h = 44
        
        student_ans = spec.get("student_answer") or spec.get("answer")
        correct_ans = spec.get("correct_answer")
        
        feedback_text = ""
        if student_ans is not None:
            feedback_val = options.get(student_ans, "")
            if feedback_val and feedback_val.lower() not in {"true", "false"}:
                feedback_text = feedback_val

        feedback_lines = []
        feedback_h = 0
        if feedback_text:
            feedback_lines = _wrap(feedback_text, inner_w - 48, size_opt)
            feedback_h = len(feedback_lines) * lead_opt + 16

        h = min(zh, q_h + 20 + btn_h + (16 + feedback_h if feedback_text else 0) + 24)
        
        out = _render_ribbon_box(zx, zy, zw, h, ribbon_type, label=spec.get("ribbon_label", ribbon_type))
        
        # Render question
        cy = zy + 16 + size_q
        for ln in q_lines:
            out.append(_text(zx + pad, cy, ln, size=size_q,
                              color=COLORS["heading"], weight="bold"))
            cy += lead_q
        cy += 12
        
        # Render buttons side-by-side
        for i, lbl in enumerate(tf_order):
            bx_start = zx + pad + i * (btn_w + 16)
            by = cy + btn_h // 2
            
            is_student = (student_ans is not None and lbl.lower() == student_ans.lower())
            is_correct = (correct_ans is not None and lbl.lower() == correct_ans.lower())
            
            is_green = False
            is_red = False
            is_blue = False
            
            if student_ans is not None and correct_ans is not None:
                # Review state
                if is_student and student_ans.lower() == correct_ans.lower():
                    is_green = True
                elif is_student:
                    is_red = True
                elif is_correct:
                    is_green = True
            elif phase == "explain":
                # Concept explanation / truth model -> show correct as green, others unselected
                if lbl.lower() == spec.get("answer", "").lower():
                    is_green = True
            else:
                # Normal state
                is_sel = False
                if is_sel:
                    is_blue = True
                    
            if is_green:
                bg_color = "#f0fdf4"      # Soft green bg (Emerald-50)
                stroke_color = "#10b981"  # Emerald-500
                text_color = "#047857"    # Emerald-700
                has_dot = True
                dot_color = "#10b981"
            elif is_red:
                bg_color = "#fef2f2"      # Soft red bg (Red-50)
                stroke_color = "#ef4444"  # Red-500
                text_color = "#b91c1c"    # Red-700
                has_dot = True
                dot_color = "#ef4444"
            elif is_blue:
                bg_color = "#eff6ff"      # Soft blue bg (Blue-50)
                stroke_color = "#3b82f6"  # Blue-500
                text_color = "#1d4ed8"    # Blue-700
                has_dot = True
                dot_color = "#3b82f6"
            else:
                bg_color = "#f8fafc"      # Soft grey bg (Slate-50)
                stroke_color = "#cbd5e1"  # Slate-300
                text_color = "#475569"    # Slate-600
                has_dot = False
                dot_color = "#cbd5e1"
            
            # Draw premium button box
            out.append(f'  <rect x="{bx_start}" y="{cy}" width="{btn_w}" height="{btn_h}" rx="8" fill="{bg_color}" stroke="{stroke_color}" stroke-width="1.5" />')
            
            # Draw radio circle indicator on the left
            r_cx = bx_start + 22
            out.append(f'  <circle cx="{r_cx}" cy="{by}" r="7" fill="none" stroke="{stroke_color}" stroke-width="1.5" />')
            if has_dot:
                out.append(f'  <circle cx="{r_cx}" cy="{by}" r="4" fill="{dot_color}" />')
                
            # Draw choice label text
            out.append(_text(bx_start + 38, by + 4.5, lbl, size=size_opt + 1, color=text_color, weight="bold"))
            
        cy += btn_h
        
        if feedback_text:
            cy += 16
            is_student_correct = False
            if student_ans is not None:
                if correct_ans is not None:
                    is_student_correct = (student_ans.lower() == correct_ans.lower())
                else:
                    is_student_correct = (student_ans.lower() == spec.get("answer", "").lower())
                    
            f_color = COLORS["green"] if is_student_correct else COLORS["red"]
            f_bg = "#f0fdf4" if is_student_correct else "#fef2f2"
            f_stroke = "#10b981" if is_student_correct else "#ef4444"
            
            # Draw premium alert card
            out.append(f'  <rect x="{zx + pad}" y="{cy}" width="{inner_w}" height="{feedback_h}" rx="8" fill="{f_bg}" opacity="0.5" />')
            out.append(f'  <rect x="{zx + pad}" y="{cy}" width="{inner_w}" height="{feedback_h}" rx="8" fill="none" stroke="{f_stroke}" stroke-width="1.2" opacity="0.4" />')
            out.append(f'  <rect x="{zx + pad}" y="{cy + 2}" width="4" height="{feedback_h - 4}" rx="2" fill="{f_stroke}" />')
            
            # Left icon (circle with white tick or cross)
            icon_cx = zx + pad + 24
            icon_cy = cy + feedback_h // 2
            out.append(f'  <circle cx="{icon_cx}" cy="{icon_cy}" r="9" fill="{f_stroke}" />')
            if is_student_correct:
                out.append(f'  <path d="M {icon_cx - 4} {icon_cy} L {icon_cx - 1} {icon_cy + 3} L {icon_cx + 4} {icon_cy - 3}" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />')
            else:
                out.append(f'  <path d="M {icon_cx - 3} {icon_cy - 3} L {icon_cx + 3} {icon_cy + 3} M {icon_cx + 3} {icon_cy - 3} L {icon_cx - 3} {icon_cy + 3}" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" />')
            
            ty = cy + (feedback_h - len(feedback_lines) * lead_opt) // 2 + size_opt - 1
            for ln in feedback_lines:
                out.append(_text(zx + pad + 44, ty, ln, size=size_opt, color=f_color, weight="bold"))
                ty += lead_opt
                
        return out, h
        
    # Calculate options layout dynamically for 2 to 5 options
    if not labels:
        labels = ["A", "B", "C", "D"]
        
    pairs = [labels[i:i+2] for i in range(0, len(labels), 2)]
    
    badge_r  = 11
    col_gap  = 16
    opt_w    = (inner_w - col_gap) // 2
    
    # Calculate max badge label length to decide if we need pill badges
    max_lbl_len = max(len(str(lbl)) for lbl in labels) if labels else 1
    if max_lbl_len > 1:
        badge_w = max_lbl_len * 7 + 14
        text_off = 8 + badge_w + 8
    else:
        badge_w = badge_r * 2
        text_off = 8 + badge_w + 8
        
    text_w   = opt_w - text_off - 8
    row_sep  = 12
    
    wrapped = {lbl: _wrap(str(options.get(lbl, "")), text_w, size_opt) or [""]
               for lbl in labels}
               
    row_heights = []
    for pair in pairs:
        max_lines = max(len(wrapped[lbl]) for lbl in pair)
        row_h = max(badge_r * 2 + 8, max_lines * lead_opt + 8)
        row_heights.append(row_h)
        
    total_options_h = sum(row_heights) + row_sep * (len(pairs) - 1)
    
    # Total card height
    h = min(zh, q_h + 20 + total_options_h + 24)
    
    out = _render_ribbon_box(zx, zy, zw, h, ribbon_type, label=spec.get("ribbon_label", ribbon_type))
    
    # Render question
    cy = zy + 16 + size_q
    for ln in q_lines:
        out.append(_text(zx + pad, cy, ln, size=size_q,
                          color=COLORS["heading"], weight="bold"))
        cy += lead_q
    cy += 10
    
    # Render options
    for r_idx, pair in enumerate(pairs):
        row_h = row_heights[r_idx]
        for i, lbl in enumerate(pair):
            ox = zx + pad + i * (opt_w + col_gap)
            by = cy + row_h // 2
            
            # Determine selection/highlight
            student_ans = spec.get("student_answer") or spec.get("answer")
            correct_ans = spec.get("correct_answer")
            
            is_student = (student_ans is not None and lbl == student_ans)
            is_correct = (correct_ans is not None and lbl == correct_ans)
            
            if student_ans is not None and correct_ans is not None:
                # Review state (red/green highlights)
                if is_student and student_ans == correct_ans:
                    bg_color = "#f0fdf4"      # Soft green bg
                    stroke_color = "#22c55e"  # Green border
                    badge_bg = "#22c55e"
                    badge_fg = "#ffffff"
                    text_color = "#14532d"
                elif is_student:
                    bg_color = "#fef2f2"      # Soft red bg
                    stroke_color = "#ef4444"  # Red border
                    badge_bg = "#ef4444"
                    badge_fg = "#ffffff"
                    text_color = "#7f1d1d"
                elif is_correct:
                    bg_color = "#f0fdf4"      # Soft green bg
                    stroke_color = "#22c55e"  # Green border
                    badge_bg = "#22c55e"
                    badge_fg = "#ffffff"
                    text_color = "#14532d"
                else:
                    bg_color = "#ffffff"
                    stroke_color = "#e2e8f0"
                    badge_bg = "#f1f5f9"
                    badge_fg = "#64748b"
                    text_color = COLORS["body"]
            else:
                # Normal state
                is_sel = False
                if is_sel:
                    bg_color = "#f0f9ff"      # Soft blue
                    stroke_color = "#3b82f6"  # Blue border
                    badge_bg = "#3b82f6"
                    badge_fg = "#ffffff"
                    text_color = "#1e3a8a"
                else:
                    bg_color = "#ffffff"
                    stroke_color = "#e2e8f0"
                    badge_bg = "#f1f5f9"
                    badge_fg = "#64748b"
                    text_color = COLORS["body"]
                    
            # Draw option card
            out.append(f'  <rect x="{ox}" y="{cy}" width="{opt_w}" height="{row_h}" rx="6" fill="{bg_color}" stroke="{stroke_color}" stroke-width="1.5" />')
            
            # Draw badge
            if len(str(lbl)) > 1:
                # Pill badge
                lbl_badge_w = len(str(lbl)) * 7 + 14
                bx_start = ox + 8
                bx = bx_start + lbl_badge_w // 2
                out.append(f'  <rect x="{bx_start}" y="{by - badge_r}" width="{lbl_badge_w}" height="{badge_r * 2}" rx="{badge_r}" fill="{badge_bg}" />')
                out.append(_text(bx, by + 3.5, lbl, size=size_opt - 1, color=badge_fg, weight="bold", anchor="middle"))
            else:
                # Circle badge
                cx = ox + 8 + badge_r
                out.append(f'  <circle cx="{cx}" cy="{by}" r="{badge_r}" fill="{badge_bg}" />')
                out.append(_text(cx, by + 3.5, lbl, size=size_opt, color=badge_fg, weight="bold", anchor="middle"))
            
            # Draw option text
            ty = cy + (row_h - len(wrapped[lbl]) * lead_opt) // 2 + size_opt - 1
            for ln in wrapped[lbl]:
                out.append(_text(ox + text_off + 4, ty, ln, size=size_opt, color=text_color))
                ty += lead_opt
                
        cy += row_h + row_sep
        
    return out, h


def _render_short_answer(spec, zx, zy, zw, zh, posting_group="G1") -> tuple[list[str], int]:
    question = spec.get("question", "")
    answer = spec.get("answer", "")
    student_ans = spec.get("student_answer") or spec.get("answer") if spec.get("student_answer") is not None else None
    
    # Check placement for ribbon type
    placement = spec.get("placement", {})
    phase = str(placement.get("lesson_phase", "")).lower()
    role = str(placement.get("memory_role", "")).lower()
    
    if phase == "recall" or role in ("retrieval", "review"):
        ribbon_type = "review"
    else:
        ribbon_type = "solve"
        
    size_q   = _get_font_size("label", posting_group) + 1
    size_opt = _get_font_size("body", posting_group)
    lead_q   = int(size_q * 1.4)
    lead_opt = int(size_opt * 1.4)
    
    pad = 36
    inner_w = zw - pad - 16
    
    # Calculate question height
    q_lines = _wrap(question, inner_w, size_q)
    q_h = len(q_lines) * lead_q
    
    input_h = 44
    feedback_text = ""
    is_correct = False
    
    if student_ans is not None:
        from eduvis.core.engine import check_answer
        res = check_answer(spec, student_ans)
        is_correct = res.get("is_correct", False)
        
        # We can show feedback text.
        feedback_val = spec.get("feedback")
        if feedback_val:
            feedback_text = feedback_val
        elif is_correct:
            feedback_text = "Correct!"
        else:
            feedback_text = f"Incorrect. The correct answer is: {answer}"
            
    feedback_lines = []
    feedback_h = 0
    if feedback_text:
        feedback_lines = _wrap(feedback_text, inner_w - 48, size_opt)
        feedback_h = len(feedback_lines) * lead_opt + 16

    h = min(zh, q_h + 20 + input_h + (16 + feedback_h if feedback_text else 0) + 24)
    
    out = _render_ribbon_box(zx, zy, zw, h, ribbon_type, label=spec.get("ribbon_label", ribbon_type))
    
    # Render question
    cy = zy + 16 + size_q
    for ln in q_lines:
        out.append(_text(zx + pad, cy, ln, size=size_q,
                          color=COLORS["heading"], weight="bold"))
        cy += lead_q
    cy += 12
    
    # Render input box
    if student_ans is not None:
        stroke_color = "#10b981" if is_correct else "#ef4444"
        bg_color = "#f0fdf4" if is_correct else "#fef2f2"
        text_color = "#047857" if is_correct else "#b91c1c"
        val_text = student_ans
    else:
        stroke_color = "#cbd5e1"  # Slate-300
        bg_color = "#f8fafc"      # Slate-50
        text_color = "#94a3b8"    # Slate-400 (placeholder color)
        val_text = "Type your answer here..."
        
    out.append(f'  <rect x="{zx + pad}" y="{cy}" width="{inner_w}" height="{input_h}" rx="8" fill="{bg_color}" stroke="{stroke_color}" stroke-width="1.5" />')
    
    # Text inside input box
    by = cy + input_h // 2 + size_opt // 2 - 1
    out.append(_text(zx + pad + 14, by, val_text, size=size_opt, color=text_color))
    
    cy += input_h
    
    # Render feedback block if present
    if feedback_text:
        cy += 16
        f_color = COLORS["green"] if is_correct else COLORS["red"]
        f_bg = "#f0fdf4" if is_correct else "#fef2f2"
        f_stroke = "#10b981" if is_correct else "#ef4444"
        
        out.append(f'  <rect x="{zx + pad}" y="{cy}" width="{inner_w}" height="{feedback_h}" rx="8" fill="{f_bg}" opacity="0.5" />')
        out.append(f'  <rect x="{zx + pad}" y="{cy}" width="{inner_w}" height="{feedback_h}" rx="8" fill="none" stroke="{f_stroke}" stroke-width="1.2" opacity="0.4" />')
        out.append(f'  <rect x="{zx + pad}" y="{cy + 2}" width="4" height="{feedback_h - 4}" rx="2" fill="{f_stroke}" />')
        
        # Left icon (circle with white tick or cross)
        icon_cx = zx + pad + 24
        icon_cy = cy + feedback_h // 2
        out.append(f'  <circle cx="{icon_cx}" cy="{icon_cy}" r="9" fill="{f_stroke}" />')
        if is_correct:
            out.append(f'  <path d="M {icon_cx - 4} {icon_cy} L {icon_cx - 1} {icon_cy + 3} L {icon_cx + 4} {icon_cy - 3}" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />')
        else:
            out.append(f'  <path d="M {icon_cx - 3} {icon_cy - 3} L {icon_cx + 3} {icon_cy + 3} M {icon_cx + 3} {icon_cy - 3} L {icon_cx - 3} {icon_cy + 3}" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" />')
        
        ty = cy + (feedback_h - len(feedback_lines) * lead_opt) // 2 + size_opt - 1
        for ln in feedback_lines:
            out.append(_text(zx + pad + 44, ty, ln, size=size_opt, color=f_color, weight="bold"))
            ty += lead_opt
            
    return out, h


def _render_remediation_block(spec, zx, zy, zw, zh, posting_group="G1") -> tuple[list[str], int]:
    from .renderers_math import RENDERERS as math_renderers
    
    # Merged renderers lookup
    all_renderers = {**RENDERERS, **math_renderers}
    
    gap = 16
    left_w = int(zw * 0.46)
    right_w = zw - left_w - gap
    
    out = []
    
    # 1. Render Review on the left:
    review = spec.get("review", {})
    q_spec = review.get("question_spec")
    
    left_h_consumed = 0
    if q_spec and isinstance(q_spec, dict):
        q_spec = q_spec.copy()
        q_spec["student_answer"] = review.get("student_answer")
        q_spec["correct_answer"] = review.get("correct_answer")
        if "placement" not in q_spec:
            q_spec["placement"] = spec.get("placement", {})
            
        q_type = q_spec.get("type", "")
        q_renderer = all_renderers.get(q_type)
        if q_renderer:
            q_out, left_h_consumed = q_renderer(q_spec, zx, zy, left_w, zh, posting_group=posting_group)
            out.extend(q_out)
            
    # 2. Render Remember (right top) and Solve (right bottom) on the right:
    remember_spec = spec.get("remember", {})
    solve_spec = spec.get("solve", {})
    
    rx = zx + left_w + gap
    
    remember_h = 0
    rem_type = remember_spec.get("type", "")
    rem_renderer = all_renderers.get(rem_type)
    
    solve_h = 0
    sol_type = solve_spec.get("type", "")
    sol_renderer = all_renderers.get(sol_type)
    
    # Dynamic height calculations
    if rem_renderer:
        try:
            _, rem_nat_h = rem_renderer(remember_spec, rx, zy, right_w, zh, posting_group=posting_group)
        except Exception:
            rem_nat_h = 100
        remember_h = rem_nat_h
        
    if sol_renderer:
        try:
            _, sol_nat_h = sol_renderer(solve_spec, rx, zy, right_w, zh, posting_group=posting_group)
        except Exception:
            sol_nat_h = 120
        solve_h = sol_nat_h
        
    right_total_h = remember_h + gap + solve_h
    total_h = max(left_h_consumed, right_total_h)
    total_h = min(zh, total_h)
    
    if rem_renderer:
        rem_spec_render = remember_spec.copy()
        if "ribbon_label" not in rem_spec_render:
            rem_spec_render["ribbon_label"] = "remember"
        if "ribbon_type" not in rem_spec_render:
            rem_spec_render["ribbon_type"] = "remember"
        rem_out, _ = rem_renderer(rem_spec_render, rx, zy, right_w, remember_h, posting_group=posting_group)
        out.extend(rem_out)
        
    if sol_renderer:
        sol_spec_render = solve_spec.copy()
        if "ribbon_label" not in sol_spec_render:
            sol_spec_render["ribbon_label"] = "solve"
        if "ribbon_type" not in sol_spec_render:
            sol_spec_render["ribbon_type"] = "solve"
        sol_out, _ = sol_renderer(sol_spec_render, rx, zy + remember_h + gap, right_w, solve_h, posting_group=posting_group)
        out.extend(sol_out)
        
    return out, total_h


def _render_hint_list(spec, zx, zy, zw, zh, posting_group="G1") -> tuple[list[str], int]:
    items = spec.get("items", [])
    final = spec.get("final", "")
    
    size  = _get_font_size("body", posting_group)
    lead  = int(size * 1.5)
    pad   = 36
    inner_w = zw - pad - 16

    step_r   = 11
    step_col = "#f97316" # Orange for solve
    
    # Pre-calculate rows height
    row_heights = []
    for item in items:
        lines = _wrap(item, inner_w - (step_r * 2 + 16), size)
        row_h = max(step_r * 2 + 10, len(lines) * lead + 8)
        row_heights.append((lines, row_h))
        
    final_h = 0
    fin_lines = []
    if final:
        fin_lines = _wrap(final, inner_w - 24, size - 1)
        final_h = 14 + len(fin_lines) * lead + 16
        
    total_h = 24 + sum(h for _, h in row_heights) + (14 + final_h if final else 0)
    h = min(zh, total_h)
    
    # We render MCQ/Hint list in 'solve' or 'remember' ribbon
    ribbon_type = "solve"
    out = _render_ribbon_box(zx, zy, zw, h, ribbon_type, label=spec.get("ribbon_label", ribbon_type))
    
    cy = zy + 16
    last_bottom = None
    
    for i, (lines, row_h) in enumerate(row_heights, start=1):
        step_cx = zx + pad + step_r + 4
        text_x  = step_cx + step_r + 12
        step_y  = cy + step_r
        
        if last_bottom is not None:
            out.append(
                f'  <line x1="{step_cx}" y1="{last_bottom}" x2="{step_cx}" y2="{step_y - step_r}" '
                f'stroke="{step_col}" stroke-width="1.2" opacity="0.3" stroke-dasharray="3 3" />'
            )
            
        out.append(f'  <circle cx="{step_cx}" cy="{step_y}" r="{step_r}" fill="{step_col}" opacity="0.15" />')
        out.append(f'  <circle cx="{step_cx}" cy="{step_y}" r="{step_r}" fill="none" stroke="{step_col}" stroke-width="1.5" />')
        out.append(_text(step_cx, step_y + 4, str(i), size=size - 1, color=step_col,
                          weight="bold", anchor="middle"))
                          
        text_start_y = step_y - ((len(lines) - 1) * lead) // 2 + 1
        for j, ln in enumerate(lines):
            out.append(_text(text_x, text_start_y + j * lead, ln, size=size, color=COLORS["body"]))
            
        last_bottom = step_y + step_r
        cy += row_h

    if final:
        cy += 10
        out.append(
            f'  <rect x="{zx + pad}" y="{cy}" width="{inner_w}" height="{final_h}" rx="6" '
            f'fill="{step_col}" opacity="0.08" />'
        )
        out.append(
            f'  <rect x="{zx + pad}" y="{cy}" width="{inner_w}" height="{final_h}" rx="6" '
            f'fill="none" stroke="{step_col}" stroke-width="1.2" opacity="0.4" />'
        )
        ty = cy + (size - 1) + 8
        for ln in fin_lines:
            out.append(_text(zx + pad + 14, ty, ln, size=size - 1, color=COLORS["heading"], weight="bold"))
            ty += lead
            
    return out, h



def _render_mixed_card(spec, zx, zy, zw, zh, posting_group="G1") -> tuple[list[str], int]:
    items = spec.get("items", [])
    ribbon_type = spec.get("ribbon_type", "solve")
    ribbon_label = spec.get("ribbon_label", ribbon_type)
    
    size = _get_font_size("body", posting_group)
    lead = int(size * 1.5)
    pad = 36
    inner_w = zw - pad - 16
    
    sub_layouts = []
    total_h = 24
    item_gap = 14
    
    from .renderers_math import RENDERERS as _R_MATH
    math_grid_fn = _R_MATH.get("math_grid")
    
    for i, item in enumerate(items):
        itype = item.get("type", "")
        
        if itype == "text":
            lines_total = []
            for line in item.get("lines", []):
                lines_total.extend(_wrap(line, inner_w, size))
            item_h = len(lines_total) * lead + 6
            sub_layouts.append({
                "type": "text",
                "lines": lines_total,
                "height": item_h
            })
            total_h += item_h + (item_gap if i < len(items) - 1 else 0)
            
        elif itype == "math_grid" and math_grid_fn:
            try:
                # Run renderer on dummy bounds to get simulated height
                _, consumed = math_grid_fn(item, zx + pad, zy, inner_w, zh, posting_group=posting_group)
            except Exception:
                consumed = 90
            sub_layouts.append({
                "type": "math_grid",
                "item_spec": item,
                "height": consumed
            })
            total_h += consumed + (item_gap if i < len(items) - 1 else 0)
            
    h = min(zh, total_h)
    out = _render_ribbon_box(zx, zy, zw, h, ribbon_type, label=ribbon_label)
    
    cy = zy + 14
    for item_layout in sub_layouts:
        itype = item_layout["type"]
        
        if itype == "text":
            for ln in item_layout["lines"]:
                out.append(_text(zx + pad, cy + size, ln, size=size, color=COLORS["body"]))
                cy += lead
            cy += 6
            
        elif itype == "math_grid" and math_grid_fn:
            grid_out, _ = math_grid_fn(item_layout["item_spec"], zx + pad, cy, inner_w, h - (cy - zy), posting_group=posting_group)
            out.extend(grid_out)
            cy += item_layout["height"]
            
        cy += item_gap
        
    return out, h


RENDERERS = {
    "number_line":       _render_number_line,
    "text_list":         _render_text_list,
    "fact_boxes":        _render_fact_boxes,
    "example_panel":     _render_example_panel,
    "callout_box":       _render_callout_box,
    "summary_list":      _render_summary_list,
    "multiple_choice":   _render_multiple_choice,
    "short_answer":      _render_short_answer,
    "hint_list":         _render_hint_list,
    "mixed_card":        _render_mixed_card,
    "remediation_block": _render_remediation_block,
}

# ── Self-documenting element specs ────────────────────────────────────────────
# Each entry is read by SVGElementRegistry at import time to generate prompt
# vocabulary docs and to validate svg_spec data before rendering.

from .element_registry import SVGElementSpec, SVGFieldSpec  # noqa: E402

ELEMENT_SPECS: list[SVGElementSpec] = [
    SVGElementSpec(
        name="text_list",
        subjects=["*"],
        synopsis="items: [strings]  (optional color per item)",
        fields=[
            SVGFieldSpec("items", type="array", required=True,
                         description="List of bullet strings; prefix 'no-bullet:' to suppress bullet"),
            SVGFieldSpec("color", type="color", required=False,
                         description="Override bullet color for all items"),
            SVGFieldSpec("anchor", type="string", required=False, default="start",
                         enum=["start", "middle", "center"],
                         description="Text alignment"),
        ],
        notes=[],
        render_fn=_render_text_list,
    ),
    SVGElementSpec(
        name="fact_boxes",
        subjects=["*"],
        synopsis="items: [{text, border_color}]",
        fields=[
            SVGFieldSpec("items", type="array", required=True,
                         description="List of fact box dicts",
                         items=SVGFieldSpec("item", type="object", properties=[
                             SVGFieldSpec("text", type="string", description="Fact box content"),
                             SVGFieldSpec("border_color", type="color", required=False,
                                          description="Box border colour"),
                         ])),
        ],
        notes=[],
        render_fn=_render_fact_boxes,
    ),
    SVGElementSpec(
        name="example_panel",
        subjects=["*"],
        synopsis="items: [{heading, body}]  — side-by-side comparison panels",
        fields=[
            SVGFieldSpec("items", type="array", required=True,
                         description="List of panel dicts (max 3 for readability)",
                         items=SVGFieldSpec("item", type="object", properties=[
                             SVGFieldSpec("heading", type="string", description="Bold panel title"),
                             SVGFieldSpec("body", type="string",
                                          description="Panel body; use \\n for explicit line breaks"),
                         ])),
        ],
        notes=[],
        render_fn=_render_example_panel,
    ),
    SVGElementSpec(
        name="callout_box",
        subjects=["*"],
        synopsis="title, lines: [strings], border_color — highlighted callout",
        fields=[
            SVGFieldSpec("title", type="string", required=False, description="Bold callout heading"),
            SVGFieldSpec("lines", type="array", required=True, description="Body text lines"),
            SVGFieldSpec("border_color", type="color", required=False, default="cyan"),
        ],
        notes=[],
        render_fn=_render_callout_box,
    ),
    SVGElementSpec(
        name="summary_list",
        subjects=["*"],
        synopsis="items: [strings]  — identical to text_list, use on summary/takeaway slides",
        fields=[
            SVGFieldSpec("items", type="array", required=True, description="Summary bullet strings"),
        ],
        notes=["PREFER summary_list on final TEACH slides to signal lesson wrap-up."],
        render_fn=_render_summary_list,
    ),
    SVGElementSpec(
        name="multiple_choice",
        subjects=["*"],
        synopsis="question: string, options: {key: text}  — MCQ layout (2 to 5 options)",
        fields=[
            SVGFieldSpec("question", type="string", required=True, description="The MCQ stem"),
            SVGFieldSpec("options", type="object", required=True,
                         description="A mapping of option keys (e.g. A, B or A, B, C, D, E) to their text"),
            SVGFieldSpec("answer", type="string", required=True,
                         description="The correct option key"),
            SVGFieldSpec("student_answer", type="string", required=False,
                         description="Optional student selection for review screens"),
            SVGFieldSpec("correct_answer", type="string", required=False,
                         description="Optional correct answer key for review screens"),
        ],
        notes=["Only use on CHECK slides — must match the option values exactly."],
        render_fn=_render_multiple_choice,
    ),
    SVGElementSpec(
        name="short_answer",
        subjects=["*"],
        synopsis="question: string, answer: string, evaluation_mode: string — open-ended text input entry",
        fields=[
            SVGFieldSpec("question", type="string", required=True, description="The open-ended question stem"),
            SVGFieldSpec("answer", type="string", required=True,
                         description="The correct answer value (e.g. '50 deg' or 'x + 2')"),
            SVGFieldSpec("evaluation_mode", type="string", required=False, default="string",
                         enum=["string", "numeric", "algebraic"],
                         description="Rule to verify answer equivalence"),
            SVGFieldSpec("student_answer", type="string", required=False,
                         description="Optional student response for review screens"),
            SVGFieldSpec("correct_answer", type="string", required=False,
                         description="Optional correct answer value for review screens"),
        ],
        notes=["Only use on CHECK/PRACTICE slides."],
        render_fn=_render_short_answer,
    ),
    SVGElementSpec(
        name="hint_list",
        subjects=["*"],
        synopsis="items: [strings], final: string  — numbered hints for HINT slides",
        fields=[
            SVGFieldSpec("items", type="array", required=True,
                         description="Hint steps (auto-numbered unless item starts with a digit or 'Step')"),
            SVGFieldSpec("final", type="string", required=False,
                         description="Confirmation method shown in a box at the bottom"),
        ],
        notes=["Only use on HINT slides."],
        render_fn=_render_hint_list,
    ),
    SVGElementSpec(
        name="number_line",
        subjects=["*"],
        synopsis="range: [min, max], highlight: {value, label, color}  — annotated number line",
        fields=[
            SVGFieldSpec("range", type="array", required=True,
                         description="[min, max] numeric bounds"),
            SVGFieldSpec("highlight", type="array", required=False,
                         description="Single dict or list of {value, label, color} highlight markers",
                         items=SVGFieldSpec("hl", type="object", properties=[
                             SVGFieldSpec("value", type="number", description="Position on the line"),
                             SVGFieldSpec("label", type="string", required=False),
                             SVGFieldSpec("color", type="color", required=False),
                             SVGFieldSpec("type", type="string", required=False,
                                          enum=["jump"], description="'jump' draws a curved hop arrow"),
                         ])),
            SVGFieldSpec("direction_labels", type="object", required=False,
                         description="{left: 'Smaller', right: 'Larger'} axis end labels",
                         properties=[
                             SVGFieldSpec("left", type="string", required=False),
                             SVGFieldSpec("right", type="string", required=False),
                         ]),
            SVGFieldSpec("caption", type="string", required=False,
                         description="Title above the line — use when stacking two number_lines on one slide"),
        ],
        notes=[
            "PREFER stacking two captioned number_lines over two near-identical slides.",
        ],
        render_fn=_render_number_line,
    ),
    SVGElementSpec(
        name="mixed_card",
        subjects=["*"],
        synopsis="ribbon_type: solve|remember|review, ribbon_label: string, items: [{type: text|math_grid, ...}] — mixed card",
        fields=[
            SVGFieldSpec("ribbon_type", type="string", required=False, default="solve",
                         enum=["solve", "remember", "review"]),
            SVGFieldSpec("ribbon_label", type="string", required=False),
            SVGFieldSpec("items", type="array", required=True,
                         description="List of sub-elements",
                         items=SVGFieldSpec("item", type="object", properties=[
                             SVGFieldSpec("type", type="string", required=True, enum=["text", "math_grid"]),
                             SVGFieldSpec("lines", type="array", required=False),
                             SVGFieldSpec("mode", type="string", required=False),
                             SVGFieldSpec("rows", type="array", required=False),
                             SVGFieldSpec("headers", type="array", required=False),
                             SVGFieldSpec("row_colors", type="array", required=False),
                         ])),
        ],
        notes=[],
        render_fn=_render_mixed_card,
    ),
    SVGElementSpec(
        name="remediation_block",
        subjects=["*"],
        synopsis="review: {source_question, student_answer, correct_answer}, remember: {type, ...}, solve: {type, ...} — remediation block",
        fields=[
            SVGFieldSpec("review", type="object", required=True,
                         description="Shows the question context and answers",
                         properties=[
                             SVGFieldSpec("source_question", type="string", required=True,
                                          description="ID of the checked question element"),
                             SVGFieldSpec("student_answer", type="string", required=False,
                                          description="Option key selected by the student"),
                             SVGFieldSpec("correct_answer", type="string", required=False,
                                          description="Correct option key"),
                         ]),
            SVGFieldSpec("remember", type="object", required=True,
                         description="The conceptual anchor element definition"),
            SVGFieldSpec("solve", type="object", required=True,
                         description="The step-by-step solution element definition"),
        ],
        notes=[],
        render_fn=_render_remediation_block,
    ),
]

