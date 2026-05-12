import math
from collections import defaultdict

from ._vec import Vec

Face = tuple[int, int, int]
Point2D = tuple[float, float]


def boundary_polygons(verts: list[Vec], faces: list[Face], tri_indices: list[int]) -> list[list[Vec]]:
    """All boundary loops of a planar face set, each as an ordered 3D vertex list.

    A planar cap on a manifold mesh can have multiple boundary loops: one outer
    perimeter plus one inner loop per hole/cutout. Each boundary edge is shared
    by exactly one triangle, so its direction is well-defined; we walk those
    directed edges loop by loop until none remain. Outer loops come out CCW
    (positive shoelace area); holes come out CW (negative).
    """
    edge_count: dict = defaultdict(int)
    edge_to_tri: dict = {}
    for ti in tri_indices:
        a, b, c = faces[ti]
        for u, v in ((a, b), (b, c), (c, a)):
            key = (min(u, v), max(u, v))
            edge_count[key] += 1
            edge_to_tri.setdefault(key, []).append((ti, u, v))

    boundary_edges = [k for k, c in edge_count.items() if c == 1]
    if not boundary_edges:
        return []

    adj: dict = defaultdict(list)
    for key in boundary_edges:
        _ti, u, v = edge_to_tri[key][0]
        adj[u].append(v)

    loops: list[list[Vec]] = []
    safety_limit = len(boundary_edges) + 5
    while True:
        start = None
        for u, nbrs in adj.items():
            if nbrs:
                start = u
                break
        if start is None:
            break
        ring = [start]
        cur = start
        steps = 0
        while True:
            if not adj.get(cur):
                break
            nxt = adj[cur].pop()
            if nxt == start:
                break
            ring.append(nxt)
            cur = nxt
            steps += 1
            if steps > safety_limit:
                break
        if len(ring) >= 3:
            loops.append([verts[i] for i in ring])
    return loops


def boundary_polygon(verts: list[Vec], faces: list[Face], tri_indices: list[int]) -> list[Vec]:
    """Single boundary loop of a planar face set — the largest, by vertex count.

    Thin compatibility shim over `boundary_polygons` for callers that only
    need one loop. Prefer `boundary_polygons` for new code.
    """
    loops = boundary_polygons(verts, faces, tri_indices)
    if not loops:
        return []
    return max(loops, key=len)


def simplify_collinear(poly2d: list[Point2D], perp_tol: float = 0.05) -> list[Point2D]:
    if len(poly2d) < 3:
        return poly2d
    poly = list(poly2d)
    changed = True
    while changed and len(poly) > 3:
        changed = False
        out: list[Point2D] = []
        n = len(poly)
        i = 0
        for _ in range(n):
            a = poly[(i - 1) % n]
            b = poly[i]
            c = poly[(i + 1) % n]
            ab = (b[0] - a[0], b[1] - a[1])
            ac = (c[0] - a[0], c[1] - a[1])
            ac_len = math.hypot(*ac)
            if ac_len < 1e-9:
                out.append(b)
                i += 1
                continue
            cross = abs(ab[0]*ac[1] - ab[1]*ac[0])
            dist = cross / ac_len
            if dist < perp_tol:
                changed = True
            else:
                out.append(b)
            i += 1
        # Collapsing every point in a pass means the boundary is densely curved
        # (a tessellated circle, not a polygon with collinear runs). Keep the
        # pre-pass polygon — circle detection will handle it downstream.
        if len(out) < 3:
            return poly
        poly = out
    return poly
