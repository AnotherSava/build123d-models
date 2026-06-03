"""Dimensioned draft of the puzzle-piece floor connector.

Each channel end's floor terminates in an interlocking dovetail so adjacent
channels snap directly into one another (this replaces the separate lock clip +
end holes). The profile is point-symmetric (180deg rotation) about the midpoint
of the end edge, which makes the connector genderless: any end mates with any
end, in either orientation (including one piece flipped 180deg about Z).

The lock region is built up to 2x the floor thickness (3.0 mm) so the tab and
socket are chunky and resist snapping; the extra 1.5 mm rises into the channel
interior (the floor bottom stays flat for printing).

Top view looks down -Z at the floor: X = channel/length axis (joint opens to
+X), Y = width. Body is to the left of the joint plane (X=0).

Run from repo root:
    venv/Scripts/python.exe models/other/cable_channel/dimensioned_drafts/puzzle_connector.py
"""
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / '.claude' / 'skills' / 'model-dimensioned-draft' / 'scripts'))
from draft_lib import Drawing, View


# --- Design parameters (mm) -------------------------------------------------
WIDTH = 15.0            # channel width (Y)
HALF = WIDTH / 2        # 7.5
FLOOR_T = 1.5           # nominal floor thickness (= wall_thickness)
LOCK_T = 2 * FLOOR_T    # 3.0  lock region thickness (raised pad eats into channel)
INNER_HALF = HALF - FLOOR_T  # 6.0  inner wall face (tab/socket stay inside this)
PROTRUSION = 3.0        # dovetail depth beyond the joint plane (X=0) — short & stubby
OFFSET_Y = 2.6          # lateral position of the tab (and socket) centre
ROOT_HALF = 1.5         # half-width at the root (joint plane); root width = 3.0
TIP_HALF = 2.0          # half-width at the tip; tip width = 4.0 (wider -> undercut)
LOCK_LEN = PROTRUSION + 1.5  # how far the 3.0 mm pad reaches inboard of the joint
FILLET = 0.7            # corner fillet (applied here and in the model)
CLEARANCE = 0.35        # tab<->socket gap for fit (noted; not drawn)
BODY_LEFT = -9.0        # representative body length shown (truncated)


def _unit(v):
    L = math.hypot(*v)
    return (v[0] / L, v[1] / L) if L else (0.0, 0.0)


def fillet_corners(pts, r, region_x=6.0, min_deflection=20.0, n=8):
    """Round sharp corners that fall inside the feature region (near the joint,
    within the inner width). Near-straight vertices and the body/wall corners are
    left untouched. Approximates each fillet with a short arc."""
    out = []
    for i, P in enumerate(pts):
        A, B = pts[i - 1], pts[(i + 1) % len(pts)]
        la = math.hypot(A[0] - P[0], A[1] - P[1])
        lb = math.hypot(B[0] - P[0], B[1] - P[1])
        if not (abs(P[0]) < region_x and abs(P[1]) < INNER_HALF + 0.5) or la < 1e-6 or lb < 1e-6:
            out.append(P)
            continue
        d1 = _unit((A[0] - P[0], A[1] - P[1]))
        d2 = _unit((B[0] - P[0], B[1] - P[1]))
        a = math.acos(max(-1.0, min(1.0, d1[0] * d2[0] + d1[1] * d2[1])))
        if math.degrees(math.pi - a) < min_deflection:
            out.append(P)
            continue
        t = min(r / math.tan(a / 2), 0.45 * min(la, lb))
        reff = t * math.tan(a / 2)
        bis = _unit((d1[0] + d2[0], d1[1] + d2[1]))
        C = (P[0] + bis[0] * reff / math.sin(a / 2), P[1] + bis[1] * reff / math.sin(a / 2))
        a1 = math.atan2(P[1] + d1[1] * t - C[1], P[0] + d1[0] * t - C[0])
        a2 = math.atan2(P[1] + d2[1] * t - C[1], P[0] + d2[0] * t - C[0])
        da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        out += [(C[0] + reff * math.cos(a1 + da * k / n), C[1] + reff * math.sin(a1 + da * k / n)) for k in range(n + 1)]
    return out


def end_seam():
    """The right-end floor boundary, traced bottom (-Y) to top (+Y).

    Dovetail socket (mouth narrower than its interior) on the -Y half; dovetail
    tab (wider at the tip) on the +Y half. The two are 180deg rotations of each
    other about the origin (the C2 centre), which makes the connector genderless."""
    return [
        (0, -HALF),
        (0, -OFFSET_Y - ROOT_HALF),          # socket mouth, lower
        (-PROTRUSION, -OFFSET_Y - TIP_HALF),  # socket interior, lower (wider)
        (-PROTRUSION, -OFFSET_Y + TIP_HALF),  # socket interior, upper
        (0, -OFFSET_Y + ROOT_HALF),          # socket mouth, upper
        (0, OFFSET_Y - ROOT_HALF),           # tab root, lower
        (PROTRUSION, OFFSET_Y - TIP_HALF),    # tab tip, lower (wider)
        (PROTRUSION, OFFSET_Y + TIP_HALF),    # tab tip, upper
        (0, OFFSET_Y + ROOT_HALF),           # tab root, upper
        (0, HALF),
    ]


