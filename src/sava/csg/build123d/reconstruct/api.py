import math
from collections import defaultdict
from dataclasses import dataclass, field

from build123d import Vector

from ._vec import Vec, vadd, vcross, vdot, vmul, vnorm
from .boundary import boundary_polygons, simplify_collinear
from .datum import build_datum_frame, make_frame, pick_datum, shift_origin_to_first_quadrant, to_local
from .extrusion import cap_depth_in_frame, classify_planes_vs_axis, pick_axis
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

    extrusion_axis = pick_axis(sig)
    buckets = classify_planes_vs_axis(sig, extrusion_axis)
    if buckets.other:
        return ReconstructionResult(
            is_2d5_extrudable=False,
            extrusion_axis=Vector(*extrusion_axis),
            error=f'Found {len(buckets.other)} tilted plane(s); part is not 2.5D-extrudable',
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

    new_silhouettes: list[tuple[PlaneCluster, list[list[Point2D]]]] = []
    for plane, _old in silhouettes:
        rings3d = boundary_polygons(verts, faces, plane.tris)
        rings3d = _filter_noise_step_loops(rings3d, plane.normal, plane.d)
        raw2d = [[to_local(pt, new_origin, x_dir, y_dir) for pt in ring3d] for ring3d in rings3d]
        raw2d = _deduplicate_loops(_filter_noise_loops(raw2d))
        loops_new: list[list[Point2D]] = []
        for poly_new in raw2d:
            poly_new = simplify_collinear(poly_new)
            if len(poly_new) >= 3:
                loops_new.append(poly_new)
        new_silhouettes.append((plane, loops_new))

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
    for plane, _ in new_silhouettes:
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
              depth=cap_depth_in_frame(p, z_dir, new_origin), loops=loops)
        for p, loops in new_silhouettes
    ]

    # Detect a single cylinder via the front_protrusion layer when it's a single
    # simple loop (presumed circular). The cylinder REPLACES the polygon emit
    # for that layer. Multi-loop fp layers (e.g. annular rings) skip this and
    # fall through to the generic outer-minus-holes emit below.
    fp_layer = next((L for L in layers if L.name == 'front_protrusion'), None)
    cyl_layer_names: set[str] = set()
    cylinder_data: dict | None = None
    if fp_layer is not None and len(fp_layer.loops) == 1:
        radius = math.sqrt(fp_layer.plane.area / math.pi)
        height = fp_layer.depth - body_max_depth
        cu, cv = _polygon_centroid(fp_layer.loops[0])
        # Base sits on the body's front face: z = body_thickness in local coords.
        cz_base = body_max_depth - body_min_depth
        cylinder_data = dict(radius=radius, height=height, area=fp_layer.plane.area,
                             cu=cu, cv=cv, cz=cz_base, layer_name='front_protrusion')
        cyl_layer_names.add('front_protrusion')

    # Anchor the cross-section origin on the vertex shared by the most emit-eligible
    # shapes. With that vertex at local (0, 0), every Pencil can drop `start=`.
    # Emit-eligible means polygons that will actually be drawn — front (= body) and
    # any non-cylinder protrusion / pocket. (`back` is implicit in the body extrude;
    # `front_protrusion` is replaced by the Cylinder primitive.)
    emit_polys: list[list[Point2D]] = []
    for L in layers:
        if L.name == 'back' or L.name in cyl_layer_names:
            continue
        emit_polys.extend(L.loops)
    shared_uv = find_shared_start(emit_polys)
    if shared_uv is not None:
        su, sv = shared_uv
        new_origin = vadd(new_origin, vadd(vmul(x_dir, su), vmul(y_dir, sv)))
        for L in layers:
            L.loops = [[(u - su, v - sv) for u, v in loop] for loop in L.loops]
        if cylinder_data is not None:
            cylinder_data['cu'] -= su
            cylinder_data['cv'] -= sv

    # Anchor cross-section origin at body_min_depth so that:
    #   body extrudes from local z=0 (back cap) to z=body_thickness (front cap).
    cross_origin = vadd(new_origin, vmul(z_dir, body_min_depth))

    cylinders: list[CylinderFeature] = []
    if cylinder_data is not None:
        cylinders.append(CylinderFeature(
            axis=Vector(*z_dir),
            radius=cylinder_data['radius'],
            height=cylinder_data['height'],
            area=cylinder_data['area'],
            base=(cylinder_data['cu'], cylinder_data['cv'], cylinder_data['cz']),
            layer_name=cylinder_data['layer_name'],
        ))

    code = _emit_code(cross_origin, x_dir, y_dir, z_dir, datum_plane,
                      datum_contact_area, layers, cylinders,
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
    parents: list[int],
    *,
    thickness: float,
    shift_z: float,
    op_outer: str,
    op_hole: str,
    base_name: str,
    blade_var: str,
    preferred_start: Point2D | None,
    skip_outer_emit: int | None = None,
) -> None:
    """Walk the nesting tree depth-first; emit each loop with alternating op.

    op_outer applies at even depths (0, 2, ...), op_hole at odd depths (1, 3, ...).
    Each loop is extruded `thickness` mm and moved `shift_z` in local z, then
    combined into `blade_var` via .fuse/.cut.

    `skip_outer_emit` is the loop index whose own emit should be skipped (used
    for the body's first outer which is already emitted as the blade initializer);
    its children are still walked.
    """
    children_of: dict[int, list[int]] = defaultdict(list)
    for i, p in enumerate(parents):
        if p != -1:
            children_of[p].append(i)
    outers = [i for i, p in enumerate(parents) if p == -1]

    sibling_counter: dict[tuple[int, int], int] = {}

    def visit(idx: int, depth: int, parent_name: str | None) -> None:
        if depth == 0:
            name = base_name if len(outers) == 1 else f'{base_name}_{outers.index(idx)}'
        else:
            role = _depth_role_name(depth)
            key = (parents[idx], depth)
            n = sibling_counter.get(key, 0)
            sibling_counter[key] = n + 1
            name = f'{parent_name}_{role}_{n}'
        op = op_outer if depth % 2 == 0 else op_hole

        if idx != skip_outer_emit:
            code.extend(emit_pencil_for(loops[idx], name, preferred_start))
            code.append(f'{name}_body = {name}.extrude({fmt(thickness)})')
            if abs(shift_z) > 1e-9:
                code.append(f'{name}_body.move(0, 0, {fmt(shift_z)})')
            code.append(f'{blade_var}.{op}({name}_body)')

        for ch in children_of[idx]:
            visit(ch, depth + 1, name)

    for o_idx in outers:
        visit(o_idx, 0, None)


