"""Math renderer: solid_shape (3D shapes with isometric projection)."""

import math
from ..primitives import COLORS, _text, _get_font_size, _line


def _isometric_project(x, y, z):
    """Project 3D point to isometric 2D.

    Standard isometric angles: 30° horizontal, 120° for depth.
    Returns (screen_x, screen_y) relative to origin.
    """
    iso_x = x - z * 0.866  # cos(30°) ≈ 0.866
    iso_y = y + z * 0.5    # y increases downward on screen
    return iso_x, iso_y


def _render_solid_shape(spec, zx, zy, zw, zh, posting_group="G1") -> tuple[list[str], int]:
    """Draw a 3D solid shape using isometric projection.

    Supported shapes: cube, rectangular_prism, triangular_prism, pyramid, cone, cylinder.
    """
    shape = spec.get("shape", "cube").lower()
    dims = spec.get("dimensions", [3, 3, 3])
    color = spec.get("color", "blue")
    label = spec.get("label", "")
    show_dimensions = spec.get("show_dimensions", False)

    if not isinstance(dims, (list, tuple)):
        dims = [3, 3, 3]
    while len(dims) < 3:
        dims.append(dims[-1] if dims else 3)

    width, height, depth = float(dims[0]), float(dims[1]), float(dims[2])
    if width <= 0 or height <= 0:
        width = height = 3
    if depth <= 0:
        depth = 3

    out: list[str] = []

    # Scale to fit zone (target ~120px max dimension on screen)
    max_dim = max(width, height, depth)
    scale = 120 / max_dim if max_dim > 0 else 1.0
    w, h, d = width * scale, height * scale, depth * scale

    # Center in zone
    iso_w = w + d * 0.866
    iso_h = h + d * 0.5
    cx = zx + (zw - iso_w) / 2
    cy = zy + 20

    face_color = _resolve_color(color)

    # Extract original dimension values (before scaling)
    if len(dims) == 1:
        orig_w, orig_h, orig_d = dims[0], dims[0], dims[0]
    elif len(dims) == 2:
        orig_w, orig_h, orig_d = dims[0], dims[1], dims[1]
    else:
        orig_w, orig_h, orig_d = dims[0], dims[1], dims[2]

    if shape == "cube":
        out.extend(_render_cube(cx, cy, w, face_color, show_dimensions, orig_w))
    elif shape == "rectangular_prism":
        out.extend(_render_rectangular_prism(cx, cy, w, h, d, face_color, show_dimensions, (orig_w, orig_h, orig_d)))
    elif shape == "triangular_prism":
        out.extend(_render_triangular_prism(cx, cy, w, h, d, face_color))
    elif shape == "pyramid":
        out.extend(_render_pyramid(cx, cy, w, h, d, face_color, show_dimensions, (orig_w, orig_d, orig_h)))
    elif shape == "cone":
        out.extend(_render_cone(cx, cy, w, h, d, face_color, show_dimensions, (orig_w / 2, orig_h)))
    elif shape == "cylinder":
        out.extend(_render_cylinder(cx, cy, w, h, d, face_color, show_dimensions, (orig_w / 2, orig_h)))
    else:
        out.extend(_render_cube(cx, cy, w, face_color, show_dimensions, orig_w))

    # Label below shape
    size_ann = _get_font_size("annotation", posting_group)
    label_y = cy + iso_h + 20

    if label:
        out.append(_text(zx + zw / 2, label_y, label,
                        size=size_ann, color=COLORS["body"], anchor="middle"))
        label_y += 18

    return out, int(iso_h + (30 if label else 10))


def _render_cube(cx, cy, side, color, show_dimensions=False, dim_value=None):
    """Render a cube by wrapping rectangular prism with equal sides."""
    return _render_rectangular_prism(
        cx, cy, side, side, side, color, show_dimensions,
        (dim_value, dim_value, dim_value) if dim_value is not None else None
    )