def build() -> Drawing:
    d = Drawing('Cable Channel - Puzzle Floor Connector', width=1120, height=760)
    seam = fillet_corners([(BODY_LEFT, -HALF)] + end_seam() + [(BODY_LEFT, HALF)], FILLET)
    seam_body = fillet_corners(end_seam(), FILLET)  # seam alone for the mated view

    # ---------------------------------------------------------------- Top view
    tv = d.add_view(View(origin=(345, 320), scale=22, title='End floor - top view',
                         title_pos=(240, 150), axis_labels=('X', 'Y')))
    tv.path(seam)

    for wy in (INNER_HALF, -INNER_HALF):
        tv.line((BODY_LEFT, wy), (0, wy), stroke='#999', stroke_width=0.5, dasharray='3,3')
    tv.text('inner wall face (Y=6)', (BODY_LEFT, INNER_HALF), size=8, color='#999', anchor='start', dy=-4)

    tv.line((0, -HALF), (0, HALF), stroke='#c0392b', stroke_width=0.8, dasharray='4,3')
    tv.text('●', (0, 0), size=9, color='#1f6feb', anchor='middle', baseline='central')
    tv.text('180° rotation centre', (0, 0), size=8, color='#1f6feb', anchor='end', dx=-8, dy=4)

    tv.text('dovetail tab', (PROTRUSION / 2, OFFSET_Y + TIP_HALF + 0.9), size=9, anchor='middle')
    tv.text('socket', (-PROTRUSION / 2, -OFFSET_Y), size=9, anchor='middle', baseline='central')

    tv.dim_v(u_at=BODY_LEFT, v1=-HALF, v2=HALF, label='15  (width)', side='left', offset_px=30)
    tv.dim_h(v_at=HALF, u1=0, u2=PROTRUSION, label='3.0  depth', side='above', offset_px=16)
    tv.dim_v(u_at=PROTRUSION, v1=OFFSET_Y - TIP_HALF, v2=OFFSET_Y + TIP_HALF, label='4.0 tip', side='right', offset_px=16)
    tv.dim_v(u_at=PROTRUSION, v1=0, v2=OFFSET_Y, label='2.6 offset', side='right', offset_px=58)
    tv.line((0, OFFSET_Y - ROOT_HALF), (1.6, 0.3), stroke='#666', stroke_width=0.5)
    tv.text('root 3.0', (1.75, 0.3), size=8.5, anchor='start', baseline='central')

    tv.text(f'all corners filleted R{FILLET}; tab/socket are 180° rotations of each other',
            (BODY_LEFT, -HALF), size=8.5, color='#777', anchor='start', dy=20)
    tv.text(f'socket is a through-cut of the lock pad; fit clearance {CLEARANCE} mm around the socket',
            (BODY_LEFT, -HALF), size=8.5, color='#777', anchor='start', dy=33)

    # ---------------------------------------------------- Mated pair schematic
    mv = d.add_view(View(origin=(720, 250), scale=15, title='Mated pair (one piece rotated 180°)',
                         title_pos=(660, 110), axis_labels=('X', 'Y')))
    mv.path([(BODY_LEFT, -HALF)] + seam_body + [(BODY_LEFT, HALF)], fill='#dde3ea')
    mv.path(seam_body + [(-BODY_LEFT, HALF), (-BODY_LEFT, -HALF)], fill='#c8d4e3')
    mv.text('A', (BODY_LEFT + 1.5, 0), size=12, anchor='middle', baseline='central')
    mv.text('B (flipped)', (-BODY_LEFT - 2.5, 0), size=11, anchor='middle', baseline='central')
    mv.text("A's tab -> B's socket, and B's tab -> A's socket: the same part mates either way up",
            (0, -HALF), size=8.5, color='#777', anchor='middle', dy=20)

    # ----------------------------- Side view (X-Z): lock pad is 2x floor thick
    sv = d.add_view(View(origin=(255, 690), scale=22, title='Side view (X-Z): lock region = 2× floor thickness',
                         title_pos=(150, 560), axis_labels=('X', 'Z')))
    sv.rect((BODY_LEFT, 0), (-LOCK_LEN, FLOOR_T))          # nominal floor (1.5)
    sv.rect((-LOCK_LEN, 0), (PROTRUSION, LOCK_T))          # raised lock pad + tab (3.0)
    sv.line((0, 0), (0, LOCK_T), stroke='#c0392b', stroke_width=0.8, dasharray='4,3')
    sv.text('raised pad rises into the channel; floor bottom stays flat', (BODY_LEFT, LOCK_T), size=8.5, color='#777', anchor='start', dy=-6)
    sv.text('wall/rim butt flush above (not shown)', (BODY_LEFT, 0), size=8.5, color='#777', anchor='start', dy=22)
    sv.dim_v(u_at=BODY_LEFT, v1=0, v2=FLOOR_T, label='1.5 floor', side='left', offset_px=14)
    sv.dim_v(u_at=PROTRUSION, v1=0, v2=LOCK_T, label='3.0 lock', side='right', offset_px=14)
    sv.dim_h(v_at=LOCK_T, u1=0, u2=PROTRUSION, label='3.0 depth', side='above', offset_px=14)

    return d


if __name__ == '__main__':
    out_path = Path(__file__).parent / 'puzzle_connector.svg'
    build().save(str(out_path))
    print(f'Wrote {out_path}')
