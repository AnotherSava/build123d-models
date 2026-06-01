import math
from dataclasses import dataclass

from ._vec import Vec, vdot, vnorm
from .planes import PlaneCluster


@dataclass
class PlaneBuckets:
    cap: list[tuple[float, PlaneCluster]]
    side: list[tuple[float, PlaneCluster]]
    other: list[tuple[float, PlaneCluster]]


def candidate_axes(planes: list[PlaneCluster], ang_tol_deg: float = 2.0) -> list[Vec]:
    """Return unique normal directions present in `planes`, sorted by descending
    total area of planes that share each direction.

    Plane clusters already canonicalize sign (first non-zero component positive),
    but two clusters can still share a direction at different offsets (front
    and back of the same wall). This groups those into one direction.

    Used by the caller to try multiple candidate extrusion axes — picking the
    largest plane's normal alone misclassifies parts where the dominant face
    happens to be a side wall.
    """
    cos_tol = math.cos(math.radians(ang_tol_deg))
    groups: list[list] = []  # list of [total_area, weighted_normal]
    for p in planes:
        n = vnorm(p.normal)
        matched = False
        for g in groups:
            if abs(vdot(n, g[1])) > cos_tol:
                aligned = n if vdot(n, g[1]) > 0 else (-n[0], -n[1], -n[2])
                total_new = g[0] + p.area
                avg = (
                    (g[1][0]*g[0] + aligned[0]*p.area) / total_new,
                    (g[1][1]*g[0] + aligned[1]*p.area) / total_new,
                    (g[1][2]*g[0] + aligned[2]*p.area) / total_new,
                )
                g[0] = total_new
                g[1] = vnorm(avg)
                matched = True
                break
        if not matched:
            groups.append([p.area, n])
    groups.sort(key=lambda g: -g[0])
    return [g[1] for g in groups]


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