def _render_rectangular_prism(cx, cy, w, h, d, color, show_dimensions=False, dims_tuple=None):
    """Render a rectangular prism (box) with given dimensions.

    Shows labeled dimension lines for width, height, and depth when show_dimensions=True.
    """
    vertices_3d = [
        (0, 0, 0),    # 0: front-bottom-left
        (w, 0, 0),    # 1: front-bottom-right
        (w, h, 0),    # 2: front-top-right
        (0, h, 0),    # 3: front-top-left
        (0, 0, d),    # 4: back-bottom-left
        (w, 0, d),    # 5: back-bottom-right
        (w, h, d),    # 6: back-top-right
        (0, h, d),    # 7: back-top-left
    ]

    verts_2d = [(cx + iso_x, cy + iso_y) for iso_x, iso_y in
                [_isometric_project(x, y, z) for x, y, z in vertices_3d]]

    out = [
        _polygon([verts_2d[0], verts_2d[1], verts_2d[2], verts_2d[3]],
                 fill=color, opacity=0.25),
        _polygon([verts_2d[3], verts_2d[2], verts_2d[6], verts_2d[7]],
                 fill=color, opacity=0.3),
        _polygon([verts_2d[1], verts_2d[5], verts_2d[6], verts_2d[2]],
                 fill=color, opacity=0.2),
    ]

    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]
    for i, j in edges:
        out.append(_line(verts_2d[i][0], verts_2d[i][1],
                        verts_2d[j][0], verts_2d[j][1],
                        color=COLORS["grey"], stroke_w=0.8))

    # Dimension labels with arrows (exacting on the edges of the prism base/front faces)
    if show_dimensions and dims_tuple:
        w_val, h_val, d_val = dims_tuple

        # Width (top front edge, 0-1)
        w_x1, w_y1 = verts_2d[0]
        w_x2, w_y2 = verts_2d[1]
        out.extend(_dimension_line(w_x1, w_y1, w_x2, w_y2,
                                   f"w: {w_val:.0f}", "red", "horizontal"))

        # Height (right front edge, 1-2)
        h_x1, h_y1 = verts_2d[1]
        h_x2, h_y2 = verts_2d[2]
        out.extend(_dimension_line(h_x1, h_y1, h_x2, h_y2,
                                   f"h: {h_val:.0f}", "cyan", "vertical"))

        # Depth (back diagonal, 0-4)
        d_x1, d_y1 = verts_2d[0]
        d_x2, d_y2 = verts_2d[4]
        out.extend(_dimension_line(d_x1, d_y1, d_x2, d_y2,
                                   f"d: {d_val:.0f}", "green", "diagonal"))

    return out


def _render_triangular_prism(cx, cy, w, h, d, color):
    """Render a triangular prism."""
    # Triangle base on front, extending back
    vertices_3d = [
        (0, 0, 0),        # 0: front-left
        (w, 0, 0),        # 1: front-right
        (w / 2, h, 0),    # 2: front-apex
        (0, 0, d),        # 3: back-left
        (w, 0, d),        # 4: back-right
        (w / 2, h, d),    # 5: back-apex
    ]

    verts_2d = [(cx + iso_x, cy + iso_y) for iso_x, iso_y in
                [_isometric_project(x, y, z) for x, y, z in vertices_3d]]

    out = [
        # Front triangle
        _polygon([verts_2d[0], verts_2d[1], verts_2d[2]], fill=color, opacity=0.3),
        # Back triangle
        _polygon([verts_2d[3], verts_2d[4], verts_2d[5]], fill=color, opacity=0.3),
        # Bottom rectangle
        _polygon([verts_2d[0], verts_2d[1], verts_2d[4], verts_2d[3]],
                 fill=color, opacity=0.2),
        # Left rectangle
        _polygon([verts_2d[0], verts_2d[2], verts_2d[5], verts_2d[3]],
                 fill=color, opacity=0.25),
        # Right rectangle
        _polygon([verts_2d[1], verts_2d[2], verts_2d[5], verts_2d[4]],
                 fill=color, opacity=0.25),
    ]

    edges = [
        (0, 1), (1, 2), (2, 0),  # front
        (3, 4), (4, 5), (5, 3),  # back
        (0, 3), (1, 4), (2, 5),  # connecting
    ]
    for i, j in edges:
        out.append(_line(verts_2d[i][0], verts_2d[i][1],
                        verts_2d[j][0], verts_2d[j][1],
                        color=COLORS["grey"], stroke_w=0.8))

    return out


