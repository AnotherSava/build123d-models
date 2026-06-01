import math
from collections import defaultdict
from dataclasses import dataclass, field

from build123d import Vector

from ._vec import Vec, vadd, vcross, vdot, vmul, vnorm
from .boundary import boundary_polygons, simplify_collinear
from .datum import build_datum_frame, make_frame, pick_datum, shift_origin_to_first_quadrant, to_local
from .extrusion import cap_depth_in_frame, candidate_axes, classify_planes_vs_axis
from .mesh_io import read_mesh
from .numbers import fmt
from .pencil_emit import Point2D, _signed_area, emit_pencil_for, find_shared_start
from .planes import PlaneCluster, cluster_planes


@dataclass
class Layer:
    plane: PlaneCluster
    name: str
    depth: float
    loops: list[list[Point2D]]
    # Parallel to `loops`. None for ordinary polygons; (radius, (cx, cy)) when
    # the raw boundary (before collinear simplification) was a tessellated
    # circle — those emit as SmarterCone.cylinder(...) instead of a Pencil.
    circles: list[tuple[float, Point2D] | None] = field(default_factory=list)
    # Parallel to `loops`. None for non-rectangles; (length, width, (cx, cy),
    # angle_deg) when the boundary is a rectangle (possibly with minor
    # corner chamfers) — those emit as SmartBox(...).rotate_z().move().
    boxes: list[tuple[float, float, Point2D, float] | None] = field(default_factory=list)
    # Parallel to `loops`. The raw (pre-simplify) 2D boundary for each loop.
    # Used by Pencil emit so arc detection can recover curved walls that the
    # 0.05 mm simplification tolerance would otherwise smooth into straight
    # chords (e.g. an 89-vert curved bar collapsing into a 4-vert rectangle).
    # Simplified `loops` are still preferred for nesting / dedup / detection
    # since their vertex count is stable across instances of the same shape.
    raw_loops: list[list[Point2D]] = field(default_factory=list)


@dataclass
class CylinderFeature:
    axis: Vector
    radius: float
    height: float
    area: float
    # Center of the cylinder's BASE face in cross-section local coordinates:
    # (u, v, z). The cylinder extrudes from this point along `axis` (= z_dir)
    # for `height`. This matches SmarterCone.cylinder(...).move(...) semantics.
    base: tuple[float, float, float] = (0.0, 0.0, 0.0)
    # Layer name this cylinder replaces in emit (e.g. 'front_protrusion').
    layer_name: str | None = None


@dataclass
class BoxFeature:
    length: float       # longer of the two in-plane dimensions
    width: float        # shorter of the two
    height: float       # extrusion thickness
    # Box placement in cross-section local coordinates: `(cu, cv, cz_base)`.
    # `SmartBox(L, W, h)` is XY-centered but Z-base-aligned, so passing
    # this triple to `.move(cu, cv, cz_base)` lands the box with its centroid
    # at `(cu, cv)` in XY and its BASE at `z = cz_base` (top at `z = cz_base + h`).
    base: tuple[float, float, float] = (0.0, 0.0, 0.0)
    angle_deg: float = 0.0
    layer_name: str | None = None


@dataclass
class ReconstructionResult:
    is_2d5_extrudable: bool
    extrusion_axis: Vector | None = None
    x_dir: Vector | None = None
    y_dir: Vector | None = None
    z_dir: Vector | None = None
    origin: Vector | None = None
    datum_plane: PlaneCluster | None = None
    datum_contact_area: float = 0.0
    layers: list[Layer] = field(default_factory=list)
    cylinders: list[CylinderFeature] = field(default_factory=list)
    boxes: list[BoxFeature] = field(default_factory=list)
    code: str = ''
    error: str | None = None


# Loops whose |signed area| is below this fraction of the cap's largest loop
# are treated as tessellation noise (sliver triangles trapped between coplanar
# facets that didn't quite merge into one cluster). 0.5% comfortably separates
# real holes (always > a few % of the outer) from noise (~0.01% typical).
_NOISE_LOOP_AREA_FRAC = 0.005


def _filter_noise_loops(loops_2d: list[list[Point2D]]) -> list[list[Point2D]]:
    if not loops_2d:
        return loops_2d
    areas = [abs(_signed_area(p)) for p in loops_2d]
    threshold = max(areas) * _NOISE_LOOP_AREA_FRAC
    return [p for p, a in zip(loops_2d, areas) if a >= threshold]


# Plane clusters merge triangles whose offsets agree within ~0.05 mm (planes.py).
# A "noise step" inside a cluster is a sub-millimeter z-discontinuity left behind
# by a CAD/STL artifact (rounding in export, fillet collapse, etc.) — too small
# to be a real feature. We treat anything within this distance as the same level.
_NOISE_STEP_HEIGHT = 0.1


def _filter_noise_step_loops(rings3d: list[list[Vec]],
                              plane_normal: Vec, plane_d: float,
                              max_step_height: float = _NOISE_STEP_HEIGHT,
                              area_rel_tol: float = 1e-3,
                              centroid_abs_tol: float = 0.1,
                              exact_dup_z_tol: float = 1e-4) -> list[list[Vec]]:
    """Detect and remove loops that come from a sub-mm step within a plane cluster.

    Two boundary loops at slightly different plane offsets but identical 2D shape
    + centroid trace the top and bottom of a tiny "step wall" inside an otherwise
    flat surface — a mesh artifact, not a real perimeter. Such pairs (or larger
    groups: triple steps, etc.) are dropped entirely.

    Exact same-position duplicates (z-spread ≤ exact_dup_z_tol) are different:
    one is kept (probably a degenerate mesh overlap). Groups whose z-spread
    exceeds max_step_height are distinct features that happen to share an
    outline — kept as-is.
    """
    if len(rings3d) < 2:
        return rings3d

    # In-plane tangent frame for projecting each loop to 2D for shape comparison.
    n = vnorm(plane_normal)
    if abs(n[2]) < 0.9:
        ex = vnorm((-n[1], n[0], 0.0))
    else:
        ex = (1.0, 0.0, 0.0)
    ey = vnorm(vcross(n, ex))

    summaries: list[tuple[float, float, float, float]] = []
    for ring in rings3d:
        m = len(ring)
        proj = [(vdot(v, ex), vdot(v, ey)) for v in ring]
        a = abs(_signed_area(proj))
        cx = sum(p[0] for p in proj) / m
        cy = sum(p[1] for p in proj) / m
        z_off = sum(vdot(v, n) for v in ring) / m - plane_d
        summaries.append((a, cx, cy, z_off))

    # Group loops by 2D shape (similar area + centroid).
    group_of = [-1] * len(rings3d)
    groups: list[list[int]] = []
    for i in range(len(rings3d)):
        a_i, cx_i, cy_i, _ = summaries[i]
        for g_idx, group in enumerate(groups):
            a_g, cx_g, cy_g, _ = summaries[group[0]]
            same_area = abs(a_i - a_g) <= max(a_i, a_g) * area_rel_tol
            same_centroid = (abs(cx_i - cx_g) <= centroid_abs_tol
                             and abs(cy_i - cy_g) <= centroid_abs_tol)
            if same_area and same_centroid:
                group.append(i)
                group_of[i] = g_idx
                break
        if group_of[i] == -1:
            group_of[i] = len(groups)
            groups.append([i])

    # For each multi-member group, decide based on z-spread.
    drop: set[int] = set()
    for group in groups:
        if len(group) < 2:
            continue
        z_offs = [summaries[i][3] for i in group]
        spread = max(z_offs) - min(z_offs)
        if spread <= exact_dup_z_tol:
            # Exact duplicate — keep one (the first), drop the rest.
            drop.update(group[1:])
        elif spread <= max_step_height:
            # Noise step (top + bottom of a sliver wall) — drop all members.
            drop.update(group)
        # else: distinct features happening to share shape — keep all.

    return [r for i, r in enumerate(rings3d) if i not in drop]


