import math

from .numbers import fmt

Point2D = tuple[float, float]

# Angle is considered "nice" if it falls within NICE_ANGLE_TOL of a multiple
# of NICE_ANGLE_STEP. Tight tolerance because angles from clean CAD geometry
# typically land within ~0.01° of their intended value after tessellation.
NICE_ANGLE_STEP = 15.0
NICE_ANGLE_TOL = 0.05

# Arc detection thresholds: tessellated arcs in CAD-exported STLs typically
# use 32+ segments per full circle (<= 11.25° per segment). 20° per-segment
# turn limit safely excludes designed n-gons up to and including the 18-gon
# (20° turns), while still catching genuine tessellated arcs that go up to
# ~16°/segment. fit_tol is loose enough for typical 10–50 µm STL noise but
# tighter than meaningful geometric variation.
ARC_FIT_TOL_MM = 0.05
ARC_MAX_TURN_DEG = 20.0
ARC_MIN_SEGMENTS = 4  # below this, the arc emit doesn't shorten the output


def _circumcircle(p0: Point2D, p1: Point2D, p2: Point2D) -> tuple[float, float, float] | None:
    """Centre + radius of the unique circle through three non-collinear points."""
    ax, ay = p0
    bx, by = p1
    cx, cy = p2
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return None
    asq = ax * ax + ay * ay
    bsq = bx * bx + by * by
    csq = cx * cx + cy * cy
    ux = (asq * (by - cy) + bsq * (cy - ay) + csq * (ay - by)) / d
    uy = (asq * (cx - bx) + bsq * (ax - cx) + csq * (bx - ax)) / d
    return (ux, uy, math.hypot(ax - ux, ay - uy))


def _seg_turn_deg(prev_p: Point2D, curr_p: Point2D, next_p: Point2D) -> float:
    """Signed turn at `curr_p` going from `prev_p → curr_p` to `curr_p → next_p`.
    Positive = CCW (left turn), negative = CW (right turn)."""
    ix, iy = curr_p[0] - prev_p[0], curr_p[1] - prev_p[1]
    ox, oy = next_p[0] - curr_p[0], next_p[1] - curr_p[1]
    return math.degrees(math.atan2(ix * oy - iy * ox, ix * ox + iy * oy))


def _detect_arc_run(poly: list[Point2D], start: int) -> tuple[int, float] | None:
    """Longest run of consecutive segments from `poly[start]` that lies on a
    common circle with small, consistent per-segment turns. Returns
    `(end_idx, signed_arc_angle_deg)`, where `end_idx` is the index of the
    arc's last vertex and the arc has `end_idx - start` segments. Returns
    None when the run is too short or the points aren't an arc.

    The per-segment turn limit `ARC_MAX_TURN_DEG` keeps regular polygons
    (hexagons, octagons, …) — whose vertices technically lie on their
    circumscribed circle — from being misread as tessellated arcs."""
    n = len(poly)
    if start + 3 > n:
        return None
    p0, p1, p2 = poly[start], poly[start + 1], poly[start + 2]
    circ = _circumcircle(p0, p1, p2)
    if circ is None:
        return None
    cx, cy, r = circ

    t0 = _seg_turn_deg(p0, p1, p2)
    if abs(t0) > ARC_MAX_TURN_DEG or abs(t0) < 1e-3:
        return None
    sign = 1 if t0 > 0 else -1

    end = start + 2
    while end + 1 < n:
        nxt = poly[end + 1]
        if abs(math.hypot(nxt[0] - cx, nxt[1] - cy) - r) > ARC_FIT_TOL_MM:
            break
        t = _seg_turn_deg(poly[end - 1], poly[end], nxt)
        if t * sign <= 0 or abs(t) > ARC_MAX_TURN_DEG:
            break
        end += 1

    if end - start < ARC_MIN_SEGMENTS:
        return None

    # Central angle of the arc: difference of endpoint polar angles around
    # the centre, signed by the established CCW/CW direction.
    a0 = math.atan2(p0[1] - cy, p0[0] - cx)
    a1 = math.atan2(poly[end][1] - cy, poly[end][0] - cx)
    arc = a1 - a0
    if sign > 0:
        while arc <= 0:
            arc += 2 * math.pi
        while arc > 2 * math.pi:
            arc -= 2 * math.pi
    else:
        while arc >= 0:
            arc -= 2 * math.pi
        while arc < -2 * math.pi:
            arc += 2 * math.pi
    return (end, math.degrees(arc))


def _signed_area(poly: list[Point2D]) -> float:
    """Shoelace formula; positive for CCW winding."""
    n = len(poly)
    s = 0.0
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s / 2


def _snap_to_nice_angle(angle_deg: float) -> float | None:
    """Return the snapped angle if it's within tolerance of a NICE_ANGLE_STEP multiple, else None."""
    wrapped = ((angle_deg + 180) % 360) - 180
    nearest = round(wrapped / NICE_ANGLE_STEP) * NICE_ANGLE_STEP
    if abs(wrapped - nearest) <= NICE_ANGLE_TOL:
        return nearest
    return None