def _render_pyramid(cx, cy, w, h, d, color, show_dimensions=False, dims_tuple=None):
    """Render a pyramid (square base at bottom, apex at top).

    Base at y=h, apex at y=0.
    """
    vertices_3d = [
        (0, h, 0),        # 0: base-left
        (w, h, 0),        # 1: base-right
        (w, h, d),        # 2: base-back-right
        (0, h, d),        # 3: base-back-left
        (w / 2, 0, d / 2), # 4: apex at top
    ]

    verts_2d = [(cx + iso_x, cy + iso_y) for iso_x, iso_y in
                [_isometric_project(x, y, z) for x, y, z in vertices_3d]]

    out = [
        # Base
        _polygon([verts_2d[0], verts_2d[1], verts_2d[2], verts_2d[3]],
                 fill=color, opacity=0.2),
        # Front triangle
        _polygon([verts_2d[0], verts_2d[1], verts_2d[4]], fill=color, opacity=0.25),
        # Right triangle
        _polygon([verts_2d[1], verts_2d[2], verts_2d[4]], fill=color, opacity=0.25),
        # Back triangle
        _polygon([verts_2d[2], verts_2d[3], verts_2d[4]], fill=color, opacity=0.25),
        # Left triangle
        _polygon([verts_2d[3], verts_2d[0], verts_2d[4]], fill=color, opacity=0.25),
    ]

    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),  # base
        (0, 4), (1, 4), (2, 4), (3, 4),  # to apex
    ]
    for i, j in edges:
        out.append(_line(verts_2d[i][0], verts_2d[i][1],
                        verts_2d[j][0], verts_2d[j][1],
                        color=COLORS["grey"], stroke_w=0.8))

    # Dimension labels with arrows (supports rectangular base: width, depth, height)
    if show_dimensions and dims_tuple:
        if len(dims_tuple) == 3:
            width_val, depth_val, height_val = dims_tuple
        else:
            # Backward compatibility: if only 2 values, treat as (base, height)
            width_val, height_val = dims_tuple
            depth_val = width_val

        # Width (front base edge, 0-1) - horizontal
        w_x1, w_y1 = verts_2d[0]
        w_x2, w_y2 = verts_2d[1]
        out.extend(_dimension_line(w_x1, w_y1, w_x2, w_y2,
                                   f"w: {width_val:.0f}", "red", "horizontal"))

        # Depth (right base edge, 1-2) - diagonal, show only if different from width
        if depth_val != width_val:
            d_x1, d_y1 = verts_2d[1]
            d_x2, d_y2 = verts_2d[2]
            out.extend(_dimension_line(d_x1, d_y1, d_x2, d_y2,
                                       f"d: {depth_val:.0f}", "green", "diagonal"))

        # Height (from apex to base center) - pixel-perfect vertical line
        # Apex is vertex 4
        apex_x, apex_y = verts_2d[4]
        # Base center is the average of the four base vertices
        base_center_x = (verts_2d[0][0] + verts_2d[1][0] + verts_2d[2][0] + verts_2d[3][0]) / 4
        base_center_y = (verts_2d[0][1] + verts_2d[1][1] + verts_2d[2][1] + verts_2d[3][1]) / 4
        # Draw height line directly from apex to base center (h_offset = 0)
        h_offset = 0
        out.extend(_dimension_line(apex_x + h_offset, apex_y, base_center_x + h_offset, base_center_y,
                                   f"h: {height_val:.0f}", "body", "vertical"))

    return out


def _render_cone(cx, cy, w, h, d, color, show_dimensions=False, dims_tuple=None):
    """Render a cone (circular base with apex).

    Apex at top (y=0), base at bottom (y=h).
    """
    base_radius = w / 2
    cx_centered = cx + (d * 0.866) / 2

    # Apex position (top center)
    apex = (cx_centered, cy)

    # Base ellipse points (horizontal)
    n_points = 64
    def _horizontal_ellipse_points(y_center):
        pts = []
        for i in range(n_points):
            angle = 2 * math.pi * i / n_points
            ex = cx_centered + base_radius * math.cos(angle)
            ey = y_center + base_radius * 0.35 * math.sin(angle)
            pts.append((ex, ey))
        return pts

    bottom_pts = _horizontal_ellipse_points(cy + h)

    idx_L = n_points // 2  # 32 (leftmost, angle = pi)
    idx_R = 0             # 0 (rightmost, angle = 0)

    out = []

    # Side face (cone wall) - curved fill using front half of ellipse
    front_half = bottom_pts[0:33]
    side_pts = [apex] + front_half
    out.append(_polygon(side_pts, fill=color, opacity=0.25))

    # Base face fill
    out.append(_polygon(bottom_pts, fill=color, opacity=0.2))

    # Base outline (subtle grey)
    for i in range(n_points):
        j = (i + 1) % n_points
        out.append(_line(bottom_pts[i][0], bottom_pts[i][1],
                         bottom_pts[j][0], bottom_pts[j][1],
                         color=COLORS["grey"], stroke_w=0.8))

    # Left outline edge
    out.append(_line(apex[0], apex[1],
                     bottom_pts[idx_L][0], bottom_pts[idx_L][1],
                     color=COLORS["body"], stroke_w=1.2))

    # Right outline edge
    out.append(_line(apex[0], apex[1],
                     bottom_pts[idx_R][0], bottom_pts[idx_R][1],
                     color=COLORS["body"], stroke_w=1.2))

    # Dimension labels
    if show_dimensions and dims_tuple:
        radius_val, height_val = dims_tuple

        # Radius line: horizontal from center of base to right edge
        out.extend(_dimension_line(cx_centered, cy + h, cx_centered + base_radius, cy + h,
                                   f"r: {radius_val:.1f}", "red", "horizontal"))

        # Height line: vertical from apex to base center
        out.extend(_dimension_line(cx_centered, cy, cx_centered, cy + h,
                                   f"h: {height_val:.0f}", "cyan", "vertical"))

    return out