def _deduplicate_loops(loops_2d: list[list[Point2D]],
                       area_rel_tol: float = 1e-4,
                       centroid_abs_tol: float = 0.01) -> list[list[Point2D]]:
    """Drop loops that are geometric duplicates of one already kept.

    Coplanar caps occasionally carry the same boundary twice — e.g. when two
    coplanar surfaces (a face and the floor of a flush inset) share an
    outline. The duplicate confuses nesting classification (the second copy
    looks "contained" in the first because they coincide), which flips the
    cut/fuse parity for everything underneath it.

    Two loops are considered the same when their signed-area magnitudes match
    within a relative tolerance and their centroids coincide within an
    absolute distance — same shape, same place.
    """
    if not loops_2d:
        return loops_2d
    out: list[list[Point2D]] = []
    sigs: list[tuple[float, float, float]] = []
    for poly in loops_2d:
        a = abs(_signed_area(poly))
        n = len(poly)
        cx = sum(p[0] for p in poly) / n
        cy = sum(p[1] for p in poly) / n
        is_dup = False
        for a2, cx2, cy2 in sigs:
            if abs(a - a2) <= max(a, a2) * area_rel_tol and \
               abs(cx - cx2) <= centroid_abs_tol and \
               abs(cy - cy2) <= centroid_abs_tol:
                is_dup = True
                break
        if not is_dup:
            out.append(poly)
            sigs.append((a, cx, cy))
    return out


def _point_in_polygon(point: Point2D, polygon: list[Point2D]) -> bool:
    """Ray-casting: True if `point` is strictly inside `polygon` (winding-agnostic)."""
    x, y = point
    inside = False
    n = len(polygon)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)):
            x_cross = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < x_cross:
                inside = not inside
        j = i
    return inside


def _classify_loops(loops: list[list[Point2D]]) -> list[int]:
    """Assign each loop a parent index in `loops`, or -1 if top-level (outer).

    A loop is a hole if it's contained inside another loop; its parent is the
    innermost containing loop. Disjoint loops are independent top-level outers.
    Picks one vertex per loop as the test point — works for simple,
    non-overlapping nesting (the only case 2.5D caps produce).
    """
    n = len(loops)
    parent = [-1] * n
    for i, loop in enumerate(loops):
        if not loop:
            continue
        test = loop[0]
        containers = [j for j in range(n) if j != i and _point_in_polygon(test, loops[j])]
        if not containers:
            continue
        # Innermost container: one that contains no other container.
        innermost = containers[0]
        for c in containers[1:]:
            if _point_in_polygon(loops[innermost][0], loops[c]):
                pass  # `innermost` is inside `c` → keep innermost
            elif _point_in_polygon(loops[c][0], loops[innermost]):
                innermost = c
        parent[i] = innermost
    return parent


def _detect_circle(raw: list[Point2D], simplified: list[Point2D],
                   area_rel_tol: float = 0.05,
                   min_vertices: int = 16) -> tuple[float, Point2D] | None:
    """Return (radius, center) if `raw` is a tessellated circle, else None.

    Two complementary tests are tried in order:

    1. **Simplified** polygon area vs π·r̄² where r̄ is the mean radius of
       simplified vertices. Catches the case where `raw` is a tessellated
       circle interrupted by smoothly-curved protrusions: simplify_collinear
       smooths those away, leaving the inner cusps that trace the circle's
       actual wall — the simplified polygon then looks like a regular
       12+gon and passes the area test. Returns the simplified radius (the
       inner-wall radius, not pulled outward by the protrusions).
    2. **Raw** polygon area vs π·r̄² where r̄ is the mean radius of raw
       vertices. Catches the clean-tessellated-circle case where simplify
       collapsed densely-sampled near-collinear vertices down to a coarse
       3–6-vert polygon — that simplified polygon fails the area test, but
       the raw boundary is unambiguously circular. Returns the raw radius.

    The minimum-vertex floor (≥16) applies to the raw polygon: real STL
    exports of circles use ≥32 segments, while polygonal features almost
    never exceed 8 sides. The area test (≤5% off) then filters out regular
    n-gons (hexagon ~17% off, octagon ~10% off, decagon ~6% off) while
    accepting 12+gon-like tessellations.
    """
    if len(raw) < min_vertices:
        return None

    # Test 1: simplified polygon.
    if len(simplified) >= 3:
        cx, cy = _polygon_centroid(simplified)
        distances = [math.hypot(x - cx, y - cy) for x, y in simplified]
        r_mean = sum(distances) / len(distances)
        if r_mean > 1e-9:
            actual_area = abs(_signed_area(simplified))
            ideal_area = math.pi * r_mean * r_mean
            if abs(actual_area - ideal_area) / ideal_area <= area_rel_tol:
                return (r_mean, (cx, cy))

    # Test 2: raw polygon.
    cx_raw, cy_raw = _polygon_centroid(raw)
    distances_raw = [math.hypot(x - cx_raw, y - cy_raw) for x, y in raw]
    r_raw = sum(distances_raw) / len(distances_raw)
    if r_raw < 1e-9:
        return None
    actual_area = abs(_signed_area(raw))
    ideal_area = math.pi * r_raw * r_raw
    if abs(actual_area - ideal_area) / ideal_area > area_rel_tol:
        return None
    cx, cy = _polygon_centroid(simplified) if len(simplified) >= 3 else (cx_raw, cy_raw)
    return (r_raw, (cx, cy))


def _detect_box(poly: list[Point2D],
                area_rel_tol: float = 0.05,
                right_angle_tol_deg: float = 6.0,
                min_right_angle_corners: int = 3) -> tuple[float, float, Point2D, float] | None:
    """Return (length, width, (cx, cy), angle_deg) if `poly` is a rectangle.

    Two conditions must both hold:
    1. The polygon fills its tightest enclosing rectangle within `area_rel_tol`
       (catches clean 4-vertex rectangles AND rectangles with minor corner
       chamfers — a ~1.5% chamfer barely shaves the OBB fill ratio).
    2. At least `min_right_angle_corners` vertices have an interior angle
       within `right_angle_tol_deg` of 90°. This separates boxes (≥3 right
       corners — a chamfered-corner rectangle keeps the remaining three) from
       trapezoids and parallelograms (0-2 right corners) whose OBB fill ratio
       can also happen to land in the 95%+ band.

    The OBB is found by rotating-calipers approximation: try aligning a
    bounding box with each polygon edge and keep the smallest one. For
    convex polygons this is exact; for non-convex polygons the result is
    at-least-as-large-as-optimal, which makes detection more conservative.

    `length` is the longer dimension; `angle_deg` is the rotation around Z
    that takes a default-orientation SmartBox (`length` along X) to the
    detected orientation. `(cx, cy)` is the box center.
    """
    n = len(poly)
    if n < 4:
        return None
    poly_area = abs(_signed_area(poly))
    if poly_area < 1e-9:
        return None

    cos_threshold = math.cos(math.radians(90 - right_angle_tol_deg))
    right_count = 0
    for i in range(n):
        v_prev = poly[(i - 1) % n]
        v_curr = poly[i]
        v_next = poly[(i + 1) % n]
        e1 = (v_curr[0] - v_prev[0], v_curr[1] - v_prev[1])
        e2 = (v_next[0] - v_curr[0], v_next[1] - v_curr[1])
        l1 = math.hypot(*e1)
        l2 = math.hypot(*e2)
        if l1 < 1e-9 or l2 < 1e-9:
            continue
        # |cos(turn)| ≤ cos_threshold → turn is within tol of ±90° (a right angle).
        if abs((e1[0] * e2[0] + e1[1] * e2[1]) / (l1 * l2)) <= cos_threshold:
            right_count += 1
    if right_count < min_right_angle_corners:
        return None

    best: tuple[float, float, float, float, tuple[float, float]] | None = None  # area, L, W, angle, center
    for i in range(n):
        dx = poly[(i + 1) % n][0] - poly[i][0]
        dy = poly[(i + 1) % n][1] - poly[i][1]
        edge_len = math.hypot(dx, dy)
        if edge_len < 1e-9:
            continue
        cos_a = dx / edge_len
        sin_a = dy / edge_len
        # Rotate polygon so edge i aligns with the +x axis, then take axis-aligned bbox.
        rot = [(p[0] * cos_a + p[1] * sin_a, -p[0] * sin_a + p[1] * cos_a) for p in poly]
        xs = [p[0] for p in rot]
        ys = [p[1] for p in rot]
        L = max(xs) - min(xs)
        W = max(ys) - min(ys)
        area = L * W
        if area < 1e-9:
            continue
        if best is None or area < best[0]:
            angle_deg = math.degrees(math.atan2(dy, dx))
            cx_rot = (max(xs) + min(xs)) / 2
            cy_rot = (max(ys) + min(ys)) / 2
            # Rotate center back to original frame (inverse rotation).
            cx = cx_rot * cos_a - cy_rot * sin_a
            cy = cx_rot * sin_a + cy_rot * cos_a
            best = (area, L, W, angle_deg, (cx, cy))

    if best is None:
        return None
    obb_area, L, W, angle, center = best
    if poly_area / obb_area < (1 - area_rel_tol):
        return None

    # Canonicalise: `length` is the longer side; angle measures the long-axis
    # orientation. Rotations of ±180° leave the box unchanged, ±90° just swap
    # length and width — normalise to keep angle in (-90, 90].
    if W > L:
        L, W = W, L
        angle += 90.0
    while angle > 90.0:
        angle -= 180.0
    while angle <= -90.0:
        angle += 180.0
    return (L, W, center, angle)


