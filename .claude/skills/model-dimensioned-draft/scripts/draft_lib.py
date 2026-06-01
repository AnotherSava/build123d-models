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

import os
from dataclasses import dataclass, field


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
    title_y_offset: float = 200  # px ABOVE the view origin where the title sits (used when title_pos is None)
    title_pos: tuple[float, float] | None = None  # absolute SVG (x, y) for the title; overrides title_y_offset
    axis_labels: tuple[str, str] | None = None  # (horizontal, vertical) labels rendered as a small axis hint before the title
    elements: list[str] = field(default_factory=list)

    def _pt(self, u_mm: float, v_mm: float) -> tuple[float, float]:
        x = self.origin[0] + u_mm * self.scale
        y = self.origin[1] + (-v_mm if self.flip_y else v_mm) * self.scale
        return (x, y)

    def path(self, points_mm: list[tuple[float, float]], *,
             fill: str = '#dde3ea', stroke: str = '#1f2933',
             stroke_width: float = 0.9, dasharray: str | None = None) -> None:
        """Closed polygon from a list of (u, v) mm coordinates."""
        d = 'M ' + ' L '.join(f'{x:.2f} {y:.2f}' for x, y in (self._pt(*p) for p in points_mm)) + ' Z'
        dash = f' stroke-dasharray="{dasharray}"' if dasharray else ''
        self.elements.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{dash}/>')

    def line(self, p1_mm: tuple[float, float], p2_mm: tuple[float, float], *,
             stroke: str = '#222', stroke_width: float = 0.8,
             dasharray: str | None = None) -> None:
        x1, y1 = self._pt(*p1_mm)
        x2, y2 = self._pt(*p2_mm)
        dash = f' stroke-dasharray="{dasharray}"' if dasharray else ''
        self.elements.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{stroke}" stroke-width="{stroke_width}"{dash}/>')

    def rect(self, p_min_mm: tuple[float, float], p_max_mm: tuple[float, float], *,
             fill: str = '#dde3ea', stroke: str = '#1f2933',
             stroke_width: float = 0.9, dasharray: str | None = None) -> None:
        """Axis-aligned rectangle from (u_min, v_min) to (u_max, v_max) in mm."""
        x1, y1 = self._pt(*p_min_mm)
        x2, y2 = self._pt(*p_max_mm)
        x, y = min(x1, x2), min(y1, y2)
        w, h = abs(x2 - x1), abs(y2 - y1)
        dash = f' stroke-dasharray="{dasharray}"' if dasharray else ''
        self.elements.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{dash}/>')

    def text(self, text: str, pos_mm: tuple[float, float], *,
             anchor: str = 'middle', baseline: str | None = None, size: float = 11, color: str = '#222',
             dx: float = 0, dy: float = 0) -> None:
        x, y = self._pt(*pos_mm)
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
        self.elements.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x1:.2f}" y2="{y1+dy:.2f}" stroke="#666" stroke-width="0.5"/>')
        self.elements.append(f'<line x1="{x2:.2f}" y1="{y2:.2f}" x2="{x2:.2f}" y2="{y2+dy:.2f}" stroke="#666" stroke-width="0.5"/>')
        self.elements.append(f'<line x1="{x1:.2f}" y1="{y1+dy:.2f}" x2="{x2:.2f}" y2="{y2+dy:.2f}" stroke="#222" stroke-width="0.8" marker-start="url(#arrL)" marker-end="url(#arrR)"/>')
        mx = (x1 + x2) / 2
        text_y = y1 + dy + (-3 if side == 'above' else 12)
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
        self.elements.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x1+dx:.2f}" y2="{y1:.2f}" stroke="#666" stroke-width="0.5"/>')
        self.elements.append(f'<line x1="{x2:.2f}" y1="{y2:.2f}" x2="{x2+dx:.2f}" y2="{y2:.2f}" stroke="#666" stroke-width="0.5"/>')
        self.elements.append(f'<line x1="{x1+dx:.2f}" y1="{y1:.2f}" x2="{x2+dx:.2f}" y2="{y2:.2f}" stroke="#222" stroke-width="0.8" marker-start="url(#arrL)" marker-end="url(#arrR)"/>')
        my = (y1 + y2) / 2
        text_anchor = 'end' if side == 'left' else 'start'
        text_x = x1 + dx + (-3 if side == 'left' else 3)
        self.elements.append(f'<text x="{text_x:.2f}" y="{my + 4:.2f}" text-anchor="{text_anchor}" font-size="11">{label}</text>')


