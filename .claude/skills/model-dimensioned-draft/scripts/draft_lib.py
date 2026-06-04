"""Reusable building blocks for SVG technical drawings of build123d models.

Usage:
    from draft_lib import Drawing, View

    d = Drawing('My Model — Dimensioned Draft', width=1000, height=800)

    main = View(origin=(150, 440), scale=14, title='Cross-section')
    main.path([(0,0), (20,0), (20,10), (0,10)], fill='#dde3ea')
    main.dim_h(v_at=10, u1=0, u2=20, label='20', side='above', offset_px=14)
    main.dim_v(u_at=0, v1=0, v2=10, label='10', side='left', offset_px=14)
    d.add_view(main)

    d.save('models/<group>/<name>/dimensioned_drafts/<draft>.svg')
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field

# Axis-hint colours follow the F3D viewer convention: X red, Y green, Z blue
AXIS_COLORS = {'X': '#d32f2f', 'Y': '#2e7d32', 'Z': '#1565c0'}

TITLE_PAD = 18        # px between the title baseline and the view's topmost element
AXIS_ARM = 22         # axis hint arm length
TITLE_FONT_SIZE = 14  # view header font size (bold)

# Helvetica-Bold advance widths in 1/1000 em (Adobe AFM; Arial Bold is
# metric-compatible), used to measure view titles so the axis hint sits at a
# fixed gap after the text. Unlisted glyphs fall back to 600.
_HELVETICA_BOLD_WIDTHS = {
    ' ': 278, '!': 333, '"': 474, '#': 556, '$': 556, '%': 889, '&': 722, "'": 238,
    '(': 333, ')': 333, '*': 389, '+': 584, ',': 278, '-': 333, '.': 278, '/': 278,
    ':': 333, ';': 333, '<': 584, '=': 584, '>': 584, '?': 611, '@': 975,
    '[': 333, '\\': 278, ']': 333, '^': 584, '_': 556, '`': 333, '{': 389, '|': 280, '}': 389, '~': 584,
    '–': 556, '—': 1000, '×': 584, '°': 400, '’': 238, '‘': 238,
    **{c: 556 for c in '0123456789'},
    'A': 722, 'B': 722, 'C': 722, 'D': 722, 'E': 667, 'F': 611, 'G': 778, 'H': 722, 'I': 278,
    'J': 556, 'K': 722, 'L': 611, 'M': 833, 'N': 722, 'O': 778, 'P': 667, 'Q': 778, 'R': 722,
    'S': 667, 'T': 611, 'U': 722, 'V': 667, 'W': 944, 'X': 667, 'Y': 667, 'Z': 611,
    'a': 556, 'b': 611, 'c': 556, 'd': 611, 'e': 556, 'f': 333, 'g': 611, 'h': 611, 'i': 278,
    'j': 278, 'k': 556, 'l': 278, 'm': 889, 'n': 611, 'o': 611, 'p': 611, 'q': 611, 'r': 389,
    's': 556, 't': 333, 'u': 611, 'v': 556, 'w': 778, 'x': 556, 'y': 556, 'z': 500,
}


def _bold_text_width(text: str, size: float) -> float:
    return sum(_HELVETICA_BOLD_WIDTHS.get(c, 600) for c in text) * size / 1000


# Title -> axis hint gap: exactly 5x the word spacing of the header font
TITLE_AXIS_GAP = 5 * _bold_text_width(' ', TITLE_FONT_SIZE)


def fillet_polyline(pts: list[tuple[float, float]], radius: float, indices=None, closed: bool = False, min_deflection: float = 20.0, n: int = 8) -> list[tuple[float, float]]:
    """Round corners of a polyline by replacing vertices with short arc polylines.

    `indices` limits rounding to the listed vertex positions (None = all).
    Endpoints of an open path and near-straight corners (deflection below
    `min_deflection` degrees) are left untouched; the trim is capped at 45% of
    the shorter adjacent segment so neighbouring fillets cannot overlap."""
    out = []
    last = len(pts) - 1
    for i, P in enumerate(pts):
        if (indices is not None and i not in indices) or (not closed and i in (0, last)):
            out.append(P)
            continue
        A, B = pts[i - 1], pts[(i + 1) % len(pts)]
        la = math.hypot(A[0] - P[0], A[1] - P[1])
        lb = math.hypot(B[0] - P[0], B[1] - P[1])
        if la < 1e-6 or lb < 1e-6:
            out.append(P)
            continue
        d1 = ((A[0] - P[0]) / la, (A[1] - P[1]) / la)
        d2 = ((B[0] - P[0]) / lb, (B[1] - P[1]) / lb)
        a = math.acos(max(-1.0, min(1.0, d1[0] * d2[0] + d1[1] * d2[1])))
        if math.degrees(math.pi - a) < min_deflection:
            out.append(P)
            continue
        t = min(radius / math.tan(a / 2), 0.45 * min(la, lb))
        reff = t * math.tan(a / 2)
        bis = (d1[0] + d2[0], d1[1] + d2[1])
        bis_len = math.hypot(*bis)
        bis = (bis[0] / bis_len, bis[1] / bis_len)
        centre = (P[0] + bis[0] * reff / math.sin(a / 2), P[1] + bis[1] * reff / math.sin(a / 2))
        a1 = math.atan2(P[1] + d1[1] * t - centre[1], P[0] + d1[0] * t - centre[0])
        a2 = math.atan2(P[1] + d2[1] * t - centre[1], P[0] + d2[0] * t - centre[0])
        da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        out += [(centre[0] + reff * math.cos(a1 + da * k / n), centre[1] + reff * math.sin(a1 + da * k / n)) for k in range(n + 1)]
    return out


@dataclass
class View:
    """A 2D projection drawn at a fixed origin (in SVG px) and scale (px/mm).

    `flip_y=True` (default) makes positive view-Y go UP visually (matches CAD
    convention; SVG Y normally goes down). Pass `flip_y=False` for views where
    increasing view-Y should go down (e.g. floor-plan top views).
    """
    origin: tuple[float, float]
    scale: float
    title: str = ''
    flip_y: bool = True
    row: int = 0  # page row this view's block is arranged into (views in a row keep add order)
    axis_labels: tuple[str, str] | None = None  # (horizontal, vertical) labels rendered as a small axis hint after the title
    elements: list[str] = field(default_factory=list)
    bounds: list[float] | None = None  # [min_x, min_y, max_x, max_y] of drawn content in SVG px, tracked for header auto-centering

    def _pt(self, u_mm: float, v_mm: float) -> tuple[float, float]:
        x = self.origin[0] + u_mm * self.scale
        y = self.origin[1] + (-v_mm if self.flip_y else v_mm) * self.scale
        return (x, y)

    def _track(self, x: float, y: float) -> None:
        if self.bounds is None:
            self.bounds = [x, y, x, y]
        else:
            self.bounds[0] = min(self.bounds[0], x)
            self.bounds[1] = min(self.bounds[1], y)
            self.bounds[2] = max(self.bounds[2], x)
            self.bounds[3] = max(self.bounds[3], y)

    def _track_text(self, x: float, y: float, text: str, size: float, anchor: str) -> None:
        w = len(text) * size * 0.5
        x1 = x - w if anchor == 'end' else x - w / 2 if anchor == 'middle' else x
        self._track(x1, y - size)
        self._track(x1 + w, y + 3)

    def path(self, points_mm: list[tuple[float, float]], *,
             fill: str = '#dde3ea', stroke: str = '#1f2933',
             stroke_width: float = 0.9, dasharray: str | None = None) -> None:
        """Closed polygon from a list of (u, v) mm coordinates."""
        pts = [self._pt(*p) for p in points_mm]
        for x, y in pts:
            self._track(x, y)
        d = 'M ' + ' L '.join(f'{x:.2f} {y:.2f}' for x, y in pts) + ' Z'
        dash = f' stroke-dasharray="{dasharray}"' if dasharray else ''
        self.elements.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{dash}/>')

    def line(self, p1_mm: tuple[float, float], p2_mm: tuple[float, float], *,
             stroke: str = '#222', stroke_width: float = 0.8,
             dasharray: str | None = None) -> None:
        x1, y1 = self._pt(*p1_mm)
        x2, y2 = self._pt(*p2_mm)
        self._track(x1, y1)
        self._track(x2, y2)
        dash = f' stroke-dasharray="{dasharray}"' if dasharray else ''
        self.elements.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{stroke}" stroke-width="{stroke_width}"{dash}/>')

    def rect(self, p_min_mm: tuple[float, float], p_max_mm: tuple[float, float], *,
             fill: str = '#dde3ea', stroke: str = '#1f2933',
             stroke_width: float = 0.9, dasharray: str | None = None) -> None:
        """Axis-aligned rectangle from (u_min, v_min) to (u_max, v_max) in mm."""
        x1, y1 = self._pt(*p_min_mm)
        x2, y2 = self._pt(*p_max_mm)
        self._track(x1, y1)
        self._track(x2, y2)
        x, y = min(x1, x2), min(y1, y2)
        w, h = abs(x2 - x1), abs(y2 - y1)
        dash = f' stroke-dasharray="{dasharray}"' if dasharray else ''
        self.elements.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{dash}/>')

    def text(self, text: str, pos_mm: tuple[float, float], *,
             anchor: str = 'middle', baseline: str | None = None, size: float = 11, color: str = '#222',
             dx: float = 0, dy: float = 0) -> None:
        x, y = self._pt(*pos_mm)
        self._track_text(x + dx, y + dy, text, size, anchor)
        baseline_attr = f' dominant-baseline="{baseline}"' if baseline else ''
        self.elements.append(f'<text x="{x + dx:.2f}" y="{y + dy:.2f}" text-anchor="{anchor}"{baseline_attr} font-size="{size}" fill="{color}">{text}</text>')

    def dim_h(self, v_at: float, u1: float, u2: float, label: str, *,
              side: str = 'above', offset_px: float = 14) -> None:
        """Horizontal dimension line between (u1, v_at) and (u2, v_at).

        `side='above'`/'below' places the dim line above/below the figure at
        `offset_px` perpendicular distance. Extension lines connect the figure
        to the dim line; arrows mark the dim ends.
        """
        x1, y1 = self._pt(u1, v_at)
        x2, y2 = self._pt(u2, v_at)
        dy = -offset_px if side == 'above' else offset_px
        self._track(x1, y1)
        self._track(x2, y2 + dy)
        self.elements.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x1:.2f}" y2="{y1+dy:.2f}" stroke="#666" stroke-width="0.5"/>')
        self.elements.append(f'<line x1="{x2:.2f}" y1="{y2:.2f}" x2="{x2:.2f}" y2="{y2+dy:.2f}" stroke="#666" stroke-width="0.5"/>')
        self.elements.append(f'<line x1="{x1:.2f}" y1="{y1+dy:.2f}" x2="{x2:.2f}" y2="{y2+dy:.2f}" stroke="#222" stroke-width="0.8" marker-start="url(#arrL)" marker-end="url(#arrR)"/>')
        mx = (x1 + x2) / 2
        text_y = y1 + dy + (-3 if side == 'above' else 12)
        self._track_text(mx, text_y, label, 11, 'middle')
        self.elements.append(f'<text x="{mx:.2f}" y="{text_y:.2f}" text-anchor="middle" font-size="11">{label}</text>')

    def dim_v(self, u_at: float, v1: float, v2: float, label: str, *,
              side: str = 'left', offset_px: float = 14) -> None:
        """Vertical dimension line between (u_at, v1) and (u_at, v2).

        `side='left'`/'right' places the dim line at `offset_px` perpendicular
        distance to the left/right of the figure.
        """
        x1, y1 = self._pt(u_at, v1)
        x2, y2 = self._pt(u_at, v2)
        dx = -offset_px if side == 'left' else offset_px
        self._track(x1, y1)
        self._track(x2 + dx, y2)
        self.elements.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x1+dx:.2f}" y2="{y1:.2f}" stroke="#666" stroke-width="0.5"/>')
        self.elements.append(f'<line x1="{x2:.2f}" y1="{y2:.2f}" x2="{x2+dx:.2f}" y2="{y2:.2f}" stroke="#666" stroke-width="0.5"/>')
        self.elements.append(f'<line x1="{x1+dx:.2f}" y1="{y1:.2f}" x2="{x2+dx:.2f}" y2="{y2:.2f}" stroke="#222" stroke-width="0.8" marker-start="url(#arrL)" marker-end="url(#arrR)"/>')
        my = (y1 + y2) / 2
        text_anchor = 'end' if side == 'left' else 'start'
        text_x = x1 + dx + (-3 if side == 'left' else 3)
        self._track_text(text_x, my + 4, label, 11, text_anchor)
        self.elements.append(f'<text x="{text_x:.2f}" y="{my + 4:.2f}" text-anchor="{text_anchor}" font-size="11">{label}</text>')


PAGE_HEADER_BOTTOM = 55   # bottom of the page title + subtitle block
BLOCK_GAP = 2 * TITLE_PAD  # padding between view blocks, and page header -> first row


@dataclass
class Drawing:
    """Top-level SVG drawing with title, subtitle, and multiple views.

    Views are arranged automatically: each view's block (content + header) is
    measured from its tracked bounds, rows (`View.row`, in add order) are placed
    BLOCK_GAP below the page header and each other, views within a row sit
    BLOCK_GAP apart, rows are centred, and the canvas is sized to the content."""
    title: str
    subtitle: str = 'Dimensioned Draft (mm)'
    views: list[View] = field(default_factory=list)

    def add_view(self, view: View) -> View:
        self.views.append(view)
        return view

    def _header_parts(self, v: View) -> tuple[list[str], list[float]]:
        """Render the view's header (title + axis hint) in authored coordinates and
        return (svg_parts, block_bbox) where block_bbox = [x0, y0, x1, y1] of the
        whole view block (header + content)."""
        x0, y0, x1, y1 = v.bounds if v.bounds is not None else [*v.origin, *v.origin]
        if not v.title:
            return [], [x0, y0, x1, y1]
        title_w = _bold_text_width(v.title, TITLE_FONT_SIZE)
        axis_w = (TITLE_AXIS_GAP + AXIS_ARM + 10) if v.axis_labels is not None else 0
        tx = (x0 + x1) / 2 - (title_w + axis_w) / 2
        ty = y0 - TITLE_PAD
        parts = [f'<text x="{tx:.2f}" y="{ty:.2f}" text-anchor="start" font-size="{TITLE_FONT_SIZE}" font-weight="bold">{v.title}</text>']
        header_top = ty - TITLE_FONT_SIZE
        if v.axis_labels is not None:
            h_label, v_label = v.axis_labels
            # Axis "L" elbow sits on the title's baseline at the fixed gap after
            # the title (measured with the AFM font metrics above)
            cx, cy = tx + title_w + TITLE_AXIS_GAP, ty
            h_color = AXIS_COLORS.get(h_label.upper(), '#333')
            v_color = AXIS_COLORS.get(v_label.upper(), '#333')
            h_marker = f'axisArr{h_label.upper()}' if h_label.upper() in AXIS_COLORS else 'axisArr'
            v_marker = f'axisArr{v_label.upper()}' if v_label.upper() in AXIS_COLORS else 'axisArr'
            parts.append(f'<line x1="{cx:.2f}" y1="{cy}" x2="{cx + AXIS_ARM:.2f}" y2="{cy}" stroke="{h_color}" stroke-width="0.9" marker-end="url(#{h_marker})"/>')
            parts.append(f'<line x1="{cx:.2f}" y1="{cy}" x2="{cx:.2f}" y2="{cy - AXIS_ARM}" stroke="{v_color}" stroke-width="0.9" marker-end="url(#{v_marker})"/>')
            # Vertical-axis label: TOP of label aligned with TIP (top) of vertical arrow, offset RIGHT of the shaft
            parts.append(f'<text x="{cx + 3:.2f}" y="{cy - AXIS_ARM}" dominant-baseline="hanging" font-size="7.5" fill="{v_color}" text-anchor="start">{v_label}</text>')
            # Horizontal-axis label: RIGHT of label aligned with TIP (right) of horizontal arrow, offset ABOVE the shaft
            parts.append(f'<text x="{cx + AXIS_ARM:.2f}" y="{cy - 3}" font-size="7.5" fill="{h_color}" text-anchor="end">{h_label}</text>')
            header_top = ty - AXIS_ARM - 4
        bbox = [min(x0, tx), min(y0, header_top), max(x1, tx + title_w + axis_w), y1]
        return parts, bbox

    def to_svg(self) -> str:
        arrows = (
            '<defs>'
            '<marker id="arrL" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
            '<path d="M 10 0 L 0 5 L 10 10 z" fill="#222"/></marker>'
            '<marker id="arrR" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            '<path d="M 0 0 L 10 5 L 0 10 z" fill="#222"/></marker>'
            '<marker id="axisArr" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
            '<path d="M 0 0 L 12 6 L 0 12 Z" fill="#333"/></marker>'
            + ''.join(f'<marker id="axisArr{axis}" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
                      f'<path d="M 0 0 L 12 6 L 0 12 Z" fill="{color}"/></marker>' for axis, color in AXIS_COLORS.items())
            + '</defs>'
        )

        # Measure every view block in authored coordinates, group into rows
        blocks = [(v, *self._header_parts(v)) for v in self.views]
        rows: dict[int, list[tuple[View, list[str], list[float]]]] = {}
        for entry in blocks:
            rows.setdefault(entry[0].row, []).append(entry)

        # Lay rows out: canvas width fits the widest row; rows are centred and
        # stacked BLOCK_GAP apart below the page header, views BLOCK_GAP apart.
        row_widths = {r: sum(bb[2] - bb[0] for _, _, bb in entries) + BLOCK_GAP * (len(entries) - 1) for r, entries in rows.items()}
        canvas_w = max(row_widths.values()) + 2 * BLOCK_GAP if row_widths else 400

        body_parts: list[str] = []
        y = PAGE_HEADER_BOTTOM + BLOCK_GAP
        for r in sorted(rows):
            entries = rows[r]
            x = (canvas_w - row_widths[r]) / 2
            row_bottom = y
            for v, header, bb in entries:
                dx, dy = x - bb[0], y - bb[1]
                body_parts.append(f'<g transform="translate({dx:.2f}, {dy:.2f})">')
                body_parts.extend(header)
                body_parts.extend(v.elements)
                body_parts.append('</g>')
                x += (bb[2] - bb[0]) + BLOCK_GAP
                row_bottom = max(row_bottom, bb[3] + dy)
            y = row_bottom + BLOCK_GAP
        canvas_h = y

        body = '\n'.join(body_parts)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w:.0f}" height="{canvas_h:.0f}" '
            f'font-family="Helvetica, Arial, sans-serif">\n{arrows}\n'
            f'<rect width="{canvas_w:.0f}" height="{canvas_h:.0f}" fill="white"/>\n'
            f'<text x="{canvas_w / 2:.0f}" y="32" text-anchor="middle" font-size="20" font-weight="bold">{self.title}</text>\n'
            f'<text x="{canvas_w / 2:.0f}" y="52" text-anchor="middle" font-size="11" fill="#555">{self.subtitle}</text>\n'
            f'{body}\n</svg>\n'
        )

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.to_svg())
