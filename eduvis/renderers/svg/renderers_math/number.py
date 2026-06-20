"""
Math renderers for number sense and the four operations:
  factor_array       — N as a dot rectangle (factors / primes / composites)
  number_line_jumps  — signed add/subtract as arrow hops on a number line
  step_pattern       — a sign-rule / number pattern as aligned rows + constant step
"""

from ..primitives import (
    COLORS,
    _line, _rect, _resolve_color, _text, _get_font_size,
)


# ── factor_array ────────────────────────────────────────────────────────────

def _factor_pairs(n: int) -> list[tuple[int, int]]:
    """Return factor pairs (r, c) with r <= c, ascending by r. e.g. 12 → [(1,12),(2,6),(3,4)]."""
    pairs = []
    i = 1
    while i * i <= n:
        if n % i == 0:
            pairs.append((i, n // i))
        i += 1
    return pairs


def _factor_count(n: int) -> int:
    """Number of distinct factors of n (e.g. 6 → 4 {1,2,3,6}; 4 → 3 {1,2,4})."""
    pairs = _factor_pairs(n)
    if not pairs:
        return 0
    return len(pairs) * 2 - (1 if pairs[-1][0] == pairs[-1][1] else 0)


def _render_factor_array(spec, zx, zy, zw, zh, posting_group="G1") -> tuple[list[str], int]:
    """Draw a whole number as a rectangle of dots (rows × cols).

    The canonical concrete→pictorial visual for factors / primes / composites:
    a prime can only form a single line of dots, a composite forms a true
    rectangle. Spec fields: number (required), rows, cols, caption, color, verdict.
    """
    number = int(spec.get("number", 0) or 0)
    if number < 1:
        return [], 0
    color = _resolve_color(spec.get("color", "green"))

    rows, cols = spec.get("rows"), spec.get("cols")
    if rows and cols:
        rows, cols = int(rows), int(cols)
    else:
        rows, cols = _factor_pairs(number)[-1]  # most-square pair (1×n for primes)

    size_lbl = _get_font_size("body", posting_group)
    size_ann = _get_font_size("annotation", posting_group)

    reserve  = 48 if spec.get("verdict") else 28
    spacing  = min(26.0, (zw - 20) / max(1, cols), (zh - reserve) / max(1, rows))
    spacing  = max(12.0, spacing)
    r_dot    = max(3.0, round(spacing * 0.32, 1))
    gw       = cols * spacing
    gx0      = zx + (zw - gw) / 2 + spacing / 2
    gy0      = zy + 10 + spacing / 2

    out: list[str] = []
    for rr in range(rows):
        for cc in range(cols):
            cx = round(gx0 + cc * spacing, 1)
            cy = round(gy0 + rr * spacing, 1)
            out.append(f'  <circle cx="{cx}" cy="{cy}" r="{r_dot}" fill="{color}" />')

    cap_y = round(gy0 + (rows - 1) * spacing + spacing / 2 + 22, 1)
    caption = spec.get("caption") or f"{number} = {rows} × {cols}"
    out.append(_text(zx + zw / 2, cap_y, caption, size=size_lbl, color=color, anchor="middle"))
    consumed = cap_y - zy + 6

    if spec.get("verdict"):
        nfac = _factor_count(number)
        if number == 1:
            verdict, vcol = "1 is neither prime nor composite", COLORS["yellow"]
        elif nfac == 2:
            verdict, vcol = f"Prime — only 1 × {number}", COLORS["green"]
        else:
            verdict, vcol = f"Composite — {nfac} factors", COLORS["cyan"]
        vy = round(cap_y + 20, 1)
        out.append(_text(zx + zw / 2, vy, verdict, size=size_ann, color=vcol, anchor="middle"))
        consumed = vy - zy + 6

    return out, int(consumed)


def _col_widths_and_fsizes(
    list_rows: list[list],
    headers: list,
    max_cols: int,
    target_font: int,
    min_cell_w: int,
    max_cell_w: int,
    cell_padding: int,
) -> tuple[list[int], list[int]]:
    """Compute per-column cell widths and font sizes from content.

    Priority:
      1. Cell expands to fit content at target_font.
      2. If expanded width exceeds max_cell_w, cap it and shrink font proportionally.
      3. Font never drops below 8px.
    Arial character width ≈ target_font × 0.6.
    """
    char_w = target_font * 0.6
    col_max_len = [0] * max_cols

    for row in list_rows:
        padded = ([""] * (max_cols - len(row)) + row)[-max_cols:]
        for c, val in enumerate(padded):
            col_max_len[c] = max(col_max_len[c], len(str(val).strip()))

    # headers counted at half-weight (they use a smaller annotation font)
    if headers:
        padded_hdr = ([""] * (max_cols - len(headers)) + headers)[-max_cols:]
        for c, h in enumerate(padded_hdr):
            col_max_len[c] = max(col_max_len[c], len(str(h).strip()))

    widths: list[int] = []
    fsizes: list[int] = []
    for max_len in col_max_len:
        if max_len == 0:
            widths.append(min_cell_w)
            fsizes.append(target_font)
            continue
        ideal_w = int(max_len * char_w + cell_padding)
        cell_w  = min(max_cell_w, max(min_cell_w, ideal_w))
        # font that fills the (capped) cell; floor at 8
        avail   = cell_w - cell_padding
        fsize   = max(8, min(target_font, int(avail / max(1, max_len) / 0.6)))
        widths.append(cell_w)
        fsizes.append(fsize)

    return widths, fsizes


def _render_math_grid(spec, zx, zy, zw, zh, posting_group="G1") -> tuple[list[str], int]:
    """Draw column math calculations inside an aligned grid box.

    Modes:
      "arithmetic" (default) — column-aligned place-value / addition grid.
          Rows are lists of cell values; operator characters (+, -, ×, ÷) in the
          first column are rendered without a box. The special string "line" draws
          a horizontal separator (equals line).
      "ratio" — ratio table showing A : B (: C …) per row.
          Each data row is a list of values; a colon separator is drawn between
          every pair of columns. Headers label each column.

    Cell sizing (both modes):
      Cells expand dynamically to fit content at the target font size.
      When content width exceeds MAX_CELL_W the cell is capped and font shrinks
      proportionally, with a hard floor of 8 px.
    """
    mode = spec.get("mode", "arithmetic")
    rows = spec.get("rows", [])
    if not rows:
        return [], 0

    headers    = spec.get("headers", [])
    row_colors = spec.get("row_colors", [])
    out: list[str] = []

    # ── ratio mode ────────────────────────────────────────────────────────────
    if mode == "ratio":
        list_rows = [r for r in rows if isinstance(r, list)]
        if not list_rows:
            return [], 0
        max_cols = max(len(r) for r in list_rows)
        show_grid = spec.get("show_grid", True)

        TARGET_FONT = 18
        MIN_CELL_W  = 52
        MAX_CELL_W  = 160
        PADDING     = 16
        SEP_W       = 32
        CELL_H      = 44
        ROW_GAP     = 8

        col_ws, col_fs = _col_widths_and_fsizes(
            list_rows, [], max_cols, TARGET_FONT, MIN_CELL_W, MAX_CELL_W, PADDING,
        )

        # total grid width: sum of column widths + separators between them
        grid_w = sum(col_ws) + max(0, max_cols - 1) * SEP_W
        gx     = zx + (zw - grid_w) // 2
        cy     = zy + 15

        # column x-offsets
        col_x = []
        cx_off = gx
        for c in range(max_cols):
            col_x.append(cx_off)
            cx_off += col_ws[c] + (SEP_W if c < max_cols - 1 else 0)

        size_hdr = _get_font_size("annotation", posting_group)

        if headers:
            padded_hdr = ([""] * (max_cols - len(headers)) + headers)[-max_cols:]
            for c in range(max_cols):
                hdr_val = str(padded_hdr[c]).strip()
                if hdr_val:
                    out.append(_text(col_x[c] + col_ws[c] // 2, cy, hdr_val,
                                     size=size_hdr, color=COLORS["body"], anchor="middle"))
            cy += 22

        r_idx = 0
        for row in rows:
            if not isinstance(row, list):
                continue
            row_color = COLORS["body"]
            if r_idx < len(row_colors) and row_colors[r_idx]:
                row_color = _resolve_color(row_colors[r_idx])

            padded = ([""] * (max_cols - len(row)) + row)[-max_cols:]
            for c in range(max_cols):
                val  = str(padded[c]).strip()
                bx   = col_x[c]
                mid_x = bx + col_ws[c] // 2
                mid_y = cy + CELL_H // 2 + 6

                if show_grid:
                    out.append(_rect(bx, cy, col_ws[c], CELL_H,
                                     fill="none", stroke=COLORS["grey"], stroke_w=1, rx=6))
                if val:
                    out.append(_text(mid_x, mid_y, val,
                                     size=col_fs[c], color=row_color, anchor="middle"))

                if c < max_cols - 1:
                    sep_x = bx + col_ws[c] + SEP_W // 2
                    out.append(_text(sep_x, mid_y, ":",
                                     size=24, color=COLORS["cyan"],
                                     anchor="middle", weight="bold"))
            cy += CELL_H + ROW_GAP
            r_idx += 1

        return out, cy - zy

    # ── arithmetic mode (default) ─────────────────────────────────────────────
    list_rows = [r for r in rows if isinstance(r, list)]
    if not list_rows:
        return [], 0
    max_cols = max(len(r) for r in list_rows)

    show_grid = spec.get("show_grid", True)

    TARGET_FONT = 18
    MIN_CELL_W  = 40
    MAX_CELL_W  = 120
    PADDING     = 12
    CELL_H      = 40
    ROW_GAP     = 4

    # arithmetic mode uses fixed 40px width boxes
    col_ws = [MIN_CELL_W] * max_cols
    col_fs = [TARGET_FONT] * max_cols

    # Normalize rows to handle list-wrapped lines like ["line"]
    normalized_rows = []
    for r in rows:
        if isinstance(r, list):
            non_empty = [v for v in r if str(v).strip()]
            if non_empty and all(str(v).strip() in ("line", "---") or str(v).strip().startswith("--") for v in non_empty):
                normalized_rows.append("line")
            else:
                normalized_rows.append(r)
        else:
            normalized_rows.append(r)

    padded_rows = []
    for r in normalized_rows:
        if isinstance(r, list):
            padded_rows.append([""] * (max_cols - len(r)) + r)
        else:
            padded_rows.append(r)

    if headers:
        headers = [""] * (max_cols - len(headers)) + headers

    grid_w = sum(col_ws)
    grid_x = zx + (zw - grid_w) // 2

    col_x = []
    cx_off = grid_x
    for c in range(max_cols):
        col_x.append(cx_off)
        cx_off += col_ws[c]

    cy = zy + 15

    if headers:
        size_ann = _get_font_size("annotation", posting_group)
        # Check collision of adjacent header text blocks and shrink size_ann if they overlap
        while size_ann > 8:
            overlap = False
            last_r = None
            for c in range(max_cols):
                val = str(headers[c]).strip()
                if not val:
                    continue
                w_c = len(val) * size_ann * 0.54
                cx_c = col_x[c] + col_ws[c] // 2
                l_c = cx_c - w_c / 2
                r_c = cx_c + w_c / 2
                if last_r is not None and last_r + 4 > l_c:
                    overlap = True
                    break
                last_r = r_c
            if overlap:
                size_ann -= 1
            else:
                break

        for c in range(max_cols):
            val = str(headers[c]).strip()
            if val:
                out.append(_text(col_x[c] + col_ws[c] // 2, cy, val,
                                 size=size_ann, color=COLORS["body"], anchor="middle"))
        cy += 20

    r_idx = 0
    for row in padded_rows:
        if isinstance(row, str) and (row in {"line", "---"} or row.startswith("-")):
            ly = cy + 4
            out.append(_line(grid_x, ly, grid_x + grid_w, ly,
                             color=COLORS["body"], stroke_w=2))
            cy += 10
        else:
            row_color = COLORS["body"]
            if r_idx < len(row_colors) and row_colors[r_idx]:
                row_color = _resolve_color(row_colors[r_idx])

            # Check if this row is a question/unknown row that should span all digit columns
            is_question_row = False
            if max_cols > 1:
                digit_vals = [str(v).strip() for v in row[1:]]
                non_empty_digits = [v for v in digit_vals if v]
                if len(non_empty_digits) == 1 and non_empty_digits[0] == "?":
                    is_question_row = True

            if is_question_row:
                # Render operator in column 0 if present
                val_op = str(row[0]).strip()
                if val_op:
                    mid_x = col_x[0] + col_ws[0] // 2
                    mid_y = cy + CELL_H // 2 + 5
                    out.append(_text(mid_x, mid_y, val_op,
                                     size=TARGET_FONT, color=row_color,
                                     anchor="middle", weight="bold"))
                
                # Render single spanning box for all digit columns
                bx = col_x[1]
                bw = (col_x[-1] + col_ws[-1]) - col_x[1]
                out.append(_rect(bx, cy, bw, CELL_H,
                                 fill="none", stroke=COLORS["grey"], stroke_w=1, rx=4))
                
                # Render "?" centered in this box
                mid_x = bx + bw // 2
                mid_y = cy + CELL_H // 2 + 5
                out.append(_text(mid_x, mid_y, "?",
                                 size=col_fs[1], color=row_color,
                                 anchor="middle"))
            else:
                for c in range(max_cols):
                    raw_val = str(row[c])
                    val  = raw_val.strip()
                    bx   = col_x[c]
                    mid_x = bx + col_ws[c] // 2
                    mid_y = cy + CELL_H // 2 + 5

                    is_line = val in {"line", "---"} or val.startswith("--")
                    if is_line:
                        ly = cy + CELL_H // 2
                        out.append(_line(bx, ly, bx + col_ws[c], ly, color=COLORS["body"], stroke_w=2))
                        continue

                    is_operator = val in ("+", "-", "×", "÷")
                    is_empty_box = not is_operator and not val and raw_val != "" and raw_val.isspace()

                    if (show_grid and not is_operator and val) or is_empty_box:
                        out.append(_rect(bx, cy, col_ws[c], CELL_H,
                                         fill="none", stroke=COLORS["grey"], stroke_w=1, rx=4))
                    if val:
                        fsize  = col_fs[c] if not is_operator else TARGET_FONT
                        weight = "bold" if is_operator else "normal"
                        out.append(_text(mid_x, mid_y, val,
                                         size=fsize, color=row_color,
                                         anchor="middle", weight=weight))
            cy += CELL_H + ROW_GAP
            r_idx += 1

    return out, cy - zy


RENDERERS = {
    "factor_array":      _render_factor_array,
    "math_grid":         _render_math_grid,
}

from ..element_registry import SVGElementSpec, SVGFieldSpec  # noqa: E402

ELEMENT_SPECS: list[SVGElementSpec] = [
    SVGElementSpec(
        name="factor_array",
        subjects=["math"],
        synopsis="number: N — draws N as a dot rectangle (concrete→pictorial for factors/primes)",
        fields=[
            SVGFieldSpec("number", type="integer", required=True,
                         description="The whole number to represent as a dot array"),
            SVGFieldSpec("rows", type="integer", required=False,
                         description="Override row count; omit to auto-pick most-square factor pair"),
            SVGFieldSpec("cols", type="integer", required=False,
                         description="Override column count; must be paired with rows"),
            SVGFieldSpec("caption", type="string", required=False,
                         description="Label below array; defaults to 'N = rows × cols'"),
            SVGFieldSpec("color", type="color", required=False, default="green"),
            SVGFieldSpec("verdict", type="boolean", required=False, default=False,
                         description="If true, adds 'Prime / Composite / neither' label"),
        ],
        notes=[
            "PREFER factor_array over example_panel whenever a slide teaches factors or primes.",
            "verdict: true adds an automatic Prime / Composite / neither label.",
        ],
        render_fn=_render_factor_array,
    ),
    SVGElementSpec(
        name="math_grid",
        subjects=["math"],
        synopsis="rows: [[cells],...], headers: [strings] — column arithmetic or ratio grid",
        fields=[
            SVGFieldSpec("mode", type="string", required=False, default="arithmetic",
                         enum=["arithmetic", "ratio"],
                         description="'arithmetic' (default) for place-value column grids with operators; "
                                     "'ratio' for ratio tables showing A : B (: C …) per row with colon separators"),
            SVGFieldSpec("rows", type="array", required=True,
                         description="List of rows; each row is a list of cell values. "
                                     "In arithmetic mode the string 'line' draws a separator. "
                                     "To render an operator (e.g. +, -), place it as the first cell of the row (e.g. ['+', '2', '0'])."),
            SVGFieldSpec("headers", type="array", required=False,
                         description="Optional column header labels"),
            SVGFieldSpec("row_colors", type="array", required=False,
                         description="Per-row color names (same length as data rows)"),
            SVGFieldSpec("show_grid", type="boolean", required=False, default=True,
                         description="If true (default), draws grid boxes around digit cells in arithmetic mode. If false, hides the boxes but keeps alignment."),
        ],
        notes=[
            "Use mode: ratio for ratio tables (e.g. concentrate:water rows).",
            "Use mode: arithmetic (or omit) for column addition/subtraction with place-value headers.",
            "In arithmetic mode, place the operator (+, -, ×, ÷) as the first cell of the operator row (e.g. ['+', '2', '0']) so that it renders next to the digits without a border box.",
        ],
        render_fn=_render_math_grid,
    ),
]