def _polygon_loops(loops: list[list[Point2D]],
                   circles: list[tuple[float, Point2D] | None],
                   boxes: list[tuple[float, float, Point2D, float] | None]) -> list[list[Point2D]]:
    """Loops that will be emitted as Pencils (not collapsed into cylinders or boxes)."""
    return [L for L, c, b in zip(loops, circles, boxes) if c is None and b is None]


def _canonical_polygon(poly: list[Point2D]) -> tuple[list[Point2D], float, Point2D]:
    """Return (canonical_vertices, rotation_deg, original_centroid).

    Canonical form: vertices translated to put the area-weighted centroid at
    the origin, then rotated so the PCA principal axis aligns with +X. The
    rotation needed to place a canonical-form polygon back into its original
    pose is `rotation_deg` (CCW around Z), followed by translation by
    `original_centroid`. The 180° ambiguity in the principal-axis direction
    is resolved by picking the orientation whose sorted-vertex tuple is
    lexicographically smaller — robust for shapes with long-axis (X-mirror)
    symmetry, where the largest-|x| vertex ties on both ends and a
    sign-of-x tiebreaker would flip-flop with tessellation order.
    """
    n = len(poly)
    if n < 3:
        return (poly[:], 0.0, (0.0, 0.0))
    cx, cy = _polygon_centroid(poly)
    p = [(x - cx, y - cy) for x, y in poly]
    cxx = sum(x * x for x, y in p) / n
    cyy = sum(y * y for x, y in p) / n
    cxy = sum(x * y for x, y in p) / n
    theta = 0.5 * math.atan2(2 * cxy, cxx - cyy)
    cos_t = math.cos(-theta)
    sin_t = math.sin(-theta)
    canon = [(x * cos_t - y * sin_t, x * sin_t + y * cos_t) for x, y in p]
    canon_rot = [(-x, -y) for x, y in canon]
    # Compare on a quantized grid: with X-mirror-symmetric shapes the two
    # smallest-x vertices coincide in design and only differ by µm of
    # tessellation noise, so a raw-float lex-min would flip-flop between
    # the two 180°-rotated orientations.
    def _quant(verts, g=0.05):
        return tuple(sorted((round(x / g), round(y / g)) for x, y in verts))
    if _quant(canon_rot) < _quant(canon):
        canon = canon_rot
        theta += math.pi
    # Normalise to (-180, 180].
    theta_deg = math.degrees(theta)
    while theta_deg > 180.0:
        theta_deg -= 360.0
    while theta_deg <= -180.0:
        theta_deg += 360.0
    return (canon, theta_deg, (cx, cy))


def _loop_signature(loop: list[Point2D],
                    circle: tuple[float, Point2D] | None,
                    box: tuple[float, float, Point2D, float] | None,
                    grid: float = 0.05,
                    area_grid: float = 0.5) -> tuple:
    """Hashable signature for duplicate detection. Same shape → same signature.

    Polygons sign on canonical bbox + signed area + vertex count, all
    quantised. Per-vertex matching would be more discriminating but is
    fragile: tiny PCA-angle differences between mesh instances rotate the
    canonical frame by ~0.3°, shifting every vertex's canonical x by up to
    `bbox_radius × sin(0.3°)` ≈ 0.05 mm — enough to push vertices across
    any reasonable quantisation grid. Canonical bbox and area are stable
    invariants under such micro-rotations. Vertex count adds a sanity check
    that keeps unrelated shapes (rectangle vs ellipse with matching bbox+
    area) from colliding.
    """
    if circle is not None:
        return ('cylinder', round(circle[0] / grid))
    if box is not None:
        L, W, _, _ = box
        return ('box', round(L / grid), round(W / grid))
    canon, _, _ = _canonical_polygon(loop)
    xs = [x for x, _ in canon]
    ys = [y for _, y in canon]
    bbox_l = max(xs) - min(xs)
    bbox_w = max(ys) - min(ys)
    area = abs(_signed_area(canon))
    return (
        'polygon',
        round(bbox_l / grid),
        round(bbox_w / grid),
        round(area / area_grid),
        len(canon),
    )


def _detect_polar_pattern(placements: list[tuple[float, float, float]],
                          rotation_modulus_deg: float = 360.0,
                          *,
                          rel_tol: float = 0.01,
                          angle_tol_deg: float = 0.5
                          ) -> tuple[tuple[float, float], float, list[int], float] | None:
    """Detect an N-fold polar (rotational) pattern in dedup-group placements.

    Returns `((cx, cy), radius, sorted_indices, step_deg)` if all `placements`
    lie on a common circle at uniform 360°/N angular spacing AND their
    primitive rotations advance by the same step (mod `rotation_modulus_deg`).
    Returns None otherwise.

    `rotation_modulus_deg` is the primitive's own rotational self-symmetry:
        - `math.inf` for cylinders (rotationally symmetric — skip the check)
        - 180.0 for boxes (a 180° rotation maps a rectangle to itself, so
          observed rotation steps wrap mod 180°)
        - 360.0 for polygons (no inherent self-symmetry)

    Requires N >= 3 (a 2-element pattern is ambiguous with reflection).
    """
    n = len(placements)
    if n < 3:
        return None
    cx0 = sum(p[1] for p in placements) / n
    cy0 = sum(p[2] for p in placements) / n
    dists = [math.hypot(p[1] - cx0, p[2] - cy0) for p in placements]
    r_mean = sum(dists) / n
    if r_mean < 1e-9:
        return None
    if any(abs(d - r_mean) > rel_tol * r_mean for d in dists):
        return None
    sorted_pos = sorted(
        (math.degrees(math.atan2(p[2] - cy0, p[1] - cx0)) % 360.0, i)
        for i, p in enumerate(placements)
    )
    sorted_indices = [i for _, i in sorted_pos]
    sorted_angles = [a for a, _ in sorted_pos]
    expected_step = 360.0 / n
    for k in range(n):
        delta = (sorted_angles[(k + 1) % n] - sorted_angles[k]) % 360.0
        if abs(delta - expected_step) > angle_tol_deg:
            return None
    if not math.isinf(rotation_modulus_deg):
        rotations = [placements[i][0] for i in sorted_indices]
        expected_rot = expected_step % rotation_modulus_deg
        for k in range(n):
            delta_rot = (rotations[(k + 1) % n] - rotations[k]) % rotation_modulus_deg
            err = abs(delta_rot - expected_rot)
            err = min(err, rotation_modulus_deg - err)
            if err > angle_tol_deg:
                return None
    return ((cx0, cy0), r_mean, sorted_indices, expected_step)


