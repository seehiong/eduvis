"""Math renderer: geometry_shape (polygon with vertex/side/angle labels)."""

import math

from ..primitives import COLORS, _text, _get_font_size


def _render_geometry_shape(spec, zx, zy, zw, zh, posting_group="G1") -> tuple[list[str], int]:
    vertices    = spec.get("vertices", [[60, 300], [200, 100], [350, 300]])
    labels      = spec.get("labels", [])
    angles      = spec.get("angles", [])
    side_labels = spec.get("side_labels", [])

    if not vertices:
        return [], 0

    raw_xs = [v[0] for v in vertices]
    raw_ys = [v[1] for v in vertices]
    min_x, max_x = min(raw_xs), max(raw_xs)
    min_y, max_y = min(raw_ys), max(raw_ys)
    
    raw_w = max(1.0, max_x - min_x)
    raw_h = max(1.0, max_y - min_y)
    
    # Cap the scaled dimensions to make it look like a standard textbook diagram.
    target_max_w = 320.0
    target_max_h = 220.0
    
    scale   = min((zw - 60) / raw_w,
                  (zh - 40) / raw_h,
                  target_max_w / raw_w,
                  target_max_h / raw_h)
                  
    pad_x   = (zw - raw_w * scale) / 2
    # Cap the centering container at 240px to prevent layout simulation (zh=9999) from pushing the shape down.
    pad_y   = (min(zh, 240.0) - raw_h * scale) / 2

    def _tv(v):
        return (
            round(zx + pad_x + (v[0] - min_x) * scale, 1),
            round(zy + pad_y + (v[1] - min_y) * scale, 1),
        )

    tverts = [_tv(v) for v in vertices]
    out    = []

    size_lbl = _get_font_size("body", posting_group) + 2
    size_ann = _get_font_size("body", posting_group)

    # Render shape outline (either custom edges or sequential closed polygon)
    edges = spec.get("edges", [])
    if edges:
        # Build map from vertex label to scaled coordinate
        vmap = {}
        for i, lbl in enumerate(labels):
            lbl_str = lbl.get("text", "") if isinstance(lbl, dict) else str(lbl)
            if lbl_str and i < len(tverts):
                vmap[lbl_str] = tverts[i]
                
        for edge in edges:
            v1_lbl, v2_lbl = None, None
            if isinstance(edge, list) and len(edge) == 2:
                v1_lbl, v2_lbl = str(edge[0]), str(edge[1])
            elif isinstance(edge, str):
                edge_str = edge.strip()
                if len(edge_str) == 2:
                    v1_lbl, v2_lbl = edge_str[0], edge_str[1]
                elif "-" in edge_str:
                    parts = edge_str.split("-")
                    if len(parts) == 2:
                        v1_lbl, v2_lbl = parts[0].strip(), parts[1].strip()
            
            if v1_lbl in vmap and v2_lbl in vmap:
                p1, p2 = vmap[v1_lbl], vmap[v2_lbl]
                out.append(
                    f'  <line x1="{p1[0]}" y1="{p1[1]}" x2="{p2[0]}" y2="{p2[1]}" '
                    f'stroke="{COLORS["body"]}" stroke-width="2" />'
                )
    else:
        # Fall back to drawing standard closed polygon
        pts_str = " ".join(f"{x},{y}" for x, y in tverts)
        out.append(
            f'  <polygon points="{pts_str}" fill="none" '
            f'stroke="{COLORS["body"]}" stroke-width="2" />'
        )

    # Vertex and custom labels
    cx_c = sum(p[0] for p in tverts) / len(tverts)
    cy_c = sum(p[1] for p in tverts) / len(tverts)
    for i, lbl in enumerate(labels):
        if isinstance(lbl, dict):
            text = lbl.get("text", "")
            pos = lbl.get("position")
            offset = lbl.get("offset")
            anchor = lbl.get("anchor", "middle")
            if pos is not None and len(pos) >= 2:
                lx, ly = _tv(pos)
            elif offset is not None and len(offset) >= 2:
                if i >= len(tverts):
                    continue
                vx, vy = tverts[i]
                lx     = round(vx + offset[0], 1)
                ly     = round(vy + offset[1], 1)
            else:
                if i >= len(tverts):
                    continue
                vx, vy = tverts[i]
                dx, dy = vx - cx_c, vy - cy_c
                norm   = max(1.0, math.hypot(dx, dy))
                lx     = round(vx + dx / norm * 14, 1)
                ly     = round(vy + dy / norm * 14 + 4, 1)
            out.append(_text(lx, ly, text, size=size_lbl, color=COLORS["heading"], anchor=anchor, weight="bold"))
        else:
            if i >= len(tverts):
                break
            vx, vy = tverts[i]
            dx, dy = vx - cx_c, vy - cy_c
            norm   = max(1.0, math.hypot(dx, dy))
            lx     = round(vx + dx / norm * 14, 1)
            ly     = round(vy + dy / norm * 14 + 4, 1)
            out.append(_text(lx, ly, lbl, size=size_lbl, color=COLORS["heading"], anchor="middle", weight="bold"))

    # Side labels (edge "AC" = polygon edge connecting A and C)
    lmap = {sl.get("edge", ""): sl.get("label", "") for sl in side_labels}
    n    = len(tverts)
    for i in range(n):
        j        = (i + 1) % n
        v_from   = labels[i] if i < len(labels) else ""
        v_to     = labels[j] if j < len(labels) else ""
        
        # Ensure we have string keys to avoid dictionary unhashable/addition TypeError
        if isinstance(v_from, dict):
            v_from = v_from.get("text", "")
        if isinstance(v_to, dict):
            v_to = v_to.get("text", "")
        v_from = str(v_from)
        v_to   = str(v_to)
        
        slabel   = lmap.get(v_from + v_to) or lmap.get(v_to + v_from, "")
        if not slabel:
            continue
        mx = (tverts[i][0] + tverts[j][0]) / 2
        my = (tverts[i][1] + tverts[j][1]) / 2
        dx =  tverts[j][0] - tverts[i][0]
        dy =  tverts[j][1] - tverts[i][1]
        
        # Determine the outward normal relative to the polygon centroid
        nx_raw = -dy
        ny_raw = dx
        vx = mx - cx_c
        vy = my - cy_c
        if nx_raw * vx + ny_raw * vy < 0:
            nx_raw, ny_raw = dy, -dx
            
        norm = math.hypot(nx_raw, ny_raw)
        if norm > 0:
            nx = nx_raw / norm
            ny = ny_raw / norm
        else:
            nx, ny = 0, 0
            
        # Offset to prevent touching the shape outline
        offset = 18
        lx = mx + nx * offset
        # SVG text baseline adjustment: shift vertically down slightly for visual alignment
        ly = my + ny * offset + 4
        
        # Choose text anchoring dynamically to prevent label overlap on steep/vertical lines
        if abs(nx) > 0.5:
            anchor = "start" if nx > 0 else "end"
        else:
            anchor = "middle"
            
        out.append(_text(round(lx, 1),
                          round(ly, 1),
                          slabel, size=size_ann, color=COLORS["green"], anchor=anchor))

    # Angle arcs
    for a_spec in angles:
        vertex_name = a_spec.get("vertex", "")
        if not vertex_name:
            continue
        v_idx = None
        for k, l in enumerate(labels):
            lbl_str_k = l.get("text", "") if isinstance(l, dict) else str(l)
            if lbl_str_k == vertex_name:
                v_idx = k
                break
        if v_idx is None or v_idx >= len(tverts):
            continue

        vx, vy   = tverts[v_idx]
        prev_v = None
        next_v = None
        sides = a_spec.get("sides")
        if sides and len(sides) == 2:
            vmap = {}
            for k, l in enumerate(labels):
                lbl_str_k = l.get("text", "") if isinstance(l, dict) else str(l)
                if lbl_str_k and k < len(tverts):
                    vmap[lbl_str_k] = tverts[k]
            if str(sides[0]) in vmap and str(sides[1]) in vmap:
                prev_v = vmap[str(sides[0])]
                next_v = vmap[str(sides[1])]
                
        if prev_v is None or next_v is None:
            prev_v = tverts[(v_idx - 1) % n]
            next_v = tverts[(v_idx + 1) % n]
        arc_r    = 16

        # Directions from vertex to adjacent vertices
        d1_x, d1_y = prev_v[0] - vx, prev_v[1] - vy
        d2_x, d2_y = next_v[0] - vx, next_v[1] - vy
        norm1 = math.hypot(d1_x, d1_y)
        norm2 = math.hypot(d2_x, d2_y)

        if norm1 > 0 and norm2 > 0:
            u1_x, u1_y = d1_x / norm1, d1_y / norm1
            u2_x, u2_y = d2_x / norm2, d2_y / norm2

            x1 = round(vx + arc_r * u1_x, 1)
            y1 = round(vy + arc_r * u1_y, 1)
            x2 = round(vx + arc_r * u2_x, 1)
            y2 = round(vy + arc_r * u2_y, 1)

            # Determine sweep direction (clockwise vs counter-clockwise) using cross product
            cross = u1_x * u2_y - u1_y * u2_x
            sweep_flag = 1 if cross > 0 else 0

            # Calculate interior angle in degrees for right-angle auto-detection
            angle_deg = math.degrees(math.acos(max(-1.0, min(1.0, u1_x * u2_x + u1_y * u2_y))))

            # Default to drawing the arc (True) unless arc: False is explicitly passed.
            arc_val = a_spec.get("arc", True)
            if arc_val:
                is_square = False
                if isinstance(arc_val, str) and arc_val.lower() in ("square", "right", "right_angle"):
                    is_square = True
                elif arc_val is True and 88 <= angle_deg <= 92:
                    is_square = True

                if is_square:
                    s = 12  # square right angle size in pixels
                    p1_x = vx + s * u1_x
                    p1_y = vy + s * u1_y
                    p2_x = vx + s * u2_x
                    p2_y = vy + s * u2_y
                    c_x  = p1_x + p2_x - vx
                    c_y  = p1_y + p2_y - vy
                    out.append(
                        f'  <path d="M {round(p1_x, 1)},{round(p1_y, 1)} L {round(c_x, 1)},{round(c_y, 1)} L {round(p2_x, 1)},{round(p2_y, 1)}" '
                        f'fill="none" stroke="{COLORS["yellow"]}" stroke-width="1.5" />'
                    )
                else:
                    out.append(
                        f'  <path d="M {x1},{y1} A {arc_r},{arc_r} 0 0,{sweep_flag} {x2},{y2}" '
                        f'fill="none" stroke="{COLORS["yellow"]}" stroke-width="1.5" />'
                    )

            if a_spec.get("label", ""):
                # Find the interior bisector pointing towards centroid
                vc_x, vc_y = cx_c - vx, cy_c - vy
                bis_x = u1_x + u2_x
                bis_y = u1_y + u2_y
                bis_len = math.hypot(bis_x, bis_y)
                if bis_len < 1e-4:
                    ub_x, ub_y = -u1_y, u1_x
                else:
                    ub_x, ub_y = bis_x / bis_len, bis_y / bis_len

                # Ensure bisector points towards centroid (interior)
                # Skip this check if custom sides are specified (since it might be an external angle)
                if not sides and ub_x * vc_x + ub_y * vc_y < 0:
                    ub_x, ub_y = -ub_x, -ub_y

                label_text = a_spec["label"]
                dist = arc_r + 14
                if len(label_text) > 4:
                    dist += (len(label_text) - 4) * 5
                label_x = round(vx + dist * ub_x, 1)
                label_y = round(vy + dist * ub_y + 4, 1)
                
                # Determine text anchoring dynamically to prevent label crossing slanted boundaries
                if abs(ub_x) > 0.3:
                    anchor = "start" if ub_x > 0 else "end"
                else:
                    anchor = "middle"

                out.append(_text(
                    label_x, label_y,
                    a_spec["label"], size=size_ann, color=COLORS["yellow"], anchor=anchor, weight="bold"
                ))

    total_h = int(max(v[1] for v in tverts) - zy + 40)
    return out, max(0, total_h)


