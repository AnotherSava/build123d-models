import math

from .numbers import fmt

Point2D = tuple[float, float]

# Angle is considered "nice" if it falls within NICE_ANGLE_TOL of a multiple
# of NICE_ANGLE_STEP. Tight tolerance because angles from clean CAD geometry
# typically land within ~0.01° of their intended value after tessellation.
NICE_ANGLE_STEP = 15.0
NICE_ANGLE_TOL = 0.05


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
    cur = poly[0]
    for nxt in poly[1:]:
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
        cur = nxt
    return lines
