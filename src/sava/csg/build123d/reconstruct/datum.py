import math

from ._vec import Vec, vsub, vdot, vcross, vnorm
from .boundary import boundary_polygons
from .planes import PlaneCluster

Face = tuple[int, int, int]
Point2D = tuple[float, float]


def make_frame(z_dir: Vec, y_dir: Vec) -> tuple[Vec, Vec, Vec]:
    z = vnorm(z_dir)
    y = vnorm(y_dir)
    y = vnorm(vsub(y, tuple(zi * vdot(y, z) for zi in z)))
    x = vnorm(vcross(y, z))
    return x, y, z


def to_local(p: Vec, origin: Vec, x: Vec, y: Vec) -> Point2D:
    rel = vsub(p, origin)
    return (vdot(rel, x), vdot(rel, y))


def plane_line_in_xs(plane: PlaneCluster, origin3: Vec, ex: Vec, ey: Vec) -> tuple[float, float, float]:
    n = vnorm(plane.normal)
    a = vdot(n, ex)
    b = vdot(n, ey)
    c = plane.d - vdot(n, origin3)
    L = math.hypot(a, b)
    if L < 1e-9:
        return (0.0, 0.0, 0.0)
    return (a / L, b / L, c / L)


def pick_datum(side_planes: list[PlaneCluster]) -> PlaneCluster:
    return max(side_planes, key=lambda p: p.area)


def build_datum_frame(extrusion_axis: Vec, datum: PlaneCluster,
                      silhouettes: list[tuple[PlaneCluster, list[list[Point2D]]]],
                      origin3_provisional: Vec, ex0: Vec, ey0: Vec) -> tuple[Vec, Vec, Vec]:
    datum_normal = vnorm(datum.normal)
    datum_line = plane_line_in_xs(datum, origin3_provisional, ex0, ey0)
    total_pts = sum(len(loop) for _, loops in silhouettes for loop in loops)
    if total_pts > 0:
        cx = sum(p[0] for _, loops in silhouettes for loop in loops for p in loop) / total_pts
        cy = sum(p[1] for _, loops in silhouettes for loop in loops for p in loop) / total_pts
        a, b, c = datum_line
        centroid_signed = a * cx + b * cy - c
        if centroid_signed < 0:
            datum_normal = tuple(-v for v in datum_normal)
    return make_frame(extrusion_axis, datum_normal)


def shift_origin_to_first_quadrant(verts: list[Vec], faces: list[Face],
                                   cap_planes: list[PlaneCluster],
                                   x_dir: Vec, y_dir: Vec) -> Vec:
    min_u = float('inf')
    min_v = float('inf')
    for plane in cap_planes:
        for ring3d in boundary_polygons(verts, faces, plane.tris):
            for pt in ring3d:
                min_u = min(min_u, vdot(pt, x_dir))
                min_v = min(min_v, vdot(pt, y_dir))
    return tuple(x_dir[i] * min_u + y_dir[i] * min_v for i in range(3))
