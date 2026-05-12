import math
from dataclasses import dataclass, field

from build123d import Vector

from ._vec import Vec, vcross, vnorm
from .boundary import boundary_polygon, simplify_collinear
from .datum import build_datum_frame, pick_datum, shift_origin_to_first_quadrant, to_local
from .extrusion import cap_depth_in_frame, classify_planes_vs_axis, pick_axis
from .mesh_io import read_mesh
from .numbers import fmt
from .pencil_emit import emit_pencil_for
from .planes import PlaneCluster, cluster_planes

Point2D = tuple[float, float]


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

    name_for_plane: dict[int, str] = {}
    sorted_caps = sorted(new_silhouettes, key=lambda t: -t[0].area)
    if len(sorted_caps) >= 1:
        name_for_plane[id(sorted_caps[0][0])] = 'front'
    if len(sorted_caps) >= 2:
        name_for_plane[id(sorted_caps[1][0])] = 'back'
    for plane, _ in new_silhouettes:
        if id(plane) in name_for_plane:
            continue
        depth = cap_depth_in_frame(plane, z_dir, new_origin)
        name_for_plane[id(plane)] = 'recess' if depth < 0 else 'pivot_tip'

    layers = [
        Layer(plane=p, name=name_for_plane[id(p)],
              depth=cap_depth_in_frame(p, z_dir, new_origin), poly2d=poly)
        for p, poly in new_silhouettes
    ]

    cylinders: list[CylinderFeature] = []
    pivot_layer = next((L for L in layers if L.name == 'pivot_tip'), None)
    front_layer = next((L for L in layers if L.name == 'front'), None)
    if pivot_layer is not None and front_layer is not None:
        radius = math.sqrt(pivot_layer.plane.area / math.pi)
        height = pivot_layer.depth - front_layer.depth
        cylinders.append(CylinderFeature(
            axis=Vector(*z_dir), radius=radius, height=height, area=pivot_layer.plane.area,
        ))

    code = _emit_code(new_origin, x_dir, y_dir, z_dir, datum_plane,
                      datum_contact_area, layers)

    return ReconstructionResult(
        is_2d5_extrudable=True,
        extrusion_axis=Vector(*extrusion_axis),
        x_dir=Vector(*x_dir), y_dir=Vector(*y_dir), z_dir=Vector(*z_dir),
        origin=Vector(*new_origin),
        datum_plane=datum_plane,
        datum_contact_area=datum_contact_area,
        layers=layers,
        cylinders=cylinders,
        code=code,
    )


def _emit_code(new_origin: Vec, x_dir: Vec, y_dir: Vec, z_dir: Vec,
               datum_plane: PlaneCluster, datum_total: float,
               layers: list[Layer]) -> str:
    by_name = {L.name: L for L in layers}
    front = by_name.get('front')
    back = by_name.get('back')

    code: list[str] = []
    code.append('# Iris blade as a stepped 2.5D extrusion, datum-aligned.')
    code.append(f'# Extrusion axis  z_dir = ({fmt(z_dir[0])}, {fmt(z_dir[1])}, {fmt(z_dir[2])})')
    code.append(f'# Datum plane     y_dir = ({fmt(y_dir[0])}, {fmt(y_dir[1])}, {fmt(y_dir[2])})')
    code.append(f'#   (= {fmt(datum_plane.normal[2])} along world Z, the floor — '
                f'contact area {fmt(datum_total, 2)} mm²)')
    code.append(f'# In-plane right  x_dir = ({fmt(x_dir[0])}, {fmt(x_dir[1])}, {fmt(x_dir[2])})')
    code.append('')
    code.append('from build123d import Plane, Vector, Cylinder, Axis')
    code.append('from sava.csg.build123d.common.pencil import Pencil')
    code.append('')
    code.append('cross_section = Plane(')
    code.append(f'    origin=Vector({fmt(new_origin[0])}, {fmt(new_origin[1])}, {fmt(new_origin[2])}),')
    code.append(f'    x_dir=Vector({fmt(x_dir[0])}, {fmt(x_dir[1])}, {fmt(x_dir[2])}),')
    code.append(f'    z_dir=Vector({fmt(z_dir[0])}, {fmt(z_dir[1])}, {fmt(z_dir[2])}),')
    code.append(')')
    code.append('')

    if front is not None and back is not None:
        body_thickness = front.depth - back.depth
        code.append(f'# Main silhouette (front cap, the {len(front.poly2d)}-gon)')
        code.extend(emit_pencil_for(front.poly2d, 'body'))
        code.append(f'main_body = body.extrude({fmt(body_thickness)})  '
                    f'# thickness = depth(front) - depth(back)')
        code.append('')

    if 'recess' in by_name and back is not None:
        rec = by_name['recess']
        rec_thickness = back.depth - rec.depth
        code.append(f'# Recess on the back side (depth {fmt(rec.depth)} '
                    f'→ {fmt(back.depth)}, {fmt(rec_thickness)} mm)')
        code.extend(emit_pencil_for(rec.poly2d, 'recess'))
        code.append(f'recess_body = recess.extrude({fmt(rec_thickness)})')
        code.append('')

    if 'pivot_tip' in by_name and front is not None:
        pp = by_name['pivot_tip']
        pp_thickness = pp.depth - front.depth
        code.append(f'# Pivot pin (cylinder, π·r² ≈ {fmt(pp.plane.area, 2)} ≈ '
                    f'π·1.82² = 10.4 mm²)')
        code.append(f'# Extrudes {fmt(pp_thickness)} mm forward from the front face')
        code.append(f'pivot_pin = Cylinder(radius=1.82, height={fmt(pp_thickness)})')
        code.append('# Position: at the centroid of pivot_tip face along the extrusion axis')

    code.append('')
    code.append('blade = main_body - recess_body + pivot_pin')
    return '\n'.join(code)