def _loop_placement(loop: list[Point2D],
                    circle: tuple[float, Point2D] | None,
                    box: tuple[float, float, Point2D, float] | None) -> tuple[float, float, float]:
    """Return (rotation_deg, cu, cv) — the transform that places the canonical/
    template form back into its source location.

    Cylinders are rotationally symmetric → rotation is always 0. Boxes carry
    their rotation from `_detect_box`. Polygons take rotation from PCA."""
    if circle is not None:
        cu, cv = circle[1]
        return (0.0, cu, cv)
    if box is not None:
        _, _, (cu, cv), angle = box
        return (angle, cu, cv)
    _, rotation_deg, (cu, cv) = _canonical_polygon(loop)
    return (rotation_deg, cu, cv)


def _polygon_centroid(poly: list[Point2D]) -> Point2D:
    """Area-weighted centroid of a simple polygon (shoelace formula)."""
    n = len(poly)
    if n == 0:
        return (0.0, 0.0)
    if n < 3:
        cx = sum(p[0] for p in poly) / n
        cy = sum(p[1] for p in poly) / n
        return (cx, cy)
    a2 = 0.0
    cx = 0.0
    cy = 0.0
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        cross = x1 * y2 - x2 * y1
        a2 += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if abs(a2) < 1e-12:
        return (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n)
    return (cx / (3 * a2), cy / (3 * a2))


def reconstruct(path: str, sig_area_frac: float = 0.005) -> ReconstructionResult:
    verts, faces = read_mesh(path)
    planes = cluster_planes(verts, faces)
    planes.sort(key=lambda p: -p.area)
    total_area = sum(p.area for p in planes)
    sig = [p for p in planes if p.area / total_area >= sig_area_frac]

    extrusion_axis = None
    buckets = None
    best_attempt: tuple[Vec, int] | None = None  # (axis, tilted_count) — for diagnostic when no axis works
    for candidate in candidate_axes(sig):
        attempt = classify_planes_vs_axis(sig, candidate)
        if not attempt.other:
            extrusion_axis = candidate
            buckets = attempt
            break
        n_other = len(attempt.other)
        if best_attempt is None or n_other < best_attempt[1]:
            best_attempt = (candidate, n_other)
    if extrusion_axis is None:
        axis, n_other = best_attempt
        return ReconstructionResult(
            is_2d5_extrudable=False,
            extrusion_axis=Vector(*axis),
            error=f'No candidate axis classifies all planes cleanly; best had {n_other} tilted plane(s) out of {len(sig)} significant planes — part is not 2.5D-extrudable',
        )

    cap_planes = [p for _, p in buckets.cap]
    side_planes = [p for _, p in buckets.side]

    if abs(extrusion_axis[2]) < 0.9:
        ex0 = vnorm((-extrusion_axis[1], extrusion_axis[0], 0))
    else:
        ex0 = (1.0, 0.0, 0.0)
    ey0 = vnorm(vcross(extrusion_axis, ex0))
    origin3 = (0.0, 0.0, 0.0)

    silhouettes: list[tuple[PlaneCluster, list[list[Point2D]]]] = []
    for p in cap_planes:
        rings3d = boundary_polygons(verts, faces, p.tris)
        rings3d = _filter_noise_step_loops(rings3d, p.normal, p.d)
        raw2d = [[to_local(pt, origin3, ex0, ey0) for pt in ring3d] for ring3d in rings3d]
        raw2d = _deduplicate_loops(_filter_noise_loops(raw2d))
        loops2d: list[list[Point2D]] = []
        for poly2d in raw2d:
            poly2d = simplify_collinear(poly2d)
            if len(poly2d) >= 3:
                loops2d.append(poly2d)
        if loops2d:
            silhouettes.append((p, loops2d))

    # Circular / no-flat-side parts have no datum plane to align the in-plane
    # axes — fall back to the provisional ex0/ey0 frame. The rotation around
    # z_dir is arbitrary in that case (the silhouette is rotationally symmetric
    # up to tessellation noise), so any orthonormal frame in the cross-section
    # is as good as any other.
    if side_planes:
        datum_plane = pick_datum(side_planes)
        datum_contact_area = datum_plane.area
        x_dir, y_dir, z_dir = build_datum_frame(
            extrusion_axis, datum_plane, silhouettes, origin3, ex0, ey0,
        )
    else:
        datum_plane = None
        datum_contact_area = 0.0
        x_dir, y_dir, z_dir = make_frame(extrusion_axis, ey0)
    new_origin = shift_origin_to_first_quadrant(verts, faces, cap_planes, x_dir, y_dir)

    new_silhouettes: list[tuple[PlaneCluster, list[list[Point2D]],
                                 list[tuple[float, Point2D] | None],
                                 list[tuple[float, float, Point2D, float] | None],
                                 list[list[Point2D]]]] = []
    for plane, _old in silhouettes:
        rings3d = boundary_polygons(verts, faces, plane.tris)
        rings3d = _filter_noise_step_loops(rings3d, plane.normal, plane.d)
        raw2d = [[to_local(pt, new_origin, x_dir, y_dir) for pt in ring3d] for ring3d in rings3d]
        raw2d = _deduplicate_loops(_filter_noise_loops(raw2d))
        loops_new: list[list[Point2D]] = []
        circles_new: list[tuple[float, Point2D] | None] = []
        boxes_new: list[tuple[float, float, Point2D, float] | None] = []
        raw_new: list[list[Point2D]] = []
        for poly_new in raw2d:
            # Detect circles on the RAW tessellation; simplify_collinear can
            # collapse a 48-vertex circle into 4 points (radial deviation
            # within the collinearity tolerance), which would defeat detection.
            simplified = simplify_collinear(poly_new)
            if len(simplified) >= 3:
                loops_new.append(simplified)
                raw_new.append(poly_new)
                circle = _detect_circle(poly_new, simplified)
                circles_new.append(circle)
                # Box detection runs on the simplified polygon — that's where
                # collinear chamfer artefacts collapse into clean ~4 vertices.
                # Skip if already detected as a circle (avoid double-emit).
                boxes_new.append(_detect_box(simplified) if circle is None else None)
        new_silhouettes.append((plane, loops_new, circles_new, boxes_new, raw_new))

    new_silhouettes.sort(key=lambda t: cap_depth_in_frame(t[0], z_dir, new_origin))

    # Identify body's z-range by the two largest-area caps (front = largest, back = second).
    sorted_by_area = sorted(new_silhouettes, key=lambda t: -t[0].area)
    front_plane = sorted_by_area[0][0] if sorted_by_area else None
    back_plane = sorted_by_area[1][0] if len(sorted_by_area) >= 2 else None
    front_depth = cap_depth_in_frame(front_plane, z_dir, new_origin) if front_plane else 0.0
    back_depth = cap_depth_in_frame(back_plane, z_dir, new_origin) if back_plane else front_depth

    body_min_depth = min(front_depth, back_depth)
    body_max_depth = max(front_depth, back_depth)

    # Classify and name each cap.
    name_for_plane: dict[int, str] = {}
    if front_plane is not None:
        name_for_plane[id(front_plane)] = 'front'
    if back_plane is not None:
        name_for_plane[id(back_plane)] = 'back'
    eps = 1e-3
    for plane, _, _, _, _ in new_silhouettes:
        if id(plane) in name_for_plane:
            continue
        d = cap_depth_in_frame(plane, z_dir, new_origin)
        if d < body_min_depth - eps:
            name_for_plane[id(plane)] = 'back_protrusion'
        elif d > body_max_depth + eps:
            name_for_plane[id(plane)] = 'front_protrusion'
        else:
            name_for_plane[id(plane)] = 'pocket'

    layers = [
        Layer(plane=p, name=name_for_plane[id(p)],
              depth=cap_depth_in_frame(p, z_dir, new_origin),
              loops=loops, circles=circles, boxes=boxes, raw_loops=raws)
        for p, loops, circles, boxes, raws in new_silhouettes
    ]

    # Anchor the cross-section origin on the vertex shared by the most polygon
    # emits. Circular/box loops become primitives (no Pencil → no anchor
    # benefit), so they're excluded from the shared-start search. `back` is
    # implicit in the body extrude and never emits its own polygon.
    emit_polys: list[list[Point2D]] = []
    for L in layers:
        if L.name == 'back':
            continue
        emit_polys.extend(_polygon_loops(L.loops, L.circles, L.boxes))
    shared_uv = find_shared_start(emit_polys)
    if shared_uv is not None:
        su, sv = shared_uv
        new_origin = vadd(new_origin, vadd(vmul(x_dir, su), vmul(y_dir, sv)))
        for L in layers:
            L.loops = [[(u - su, v - sv) for u, v in loop] for loop in L.loops]
            L.raw_loops = [[(u - su, v - sv) for u, v in loop] for loop in L.raw_loops]
            L.circles = [None if c is None else (c[0], (c[1][0] - su, c[1][1] - sv))
                         for c in L.circles]
            L.boxes = [None if b is None else (b[0], b[1], (b[2][0] - su, b[2][1] - sv), b[3])
                       for b in L.boxes]

    # Anchor cross-section origin at body_min_depth so that:
    #   body extrudes from local z=0 (back cap) to z=body_thickness (front cap).
    cross_origin = vadd(new_origin, vmul(z_dir, body_min_depth))

    cylinders: list[CylinderFeature] = []
    boxes_out: list[BoxFeature] = []
    code = _emit_code(cross_origin, x_dir, y_dir, z_dir, datum_plane,
                      datum_contact_area, layers, cylinders, boxes_out,
                      body_min_depth, body_max_depth)

    return ReconstructionResult(
        is_2d5_extrudable=True,
        extrusion_axis=Vector(*extrusion_axis),
        x_dir=Vector(*x_dir), y_dir=Vector(*y_dir), z_dir=Vector(*z_dir),
        origin=Vector(*cross_origin),
        datum_plane=datum_plane,
        datum_contact_area=datum_contact_area,
        layers=layers,
        cylinders=cylinders,
        boxes=boxes_out,
        code=code,
    )


