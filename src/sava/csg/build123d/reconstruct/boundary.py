import math
from collections import defaultdict

from ._vec import Vec

Face = tuple[int, int, int]
Point2D = tuple[float, float]


def boundary_polygon(verts: list[Vec], faces: list[Face], tri_indices: list[int]) -> list[Vec]:
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

    directed = []
    for key in boundary_edges:
        _ti, u, v = edge_to_tri[key][0]
        directed.append((u, v))

    adj: dict = defaultdict(list)
    for u, v in directed:
        adj[u].append(v)

    if not adj:
        return []
    start = next(iter(adj))
    ring = [start]
    cur = start
    while True:
        if not adj[cur]:
            break
        nxt = adj[cur].pop()
        if nxt == start:
            break
        ring.append(nxt)
        cur = nxt
        if len(ring) > len(boundary_edges) + 5:
            break

    return [verts[i] for i in ring]


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
        while i < n:
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
        poly = out
    return poly
