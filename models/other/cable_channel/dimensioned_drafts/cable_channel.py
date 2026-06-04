"""Dimensioned draft of the cable channel cross-section.

Views: full cross-section (Y-Z) with vertex labels A-H matching the Pencil
trace comments in cablechannel.py, plus a zoomed rim detail showing the
V-groove and the rim_fillet rounding at corners A-D. End/connector geometry
(puzzle dovetail, lead-ins) lives in the puzzle_connector draft.

Run from repo root:
    venv/Scripts/python.exe models/other/cable_channel/dimensioned_drafts/cable_channel.py

Outputs cable_channel.svg next to this script.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / '.claude' / 'skills' / 'model-dimensioned-draft' / 'scripts'))
from draft_lib import Drawing, View, fillet_polyline


# --- Design parameters (mm), mirrored from CableChannelDimensions ------------
WIDTH = 15.0
WALL = 1.2                  # wall_thickness (= floor thickness)
TOTAL = 12.9                # total_height
RIM = 3.4                   # rim_height
G_DEPTH = 0.674             # rim_groove_depth
APEX_DZ = 1.75              # rim_groove_apex_dz
RIM_INNER_FACE = 2.4        # rim_inner_face_length
RIM_FILLET = 0.4            # rim_fillet (corners A-D, channel and cap alike)

# Derived (same formulas as the model's properties)
SHOULDER = TOTAL - RIM                          # 9.5   outer wall top
UPPER_DZ = APEX_DZ + G_DEPTH                    # 2.424 groove upper edge above shoulder
RIM_OUT = G_DEPTH / 2                           # 0.337 rim_outer_offset
INNER_DIAG_DZ = WALL * APEX_DZ / G_DEPTH        # 3.116 inner diagonal Z extent
CAVITY_WALL = TOTAL - WALL - RIM_INNER_FACE - INNER_DIAG_DZ  # 6.184

# Cross-section vertices, right half (Y, Z) — letters match the Pencil trace
A = (WIDTH - (WALL - RIM_OUT), SHOULDER)
B = (A[0] - G_DEPTH, SHOULDER + APEX_DZ)
C = (A[0], SHOULDER + UPPER_DZ)
D = (A[0], TOTAL)
E = (D[0] - (WALL + RIM_OUT), TOTAL)
F = (E[0], TOTAL - RIM_INNER_FACE)
G = (F[0] + WALL, F[1] - INNER_DIAG_DZ)
H = (G[0], WALL)


def mirrored(p):
    return (WIDTH - p[0], p[1])


# Full polygon, CCW: floor, right side up, across the rim, left side down
PROFILE = [(0, 0), (WIDTH, 0), (WIDTH, SHOULDER), A, B, C, D, E, F, G, H,
           mirrored(H), mirrored(G), mirrored(F), mirrored(E), mirrored(D),
           mirrored(C), mirrored(B), mirrored(A), (0, SHOULDER)]


def build() -> Drawing:
    d = Drawing('Cable Channel')

    # --- Cross-section (Y-Z) ---
    cs = d.add_view(View(origin=(150, 375), scale=14, title='Cross-section', axis_labels=('Y', 'Z')))
    cs.path(PROFILE)

    # Vertex labels (right side only — left mirrors are symmetric). Each letter
    # sits ~0.3 mm from the vertex along the bisector of the wider angle (the
    # interior side at concave vertices A/B/G/H, the exterior side at convex
    # vertices C/D/E/F). Referenced from the Pencil traces in cablechannel.py.
    for label, vertex, (dx, dy) in [('A', A, (-0.170, -0.247)), ('B', B, (-0.293, 0.062)),
                                    ('C', C, (0.277, -0.115)), ('D', D, (0.212, 0.212)),
                                    ('E', E, (-0.212, 0.212)), ('F', F, (-0.295, -0.055)),
                                    ('G', G, (0.295, 0.055)), ('H', H, (0.212, -0.212))]:
        cs.text(label, (vertex[0] + dx, vertex[1] + dy), size=6, color='#1f6feb', anchor='middle', baseline='central')

    # Top: rim opening + overall (the small rim-wall segments are dimensioned
    # in the rim detail, where they are legible)
    cs.dim_h(v_at=TOTAL, u1=mirrored(E)[0], u2=E[0], label=f'{E[0] - mirrored(E)[0]:g}', side='above', offset_px=16)
    cs.dim_h(v_at=TOTAL, u1=0, u2=WIDTH, label=f'{WIDTH:g}', side='above', offset_px=40)

    # Left: major Z transitions (rim sub-features go in the rim detail callout)
    cs.dim_v(u_at=0, v1=0, v2=WALL, label=f'{WALL:g}', side='left', offset_px=20)
    cs.dim_v(u_at=0, v1=WALL, v2=G[1], label=f'{CAVITY_WALL:.4g}', side='left', offset_px=20)
    cs.dim_v(u_at=0, v1=G[1], v2=SHOULDER, label=f'{SHOULDER - G[1]:.4g}', side='left', offset_px=20)
    cs.dim_v(u_at=0, v1=SHOULDER, v2=F[1], label=f'{F[1] - SHOULDER:g}', side='left', offset_px=20)
    cs.dim_v(u_at=0, v1=F[1], v2=TOTAL, label=f'{RIM_INNER_FACE:g}', side='left', offset_px=20)
    cs.dim_v(u_at=0, v1=WALL, v2=SHOULDER, label=f'{SHOULDER - WALL:g}', side='left', offset_px=50)
    cs.dim_v(u_at=0, v1=SHOULDER, v2=TOTAL, label=f'{RIM:g}', side='left', offset_px=50)
    cs.dim_v(u_at=0, v1=0, v2=TOTAL, label=f'{TOTAL:g}', side='left', offset_px=80)

    # Footer left-aligns with the outermost dim ladder line (offset_px=80)
    cs.text(f'corners A–D rounded R{RIM_FILLET:g} (rim_fillet) — drawn in the rim detail', (0, 0), size=8.5, color='#777', anchor='start', dx=-80, dy=30)
    cs.text('floor lock pad and end connectors are in the puzzle_connector draft', (0, 0), size=8.5, color='#777', anchor='start', dx=-80, dy=43)

    # --- Top rim detail (right side, zoomed) ---
    # Anchor: mm (12.6, 9.5) at SVG (600, 371)  →  origin = (600 - 12.6*60, 371 + 9.5*60)
    diag_at_shoulder = (F[0] + WALL * (F[1] - SHOULDER) / INNER_DIAG_DZ, SHOULDER)
    rim = d.add_view(View(origin=(600 - 12.6 * 60, 371 + 9.5 * 60), scale=60, title='Top rim detail (right side)', axis_labels=('Y', 'Z')))
    rim_outline = [(WIDTH, SHOULDER), A, B, C, D, E, F, diag_at_shoulder]
    rim.path(fillet_polyline(rim_outline, RIM_FILLET, indices={1, 2, 3, 4}))   # fillets at A, B, C, D

    rim.dim_v(u_at=WIDTH, v1=SHOULDER, v2=F[1], label=f'{F[1] - SHOULDER:g}', side='right', offset_px=14)
    rim.dim_v(u_at=WIDTH, v1=F[1], v2=B[1], label=f'{B[1] - F[1]:g}', side='right', offset_px=14)
    rim.dim_v(u_at=WIDTH, v1=B[1], v2=C[1], label=f'{G_DEPTH:g}', side='right', offset_px=14)
    rim.dim_v(u_at=WIDTH, v1=C[1], v2=TOTAL, label=f'{TOTAL - C[1]:.4g}', side='right', offset_px=14)
    rim.dim_v(u_at=WIDTH, v1=SHOULDER, v2=TOTAL, label=f'{RIM:g}', side='right', offset_px=45)
    rim.dim_h(v_at=TOTAL, u1=E[0], u2=D[0], label=f'{WALL + RIM_OUT:g}', side='above', offset_px=14)
    rim.dim_h(v_at=TOTAL, u1=D[0], u2=WIDTH, label=f'{WALL - RIM_OUT:g}', side='above', offset_px=14)
    rim.dim_h(v_at=SHOULDER, u1=B[0], u2=A[0], label=f'{G_DEPTH:g}', side='below', offset_px=14)

    # Centered under the view block (figure + right dim ladder)
    rim.text(f'A–D filleted R{RIM_FILLET:g}; the cap inner profile carries the same arcs, so the fit stays tight',
             (E[0], SHOULDER), size=8.5, color='#777', anchor='middle', dx=100, dy=52)

    return d


if __name__ == '__main__':
    out_path = Path(__file__).parent / 'cable_channel.svg'
    build().save(str(out_path))
    print(f'Wrote {out_path}')