def _vertex_key(p: Point2D, tol: float = 1e-3) -> tuple[int, int]:
    """Quantize a vertex onto a tol-spaced grid for robust cross-polygon matching."""
    return (round(p[0] / tol), round(p[1] / tol))


def find_shared_start(polygons: list[list[Point2D]]) -> Point2D | None:
    """Vertex shared by the most polygons (>= 2). Ties broken by leftmost-bottommost.

    Returns None if no vertex is shared between at least 2 polygons.
    """
    counts: dict[tuple[int, int], list[Point2D]] = {}
    for poly in polygons:
        seen: set[tuple[int, int]] = set()
        for v in poly:
            k = _vertex_key(v)
            if k in seen:
                continue
            seen.add(k)
            counts.setdefault(k, []).append(v)
    if not counts:
        return None
    max_count = max(len(vs) for vs in counts.values())
    if max_count < 2:
        return None
    candidates = [vs[0] for vs in counts.values() if len(vs) == max_count]
    return min(candidates, key=lambda v: (v[1], v[0]))


def emit_pencil_for(poly: list[Point2D], name: str,
                    preferred_start: Point2D | None = None) -> list[str]:
    # Tight collinear merge: drop truly-collinear vertices (perp deviation
    # under 1 µm = ~tessellation noise) so a raw n-gon side with 8 collinear
    # samples emits as one `.draw()` instead of 8 `.jump()`s. Arc-sampled
    # vertices have sagitta well above this floor and stay.
    from .boundary import simplify_collinear
    poly = simplify_collinear(poly, perp_tol=0.001)
    # Pencil.extrude(+h) extrudes along the face normal, which points in +z_dir
    # only when the polygon is wound CCW. Reverse CW polygons so emitted code
    # extrudes in the expected direction.
    if _signed_area(poly) < 0:
        poly = [poly[0]] + list(reversed(poly[1:]))

    # Pick the starting vertex. Prefer a vertex shared with other polygons in
    # the part so multiple shapes visually anchor to the same point; fall back
    # to the leftmost-bottommost vertex (typically on the datum at y=0).
    start_idx = None
    if preferred_start is not None:
        target = _vertex_key(preferred_start)
        for i, v in enumerate(poly):
            if _vertex_key(v) == target:
                start_idx = i
                break
    if start_idx is None:
        start_idx = min(range(len(poly)), key=lambda i: (poly[i][1], poly[i][0]))
    poly = poly[start_idx:] + poly[:start_idx]

    sx, sy = poly[0]
    if abs(sx) < 1e-3 and abs(sy) < 1e-3:
        lines = [f'{name} = Pencil()']
    else:
        lines = [f'{name} = Pencil(start=({fmt(sx)}, {fmt(sy)}))']

    i = 0
    while i < len(poly) - 1:
        arc = _detect_arc_run(poly, i)
        if arc is not None:
            end_idx, arc_deg = arc
            cur = poly[i]
            end_v = poly[end_idx]
            dx = end_v[0] - cur[0]
            dy = end_v[1] - cur[1]
            lines.append(
                f'{name}.arc_with_destination(({fmt(dx)}, {fmt(dy)}), {fmt(arc_deg, 2)})'
            )
            i = end_idx
            continue

        cur = poly[i]
        nxt = poly[i + 1]
        dx = nxt[0] - cur[0]
        dy = nxt[1] - cur[1]
        # In Pencil-local coords, start maps to (0, 0). When a stroke lands on
        # the start axis (local x=0 for right/left, local y=0 for up/down), the
        # param-less form snaps to that axis automatically — cleaner to emit.
        nxt_lx = nxt[0] - sx
        nxt_ly = nxt[1] - sy
        if abs(dy) < 1e-3 and dx > 0:
            arg = '' if abs(nxt_lx) < 1e-3 else fmt(dx)
            lines.append(f'{name}.right({arg})')
        elif abs(dy) < 1e-3 and dx < 0:
            arg = '' if abs(nxt_lx) < 1e-3 else fmt(-dx)
            lines.append(f'{name}.left({arg})')
        elif abs(dx) < 1e-3 and dy > 0:
            arg = '' if abs(nxt_ly) < 1e-3 else fmt(dy)
            lines.append(f'{name}.up({arg})')
        elif abs(dx) < 1e-3 and dy < 0:
            arg = '' if abs(nxt_ly) < 1e-3 else fmt(-dy)
            lines.append(f'{name}.down({arg})')
        else:
            # Pencil.draw uses angle CCW from +Y (see geometry.create_vector):
            # dx = -L * sin(angle), dy = L * cos(angle) → angle = atan2(-dx, dy).
            angle = math.degrees(math.atan2(-dx, dy))
            snapped = _snap_to_nice_angle(angle)
            if snapped is not None:
                length = math.hypot(dx, dy)
                lines.append(f'{name}.draw({fmt(length)}, {fmt(snapped, 2)})')
            else:
                lines.append(f'{name}.jump(({fmt(dx)}, {fmt(dy)}))')
        i += 1
    return lines
