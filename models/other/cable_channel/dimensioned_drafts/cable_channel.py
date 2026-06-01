"""Dimensioned draft of the cable channel.

Run from repo root:
    venv/Scripts/python.exe models/other/cable_channel/dimensioned_drafts/cable_channel.py

Outputs cable_channel.svg next to this script.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / '.claude' / 'skills' / 'model-dimensioned-draft' / 'scripts'))
from draft_lib import Drawing, View


# Cross-section profile vertices in (Y_mm, Z_mm), CCW, from the cable channel
# model's Pencil trace (full polygon — mirror not applied).
PROFILE = [
    (0, 0), (20, 0),
    (20, 9.5), (18.837, 9.5),
    (18.163, 11.25), (18.837, 11.924),
    (18.837, 12.9), (17, 12.9),
    (17, 10.5), (18.5, 6.6053),
    (18.5, 1.5), (1.5, 1.5),
    (1.5, 6.6053), (3, 10.5),
    (3, 12.9), (1.163, 12.9),
    (1.163, 11.924), (1.837, 11.25),
    (1.163, 9.5), (0, 9.5),
]


def build() -> Drawing:
    d = Drawing('Cable Channel — Dimensioned Draft', width=1000, height=800)

    # --- Cross-section (Y-Z) ---
    cs = d.add_view(View(origin=(150, 455), scale=14, title='Cross-section',
                         title_pos=(220, 200), axis_labels=('Y', 'Z')))
    cs.path(PROFILE)

    # Cavity slope (cut at the Y-ends only) — dashed red
    cs.line((1, 1.5), (1.5, 3), stroke='#c0392b', stroke_width=0.9, dasharray='4,3')
    cs.line((19, 1.5), (18.5, 3), stroke='#c0392b', stroke_width=0.9, dasharray='4,3')
    cs.text('cavity slope (at Y-ends only)', (10, 0.7), size=9, color='#c0392b')

    # Vertex labels (right side only — left mirrors are symmetric). Each letter
    # sits 0.3 mm from the vertex along the bisector of the wider angle (the
    # interior side at concave vertices A/B/G/H, the exterior side at convex
    # vertices C/D/E/F). Referenced from the Pencil traces in cablechannel.py.
    for label, pos in [('A', (18.667, 9.253)), ('B', (17.870, 11.312)), ('C', (19.114, 11.809)),
                       ('D', (19.049, 13.112)), ('E', (16.788, 13.112)), ('F', (16.705, 10.445)),
                       ('G', (18.795, 6.660)), ('H', (18.712, 1.288))]:
        cs.text(label, pos, size=6, color='#1f6feb', anchor='middle', baseline='central')

    # Top: width sub-segments + overall
    for u1, u2, label in [(0, 1.163, '1.163'), (1.163, 3, '1.837'), (3, 17, '14'), (17, 18.837, '1.837'), (18.837, 20, '1.163')]:
        cs.dim_h(v_at=12.9, u1=u1, u2=u2, label=label, side='above', offset_px=16)
    cs.dim_h(v_at=12.9, u1=0, u2=20, label='20', side='above', offset_px=40)

    # Left: major Z transitions (rim sub-features go in the rim detail callout)
    cs.dim_v(u_at=0, v1=0, v2=1.5, label='1.5', side='left', offset_px=20)
    cs.dim_v(u_at=0, v1=1.5, v2=6.6053, label='5.105', side='left', offset_px=20)
    cs.dim_v(u_at=0, v1=6.6053, v2=9.5, label='2.895', side='left', offset_px=20)
    cs.dim_v(u_at=0, v1=9.5, v2=10.5, label='1', side='left', offset_px=20)
    cs.dim_v(u_at=0, v1=10.5, v2=12.9, label='2.4', side='left', offset_px=20)
    cs.dim_v(u_at=0, v1=1.5, v2=9.5, label='8', side='left', offset_px=50)
    cs.dim_v(u_at=0, v1=9.5, v2=12.9, label='3.4', side='left', offset_px=50)
    cs.dim_v(u_at=0, v1=0, v2=12.9, label='12.9', side='left', offset_px=80)

    # --- Right corner detail (zoomed) ---
    # Shows the wall thickness + cavity slope relationship in isolation.
    # Anchor: SVG (540, 400) shows mm (18.5, 0)  →  origin = (540 - 18.5*80, 400) = (-940, 400)
    zoom = d.add_view(View(origin=(-940, 405), scale=80, title='Right corner detail',
                           title_pos=(515, 200), axis_labels=('Y', 'Z')))
    zoom.path([(18.5, 0), (20, 0), (20, 2), (18.5, 2)])
    zoom.line((19, 0), (18.5, 1.5), stroke='#c0392b', stroke_width=1.2, dasharray='5,3')
    zoom.dim_h(v_at=2, u1=18.5, u2=20, label='1.5  (wall thickness)', side='above', offset_px=14)
    zoom.dim_h(v_at=0, u1=19, u2=20, label='1.0', side='below', offset_px=14)
    zoom.dim_v(u_at=20, v1=0, v2=1.5, label='1.5  (floor)', side='right', offset_px=18)
    zoom.dim_v(u_at=18.5, v1=1.5, v2=2, label='0.5*', side='left', offset_px=18)
    # Slope annotations placed INSIDE the body (right of the slope line) to avoid the right-side dim.
    zoom.text('slope run: 0.5 mm', (18.85, 1.4), anchor='start', size=8, color='#c0392b')
    zoom.text('slope rise: 1.5 mm', (18.85, 1.2), anchor='start', size=8, color='#c0392b')
    zoom.text('(= wall_thickness)', (18.85, 1.0), anchor='start', size=8, color='#c0392b')
    # Footer pushed below the "1.0" dim label (which sits at SVG y ≈ 426).
    zoom.text('* slope_run (cavity widens by this on each side)', (18.5, 0), anchor='start', size=9, color='#777', dy=42)

    # --- Top rim detail (right side, zoomed) ---
    # Title-to-top-dim padding ≈ 18 px; pushed down 20 more so the inter-view padding
    # from the corner-detail footer is ≥ 2× the title-to-top padding (≈ 41 px).
    # Anchor: mm (17, 9.5) at SVG (540, 760)  →  origin = (540 - 17*60, 760 + 9.5*60) = (-480, 1330)
    rim = d.add_view(View(origin=(-480, 1330), scale=60, title='Top rim detail (right side)',
                          title_pos=(500, 510), axis_labels=('Y', 'Z')))
    rim.path([
        (20, 9.5), (18.837, 9.5), (18.163, 11.25), (18.837, 11.924),
        (18.837, 12.9), (17, 12.9), (17, 10.5), (17.385, 9.5),
    ])
    rim.dim_v(u_at=20, v1=9.5, v2=10.5, label='1', side='right', offset_px=14)
    rim.dim_v(u_at=20, v1=10.5, v2=11.25, label='0.75', side='right', offset_px=14)
    rim.dim_v(u_at=20, v1=11.25, v2=11.924, label='0.674', side='right', offset_px=14)
    rim.dim_v(u_at=20, v1=11.924, v2=12.9, label='0.976', side='right', offset_px=14)
    rim.dim_v(u_at=20, v1=9.5, v2=12.9, label='3.4', side='right', offset_px=45)
    rim.dim_h(v_at=12.9, u1=17, u2=18.837, label='1.837', side='above', offset_px=14)
    rim.dim_h(v_at=9.5, u1=18.163, u2=18.837, label='0.674', side='below', offset_px=14)

    # --- Side view (X-Z) ---
    sv = d.add_view(View(origin=(80, 730), scale=4, title='Side view',
                         title_pos=(225, 610), axis_labels=('X', 'Z')))
    sv.rect((0, 0), (100, 12.9))
    for x0, x1 in [(0, 11), (89, 100)]:
        sv.rect((x0, 1.5), (x1, 3), fill='#fcebea', stroke='#c0392b', stroke_width=0.9, dasharray='4,3')
    sv.text('cavity', (5.5, 2.25), size=10, color='#c0392b', dy=-18)
    sv.text('cavity', (94.5, 2.25), size=10, color='#c0392b', dy=-18)
    sv.dim_h(v_at=12.9, u1=0, u2=11, label='11', side='above', offset_px=14)
    sv.dim_h(v_at=12.9, u1=11, u2=89, label='78', side='above', offset_px=14)
    sv.dim_h(v_at=12.9, u1=89, u2=100, label='11', side='above', offset_px=14)
    sv.dim_h(v_at=12.9, u1=0, u2=100, label='100', side='above', offset_px=36)

    return d


if __name__ == '__main__':
    out_path = Path(__file__).parent / 'cable_channel.svg'
    build().save(str(out_path))
    print(f'Wrote {out_path}')