RENDERERS = {
    "geometry_shape": _render_geometry_shape,
}

from ..element_registry import SVGElementSpec, SVGFieldSpec  # noqa: E402

ELEMENT_SPECS: list[SVGElementSpec] = [
    SVGElementSpec(
        name="geometry_shape",
        subjects=["math"],
        synopsis="vertices: [[x,y],...], labels, side_labels, angles — polygon with annotations",
        fields=[
            SVGFieldSpec("vertices", type="array", required=True,
                         description="List of [x, y] coordinate pairs defining the polygon"),
            SVGFieldSpec("labels", type="array", required=False,
                         description="Vertex label strings or {text, position, offset, anchor} dicts (one per vertex)"),
            SVGFieldSpec("side_labels", type="array", required=False,
                         description="[{edge: 'AB', label: '5 cm'}] — label for each named edge",
                         items=SVGFieldSpec("sl", type="object", properties=[
                             SVGFieldSpec("edge", type="string",
                                          description="Two-letter vertex pair e.g. 'AB'"),
                             SVGFieldSpec("label", type="string",
                                          description="Text shown at the midpoint of the edge"),
                         ])),
            SVGFieldSpec("angles", type="array", required=False,
                         description="[{vertex: 'A', arc: true, label: '90°'}] — angle annotations",
                         items=SVGFieldSpec("ang", type="object", properties=[
                             SVGFieldSpec("vertex", type="string",
                                          description="Vertex label where the angle sits"),
                             SVGFieldSpec("sides", type="array", required=False,
                                          description="Optional list of two vertex labels e.g. ['B', 'D'] specifying custom bounding sides for the angle (useful for external angles)"),
                             SVGFieldSpec("arc", type="any", required=False,
                                          description="Draws arc by default (True), auto-detecting right angles to draw a square; set to False to disable, or 'square' to force square right-angle indicator"),
                             SVGFieldSpec("label", type="string", required=False,
                                          description="Angle measure label e.g. '90°'"),
                         ])),
            SVGFieldSpec("edges", type="array", required=False,
                         description="Optional list of edge connections between vertex labels (e.g. ['AB', 'BC'] or [['A', 'B']]). If specified, renders separate lines instead of a single closed polygon."),
        ],
        notes=[],
        render_fn=_render_geometry_shape,
    ),
]

