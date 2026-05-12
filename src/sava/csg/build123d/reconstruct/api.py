import math
from dataclasses import dataclass, field

from build123d import Vector

from ._vec import Vec, vadd, vcross, vmul, vnorm
from .boundary import boundary_polygon, simplify_collinear
from .datum import build_datum_frame, pick_datum, shift_origin_to_first_quadrant, to_local
from .extrusion import cap_depth_in_frame, classify_planes_vs_axis, pick_axis
from .mesh_io import read_mesh
from .numbers import fmt
from .pencil_emit import Point2D, emit_pencil_for, find_shared_start
from .planes import PlaneCluster, cluster_planes


@dataclass
class Layer:
    plane: PlaneCluster
    name: str
    depth: float
    poly2d: list[Point2D]


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

    silhouettes: list[tuple[PlaneCluster, list[Point2D]]] = []
    for p in cap_planes:
        ring3d = boundary_polygon(verts, faces, p.tris)
        if not ring3d:
            continue
        poly2d = [to_local(pt, origin3, ex0, ey0) for pt in ring3d]
        poly2d = simplify_collinear(poly2d)
        silhouettes.append((p, poly2d))

    datum_plane = pick_datum(side_planes)
    datum_contact_area = datum_plane.area

    x_dir, y_dir, z_dir = build_datum_frame(
        extrusion_axis, datum_plane, silhouettes, origin3, ex0, ey0,
    )
    new_origin = shift_origin_to_first_quadrant(verts, faces, cap_planes, x_dir, y_dir)

    new_silhouettes: list[tuple[PlaneCluster, list[Point2D]]] = []
    for plane, _old in silhouettes:
        ring3d = boundary_polygon(verts, faces, plane.tris)
        poly_new = [to_local(pt, new_origin, x_dir, y_dir) for pt in ring3d]
        poly_new = simplify_collinear(poly_new)
        new_silhouettes.append((plane, poly_new))

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
              depth=cap_depth_in_frame(p, z_dir, new_origin), poly2d=poly)
        for p, poly in new_silhouettes
    ]

    # Detect a single cylinder via the front_protrusion layer (if its silhouette
    # is roughly circular). The cylinder REPLACES the polygon emit for that layer.
    fp_layer = next((L for L in layers if L.name == 'front_protrusion'), None)
    cyl_layer_names: set[str] = set()
    cylinder_data: dict | None = None
    if fp_layer is not None:
        radius = math.sqrt(fp_layer.plane.area / math.pi)
        height = fp_layer.depth - body_max_depth
        cu, cv = _polygon_centroid(fp_layer.poly2d)
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
    emit_polys: list[Point2D] = []
    for L in layers:
        if L.name == 'back' or L.name in cyl_layer_names:
            continue
        emit_polys.append(L.poly2d)
    shared_uv = find_shared_start(emit_polys)
    if shared_uv is not None:
        su, sv = shared_uv
        new_origin = vadd(new_origin, vadd(vmul(x_dir, su), vmul(y_dir, sv)))
        for L in layers:
            L.poly2d = [(u - su, v - sv) for u, v in L.poly2d]
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


def _emit_code(cross_origin: Vec, x_dir: Vec, y_dir: Vec, z_dir: Vec,
               datum_plane: PlaneCluster, datum_total: float,
               layers: list[Layer], cylinders: list[CylinderFeature],
               body_min_depth: float, body_max_depth: float) -> str:
    body_thickness = body_max_depth - body_min_depth
    by_name = {L.name: L for L in layers}
    front = by_name.get('front')

    code: list[str] = []
    code.append('# Iris blade as a stepped 2.5D extrusion, datum-aligned.')
    code.append(f'# Extrusion axis  z_dir = ({fmt(z_dir[0])}, {fmt(z_dir[1])}, {fmt(z_dir[2])})')
    code.append(f'# Datum plane     y_dir = ({fmt(y_dir[0])}, {fmt(y_dir[1])}, {fmt(y_dir[2])})')
    code.append(f'#   (= {fmt(datum_plane.normal[2])} along world Z, the floor — '
                f'contact area {fmt(datum_total, 2)} mm²)')
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

    # Collect every polygon that will actually be emitted so we can pick a
    # globally-shared start vertex (anchors all shapes to the same point).
    emit_polys: list[list[Point2D]] = []
    if front is not None:
        emit_polys.append(front.poly2d)
    for L in layers:
        if L.name in ('front', 'back') or L.name in cyl_layer_names:
            continue
        emit_polys.append(L.poly2d)
    preferred_start = find_shared_start(emit_polys)

    if front is not None:
        code.append(f'# Main body (front-cap silhouette, the {len(front.poly2d)}-gon)')
        code.extend(emit_pencil_for(front.poly2d, 'body', preferred_start))
        code.append(f'blade = body.extrude({fmt(body_thickness)})')
        code.append('')

    for L in layers:
        if L.name in ('front', 'back'):
            continue
        if L.name in cyl_layer_names:
            continue
        thickness = abs(L.depth - (body_min_depth if L.name == 'back_protrusion' else body_max_depth))
        if L.name == 'back_protrusion':
            shift_z = -thickness
            comment = (f'# Back protrusion (depth {fmt(L.depth)} → {fmt(body_min_depth)}, '
                       f'{fmt(thickness)} mm), fused below the body')
            op = 'fuse'
        elif L.name == 'front_protrusion':
            shift_z = body_thickness
            comment = (f'# Front protrusion (depth {fmt(body_max_depth)} → {fmt(L.depth)}, '
                       f'{fmt(thickness)} mm), fused above the body')
            op = 'fuse'
        else:  # pocket
            shift_z = L.depth - body_min_depth
            comment = (f'# Pocket at local z={fmt(shift_z)} ({fmt(thickness)} mm deep), '
                       f'cut from body')
            op = 'cut'
        var_name = L.name
        code.append(comment)
        code.extend(emit_pencil_for(L.poly2d, var_name, preferred_start))
        code.append(f'{var_name}_body = {var_name}.extrude({fmt(thickness)})')
        code.append(f'{var_name}_body.move(0, 0, {fmt(shift_z)})')
        code.append(f'blade.{op}({var_name}_body)')
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
    code.append('blade = SmartSolid(cross_section * blade.solid, label=\'blade\')')
    return '\n'.join(code).rstrip() + '\n'