def _depth_role_name(depth: int) -> str:
    """Hierarchical loop-role label: outer | hole | island | deephole | deepisland ..."""
    if depth == 0:
        return 'outer'
    if depth == 1:
        return 'hole'
    if depth == 2:
        return 'island'
    # Beyond depth 2, fall back to a generic name.
    return f'deep{depth - 1}'


def _emit_nested_loops(
    code: list[str],
    loops: list[list[Point2D]],
    circles: list[tuple[float, Point2D] | None],
    boxes: list[tuple[float, float, Point2D, float] | None],
    parents: list[int],
    *,
    thickness: float,
    shift_z: float,
    op_outer: str,
    op_hole: str,
    base_name: str,
    blade_var: str,
    preferred_start: Point2D | None,
    z_dir: Vec,
    cylinders_out: list['CylinderFeature'],
    boxes_out: list['BoxFeature'],
    skip_outer_emit: int | None = None,
    raw_loops: list[list[Point2D]] | None = None,
) -> None:
    """Walk the nesting tree depth-first; emit each loop with alternating op.

    op_outer applies at even depths (0, 2, ...), op_hole at odd depths (1, 3, ...).
    Each loop is extruded `thickness` mm and moved `shift_z` in local z, then
    combined into `blade_var` via .fuse/.cut. Loops detected as tessellated
    circles are emitted as `SmarterCone.cylinder(...)`; loops detected as
    rectangles are emitted as `SmartBox(...).rotate_z(...).move(...)`. Both
    paths skip the Pencil + extrude emission and are recorded in their
    respective `*_out` lists.

    Leaf siblings (loops with no children) that share a canonical signature
    are deduplicated at every depth: a single template is emitted once and
    placed at each location, preferring an `Axis`-pivoted polar pattern when
    one is detected.

    `skip_outer_emit` is the loop index whose own emit should be skipped (used
    for the body's first outer which is already emitted as the blade initializer);
    its children are still walked.

    `thickness` and `shift_z` accept either a scalar (applied to every loop in
    the layer) or a list of length `len(loops)` (per-loop override). The
    per-loop form lets a front-protrusion layer extrude polygon tabs that
    extend outside the body silhouette as full-height features (from
    body_min_depth up to the layer) while keeping cylinder/box co-axial
    features (e.g. annular rings) as thin caps on the body's top face.
    """
    n = len(loops)
    t_per = thickness if isinstance(thickness, list) else [thickness] * n
    sz_per = shift_z if isinstance(shift_z, list) else [shift_z] * n
    # Polygon emit prefers the pre-simplify raw boundary so arc detection can
    # recover curved walls. Simplified `loops` are still used for nesting,
    # signature, circle/box detection, and centroid/rotation alignment.
    emit_loops = raw_loops if raw_loops is not None else loops

    children_of: dict[int, list[int]] = defaultdict(list)
    for i, p in enumerate(parents):
        if p != -1:
            children_of[p].append(i)
    outers = [i for i, p in enumerate(parents) if p == -1]

    def emit_loop_at(idx: int, depth: int, name: str) -> None:
        """Emit a single loop (circle, box, or polygon) under `name`. No recursion."""
        if idx == skip_outer_emit:
            return
        t = t_per[idx]
        sz = sz_per[idx]
        op = op_outer if depth % 2 == 0 else op_hole
        circle = circles[idx]
        box = boxes[idx]
        if circle is not None:
            radius, (cu, cv) = circle
            code.append(f'{name} = SmarterCone.cylinder({fmt(radius)}, {fmt(t)})')
            if abs(cu) > 1e-9 or abs(cv) > 1e-9 or abs(sz) > 1e-9:
                code.append(f'{name}.move({fmt(cu)}, {fmt(cv)}, {fmt(sz)})')
            code.append(f'{blade_var}.{op}({name})')
            cylinders_out.append(CylinderFeature(
                axis=Vector(*z_dir),
                radius=radius,
                height=t,
                area=math.pi * radius * radius,
                base=(cu, cv, sz),
                layer_name=base_name,
            ))
        elif box is not None:
            L, W, (cu, cv), angle = box
            # SmartBox is XY-centered but Z-base-aligned (see SmartBox.__init__):
            # `.move(cu, cv, sz)` lands the box centroid at (cu, cv) with
            # its base at z=sz and top at z=sz+t.
            code.append(f'{name} = SmartBox({fmt(L)}, {fmt(W)}, {fmt(t)})')
            if abs(angle) > 1e-3:
                code.append(f'{name}.rotate_z({fmt(angle)})')
            if abs(cu) > 1e-9 or abs(cv) > 1e-9 or abs(sz) > 1e-9:
                code.append(f'{name}.move({fmt(cu)}, {fmt(cv)}, {fmt(sz)})')
            code.append(f'{blade_var}.{op}({name})')
            boxes_out.append(BoxFeature(
                length=L, width=W, height=t,
                base=(cu, cv, sz),
                angle_deg=angle,
                layer_name=base_name,
            ))
        else:
            code.extend(emit_pencil_for(emit_loops[idx], name, preferred_start))
            code.append(f'{name}_body = {name}.extrude({fmt(t)})')
            if abs(sz) > 1e-9:
                code.append(f'{name}_body.move(0, 0, {fmt(sz)})')
            code.append(f'{blade_var}.{op}({name}_body)')

    def is_annulus(idx: int) -> bool:
        """True when `idx` is an outer cylinder with exactly one circular hole
        child and nothing nested below the hole. The naive emit (fuse outer,
        then cut inner) leaves OCCT with a degenerate "lid over an open ring"
        when another same-radius cut sits directly below — building the ring
        as a standalone solid first sidesteps the issue universally."""
        if idx == skip_outer_emit:
            return False
        if circles[idx] is None:
            return False
        kids = children_of[idx]
        if len(kids) != 1:
            return False
        ch = kids[0]
        return circles[ch] is not None and not children_of[ch]

    def emit_annulus_at(outer_idx: int, inner_idx: int, depth: int, name: str) -> None:
        op = op_outer if depth % 2 == 0 else op_hole
        t = t_per[outer_idx]
        sz = sz_per[outer_idx]
        outer_r, (cu, cv) = circles[outer_idx]
        inner_r, (icu, icv) = circles[inner_idx]
        hole_name = f'{name}_hole'
        code.append(f'{name} = SmarterCone.cylinder({fmt(outer_r)}, {fmt(t)})')
        code.append(f'{hole_name} = SmarterCone.cylinder({fmt(inner_r)}, {fmt(t)})')
        if abs(cu) > 1e-9 or abs(cv) > 1e-9 or abs(sz) > 1e-9:
            code.append(f'{name}.move({fmt(cu)}, {fmt(cv)}, {fmt(sz)})')
        if abs(icu) > 1e-9 or abs(icv) > 1e-9 or abs(sz) > 1e-9:
            code.append(f'{hole_name}.move({fmt(icu)}, {fmt(icv)}, {fmt(sz)})')
        code.append(f'{name}.cut({hole_name})')
        code.append(f'{blade_var}.{op}({name})')
        cylinders_out.append(CylinderFeature(
            axis=Vector(*z_dir), radius=outer_r, height=t,
            area=math.pi * outer_r * outer_r,
            base=(cu, cv, sz), layer_name=base_name,
        ))
        cylinders_out.append(CylinderFeature(
            axis=Vector(*z_dir), radius=inner_r, height=t,
            area=math.pi * inner_r * inner_r,
            base=(icu, icv, sz), layer_name=base_name,
        ))

    def visit(idx: int, depth: int, name: str) -> None:
        """Emit `idx` with the given `name` and recurse into its children."""
        if is_annulus(idx):
            emit_annulus_at(idx, children_of[idx][0], depth, name)
            return
        emit_loop_at(idx, depth, name)
        emit_children(children_of[idx], depth + 1, name)

    def emit_children(child_indices: list[int], child_depth: int,
                      parent_name: str) -> None:
        """Emit the children of a node, collapsing leaf siblings that share a
        signature into a single template + placement loop. Non-leaf children
        and singleton leaves visit individually."""
        if not child_indices:
            return
        role = _depth_role_name(child_depth)
        child_op = op_outer if child_depth % 2 == 0 else op_hole

        # Map each child to its signature (None = non-leaf, can't be deduped).
        sig_of: dict[int, tuple | None] = {}
        sig_to_indices: dict[tuple, list[int]] = {}
        for ch in child_indices:
            if children_of[ch]:
                sig_of[ch] = None
            else:
                sig = _loop_signature(loops[ch], circles[ch], boxes[ch])
                sig_of[ch] = sig
                sig_to_indices.setdefault(sig, []).append(ch)

        # Walk children in tree order; each non-leaf, multi-member group
        # (counted once at first occurrence), or singleton leaf consumes one
        # emission "unit" slot.
        units: list[tuple[str, object]] = []
        seen_groups: set[tuple] = set()
        for ch in child_indices:
            sig = sig_of[ch]
            if sig is None:
                units.append(('nonleaf', ch))
            elif sig in seen_groups:
                continue
            elif len(sig_to_indices[sig]) > 1:
                seen_groups.add(sig)
                units.append(('group', sig))
            else:
                units.append(('singleton', ch))

        single_unit = len(units) == 1
        for i, (kind, payload) in enumerate(units):
            label = f'{parent_name}_{role}' if single_unit else f'{parent_name}_{role}_{i}'
            if kind == 'nonleaf':
                visit(payload, child_depth, label)
            elif kind == 'group':
                indices = sig_to_indices[payload]
                # Members of a dedup group share a signature and thus end up
                # with the same classification (inside vs outside body
                # silhouette). Use the first member's per-loop thickness/shift.
                _emit_dedup_group(
                    code, indices, payload, loops, circles, boxes,
                    thickness=t_per[indices[0]], shift_z=sz_per[indices[0]],
                    op=child_op,
                    base_name=label, blade_var=blade_var,
                    z_dir=z_dir, cylinders_out=cylinders_out, boxes_out=boxes_out,
                    group_idx=0, single_group=True,
                    raw_loops=raw_loops,
                )
            else:  # singleton
                visit(payload, child_depth, label)

    # Top-level (depth-0): outers without children that share a signature
    # collapse into a single template; outers with children visit recursively.
    leaf_groups: dict[tuple, list[int]] = defaultdict(list)
    visited_individually: list[int] = []
    for o_idx in outers:
        if o_idx == skip_outer_emit or children_of[o_idx]:
            visited_individually.append(o_idx)
        else:
            sig = _loop_signature(loops[o_idx], circles[o_idx], boxes[o_idx])
            leaf_groups[sig].append(o_idx)

    def outer_name(o_idx: int) -> str:
        return base_name if len(outers) == 1 else f'{base_name}_{outers.index(o_idx)}'

    for o_idx in visited_individually:
        visit(o_idx, 0, outer_name(o_idx))

    single_group = len(leaf_groups) == 1 and not visited_individually
    group_idx = 0
    for sig, indices in leaf_groups.items():
        if len(indices) > 1:
            _emit_dedup_group(
                code, indices, sig, loops, circles, boxes,
                thickness=t_per[indices[0]], shift_z=sz_per[indices[0]],
                op=op_outer,
                base_name=base_name, blade_var=blade_var,
                z_dir=z_dir, cylinders_out=cylinders_out, boxes_out=boxes_out,
                group_idx=group_idx, single_group=single_group,
                raw_loops=raw_loops,
            )
            group_idx += 1
        else:
            visit(indices[0], 0, outer_name(indices[0]))


