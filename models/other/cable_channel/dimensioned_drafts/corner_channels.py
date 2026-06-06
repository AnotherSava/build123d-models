"""Dimensioned draft of the cable channel corner pieces.

Two corner variants share one construction (bend_right / bend_down): the legs
are mitred at a 45deg seam through the corner, the bodies meet at that plain
seam, and the rim bands retreat from it by rim_inner_face_length on both legs
(the lap) — clearing the path of the crossing cap walls. Free ends carry the
puzzle connector (see the puzzle_connector draft).

Corner right turns in plan (X-Y, about Z); corner down turns in elevation
(X-Z, about Y) — its after leg runs downward with the opening facing +X, and
the piece prints lying on its side. The caps (not drawn) are mitred at the
body seam; the down cap shares the channel's seam plane.

Run from repo root:
    venv/Scripts/python.exe models/other/cable_channel/dimensioned_drafts/corner_channels.py

Outputs corner_channels.svg next to this script.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / '.claude' / 'skills' / 'model-dimensioned-draft' / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent))
from draft_lib import Drawing, View, fillet_polyline
from puzzle_connector import FILLET, end_seam


# --- Design parameters (mm), mirrored from the model -------------------------
WIDTH = 15.0
WALL = 1.2              # wall_thickness: the cap rides this far above the channel rim
TOTAL = 12.9            # total_height
RIM_H = 3.4             # rim_height
LAP = 2.4               # rim_inner_face_length: the rim seam retreat on each leg
L_BEFORE = 30.0         # right-corner demo leg lengths (create_channel(outer=30).right(outer=45))
L_AFTER = 45.0
DOWN_BEFORE = 20.0      # down-corner demo channel leg lengths (create_channel(inner=7.1).down())
DOWN_AFTER = 20.0
K = DOWN_BEFORE - TOTAL  # 7.1  inner corner of the down turn (seam plane x - z = K)
TAB = 3.05              # connector tab reach (lock_protrusion + lock_clearance)
LEAD = 0.3              # lock_lead_in
LEAD_H = 0.6            # lock_lead_in_height
LOCK_T = 2.4            # lock_thickness


def build() -> Drawing:
    d = Drawing('Cable Channel - Corners')

    # ------------------------------------------- Corner right, top view (X-Y)
    tv = d.add_view(View(origin=(150, 480), scale=8, title='Corner right - top view', axis_labels=('X', 'Y')))
    # Outline: the plan L with the puzzle connectors at the free ends. end_seam()
    # gives a joint at x=0, tab toward +x, centred across — transform per end.
    w_end = [(-px, py + WIDTH / 2) for px, py in end_seam()]                       # before leg start, tab -X
    after_end = [(L_BEFORE - WIDTH / 2 + py, L_BEFORE - L_AFTER - px) for px, py in end_seam()]  # after leg end, tab -Y
    outline = [(WIDTH, 0), *after_end, (L_BEFORE, WIDTH), *reversed(w_end)]
    dovetails = set(range(2, 10)) | set(range(13, 21))   # the two end_seam runs within `outline`
    tv.path(fillet_polyline(outline, FILLET, indices=dovetails, closed=True))

    tv.line((WIDTH, 0), (L_BEFORE, WIDTH), stroke='#c0392b', stroke_width=0.8, dasharray='4,3')
    tv.line((WIDTH - LAP, 0), (L_BEFORE - LAP, WIDTH), stroke='#999', stroke_width=0.6, dasharray='3,3')
    tv.line((WIDTH, -LAP), (L_BEFORE, WIDTH - LAP), stroke='#999', stroke_width=0.6, dasharray='3,3')
    tv.text('body seam (45°)', (24.5, 8.2), size=8, color='#c0392b', anchor='start')
    tv.text('rim seams', (13.2, 3.2), size=8, color='#777', anchor='end')
    tv.line((13.5, 3.4), (16.2, 4.6), stroke='#666', stroke_width=0.5)
    tv.line((13.5, 3.0), (17.2, 0.6), stroke='#666', stroke_width=0.5)

    tv.dim_h(v_at=WIDTH, u1=0, u2=L_BEFORE, label=f'{L_BEFORE:g} (outer)', side='above', offset_px=16)
    tv.dim_v(u_at=-TAB, v1=0, v2=WIDTH, label=f'{WIDTH:g}', side='left', offset_px=16)
    tv.dim_v(u_at=L_BEFORE, v1=WIDTH - L_AFTER, v2=WIDTH, label=f'{L_AFTER:g} (outer)', side='right', offset_px=16)
    tv.dim_h(v_at=0, u1=WIDTH - LAP, u2=WIDTH, label=f'{LAP:g}', side='below', offset_px=14)
    # Each leg can equivalently be sized by its inner edge: inner = outer - WIDTH
    tv.dim_h(v_at=0, u1=0, u2=L_BEFORE - WIDTH, label=f'{L_BEFORE - WIDTH:g} (inner)', side='below', offset_px=30)
    tv.dim_v(u_at=L_BEFORE - WIDTH, v1=WIDTH - L_AFTER, v2=0, label=f'{L_AFTER - WIDTH:g} (inner)', side='left', offset_px=16)

    tv.text(f'rim bands retreat {LAP:g} from the body seam on both legs (the lap) — the crossing cap walls pass through the cleared zone',
            (-TAB, WIDTH - L_AFTER), size=8.5, color='#777', anchor='start', dy=20)
    tv.text('puzzle connectors at the free ends — see the puzzle_connector draft',
            (-TAB, WIDTH - L_AFTER), size=8.5, color='#777', anchor='start', dy=33)
    tv.text('the cap is flush in plan, so the outer lengths hold with the cap on as well',
            (-TAB, WIDTH - L_AFTER), size=8.5, color='#777', anchor='start', dy=46)

    # ------------------------------------------ Corner down, side view (X-Z)
    sv = d.add_view(View(origin=(640, 480), scale=8, title='Corner down - side view', axis_labels=('X', 'Z')))
    down_bottom = TOTAL - DOWN_AFTER   # -7.1  joint plane of the down leg's far connector
    # The down leg's floor (and so its lock band + connector tab) sits on the
    # INNER side of the corner: pre-rotation floor z 0..lock maps to x = K..K+lock
    outline = [
        (K, 0), (K, down_bottom - TAB + LEAD),                      # inner face (= floor) of the down leg
        (K + LEAD, down_bottom - TAB),                              # tab, lead-in
        (K + LOCK_T - LEAD, down_bottom - TAB), (K + LOCK_T, down_bottom - TAB + LEAD),  # tab tip
        (K + LOCK_T, down_bottom), (DOWN_BEFORE, down_bottom),      # bottom joint plane
        (DOWN_BEFORE, TOTAL - 2 * LAP),                             # outer face, up to the corner chamfer
        (DOWN_BEFORE - 2 * LAP, TOTAL),                             # 45deg outer corner chamfer, perpendicular to the body seam
        (0, TOTAL),                                                 # rim top of the horizontal leg
        (0, LOCK_T),                                                # start joint, down to the lock band
        (-TAB + LEAD, LOCK_T), (-TAB, LOCK_T - LEAD_H),             # tab, lead-in
        (-TAB, LEAD_H), (-TAB + LEAD, 0),                           # tab tip
    ]
    sv.path(outline)

    sv.line((K, 0), (DOWN_BEFORE - LAP, TOTAL - LAP), stroke='#c0392b', stroke_width=0.8, dasharray='4,3')  # ends on the chamfer face
    # Rim band boundaries (light dashed): the horizontal leg's rim band starts at
    # z = TOTAL - LAP, the down leg's at x = K + outer_wall_height.
    sv.line((10, TOTAL - LAP), (K + TOTAL - LAP - LAP, TOTAL - LAP), stroke='#999', stroke_width=0.5, dasharray='3,3')
    sv.line((K + TOTAL - RIM_H, -4), (K + TOTAL - RIM_H, TOTAL - RIM_H - LAP), stroke='#999', stroke_width=0.5, dasharray='3,3')
    sv.text('body seam (45°)', (11.5, 3.4), size=8, color='#c0392b', anchor='end')

    # Cap outer profile (dashed): the cap rides WALL above the rim, so the API's
    # outer lengths measure to the cap's faces, not the channel's. Its down leg
    # runs to the channel's far joint plane, covering the leg fully.
    sv.line((0, TOTAL + WALL), (DOWN_BEFORE + WALL, TOTAL + WALL), stroke='#888', stroke_width=0.6, dasharray='4,2')
    sv.line((DOWN_BEFORE + WALL, TOTAL + WALL), (DOWN_BEFORE + WALL, down_bottom), stroke='#888', stroke_width=0.6, dasharray='4,2')
    sv.text('cap outer faces', (DOWN_BEFORE + WALL + 0.8, TOTAL - 2), size=8, color='#777', anchor='start')

    sv.dim_h(v_at=TOTAL, u1=DOWN_BEFORE - 2 * LAP, u2=DOWN_BEFORE, label=f'{2 * LAP:g}', side='above', offset_px=16)
    sv.dim_h(v_at=TOTAL + WALL, u1=0, u2=DOWN_BEFORE + WALL, label=f'{DOWN_BEFORE + WALL:g} (outer, with cap)', side='above', offset_px=40)
    sv.dim_v(u_at=-TAB, v1=0, v2=TOTAL, label=f'{TOTAL:g}', side='left', offset_px=16)
    sv.dim_v(u_at=DOWN_BEFORE, v1=TOTAL - 2 * LAP, v2=TOTAL, label=f'{2 * LAP:g}', side='right', offset_px=16)
    sv.dim_v(u_at=DOWN_BEFORE + WALL, v1=down_bottom, v2=TOTAL + WALL, label=f'{DOWN_AFTER + WALL:g} (outer, with cap)', side='right', offset_px=40)
    sv.dim_h(v_at=down_bottom - TAB, u1=K, u2=K + LOCK_T, label=f'{LOCK_T:g}', side='below', offset_px=14)
    # Each leg can equivalently be sized by its inner edge; the outer edge is the
    # assembled duct's (cap on), so inner = outer - (TOTAL + WALL)
    sv.dim_h(v_at=0, u1=0, u2=K, label=f'{K:g} (inner = outer − {TOTAL + WALL:g})', side='below', offset_px=14)
    sv.dim_v(u_at=K, v1=down_bottom, v2=0, label=f'{DOWN_AFTER - TOTAL:g} (inner)', side='left', offset_px=16)

    sv.text('after leg runs down, opening toward +X; the piece prints lying on its side',
            (-TAB, down_bottom - TAB), size=8.5, color='#777', anchor='start', dy=44)
    sv.text(f'bodies meet at the plain seam; the outer corner is a single {2 * LAP:g} × {2 * LAP:g} chamfer (45°),',
            (-TAB, down_bottom - TAB), size=8.5, color='#777', anchor='start', dy=57)
    sv.text('perpendicular to the body seam through its exit at the bodies’ top — the cap’s corner covers the wedge',
            (-TAB, down_bottom - TAB), size=8.5, color='#777', anchor='start', dy=70)

    return d


if __name__ == '__main__':
    out_path = Path(__file__).parent / 'corner_channels.svg'
    build().save(str(out_path))
    print(f'Wrote {out_path}')
