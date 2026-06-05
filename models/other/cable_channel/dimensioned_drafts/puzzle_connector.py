"""Dimensioned draft of the puzzle-piece floor connector.

Each channel end's floor terminates in an interlocking dovetail so adjacent
channels snap directly into one another (this replaces the separate lock clip +
end holes). The profile is point-symmetric (180deg rotation) about the midpoint
of the end edge, which makes the connector genderless: any end mates with any
end, in either orientation (including one piece flipped 180deg about Z).

The lock region is built up to 2x the floor thickness (2.4 mm) so the tab and
socket are chunky and resist snapping; the extra 1.2 mm rises into the channel
interior (the floor bottom stays flat for printing).

Insertion lead-in: the joint assembles vertically (one piece drops onto the
other), with near-zero clearance. To ease the drop, the top and bottom 25%
of the lock height (0.6 mm each) are graded: the tab shrinks by 0.3 mm per
side toward its top and bottom edges, and the socket opens by 0.3 mm per side
toward both mouths. Every contact pair then has lead-ins on both parts — the
descending tab's tapered bottom meets a flared socket top, and the descending
socket's flared bottom passes over a tapered tab top.

Top view looks down -Z at the end joint: X = channel/length axis (joint opens
to +X), Y = width. Body is to the left of the joint plane (X=0); the side
walls butt at the joint plane.

Run from repo root:
    venv/Scripts/python.exe models/other/cable_channel/dimensioned_drafts/puzzle_connector.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / '.claude' / 'skills' / 'model-dimensioned-draft' / 'scripts'))
from draft_lib import Drawing, View, fillet_polyline


# --- Design parameters (mm) -------------------------------------------------
WIDTH = 15.0            # channel width (Y)
HALF = WIDTH / 2        # 7.5
FLOOR_T = 1.2           # nominal floor thickness (= wall_thickness)
LOCK_T = 2 * FLOOR_T    # 2.4  lock region thickness (raised pad eats into channel)
INNER_HALF = HALF - FLOOR_T  # 6.3  inner wall face (tab/socket stay inside this)
PROTRUSION = 3.0        # dovetail depth beyond the joint plane (X=0) — short & stubby
OFFSET_Y = 3.0          # lateral position of the tab (and socket) centre
ROOT_HALF = 1.2         # half-width at the root (joint plane); root width = 2.4
TIP_HALF = 2.5          # half-width at the tip; tip width = 5.0 (wider -> undercut)
FILLET = 0.8            # corner fillet (applied here and in the model)
CLEARANCE = 0.05        # tab<->socket gap for fit; the lead-ins ease entry
LOCK_LEN = PROTRUSION + CLEARANCE + 1.5  # how far the pad reaches inboard of the joint
LEAD_IN = 0.3           # per-side lead-in at the top and bottom edges (tab -, socket +)
LEAD_IN_FRACTION = 0.25  # fraction of the lock height each lead-in is graded over
LEAD_IN_H = LEAD_IN_FRACTION * LOCK_T  # 0.6  lead-in zone height (each end)
GROOVE_D = 0.674        # rim_groove_depth
Y_ACD = HALF - (FLOOR_T - GROOVE_D / 2)  # 6.637 rim outer face: cross-section A, C and D project onto this line
Y_B = Y_ACD - GROOVE_D                   # 5.963 V-groove apex line (cross-section B)
Y_EF = HALF - 2 * FLOOR_T                # 5.1   rim inner face line (cross-section E, F)
BODY_LEFT = -9.0        # representative body length shown (truncated)


def fillet_seam(pts, dovetail_start):
    """Round the eight dovetail vertices (starting at index `dovetail_start` in
    `pts`); body and wall corners stay sharp, as in the model."""
    return fillet_polyline(pts, FILLET, indices=set(range(dovetail_start, dovetail_start + 8)), closed=True)


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
    d = Drawing('Cable Channel - Puzzle Floor Connector')
    seam = fillet_seam([(BODY_LEFT, -HALF)] + end_seam() + [(BODY_LEFT, HALF)], dovetail_start=2)
    seam_body = fillet_seam(end_seam(), dovetail_start=1)  # seam alone for the mated view

    # ---------------------------------------------------------------- Top view
    tv = d.add_view(View(origin=(345, 334), scale=22, title='End joint - top view', axis_labels=('X', 'Y')))
    tv.path(seam)

    for wy in (INNER_HALF, -INNER_HALF):
        tv.line((BODY_LEFT, wy), (0, wy), stroke='#999', stroke_width=0.5, dasharray='3,3')
    tv.text(f'inner wall face (Y={INNER_HALF:g})', (BODY_LEFT, INNER_HALF), size=8, color='#999', anchor='start', dy=-4)
    tv.line((-LOCK_LEN, -INNER_HALF), (-LOCK_LEN, INNER_HALF), stroke='#999', stroke_width=0.5, dasharray='3,3')
    tv.text(f'lock pad reach (z 0–{LOCK_T:g})', (-LOCK_LEN, -INNER_HALF), size=8, color='#999', anchor='middle', dy=12)

    tv.line((0, -HALF), (0, HALF), stroke='#c0392b', stroke_width=0.8, dasharray='4,3')
    tv.text('●', (0, 0), size=9, color='#1f6feb', anchor='middle', baseline='central')
    tv.text('180° rotation centre', (0, 0), size=8, color='#1f6feb', anchor='end', dx=-8, dy=4)

    tv.text('dovetail tab', (PROTRUSION / 2, OFFSET_Y + TIP_HALF + 0.9), size=9, anchor='middle')
    tv.text('socket', (-PROTRUSION / 2, -OFFSET_Y), size=9, anchor='middle', baseline='central')
    # Key-point letters at the nominal (pre-fillet) seam corners, placed along the
    # bisector of the wider angle. Lettering continues the cross-section draft's
    # A-H, so references stay unique across the two drawings.
    for letter, pos in [('J', (0.28, -HALF - 0.18)), ('M', (0.28, -OFFSET_Y - ROOT_HALF + 0.3)),
                        ('N', (-PROTRUSION - 0.22, -OFFSET_Y - TIP_HALF - 0.22)), ('P', (-PROTRUSION - 0.22, -OFFSET_Y + TIP_HALF + 0.22)),
                        ('Q', (0.28, -OFFSET_Y + ROOT_HALF - 0.3)), ('R', (-0.25, OFFSET_Y - ROOT_HALF - 0.18)),
                        ('S', (PROTRUSION + 0.22, OFFSET_Y - TIP_HALF - 0.22)), ('T', (PROTRUSION + 0.22, OFFSET_Y + TIP_HALF + 0.22)),
                        ('U', (-0.25, OFFSET_Y + ROOT_HALF + 0.18)), ('X', (0.35, HALF + 0.28))]:
        tv.text(letter, pos, size=6, color='#1f6feb', anchor='middle', baseline='central')

    tv.dim_v(u_at=BODY_LEFT, v1=-HALF, v2=HALF, label=f'{WIDTH:g}  (width)', side='left', offset_px=30)
    tv.dim_h(v_at=HALF, u1=0, u2=PROTRUSION, label=f'{PROTRUSION:g}  depth', side='above', offset_px=16)
    tv.dim_v(u_at=PROTRUSION, v1=OFFSET_Y - TIP_HALF, v2=OFFSET_Y + TIP_HALF, label=f'{2 * TIP_HALF:g} tip', side='right', offset_px=16)
    tv.dim_v(u_at=PROTRUSION, v1=0, v2=OFFSET_Y, label=f'{OFFSET_Y:g} offset', side='right', offset_px=58)
    tv.line((0, OFFSET_Y - ROOT_HALF), (1.6, 0.3), stroke='#666', stroke_width=0.5)
    tv.text(f'root {2 * ROOT_HALF:g}', (1.75, 0.3), size=8.5, anchor='start', baseline='central')

    tv.text(f'all corners filleted R{FILLET}; tab/socket are 180° rotations of each other',
            (BODY_LEFT, -HALF), size=8.5, color='#777', anchor='start', dy=20)
    tv.text(f'socket is a through-cut of the lock pad, grown by the {CLEARANCE:g} fit clearance — profile shown in the middle band ({LEAD_IN_H:g} ≤ z ≤ {LOCK_T - LEAD_IN_H:g})',
            (BODY_LEFT, -HALF), size=8.5, color='#777', anchor='start', dy=33)
    tv.text('key points marked at the nominal (pre-fillet) corners; letters continue the cross-section draft (A–H there)',
            (BODY_LEFT, -HALF), size=8.5, color='#777', anchor='start', dy=46)

    # ---------------------------------------------------- Mated pair schematic
    mv = d.add_view(View(origin=(720, 252), scale=15, title='Mated pair (one piece rotated 180°)', axis_labels=('X', 'Y')))
    mv.path([(BODY_LEFT, -HALF)] + seam_body + [(BODY_LEFT, HALF)], fill='#dde3ea')
    mv.path(seam_body + [(-BODY_LEFT, HALF), (-BODY_LEFT, -HALF)], fill='#c8d4e3')
    mv.text('A', (BODY_LEFT + 1.5, 0), size=12, anchor='middle', baseline='central')
    mv.text('B (flipped)', (-BODY_LEFT - 2.5, 0), size=11, anchor='middle', baseline='central')
    mv.text("A's tab -> B's socket, and B's tab -> A's socket: the same part mates either way up",
            (0, -HALF), size=8.5, color='#777', anchor='middle', dy=20)

    # ----------------------------- Side view (X-Z): lock pad is 2x floor thick
    sv = d.add_view(View(origin=(255, 710), scale=22, title='Side view: lock = 2× floor', row=1, axis_labels=('X', 'Z')))
    sv.rect((BODY_LEFT, 0), (-LOCK_LEN, FLOOR_T))          # nominal floor
    sv.path([(-LOCK_LEN, 0), (PROTRUSION - LEAD_IN, 0), (PROTRUSION, LEAD_IN_H),
             (PROTRUSION, LOCK_T - LEAD_IN_H), (PROTRUSION - LEAD_IN, LOCK_T),
             (-LOCK_LEN, LOCK_T)])                         # raised lock pad + tab, tip lead-ins top and bottom
    sv.line((0, 0), (0, LOCK_T), stroke='#c0392b', stroke_width=0.8, dasharray='4,3')
    sv.text('floor', (BODY_LEFT + 2.2, FLOOR_T / 2), size=8, anchor='middle', baseline='central')
    sv.text('lock pad', (-LOCK_LEN / 2, LOCK_T - 0.6), size=8, anchor='middle', baseline='central')
    sv.text('tab', (PROTRUSION / 2, LOCK_T - 0.6), size=8, anchor='middle', baseline='central')
    sv.text('raised pad rises into the channel; floor bottom stays flat', (BODY_LEFT, LOCK_T), size=8.5, color='#777', anchor='start', dy=-6)
    sv.text('wall/rim butt flush above (not shown)', (BODY_LEFT, 0), size=8.5, color='#777', anchor='start', dy=22)
    sv.text(f'tab faces pull in {LEAD_IN:g} over the top and bottom {LEAD_IN_H:g} — see lead-in section', (BODY_LEFT, 0), size=8.5, color='#777', anchor='start', dy=35)
    sv.dim_v(u_at=BODY_LEFT, v1=0, v2=FLOOR_T, label=f'{FLOOR_T:g} floor', side='left', offset_px=14)
    sv.dim_v(u_at=PROTRUSION, v1=0, v2=LOCK_T, label=f'{LOCK_T:g} lock', side='right', offset_px=14)
    sv.dim_h(v_at=LOCK_T, u1=0, u2=PROTRUSION, label=f'{PROTRUSION:g} depth', side='above', offset_px=14)

    # --------- Lead-in section (Y-Z): graded entry over the top and bottom 25%
    # Vertical section across the tab tip, mated at full seat. In the middle band
    # tab and socket faces sit at the fit clearance (drawn coincident); toward both
    # edges the tab pulls in and the socket opens out, so the edges never have to
    # align exactly.
    WALL_HALF = 4.2  # representative socket-wall extent shown (truncated)
    lv = d.add_view(View(origin=(840, 649), scale=50, title='Lead-in — section across the tab tip (mated)', row=1, axis_labels=('Y', 'Z')))
    for s in (-1, 1):  # A's lock pad around the socket, opened +LEAD_IN/side toward both mouths
        lv.path([(s * WALL_HALF, 0), (s * (TIP_HALF + LEAD_IN), 0), (s * TIP_HALF, LEAD_IN_H),
                 (s * TIP_HALF, LOCK_T - LEAD_IN_H), (s * (TIP_HALF + LEAD_IN), LOCK_T), (s * WALL_HALF, LOCK_T)])
    # B's tab, pulled in -LEAD_IN/side toward its top and bottom edges
    lv.path([(-(TIP_HALF - LEAD_IN), 0), (TIP_HALF - LEAD_IN, 0), (TIP_HALF, LEAD_IN_H),
             (TIP_HALF, LOCK_T - LEAD_IN_H), (TIP_HALF - LEAD_IN, LOCK_T),
             (-(TIP_HALF - LEAD_IN), LOCK_T), (-TIP_HALF, LOCK_T - LEAD_IN_H), (-TIP_HALF, LEAD_IN_H)], fill='#c8d4e3')
    lv.text('B tab — drops in ▼', (0, LOCK_T / 2 + 0.45), size=9, anchor='middle', baseline='central')
    lv.text('S', (-TIP_HALF - 0.18, LOCK_T / 2), size=6, color='#1f6feb', anchor='middle', baseline='central')
    lv.text('T', (TIP_HALF + 0.18, LOCK_T / 2), size=6, color='#1f6feb', anchor='middle', baseline='central')
    lv.text(f'{2 * TIP_HALF:g} nominal (+{CLEARANCE:g} clearance) in the middle band', (0, LOCK_T / 2 - 0.45), size=8, color='#777', anchor='middle', baseline='central')
    lv.text('A', (-WALL_HALF + 0.55, LOCK_T / 2 + 0.45), size=9, anchor='middle', baseline='central')
    lv.text('A', (WALL_HALF - 0.55, LOCK_T / 2 + 0.45), size=9, anchor='middle', baseline='central')

    lv.dim_h(v_at=LOCK_T, u1=-(TIP_HALF - LEAD_IN), u2=TIP_HALF - LEAD_IN, label=f'{2 * (TIP_HALF - LEAD_IN):g} tab top (−{LEAD_IN:g}/side)', side='above', offset_px=16)
    lv.dim_h(v_at=0, u1=-(TIP_HALF - LEAD_IN), u2=TIP_HALF - LEAD_IN, label=f'{2 * (TIP_HALF - LEAD_IN):g} tab bottom (−{LEAD_IN:g}/side)', side='below', offset_px=14)
    lv.dim_h(v_at=0, u1=-(TIP_HALF + LEAD_IN), u2=TIP_HALF + LEAD_IN, label=f'{2 * (TIP_HALF + LEAD_IN):g} socket mouth at top and bottom (+{LEAD_IN:g}/side)', side='below', offset_px=36)
    lv.dim_v(u_at=WALL_HALF, v1=0, v2=LOCK_T, label=f'{LOCK_T:g} lock', side='right', offset_px=14)
    lv.dim_v(u_at=-WALL_HALF, v1=0, v2=LEAD_IN_H, label=f'{LEAD_IN_H:g} lead-in ({LEAD_IN_FRACTION:.0%})', side='left', offset_px=14)
    lv.dim_v(u_at=-WALL_HALF, v1=LOCK_T - LEAD_IN_H, v2=LOCK_T, label=f'{LEAD_IN_H:g}', side='left', offset_px=14)

    # --------------- End wall edges (X-Y): cross-section features in plan view
    # Same end as the top view, with the wall's cross-section features projected
    # as edge lines: A/C/D (rim outer face), B (groove apex), G/H (cavity wall
    # face), E/F (rim inner face) — letters from the cross-section draft.
    ev = d.add_view(View(origin=(900, 1000), scale=30, title='End wall edges - top view', row=2, axis_labels=('X', 'Y')))
    EV_LEFT = -6.0
    # Walls only — each band is the wall + rim plan footprint (outer skin down to
    # the rim inner face E/F); the floor and its dovetail are omitted, so the
    # space between the bands is the open channel. Both walls butt at the joint.
    for s in (1, -1):
        ev.path([(EV_LEFT, s * Y_EF), (0, s * Y_EF), (0, s * HALF), (EV_LEFT, s * HALF)])
        ev.line((EV_LEFT, s * Y_ACD), (0, s * Y_ACD), stroke='#1f2933', stroke_width=0.5)
        ev.line((EV_LEFT, s * Y_B), (0, s * Y_B), stroke='#999', stroke_width=0.5, dasharray='3,3')
        ev.line((EV_LEFT, s * INNER_HALF), (0, s * INNER_HALF), stroke='#999', stroke_width=0.5, dasharray='3,3')
        for label, y in (('A/C/D', Y_ACD), ('G/H', INNER_HALF), ('B', Y_B), ('E/F', Y_EF)):
            ev.text(label, (EV_LEFT, s * y), size=6, color='#1f6feb', anchor='end', dx=-4, baseline='central')
    ev.line((0, -HALF), (0, HALF), stroke='#c0392b', stroke_width=0.8, dasharray='4,3')
    for letter, pos in [('X', (0.35, HALF + 0.28)), ('J', (0.28, -HALF - 0.28))]:
        ev.text(letter, pos, size=6, color='#1f6feb', anchor='middle', baseline='central')
    ev.text('walls only (floor and dovetail omitted); red dashed = joint plane through the rotation centre',
            (EV_LEFT, -HALF), size=8.5, color='#777', anchor='start', dy=20)
    ev.text('cross-section features projected in plan: solid = visible from above, dashed = hidden under the rim top',
            (EV_LEFT, -HALF), size=8.5, color='#777', anchor='start', dy=33)

    return d


if __name__ == '__main__':
    out_path = Path(__file__).parent / 'puzzle_connector.svg'
    build().save(str(out_path))
    print(f'Wrote {out_path}')