_PRIMITIVE_ROTATION_MODULUS = {
    'cylinder': math.inf,  # rotationally symmetric — rotation step doesn't matter
    'box': 180.0,          # rectangle = self after 180° rotation
    'polygon': 360.0,      # no inherent self-symmetry
}


def _emit_polar_group(
    code: list[str],
    polar: tuple[tuple[float, float], float, list[int], float],
    placements: list[tuple[float, float, float]],
    indices: list[int],
    sig: tuple,
    loops: list[list[Point2D]],
    circles: list[tuple[float, Point2D] | None],
    boxes: list[tuple[float, float, Point2D, float] | None],
    *,
    thickness: float,
    shift_z: float,
    op: str,
    blade_var: str,
    z_dir: Vec,
    cylinders_out: list['CylinderFeature'],
    boxes_out: list['BoxFeature'],
    group_label: str,
    raw_loops: list[list[Point2D]] | None = None,
) -> None:
    """Emit an N-fold polar pattern: build one template, rotate it N times around a Z-axis pivot."""
    (cx, cy), _r, sorted_indices, step = polar
    n = len(sorted_indices)
    template_sorted_idx = sorted_indices[0]
    template_loop_idx = indices[template_sorted_idx]
    angle0, cu0, cv0 = placements[template_sorted_idx]
    template_name = f'{group_label}_template'
    pivot_name = f'{group_label}_pivot'

    code.append(f'# {group_label}: {n}-fold polar pattern around ({fmt(cx)}, {fmt(cy)})')

    if sig[0] == 'cylinder':
        radius_val = circles[template_loop_idx][0]
        code.append(f'{template_name} = SmarterCone.cylinder({fmt(radius_val)}, {fmt(thickness)}).move({fmt(cu0)}, {fmt(cv0)}, {fmt(shift_z)})')
    elif sig[0] == 'box':
        L, W, _, _ = boxes[template_loop_idx]
        chain = f'SmartBox({fmt(L)}, {fmt(W)}, {fmt(thickness)})'
        if abs(angle0) > 1e-3:
            chain += f'.rotate_z({fmt(angle0)})'
        chain += f'.move({fmt(cu0)}, {fmt(cv0)}, {fmt(shift_z)})'
        code.append(f'{template_name} = {chain}')
    else:  # polygon
        # Use raw polygon for the template Pencil emit so arc-bounded shapes
        # (curved bars, etc.) keep their curvature instead of collapsing into
        # the simplified bbox quadrilateral.
        source_loop = (raw_loops[template_loop_idx]
                       if raw_loops is not None else loops[template_loop_idx])
        canon, _, _ = _canonical_polygon(source_loop)
        pencil_name = f'{template_name}_pencil'
        code.extend(emit_pencil_for(canon, pencil_name, None))
        code.append(f'{template_name} = {pencil_name}.extrude({fmt(thickness)})')
        if abs(angle0) > 1e-3:
            code.append(f'{template_name}.rotate_z({fmt(angle0)})')
        if abs(cu0) > 1e-9 or abs(cv0) > 1e-9 or abs(shift_z) > 1e-9:
            code.append(f'{template_name}.move({fmt(cu0)}, {fmt(cv0)}, {fmt(shift_z)})')

    pivot_name = f'{group_label}_pivot'
    code.append(f'{pivot_name} = Axis(({fmt(cx)}, {fmt(cy)}, 0), (0, 0, 1))')
    code.append(f'for i in range({n}):')
    code.append(f'    {blade_var}.{op}({template_name}.rotated({pivot_name}, i * {fmt(step)}))')

    # Record one feature per placement (in sorted order).
    for sorted_idx in sorted_indices:
        loop_idx = indices[sorted_idx]
        angle, cu, cv = placements[sorted_idx]
        if sig[0] == 'cylinder':
            radius_val = circles[loop_idx][0]
            cylinders_out.append(CylinderFeature(
                axis=Vector(*z_dir),
                radius=radius_val, height=thickness,
                area=math.pi * radius_val * radius_val,
                base=(cu, cv, shift_z),
                layer_name=group_label,
            ))
        elif sig[0] == 'box':
            L, W, _, _ = boxes[loop_idx]
            boxes_out.append(BoxFeature(
                length=L, width=W, height=thickness,
                base=(cu, cv, shift_z),
                angle_deg=angle,
                layer_name=group_label,
            ))