def _render_cylinder(cx, cy, w, h, d, color, show_dimensions=False, dims_tuple=None):
    """Render a cylinder (circular bases with height)."""
    base_radius = w / 2
    cx_centered = cx + (d * 0.866) / 2

    n_points = 64
    def _horizontal_ellipse_points(y_center):
        pts = []
        for i in range(n_points):
            angle = 2 * math.pi * i / n_points
            ex = cx_centered + base_radius * math.cos(angle)
            ey = y_center + base_radius * 0.35 * math.sin(angle)
            pts.append((ex, ey))
        return pts

    top_pts = _horizontal_ellipse_points(cy)
    bottom_pts = _horizontal_ellipse_points(cy + h)

    idx_L = n_points // 2  # 32 (leftmost, angle = pi)
    idx_R = 0             # 0 (rightmost, angle = 0)

    out = []

    # Side face (cylinder wall) - single solid polygon
    side_pts = top_pts + list(reversed(bottom_pts))
    out.append(_polygon(side_pts, fill=color, opacity=0.25))

    # Bottom face
    out.append(_polygon(bottom_pts, fill=color, opacity=0.2))

    # Top face
    out.append(_polygon(top_pts, fill=color, opacity=0.3))

    # Bottom edge outline (subtle grey)
    for i in range(n_points):
        j = (i + 1) % n_points
        out.append(_line(bottom_pts[i][0], bottom_pts[i][1],
                         bottom_pts[j][0], bottom_pts[j][1],
                         color=COLORS["grey"], stroke_w=0.6))

    # Top edge outline (dark body color)
    for i in range(n_points):
        j = (i + 1) % n_points
        out.append(_line(top_pts[i][0], top_pts[i][1],
                         top_pts[j][0], top_pts[j][1],
                         color=COLORS["body"], stroke_w=1.2))

    # Exactly two vertical outline lines (leftmost and rightmost edges)
    out.append(_line(top_pts[idx_L][0], top_pts[idx_L][1],
                     bottom_pts[idx_L][0], bottom_pts[idx_L][1],
                     color=COLORS["body"], stroke_w=1.2))
    out.append(_line(top_pts[idx_R][0], top_pts[idx_R][1],
                     bottom_pts[idx_R][0], bottom_pts[idx_R][1],
                     color=COLORS["body"], stroke_w=1.2))

    # Dimension lines
    if show_dimensions and dims_tuple:
        radius_val, height_val = dims_tuple

        # Radius line: horizontal from center of top ellipse to the right edge
        out.extend(_dimension_line(cx_centered, cy, cx_centered + base_radius, cy,
                                   f"r: {radius_val:.1f}", "red", "horizontal"))

        # Height line: vertical from center of top ellipse to center of bottom ellipse
        out.extend(_dimension_line(cx_centered, cy, cx_centered, cy + h,
                                   f"h: {height_val:.0f}", "cyan", "vertical"))

    return out


def _polygon(points, fill=None, opacity=1.0, stroke=None):
    """Create a filled polygon SVG element."""
    f = _resolve_color(fill) if fill else COLORS["blue"]
    s = stroke or COLORS["grey"]
    pts_str = " ".join(f"{x},{y}" for x, y in points)
    return (
        f'  <polygon points="{pts_str}" fill="{f}" opacity="{opacity}" '
        f'stroke="{s}" stroke-width="0.8" />'
    )


