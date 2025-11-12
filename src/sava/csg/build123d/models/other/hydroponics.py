from copy import copy
from dataclasses import dataclass
from math import radians, sin, degrees, asin
from math import tan
from typing import Tuple

from build123d import Solid, Trapezoid, Circle, Plane, Location, fillet, Box, loft, extrude, Face, Sphere, revolve, Axis

from sava.csg.build123d.common.exporter import Exporter
from sava.csg.build123d.common.geometry import Alignment, Direction, create_plane
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartcone import SmartCone
from sava.csg.build123d.common.smartsolid import SmartSolid
from sava.csg.build123d.common.sweepsolid import SweepSolid


@dataclass
class PipeDimensions:
    bend_radius: float = 15
    countertop_thickness: float = 45
    intake_pipe_bend_angle: float = 40
    wall_thickness: float = 2
    diameter_inner: float = None

    @property
    def diameter_outer(self) -> float:
        return self.diameter_inner + self.wall_thickness * 2

    @property
    def radius_outer(self) -> float:
        return self.diameter_outer / 2


@dataclass
class HoseHolderDimensions:
    slope_radius = 45
    thickness = 1.2
    diameter_inner = 19

@dataclass
class HoseConnectorDimensions:
    pipe_length: float = 0
    diameter_outer: float = 18.0
    thickness: float = 1.6
    length: float = 20.0
    segment_count: int = 3
    diameter_delta: float = 1.5 # diameter gradient will be [diameter_outer - diameter_delta; diameter_outer + diameter_delta]
    distance_between_connectors: float = 10
    connector_offset_x: float = 5
    connector_offset_z: float = -5

    @property
    def diameter_inner(self) -> float:
        return self.diameter_outer - 2 * self.thickness - self.diameter_delta

    @property
    def diameter_outer_max(self) -> float:
        return self.diameter_outer + self.diameter_delta

    @property
    def distance_between_pipe_centres(self):
        return self.distance_between_connectors + self.diameter_outer_max


@dataclass
class TubeEtchesDimensions:
    thickness: float = 2.9
    outer_width: float = 7.5
    side_angle: float = 45
    fillet_radius: float = 0.5
    angle_measure: float = 50
    distance_from_top: float = 5

    padding: float = 0.1
    angle_padding: float = 0.5

    def pad_inner(self) -> 'TubeEtchesDimensions':
        return self.pad(-self.padding, -self.angle_padding)

    def pad_outer(self) -> 'TubeEtchesDimensions':
        return self.pad(self.padding, self.angle_padding)

    def pad(self, padding: float, angle_padding: float) -> 'TubeEtchesDimensions':
        padded_dimensions = copy(self)
        padded_dimensions.thickness += padding
        padded_dimensions.outer_width += padding * 2
        padded_dimensions.angle_measure += angle_padding * 2
        padded_dimensions.distance_from_top += padding
        return padded_dimensions


@dataclass
class HydroponicsDimensions:
    _etches: TubeEtchesDimensions = None

    hose: HoseConnectorDimensions = None
    hose_holder: HoseHolderDimensions = None
    pipe: PipeDimensions = None
    tube_internal_diameter: float = 142
    tube_floor_sphere_radius: float = 400
    tube_floor_angle: float = 15
    tube_floor_thickness: float = 3
    tube_wall_thickness: float = 4
    pot_wall_thickness: float = 3.1
    edge_angle: float = 45.0

    tube_height: float = 80
    support_free_angle: float = 35

    def __post_init__(self):
        self.hose = self.hose or HoseConnectorDimensions()
        self.hose_holder = self.hose_holder or HoseHolderDimensions()
        self.pipe = self.pipe or PipeDimensions()

        self._etches = self._etches or TubeEtchesDimensions()
        self.etches_inner = self._etches.pad_inner()
        self.etches_outer = self._etches.pad_outer()

        self.pipe.diameter_inner = self.hose.diameter_inner

    @property
    def support_free_angle_rad(self):
        return radians(self.support_free_angle)

    @property
    def outlet_hole_offset_z(self):
        return self.hose.connector_offset_x + self.hose_holder.diameter_inner

    @property
    def pipe_extra_distance(self) -> float:
        dim = self.pipe
        return dim.bend_radius / tan(radians(dim.intake_pipe_bend_angle)) + dim.radius_outer / tan(radians(dim.intake_pipe_bend_angle)) + self.pot_wall_thickness / sin(radians(dim.intake_pipe_bend_angle)) * 2.5