def _emit_dedup_group(
    code: list[str],
    indices: list[int],
    sig: tuple,
    loops: list[list[Point2D]],
    circles: list[tuple[float, Point2D] | None],
    boxes: list[tuple[float, float, Point2D, float] | None],
    *,
    thickness: float,
    shift_z: float,
    op: str,
    base_name: str,
    blade_var: str,
    z_dir: Vec,
    cylinders_out: list['CylinderFeature'],
    boxes_out: list['BoxFeature'],
    group_idx: int,
    single_group: bool,
    raw_loops: list[list[Point2D]] | None = None,
) -> None:
    """Emit a `for` loop over placements that share a single template.

    Tries polar-pattern detection first (N-fold rotational symmetry around a
    common axis) — when it matches, emits a `rotate(pivot, i*step)` form that
    expresses the design intent. Falls back to an explicit placement list when
    placements don't form a polar pattern.
    """
    n = len(indices)
    placements = [_loop_placement(loops[i], circles[i], boxes[i]) for i in indices]
    group_label = base_name if single_group else f'{base_name}_{group_idx}'

    polar = _detect_polar_pattern(placements, _PRIMITIVE_ROTATION_MODULUS[sig[0]])
    if polar is not None:
        _emit_polar_group(
            code, polar, placements, indices, sig, loops, circles, boxes,
            thickness=thickness, shift_z=shift_z, op=op,
            blade_var=blade_var, z_dir=z_dir,
            cylinders_out=cylinders_out, boxes_out=boxes_out,
            group_label=group_label,
            raw_loops=raw_loops,
        )
        return

    if sig[0] == 'cylinder':
        radius = circles[indices[0]][0]
        code.append(f'# {group_label}: {n} × SmarterCone.cylinder(r={fmt(radius)}, h={fmt(thickness)})')
        code.append('for cu, cv in [')
        for _, cu, cv in placements:
            code.append(f'    ({fmt(cu)}, {fmt(cv)}),')
        code.append(']:')
        code.append(f'    {blade_var}.{op}(SmarterCone.cylinder({fmt(radius)}, {fmt(thickness)}).move(cu, cv, {fmt(shift_z)}))')
        for _, cu, cv in placements:
            cylinders_out.append(CylinderFeature(
                axis=Vector(*z_dir),
                radius=radius, height=thickness,
                area=math.pi * radius * radius,
                base=(cu, cv, shift_z),
                layer_name=base_name,
            ))
    elif sig[0] == 'box':
        L, W, _, _ = boxes[indices[0]]
        code.append(f'# {group_label}: {n} × SmartBox({fmt(L)}, {fmt(W)}, {fmt(thickness)})')
        code.append('for angle, cu, cv in [')
        for angle, cu, cv in placements:
            code.append(f'    ({fmt(angle)}, {fmt(cu)}, {fmt(cv)}),')
        code.append(']:')
        code.append(f'    {blade_var}.{op}(SmartBox({fmt(L)}, {fmt(W)}, {fmt(thickness)}).rotate_z(angle).move(cu, cv, {fmt(shift_z)}))')
        for angle, cu, cv in placements:
            boxes_out.append(BoxFeature(
                length=L, width=W, height=thickness,
                base=(cu, cv, shift_z),
                angle_deg=angle,
                layer_name=base_name,
            ))
    else:  # polygon
        source_loop = (raw_loops[indices[0]]
                       if raw_loops is not None else loops[indices[0]])
        canon, _, _ = _canonical_polygon(source_loop)
        template_name = f'{group_label}_template'
        code.append(f'# {group_label}: {n} × custom polygon template')
        code.extend(emit_pencil_for(canon, template_name, None))
        code.append(f'{template_name}_body = {template_name}.extrude({fmt(thickness)})')
        code.append('for angle, cu, cv in [')
        for angle, cu, cv in placements:
            code.append(f'    ({fmt(angle)}, {fmt(cu)}, {fmt(cv)}),')
        code.append(']:')
        code.append(f'    {blade_var}.{op}({template_name}_body.copy().rotate_z(angle).move(cu, cv, {fmt(shift_z)}))')