@dataclass
class Drawing:
    """Top-level SVG drawing with title, subtitle, and multiple views."""
    title: str
    subtitle: str = 'all dimensions in mm'
    width: int = 1000
    height: int = 800
    views: list[View] = field(default_factory=list)

    def add_view(self, view: View) -> View:
        self.views.append(view)
        return view

    def to_svg(self) -> str:
        arrows = (
            '<defs>'
            '<marker id="arrL" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
            '<path d="M 10 0 L 0 5 L 10 10 z" fill="#222"/></marker>'
            '<marker id="arrR" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            '<path d="M 0 0 L 10 5 L 0 10 z" fill="#222"/></marker>'
            '<marker id="axisArr" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
            '<path d="M 0 0 L 12 6 L 0 12 Z" fill="#333"/></marker>'
            '</defs>'
        )
        body_parts: list[str] = []
        for v in self.views:
            if v.title:
                if v.title_pos is not None:
                    tx, ty = v.title_pos
                else:
                    tx = v.origin[0]
                    ty = v.origin[1] - v.title_y_offset
                if v.axis_labels is not None:
                    h_label, v_label = v.axis_labels
                    arm = 22
                    # Axis "L" elbow sits on the title's baseline, axis extends UP and RIGHT
                    cx, cy = tx, ty
                    body_parts.append(f'<line x1="{cx}" y1="{cy}" x2="{cx + arm}" y2="{cy}" stroke="#333" stroke-width="0.9" marker-end="url(#axisArr)"/>')
                    body_parts.append(f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy - arm}" stroke="#333" stroke-width="0.9" marker-end="url(#axisArr)"/>')
                    # Vertical-axis label: TOP of label aligned with TIP (top) of vertical arrow, offset RIGHT of the shaft
                    body_parts.append(f'<text x="{cx + 3}" y="{cy - arm}" dominant-baseline="hanging" font-size="7.5" fill="#333" text-anchor="start">{v_label}</text>')
                    # Horizontal-axis label: RIGHT of label aligned with TIP (right) of horizontal arrow, offset ABOVE the shaft
                    body_parts.append(f'<text x="{cx + arm}" y="{cy - 3}" font-size="7.5" fill="#333" text-anchor="end">{h_label}</text>')
                    # Title sits right of the axis hint at fixed padding
                    title_x = cx + arm + 14
                    body_parts.append(f'<text x="{title_x}" y="{ty}" text-anchor="start" font-size="14" font-weight="bold">{v.title}</text>')
                else:
                    body_parts.append(f'<text x="{tx}" y="{ty}" text-anchor="middle" font-size="14" font-weight="bold">{v.title}</text>')
            body_parts.extend(v.elements)
        body = '\n'.join(body_parts)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
            f'font-family="Helvetica, Arial, sans-serif">\n{arrows}\n'
            f'<rect width="{self.width}" height="{self.height}" fill="white"/>\n'
            f'<text x="{self.width//2}" y="32" text-anchor="middle" font-size="20" font-weight="bold">{self.title}</text>\n'
            f'<text x="{self.width//2}" y="52" text-anchor="middle" font-size="11" fill="#555">{self.subtitle}</text>\n'
            f'{body}\n</svg>\n'
        )

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.to_svg())
