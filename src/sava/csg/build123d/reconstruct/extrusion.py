import math
from dataclasses import dataclass

from ._vec import Vec, vdot, vnorm
from .planes import PlaneCluster


@dataclass
class PlaneBuckets:
    cap: list[tuple[float, PlaneCluster]]
    side: list[tuple[float, PlaneCluster]]
    other: list[tuple[float, PlaneCluster]]


def pick_axis(planes: list[PlaneCluster]) -> Vec:
    largest = max(planes, key=lambda p: p.area)
    return vnorm(largest.normal)


def classify_planes_vs_axis(planes: list[PlaneCluster], axis: Vec,
                            ang_tol_deg: float = 3.0) -> PlaneBuckets:
    cap: list[tuple[float, PlaneCluster]] = []
    side: list[tuple[float, PlaneCluster]] = []
    other: list[tuple[float, PlaneCluster]] = []
    cos_par = math.cos(math.radians(ang_tol_deg))
    cos_perp = math.sin(math.radians(ang_tol_deg))
    axis = vnorm(axis)
    for p in planes:
        n = vnorm(p.normal)
        c = abs(vdot(n, axis))
        if c > cos_par:
            cap.append((c, p))
        elif c < cos_perp:
            side.append((c, p))
        else:
            other.append((c, p))
    return PlaneBuckets(cap=cap, side=side, other=other)


def cap_depth_in_frame(plane: PlaneCluster, z_dir: Vec, origin: Vec) -> float:
    n = vnorm(plane.normal)
    sign = 1.0 if vdot(n, z_dir) > 0 else -1.0
    return sign * plane.d - vdot(z_dir, origin)