def _emit_code(cross_origin: Vec, x_dir: Vec, y_dir: Vec, z_dir: Vec,
               datum_plane: PlaneCluster | None, datum_total: float,
               layers: list[Layer], cylinders: list[CylinderFeature],
               boxes_out: list[BoxFeature],
               body_min_depth: float, body_max_depth: float) -> str:
    body_thickness = body_max_depth - body_min_depth
    by_name = {L.name: L for L in layers}
    front = by_name.get('front')

    code: list[str] = []
    code.append('# Iris blade as a stepped 2.5D extrusion, datum-aligned.')
    code.append(f'# Extrusion axis  z_dir = ({fmt(z_dir[0])}, {fmt(z_dir[1])}, {fmt(z_dir[2])})')
    code.append(f'# Datum plane     y_dir = ({fmt(y_dir[0])}, {fmt(y_dir[1])}, {fmt(y_dir[2])})')
    if datum_plane is not None:
        code.append(f'#   (= {fmt(datum_plane.normal[2])} along world Z, the floor — '
                    f'contact area {fmt(datum_total, 2)} mm²)')
    else:
        code.append('#   (no flat side wall — circular silhouette; in-plane '
                    'orientation is arbitrary)')
    code.append(f'# In-plane right  x_dir = ({fmt(x_dir[0])}, {fmt(x_dir[1])}, {fmt(x_dir[2])})')
    code.append('# Built in default Plane.XY (local frame); a final transform places the')
    code.append('# blade back into the source-mesh world frame. Drop that transform to use')
    code.append('# the blade as a clean, axis-aligned local-frame component.')
    code.append('')
    code.append('from build123d import Axis, Plane, Vector')
    code.append('from sava.csg.build123d.common.pencil import Pencil')
    code.append('from sava.csg.build123d.common.smartbox import SmartBox')
    code.append('from sava.csg.build123d.common.smartercone import SmarterCone')
    code.append('from sava.csg.build123d.common.smartsolid import SmartSolid')
    code.append('')

    # Collect polygon loops only (circular/box loops emit as primitives, which
    # don't benefit from a shared-anchor vertex) and pick a globally-shared
    # start vertex to anchor every Pencil to the same point.
    emit_polys: list[list[Point2D]] = []
    if front is not None:
        emit_polys.extend(_polygon_loops(front.loops, front.circles, front.boxes))
    for L in layers:
        if L.name in ('front', 'back'):
            continue
        emit_polys.extend(_polygon_loops(L.loops, L.circles, L.boxes))
    preferred_start = find_shared_start(emit_polys)

    body_silhouette: list[Point2D] | None = None
    if front is not None:
        parents = _classify_loops(front.loops)
        outers = [i for i, p in enumerate(parents) if p == -1]
        if outers:
            o0 = outers[0]
            body_silhouette = front.loops[o0]
            body_circle = front.circles[o0]
            children_of_o0 = sum(1 for p in parents if p == o0)
            if body_circle is not None:
                radius, (bcx, bcy) = body_circle
                descriptor = f'circular front-cap silhouette, r={fmt(radius)}'
                code.append(f'# Main body ({descriptor})')
                code.append(f'body = SmarterCone.cylinder({fmt(radius)}, {fmt(body_thickness)})')
                if abs(bcx) > 1e-9 or abs(bcy) > 1e-9:
                    code.append(f'body.move({fmt(bcx)}, {fmt(bcy)}, 0)')
                code.append('blade = body')
                cylinders.append(CylinderFeature(
                    axis=Vector(*z_dir), radius=radius, height=body_thickness,
                    area=math.pi * radius * radius,
                    base=(bcx, bcy, 0.0), layer_name='body',
                ))
            else:
                descriptor = (f'front-cap silhouette, the {len(front.loops[o0])}-gon'
                              if children_of_o0 == 0 and len(outers) == 1
                              else f'front-cap outer silhouette, '
                                   f'the {len(front.loops[o0])}-gon outline')
                code.append(f'# Main body ({descriptor})')
                # Emit the first outer manually as the blade initializer; its
                # children + any extra outers are then emitted by the recursive
                # walker with skip_outer_emit set so we don't re-emit o0 itself.
                code.extend(emit_pencil_for(front.loops[o0], 'body', preferred_start))
                code.append(f'blade = body.extrude({fmt(body_thickness)})')
            _emit_nested_loops(
                code, front.loops, front.circles, front.boxes, parents,
                thickness=body_thickness, shift_z=0.0,
                op_outer='fuse', op_hole='cut',
                base_name='body', blade_var='blade',
                preferred_start=preferred_start,
                z_dir=z_dir, cylinders_out=cylinders, boxes_out=boxes_out,
                skip_outer_emit=o0,
                raw_loops=front.raw_loops,
            )
            code.append('')

    for L in layers:
        if L.name in ('front', 'back'):
            continue
        cap_thickness = abs(L.depth - (body_min_depth if L.name == 'back_protrusion' else body_max_depth))
        # Pockets can open from either body face; pick the closer end and cut
        # only that distance. The previous "always cut from body_max_depth"
        # assumption produced wrong geometry for back-opening pockets.
        if L.name == 'pocket':
            dist_to_min = L.depth - body_min_depth
            dist_to_max = body_max_depth - L.depth
            cap_thickness = min(dist_to_min, dist_to_max)
            pocket_opens_from_min = dist_to_min <= dist_to_max
        if L.name == 'back_protrusion':
            thickness = cap_thickness
            shift_z = -cap_thickness
            comment_head = (f'# Back protrusion (depth {fmt(L.depth)} → '
                            f'{fmt(body_min_depth)}, {fmt(cap_thickness)} mm), fused below the body')
            op_outer = 'fuse'
            op_hole = 'cut'
        elif L.name == 'front_protrusion':
            # Per-loop classification: polygon loops whose silhouettes extend
            # outside the body's z=0 silhouette get extruded full-height (from
            # body_min_depth up to the layer) so they have proper support down
            # to the floor instead of floating as caps over open air. Cylinder
            # and box loops (e.g. annular rings co-axial with the body) stay
            # as thin caps regardless — extending them would fill back cuts
            # made by pocket layers below.
            cap_shift = body_thickness
            full_thickness = L.depth - body_min_depth
            full_shift = 0.0
            sub_parents = _classify_loops(L.loops)
            n_loops = len(L.loops)
            cls: list[bool | None] = [None] * n_loops
            for i in range(n_loops):
                if sub_parents[i] == -1:
                    if L.circles[i] is not None or L.boxes[i] is not None:
                        cls[i] = False
                    elif body_silhouette is None:
                        cls[i] = False
                    else:
                        cls[i] = any(
                            not _point_in_polygon(v, body_silhouette)
                            for v in L.loops[i]
                        )
            # Propagate classification from each outer to its descendants so
            # holes inside an outside-body tab inherit the tab's full-height
            # treatment (avoids breaking parent-child topology in the emit).
            changed = True
            while changed:
                changed = False
                for i in range(n_loops):
                    if cls[i] is None and cls[sub_parents[i]] is not None:
                        cls[i] = cls[sub_parents[i]]
                        changed = True
            thickness = [full_thickness if cls[i] else cap_thickness for i in range(n_loops)]
            shift_z = [full_shift if cls[i] else cap_shift for i in range(n_loops)]
            n_full = sum(1 for c in cls if c)
            n_cap = n_loops - n_full
            if n_full and n_cap:
                comment_head = (f'# Front protrusion ({n_cap} cap loop(s) at '
                                f'depth {fmt(body_max_depth)} → {fmt(L.depth)}, '
                                f'{n_full} full-height loop(s) at '
                                f'depth {fmt(body_min_depth)} → {fmt(L.depth)}), fused')
            elif n_full:
                comment_head = (f'# Front protrusion (depth {fmt(body_min_depth)} → '
                                f'{fmt(L.depth)}, {fmt(full_thickness)} mm full-height '
                                f'— silhouette extends outside body), fused')
            else:
                comment_head = (f'# Front protrusion (depth {fmt(body_max_depth)} → '
                                f'{fmt(L.depth)}, {fmt(cap_thickness)} mm), fused above the body')
            op_outer = 'fuse'
            op_hole = 'cut'
        else:  # pocket
            thickness = cap_thickness
            if pocket_opens_from_min:
                shift_z = 0.0
                comment_head = (f'# Pocket at local z=0 ({fmt(cap_thickness)} mm deep), '
                                f'cut from body (opens at back face)')
            else:
                shift_z = L.depth - body_min_depth
                comment_head = (f'# Pocket at local z={fmt(shift_z)} ({fmt(cap_thickness)} mm deep), '
                                f'cut from body (opens at front face)')
            op_outer = 'cut'
            op_hole = 'fuse'

        parents = _classify_loops(L.loops)
        code.append(comment_head)
        _emit_nested_loops(
            code, L.loops, L.circles, L.boxes, parents,
            thickness=thickness, shift_z=shift_z,
            op_outer=op_outer, op_hole=op_hole,
            base_name=L.name, blade_var='blade',
            preferred_start=preferred_start,
            z_dir=z_dir, cylinders_out=cylinders, boxes_out=boxes_out,
            raw_loops=L.raw_loops,
        )
        code.append('')

    code.append('# Place the blade into the source-mesh world frame.')
    code.append('# Delete if object orientation and position are irrelevant.')
    code.append(
        f'cross_section = Plane('
        f'origin=Vector({fmt(cross_origin[0])}, {fmt(cross_origin[1])}, {fmt(cross_origin[2])}), '
        f'x_dir=Vector({fmt(x_dir[0])}, {fmt(x_dir[1])}, {fmt(x_dir[2])}), '
        f'z_dir=Vector({fmt(z_dir[0])}, {fmt(z_dir[1])}, {fmt(z_dir[2])}))'
    )
    # blade.solid may be a single Solid or a ShapeList (when nested cut/fuse
    # ops produced disconnected pieces — e.g. an island in a through-hole).
    # SmartSolid's variadic constructor fuses all parts back into one shape.
    code.append('_parts = list(blade.solid) if hasattr(blade.solid, \'__iter__\') else [blade.solid]')
    code.append('blade = SmartSolid(*(cross_section * s for s in _parts), label=\'blade\')')
    return '\n'.join(code).rstrip() + '\n'