class Hydroponics:
    def __init__(self, dim: HydroponicsDimensions):
        self.dim = dim

    def create_stand(self) -> SmartSolid:
        tube = SmartSolid(Solid.make_cylinder(self.dim.tube_internal_diameter / 2 + self.dim.tube_wall_thickness, self.dim.tube_height))

        tube_inside = SmartSolid(Solid.make_cylinder(self.dim.tube_internal_diameter / 2, self.dim.tube_height))
        top_cut = self.create_side_cut_angle().align_zxy(tube, Alignment.RL)

        handles = self.create_handles(tube)
        etches = self.create_etches(tube)

        inlet_connector_bottom = self.create_connector_bottom(tube, Direction.S)
        inlet_pipe_inner, inlet_pipe_outer = self.create_pipe(inlet_connector_bottom)
        inlet_connector_top = self.create_inlet_connector_top(inlet_pipe_outer)

        outlet_connector_bottom = self.create_connector_bottom(tube, Direction.N)
        outlet_pipe_inner, outlet_pipe_outer = self.create_pipe(outlet_connector_bottom)

        pipe_cover = self.create_pipe_cover(inlet_pipe_outer, outlet_pipe_outer, tube)
        outlet_hole = self.create_outlet_hole(outlet_pipe_inner)

        surface = self.create_magic_surface(tube, tube_inside, outlet_pipe_outer, pipe_cover, outlet_hole)

        tube.cut(top_cut)
        tube.fuse(pipe_cover, outlet_pipe_outer)
        tube.cut(tube_inside, outlet_hole)
        tube.fuse(surface, handles, etches, inlet_pipe_outer, inlet_connector_top, inlet_connector_bottom, outlet_connector_bottom)
        tube.cut(inlet_pipe_inner, outlet_pipe_inner)

        return tube

    def create_spheres(self, outlet_connector_bottom: SmartSolid) -> Tuple[SmartSolid, SmartSolid]:
        sphere_outer = SmartSolid(Sphere(self.dim.tube_floor_sphere_radius))
        sphere_outer.align_zxy(outlet_connector_bottom, Alignment.RR, - self.dim.hose.connector_offset_z)
        sphere_inner = SmartSolid(Sphere(self.dim.tube_floor_sphere_radius - self.dim.tube_floor_thickness))
        sphere_inner.align(sphere_outer)

        return sphere_outer, sphere_inner

    def create_pipe_cover_face_middle(self, pipe: SweepSolid) -> Face:
        pencil = Pencil(plane=pipe.create_path_plane())
        pencil.arc_with_radius(self.dim.pipe.bend_radius + self.dim.pipe.radius_outer, -90, -self.dim.pipe.intake_pipe_bend_angle)
        pencil.draw(self.dim.pipe_extra_distance, -self.dim.pipe.intake_pipe_bend_angle)
        pencil.down(pencil.location.Y)
        return pencil.create_face()

    def create_pipe_cover_face_wider(self, pipe: SweepSolid, shift_z: float = 0, offset_z: float = 0, skip_height: float = 0) -> Face:
        skip_angle = degrees(asin(skip_height / self.dim.pipe.bend_radius))
        pencil = Pencil((0, 0, shift_z), pipe.create_path_plane())
        pencil.arc_with_radius(self.dim.pipe.bend_radius, -90 - skip_angle, -self.dim.pipe.intake_pipe_bend_angle + skip_angle)
        pencil.draw(self.dim.pipe_extra_distance, -self.dim.pipe.intake_pipe_bend_angle)
        pencil.down(pencil.location.Y - offset_z)
        return pencil.create_face()

    def create_pipe_cover(self, inlet_pipe_outer: SweepSolid, outlet_pipe_outer: SweepSolid, tube: SmartSolid) -> SmartSolid:
        face1 = self.create_pipe_cover_face_middle(inlet_pipe_outer)
        face2 = self.create_pipe_cover_face_middle(outlet_pipe_outer)
        middle_part = SmartSolid(loft([face1, face2]))

        middle_part.align_x(outlet_pipe_outer, Alignment.LR)
        middle_part.align_z(outlet_pipe_outer, Alignment.RL)
        middle_part.align_y(inlet_pipe_outer, Alignment.CR)

        face1 = self.create_pipe_cover_face_wider(inlet_pipe_outer, self.dim.pipe.radius_outer)
        face2 = self.create_pipe_cover_face_wider(outlet_pipe_outer, -self.dim.pipe.radius_outer)
        wider_part = SmartSolid(loft([face1, face2]))

        wider_part.align_x(middle_part, Alignment.LR, self.dim.pipe.radius_outer)
        wider_part.align_z(middle_part, Alignment.LR)
        wider_part.align_y(inlet_pipe_outer, Alignment.LR)

        return wider_part.fuse(middle_part).intersect(tube.scaled(2, 2, 1))

    def create_inlet_connector_top(self, inlet_pipe_outer: SweepSolid) -> SmartSolid:
        connector_top = self.create_hose_connector(3)

        plane = inlet_pipe_outer.create_plane_end()

        connector_top.solid.location = Location(plane)
        connector_top.rotate((180, 0, 0), plane)
        connector_top.align_z(inlet_pipe_outer, Alignment.RR, 0, plane)

        return connector_top

    def create_pipe(self, inlet_connector_bottom: SmartSolid) -> tuple[SweepSolid, SweepSolid]:
        dim = self.dim.pipe

        plane = create_plane((0, 0, 0), (-inlet_connector_bottom.x_mid, -inlet_connector_bottom.y_mid, 0), (0, 0, 1))

        path = Pencil(plane=plane)
        path.arc_with_radius(dim.bend_radius, -90, -dim.intake_pipe_bend_angle)
        path.draw(self.dim.pipe_extra_distance, -dim.intake_pipe_bend_angle)
        wire = path.create_wire(False)

        inlet_pipe_outer = SweepSolid(Circle(dim.radius_outer), wire, plane)

        inlet_pipe_outer.align_x(inlet_connector_bottom, Alignment.CR, -dim.radius_outer, plane)
        inlet_pipe_outer.align_z(inlet_connector_bottom, Alignment.RR)

        inlet_pipe_inner = SweepSolid(Circle(dim.diameter_inner / 2), wire, plane)
        inlet_pipe_inner.solid.position = inlet_pipe_outer.solid.position

        return inlet_pipe_inner, inlet_pipe_outer

    def create_connector_bottom(self, tube: SmartSolid, direction: Direction) -> SmartSolid:
        assert direction in [Direction.S, Direction.N]
        inlet_connector_bottom = self.create_hose_connector(self.dim.hose.pipe_length)
        inlet_connector_bottom.align_z(tube, Alignment.LL, self.dim.hose.connector_offset_z)
        inlet_connector_bottom.align_x(tube, Alignment.LL, -self.dim.hose.connector_offset_x)
        inlet_connector_bottom.align_y(tube, Alignment.C, self.dim.hose.distance_between_pipe_centres / 2 * (1 if direction == Direction.N else -1))
        return inlet_connector_bottom

    def create_etches(self, tube: SmartSolid):
        trapezoid = Trapezoid(self.dim.etches_inner.outer_width, self.dim.etches_inner.thickness, self.dim.etches_inner.side_angle)

        # Fillet two vertices facing inside the tube
        internal_vertices = sorted(trapezoid.vertices(), key=lambda v: v.Y)[-2:]
        trapezoid = fillet(internal_vertices, self.dim.etches_inner.fillet_radius)
        
        trapezoid.orientation = (90, 0, -90)
        trapezoid.position = ((self.dim.etches_inner.thickness - self.dim.tube_internal_diameter) / 2, 0, 0)

        single_edge = SmartSolid(revolve(trapezoid, Axis.Z, self.dim.etches_inner.angle_measure))
        etches = SmartSolid(single_edge.oriented((0, 0, i * 120 + 60 - self.dim.etches_inner.angle_measure / 2)) for i in range(3))

        return etches.align_z(tube, Alignment.RL, -self.dim.etches_inner.distance_from_top)


    def create_side_cut_height(self, bottom_radius: float = None, top_radius: float = None, height: float = None) -> SmartSolid:
        bottom = Circle(bottom_radius)
        top = Circle(top_radius).move(Location((0, 0, height)))

        return SmartSolid(loft([bottom, top]))

    def create_side_cut_angle(self, bottom_radius: float = None, top_radius: float = None, angle: float = None) -> SmartSolid:
        bottom_radius = self.dim.tube_internal_diameter / 2 if bottom_radius is None else bottom_radius
        top_radius = self.dim.tube_internal_diameter / 2 + self.dim.tube_wall_thickness if top_radius is None else top_radius
        angle = self.dim.etches_inner.side_angle if angle is None else angle

        height = (top_radius - bottom_radius) / tan(radians(angle))
        return self.create_side_cut_height(bottom_radius, top_radius, height)

    def create_handles(self, tube: SmartSolid):
        shapes = []
        for i in range(6):
            box = Box(self.dim.tube_internal_diameter + self.dim.tube_wall_thickness * 3, self.dim.tube_wall_thickness, self.dim.tube_height)
            box.orientation = (0, 0, i * 30)
            shapes.append(box)

        return SmartSolid(shapes).align(tube).cut(tube)

    def create_hose_connector(self, pipe_length: float = None, pipe_diameter: float = None):
        dim = self.dim.hose
        pipe_diameter_actual = pipe_diameter or self.dim.pipe.diameter_outer

        result = None

        segment_length = dim.length / dim.segment_count
        last_segment = None
        for i in range(dim.segment_count):
            diameter_min = dim.diameter_outer - dim.diameter_delta * (1 - i / (dim.segment_count - 1))
            diameter_max = dim.diameter_outer + dim.diameter_delta * i / (dim.segment_count - 1)
            segment = self.create_side_cut_height(diameter_min / 2, diameter_max / 2, segment_length)
            cap = self.create_side_cut_angle(diameter_max / 2, min(pipe_diameter_actual, diameter_min) / 2, -45)

            if result is None:
                result = segment.copy() # segment shouldn't be modified (reused as last_segment)
            else:
                segment.align_zxy(last_segment, Alignment.RR)
                result.fuse(segment)

            cap.align_zxy(result, Alignment.RR)
            result.fuse(cap)

            last_segment = segment

        if pipe_length:
            cap = SmartSolid(Solid.make_cylinder(pipe_diameter_actual / 2, pipe_length))
            result.fuse(cap.align_zxy(result, Alignment.RR))

        internal = SmartSolid(Solid.make_cylinder(dim.diameter_inner / 2, result.z_size))
        return result.cut(internal.align(result))

    def create_hose_holder(self) -> SweepSolid:
        dim = self.dim.hose_holder

        pencil = Pencil(plane=Plane.YZ)
        pencil.arc_with_radius(dim.diameter_inner / 2, -90, 180)
        pencil.right(dim.thickness)
        pencil.arc_with_radius(dim.diameter_inner / 2 + dim.thickness, 90, -180)

        path = pencil.create_sweep_path(Plane.XZ)
        path.arc_with_radius(dim.slope_radius,0, 90)

        return path.sweep()

    def create_outlet_hole(self, outlet_pipe_inner: SweepSolid):
        skip_height = self.dim.tube_floor_thickness - self.dim.hose.connector_offset_z
        face = self.create_pipe_cover_face_wider(outlet_pipe_inner, skip_height=skip_height)
        outlet_hole = SmartSolid(extrude(face, self.dim.pipe.diameter_inner))

        plane = outlet_pipe_inner.create_plane_end()
        outlet_hole.align_x(None, Alignment.CR, plane=plane)
        outlet_hole.align_y(None, plane=plane)
        outlet_hole.align_z(None, Alignment.CL, plane=plane)

        return outlet_hole

    def create_magic_surface(self, tube: SmartSolid, tube_inside: SmartSolid, outlet_pipe_outer: SweepSolid, pipe_cover: SmartSolid, outlet_hole: SmartSolid):

        inner_radius = self.dim.hose_holder.diameter_inner / 2 + self.dim.hose_holder.thickness
        radius = self.dim.tube_internal_diameter / 2 + self.dim.tube_wall_thickness + self.dim.hose.connector_offset_x + self.dim.hose.diameter_outer_max / 2

        bottom = SmartCone.create_cone(90 - self.dim.support_free_angle, radius, inner_radius)
        bottom.align_zxy(tube, Alignment.LR)

        outlet_hole.cut(bottom)

        bottom_cut = bottom.pad_outer(-self.dim.tube_floor_thickness, radius * 2)

        top = SmartSolid(Solid.make_cylinder(inner_radius, self.dim.tube_height))
        top.align_zxy(bottom, Alignment.RR)
        top.intersect(tube)

        cone_bottom_angle = self.dim.support_free_angle - self.dim.tube_floor_angle

        invert = SmartCone.create_empty(90 - self.dim.support_free_angle, self.dim.tube_internal_diameter, self.dim.tube_floor_thickness, cone_bottom_angle)
        invert.rotate((0, 180, 0))
        pipe_path_plane = outlet_pipe_outer.create_path_plane()

        height_outlet = self.dim.tube_wall_thickness * 2.25
        height_opposite = self.dim.tube_height * 2 / 3
        offset_x = (height_outlet - height_opposite) / (2 * tan(self.dim.support_free_angle_rad))
        base = self.dim.tube_internal_diameter - (height_outlet + height_opposite) / tan(self.dim.support_free_angle_rad)
        offset_z = base * tan(self.dim.support_free_angle_rad) / 2

        invert.align_z(plane=pipe_path_plane)
        invert.align_x(tube, Alignment.C, offset_x, pipe_path_plane)
        invert.align_z(tube, Alignment.LR, -offset_z)

        above_floor = invert.create_outer_cone(radius * 2).fuse(pipe_cover.cut(tube_inside))
        invert.intersect(tube_inside)

        return top.fuse(bottom).intersect(above_floor).fuse(invert).cut(bottom_cut)


dimensions = HydroponicsDimensions()
hydroponics = Hydroponics(dimensions)

component = hydroponics.create_stand()
# component = hydroponics.create_empty_cone(30, 50, 5)
# component = hydroponics.create_magic_surface()
# component = hydroponics.create_pipe(dimensions.pipe.countertop_thickness)
# component = hydroponics.create_hose_holder()
# solid.orientation = (90, 0, -90)
# component = hydroponics.create_hose_connector(2, 23)
print(component.bound_box.size)
Exporter(component).export()