def _dimension_line(x1, y1, x2, y2, label, color_name, orientation="horizontal"):
    """Draw a dimension line with arrows and label positioned in white space.

    Arrow heads are tangent to (aligned with) the dimension line direction.

    Args:
        (x1, y1), (x2, y2): line endpoints
        label: text label (e.g. "w: 5")
        color_name: color key from COLORS dict
        orientation: "horizontal", "vertical", or "diagonal" for label placement
    """
    color = _resolve_color(color_name)
    out = []

    # Calculate direction and perpendicular vectors
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)

    if length > 0:
        # Unit direction vector (along the line)
        ux, uy = dx / length, dy / length
        # Unit perpendicular vector (perpendicular to line)
        px, py = -uy, ux

        arrow_size = 5.0
        back_size = 3.0

        # Shorten the line segment to start/end at the bases of the arrow heads
        line_x1 = x1 + ux * arrow_size
        line_y1 = y1 + uy * arrow_size
        line_x2 = x2 - ux * arrow_size
        line_y2 = y2 - uy * arrow_size

        # Main dimension line (drawn between the arrow bases)
        out.append(f'  <line x1="{line_x1}" y1="{line_y1}" x2="{line_x2}" y2="{line_y2}" '
                   f'stroke="{color}" stroke-width="1.8" />')

        # Arrow head at start (x1, y1) pointing outward (tip at x1, y1)
        back_left_x1 = line_x1 + px * back_size
        back_left_y1 = line_y1 + py * back_size
        back_right_x1 = line_x1 - px * back_size
        back_right_y1 = line_y1 - py * back_size
        out.append(f'  <polygon points="{x1},{y1} {back_left_x1},{back_left_y1} {back_right_x1},{back_right_y1}" '
                   f'fill="{color}" />')

        # Arrow head at end (x2, y2) pointing outward (tip at x2, y2)
        back_left_x2 = line_x2 + px * back_size
        back_left_y2 = line_y2 + py * back_size
        back_right_x2 = line_x2 - px * back_size
        back_right_y2 = line_y2 - py * back_size
        out.append(f'  <polygon points="{x2},{y2} {back_left_x2},{back_left_y2} {back_right_x2},{back_right_y2}" '
                   f'fill="{color}" />')
    else:
        # Fallback if length is 0
        out.append(f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                   f'stroke="{color}" stroke-width="1.8" />')

    # Label positioning based on orientation
    if orientation == "horizontal":
        label_x = (x1 + x2) / 2
        label_y = max(y1, y2) + 18
    elif orientation == "vertical":
        label_x = min(x1, x2) - 28
        label_y = (y1 + y2) / 2
    else:  # diagonal
        label_x = (x1 + x2) / 2 + 20
        label_y = (y1 + y2) / 2

    # Label text
    out.append(_text(label_x, label_y, label, size=8, color=color, anchor="middle", weight="bold"))

    return out


def _resolve_color(name: str) -> str:
    """Resolve color name to hex value."""
    return COLORS.get(str(name).lower(), COLORS["blue"])


RENDERERS = {
    "solid_shape": _render_solid_shape,
}

from ..element_registry import SVGElementSpec, SVGFieldSpec  # noqa: E402

ELEMENT_SPECS: list[SVGElementSpec] = [
    SVGElementSpec(
        name="solid_shape",
        subjects=["math"],
        synopsis="shape: cube|rectangular_prism|triangular_prism|pyramid|cone|cylinder, dimensions, color, label",
        fields=[
            SVGFieldSpec("shape", type="string", required=False, default="cube",
                         enum=["cube", "rectangular_prism", "triangular_prism", "pyramid", "cone", "cylinder"],
                         description="3D shape type"),
            SVGFieldSpec("dimensions", type="array", required=False, default=[3, 3, 3],
                         description="[width, height, depth] — if 1 value given, used for all; if 2 given, third defaults to second"),
            SVGFieldSpec("color", type="color", required=False, default="blue"),
            SVGFieldSpec("label", type="string", required=False,
                         description="Measurement label below the shape (e.g. '5 cm' or '5×3×2 cm³')"),
        ],
        notes=[
            "All shapes use isometric projection for consistent 3D perspective.",
            "Dimensions are auto-scaled to fit the content zone.",
            "For a cube, pass dimensions: [side] or dimensions: [5].",
            "For a rectangular prism, pass dimensions: [width, height, depth].",
        ],
        render_fn=_render_solid_shape,
    ),
]
