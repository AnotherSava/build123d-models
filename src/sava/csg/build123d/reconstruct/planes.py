import math
from dataclasses import dataclass, field

from ._vec import Vec, vcross, vdot, vlen, vsub

Face = tuple[int, int, int]


@dataclass
class PlaneCluster:
    normal: Vec
    d: float
    area: float
    tris: list[int] = field(default_factory=list)
    verts: set[int] = field(default_factory=set)


def plane_of_triangle(v0: Vec, v1: Vec, v2: Vec) -> tuple[Vec | None, float, float]:
    n = vcross(vsub(v1, v0), vsub(v2, v0))
    a = vlen(n)
    if a < 1e-12:
        return None, 0.0, 0.0
    unit = (n[0]/a, n[1]/a, n[2]/a)
    d = vdot(unit, v0)
    area = a / 2.0
    return unit, d, area


def canon_normal(n: Vec, d: float, eps: float = 1e-6) -> tuple[Vec, float]:
    for c in n:
        if abs(c) > eps:
            if c < 0:
                return (-n[0], -n[1], -n[2]), -d
            return n, d
    return n, d


def cluster_planes(verts: list[Vec], faces: list[Face],
                   ang_tol_deg: float = 2.0, off_tol: float = 0.05) -> list[PlaneCluster]:
    cos_tol = math.cos(math.radians(ang_tol_deg))
    planes: list[PlaneCluster] = []
    for fi, (a, b, c) in enumerate(faces):
        v0, v1, v2 = verts[a], verts[b], verts[c]
        n, d, area = plane_of_triangle(v0, v1, v2)
        if n is None:
            continue
        n, d = canon_normal(n, d)
        matched: PlaneCluster | None = None
        for p in planes:
            if vdot(n, p.normal) > cos_tol and abs(d - p.d) < off_tol:
                matched = p
                break
        if matched is None:
            planes.append(PlaneCluster(normal=n, d=d, area=area, tris=[fi], verts={a, b, c}))
        else:
            w_old = matched.area
            w_new = area
            w = w_old + w_new
            new_n = (
                (matched.normal[0]*w_old + n[0]*w_new)/w,
                (matched.normal[1]*w_old + n[1]*w_new)/w,
                (matched.normal[2]*w_old + n[2]*w_new)/w,
            )
            m = vlen(new_n)
            matched.normal = (new_n[0]/m, new_n[1]/m, new_n[2]/m)
            matched.d = (matched.d*w_old + d*w_new)/w
            matched.area += area
            matched.tris.append(fi)
            matched.verts.update([a, b, c])
    return planes
