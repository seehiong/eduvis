"""
Shared canvas constants, palette, SVG primitive builders, and layout utilities.
Imported by all renderer modules — no dependencies on other src.svg submodules.
"""

import html
import re
import textwrap

# Characters banned in XML 1.0 (control chars outside #x9/#xA/#xD, plus U+FFFE/FFFF)
_XML_INVALID_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]')

# ── Canvas & palette ──────────────────────────────────────────────────────────

CANVAS_W  = 800
CANVAS_H  = 480
MARGIN    = 80   # Symmetrical 80px horizontal margin
HEADER_H  = 65   # y of the separator line beneath the title
CONTENT_Y = 90   # top of the first content zone (aligned to standards)
LEAD      = 22   # line-height in px for body text

COLORS = {
    "background": "#f8fafc",
    "panel":      "#ffffff",
    "separator":  "#e2e8f0",
    "title":      "#0284c7",
    "body":       "#334155",
    "bullet":     "#10b981",
    "heading":    "#0f172a",
    "green":      "#22c55e",
    "red":        "#ef4444",
    "yellow":     "#eab308",
    "cyan":       "#06b6d4",
    "blue":       "#3b82f6",
    "orange":     "#f97316",
    "purple":     "#a855f7",
    "pink":       "#ec4899",
    "grey":       "#64748b",
    "gray":       "#64748b",
    "white":      "#ffffff",
}

# ── SVG primitive builders ────────────────────────────────────────────────────

def _esc(s: str) -> str:
    return html.escape(_XML_INVALID_RE.sub('', str(s)))


def _resolve_text_color(color_in: str | None) -> str:
    if not color_in:
        return COLORS["body"]
    
    resolved = COLORS.get(str(color_in).lower(), color_in)
    
    mapping = {
        "#22c55e": "#15803d",
        "#eab308": "#a16207",
        "#06b6d4": "#0e7490",
        "#3b82f6": "#1d4ed8",
        "#ef4444": "#b91c1c",
        "#f97316": "#c2410c",
        "#a855f7": "#701a75",
        "#ec4899": "#be185d",
    }
    
    return mapping.get(resolved.lower(), resolved)


def _text(x, y, content, size=14, color=None, weight="normal", anchor="start") -> str:
    c = _resolve_text_color(color)
    return (
        f'  <text x="{x}" y="{y}" font-family="Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{c}" '
        f'text-anchor="{anchor}">{_esc(content)}</text>'
    )


def _rect(x, y, w, h, fill=None, stroke=None, stroke_w=1.5, rx=8) -> str:
    f = fill   or COLORS["panel"]
    s = stroke or COLORS["separator"]
    return (
        f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
        f'fill="{f}" stroke="{s}" stroke-width="{stroke_w}" />'
    )


def _line(x1, y1, x2, y2, color=None, stroke_w=1.5) -> str:
    c = color or COLORS["separator"]
    return (
        f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{c}" stroke-width="{stroke_w}" />'
    )


def _resolve_color(name: str) -> str:
    return COLORS.get(str(name).lower(), COLORS["separator"])


def _get_font_size(role: str, posting_group: str = "G1") -> int:
    """Return the font size for a given role and grade level according to visual standards."""
    lvl = str(posting_group).upper()
    if lvl not in ("G1", "G2", "G3"):
        lvl = "G1"

    if role == "title":
        return 18
    elif role in ("body", "label"):
        return {"G1": 12, "G2": 14, "G3": 16}[lvl]
    elif role == "annotation":
        return {"G1": 10, "G2": 12, "G3": 12}[lvl]
    return 14

# ── Text wrapping ─────────────────────────────────────────────────────────────

def _wrap(text: str, max_px: float, size: int) -> list[str]:
    """Split *text* into lines that fit within *max_px* pixels."""
    max_chars = max(1, int(max_px / (size * 0.54)))
    return textwrap.wrap(str(text), width=max_chars) or [""]

# ── Zone geometry ─────────────────────────────────────────────────────────────

def _zones(layout: str, zone_keys: list) -> dict:
    """Return a {zone_name: (x, y, w, h)} map for the given layout string."""
    has_bot = "bottom" in zone_keys
    lk = layout.lower().replace(" ", "").replace("-", "")

    if "twocolumn" in lk:
        col_w = 315  # 315px width per visual standards
        col_h = 230 if has_bot else 340
        bot_y = CONTENT_Y + col_h + 10
        return {
            "left":   (MARGIN, CONTENT_Y, col_w, col_h),
            "right":  (MARGIN + col_w + 10, CONTENT_Y, col_w, col_h),  # 10px gutter
            "bottom": (MARGIN, bot_y, CANVAS_W - 2 * MARGIN, CANVAS_H - bot_y - 10),
        }

    if "visual" in lk:
        vis_h = 150
        txt_y = CONTENT_Y + vis_h + 10
        txt_h = 100 if has_bot else CANVAS_H - txt_y - 10
        bot_y = txt_y + txt_h + 10
        return {
            "center": (MARGIN, CONTENT_Y, CANVAS_W - 2 * MARGIN, vis_h),
            "full":   (MARGIN, txt_y, CANVAS_W - 2 * MARGIN, txt_h),
            "bottom": (MARGIN, bot_y, CANVAS_W - 2 * MARGIN, CANVAS_H - bot_y - 10),
        }

    return {
        "full": (MARGIN, CONTENT_Y, CANVAS_W - 2 * MARGIN, CANVAS_H - CONTENT_Y - 10),
    }