def _emit_code(cross_origin: Vec, x_dir: Vec, y_dir: Vec, z_dir: Vec,
               datum_plane: PlaneCluster | None, datum_total: float,
               layers: list[Layer], cylinders: list[CylinderFeature],
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
    code.append('from build123d import Plane, Vector')
    code.append('from sava.csg.build123d.common.pencil import Pencil')
    code.append('from sava.csg.build123d.common.smartercone import SmarterCone')
    code.append('from sava.csg.build123d.common.smartsolid import SmartSolid')
    code.append('')

    # Cylinder-replaced layer names (skip their polygon emit).
    cyl_layer_names = {c.layer_name for c in cylinders if c.layer_name}

    # Collect every loop that will actually be emitted so we can pick a
    # globally-shared start vertex (anchors all shapes to the same point).
    emit_polys: list[list[Point2D]] = []
    if front is not None:
        emit_polys.extend(front.loops)
    for L in layers:
        if L.name in ('front', 'back') or L.name in cyl_layer_names:
            continue
        emit_polys.extend(L.loops)
    preferred_start = find_shared_start(emit_polys)

    if front is not None:
        parents = _classify_loops(front.loops)
        outers = [i for i, p in enumerate(parents) if p == -1]
        if outers:
            o0 = outers[0]
            children_of_o0 = sum(1 for p in parents if p == o0)
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
                code, front.loops, parents,
                thickness=body_thickness, shift_z=0.0,
                op_outer='fuse', op_hole='cut',
                base_name='body', blade_var='blade',
                preferred_start=preferred_start,
                skip_outer_emit=o0,
            )
            code.append('')

    for L in layers:
        if L.name in ('front', 'back'):
            continue
        if L.name in cyl_layer_names:
            continue
        thickness = abs(L.depth - (body_min_depth if L.name == 'back_protrusion' else body_max_depth))
        if L.name == 'back_protrusion':
            shift_z = -thickness
            comment_head = (f'# Back protrusion (depth {fmt(L.depth)} → '
                            f'{fmt(body_min_depth)}, {fmt(thickness)} mm), fused below the body')
            op_outer = 'fuse'
            op_hole = 'cut'
        elif L.name == 'front_protrusion':
            shift_z = body_thickness
            comment_head = (f'# Front protrusion (depth {fmt(body_max_depth)} → '
                            f'{fmt(L.depth)}, {fmt(thickness)} mm), fused above the body')
            op_outer = 'fuse'
            op_hole = 'cut'
        else:  # pocket
            shift_z = L.depth - body_min_depth
            comment_head = (f'# Pocket at local z={fmt(shift_z)} ({fmt(thickness)} mm deep), '
                            f'cut from body')
            op_outer = 'cut'
            op_hole = 'fuse'

        parents = _classify_loops(L.loops)
        code.append(comment_head)
        _emit_nested_loops(
            code, L.loops, parents,
            thickness=thickness, shift_z=shift_z,
            op_outer=op_outer, op_hole=op_hole,
            base_name=L.name, blade_var='blade',
            preferred_start=preferred_start,
        )
        code.append('')

    for i, c in enumerate(cylinders):
        suffix = '' if len(cylinders) == 1 else f'_{i}'
        cu, cv, cz = c.base
        code.append(f'# Cylinder (r={fmt(c.radius)}, h={fmt(c.height)}, area={fmt(c.area, 2)} mm²)')
        code.append('# Oriented along the extrusion axis, positioned at the layer centroid.')
        code.append(f'pivot_pin{suffix} = SmarterCone.cylinder('
                    f'{fmt(c.radius)}, {fmt(c.height)})')
        code.append(f'pivot_pin{suffix}.move({fmt(cu)}, {fmt(cv)}, {fmt(cz)})')
        code.append(f'blade.fuse(pivot_pin{suffix})')
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
