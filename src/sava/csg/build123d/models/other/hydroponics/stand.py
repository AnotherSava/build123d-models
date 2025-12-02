from copy import copy
from dataclasses import dataclass
from math import radians, sin, degrees, asin
from math import tan

from build123d import Solid, Trapezoid, Circle, Location, fillet, loft, extrude, Face, revolve, Axis, Wire

from sava.csg.build123d.common.exporter import Exporter
from sava.csg.build123d.common.geometry import Alignment, Direction, create_plane, create_vector
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.primitives import create_cone_with_angle
from sava.csg.build123d.common.smartcone import SmartCone
from sava.csg.build123d.common.smartsolid import SmartSolid
from sava.csg.build123d.common.sweepsolid import SweepSolid
from sava.csg.build123d.models.other.hydroponics.connector import HoseConnectorFactory, HoseConnectorDimensions


@dataclass
class PipeDimensions:
    bend_radius: float = 15
    countertop_thickness: float = 45
    bend_angle: float = 55
    length_straight: float = 15
    wall_thickness: float = 2
    diameter_inner: float = None

    @property
    def diameter_outer(self) -> float:
        return self.diameter_inner + self.wall_thickness * 2

    @property
    def radius_outer(self) -> float:
        return self.diameter_outer / 2

    @property
    def bend_angle_rad(self):
        return radians(self.bend_angle)


@dataclass
class HoseHolder:
    bend_radius = 60
    diameter_outer = 20
    central_holder_radius = 10
    hole_radius = 1
    hole_distance = 8


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
class HandleDimensions:
    height: float = 12
    width: float = 5
    thickness: float = 3
    count = 12

@dataclass
class StandDimensions:
    _etches: TubeEtchesDimensions = None

    handles: HandleDimensions = None
    hose_connector: HoseConnectorDimensions = None
    hose_holder: HoseHolder = None
    pipe: PipeDimensions = None
    tube_internal_diameter: float = 142
    tube_top_cut_offset: float = 1.3
    tube_floor_angle: float = 15
    tube_floor_thickness: float = 3
    tube_wall_thickness: float = 4
    pot_wall_thickness: float = 3.1
    edge_angle: float = 45.0

    tube_height: float = 80
    support_free_angle: float = 35

    def __post_init__(self):
        self.handles = self.handles or HandleDimensions()
        self.hose_connector = self.hose_connector or HoseConnectorDimensions()
        self.hose_holder = self.hose_holder or HoseHolder()
        self.pipe = self.pipe or PipeDimensions()

        self._etches = self._etches or TubeEtchesDimensions()
        self.etches_inner = self._etches.pad_inner()
        self.etches_outer = self._etches.pad_outer()

        self.pipe.diameter_inner = self.hose_connector.diameter_inner

    @property
    def support_free_angle_rad(self):
        return radians(self.support_free_angle)

    @property
    def pipe_extra_distance(self) -> float:
        dim = self.pipe
        return dim.bend_radius / tan(dim.bend_angle_rad) + dim.radius_outer / tan(radians(dim.bend_angle)) + self.pot_wall_thickness / sin(dim.bend_angle_rad) * 2.5


class HydroponicsStand:
    def __init__(self, dim: StandDimensions):
        self.dim = dim
        self.host_connector_factory = HoseConnectorFactory(self.dim.hose_connector)

    def create_stand(self) -> SmartSolid:
        tube = SmartSolid(Solid.make_cylinder(self.dim.tube_internal_diameter / 2 + self.dim.tube_wall_thickness, self.dim.tube_height))

        tube_inside = SmartSolid(Solid.make_cylinder(self.dim.tube_internal_diameter / 2, self.dim.tube_height))
        top_cut = create_cone_with_angle(self.dim.tube_internal_diameter / 2, self.dim.tube_internal_diameter / 2 + self.dim.tube_wall_thickness, self.dim.etches_inner.side_angle)
        top_cut.align_zxy(tube, Alignment.RL, self.dim.tube_top_cut_offset)

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

        hose_holder = self.create_hose_holder(inlet_pipe_outer, inlet_connector_top, tube)

        tube.cut(top_cut)
        tube.fuse(pipe_cover, outlet_pipe_outer)
        tube.cut(tube_inside, outlet_hole)
        tube.fuse(surface, handles, etches, inlet_pipe_outer, inlet_connector_top, inlet_connector_bottom, outlet_connector_bottom)
        tube.cut(inlet_pipe_inner, outlet_pipe_inner, hose_holder)

        return tube

    def create_pipe_cover_face_middle(self, pipe: SweepSolid) -> Face:
        dim = self.dim.pipe

        pencil = Pencil((-self.dim.pipe.radius_outer, 0, 0), pipe.create_path_plane())
        pencil.up(dim.length_straight)
        pencil.arc_with_radius(dim.bend_radius + dim.radius_outer, -90, -dim.bend_angle)
        pencil.draw(self.dim.pipe_extra_distance, -dim.bend_angle)
        pencil.down()
        return pencil.create_face()

    def create_pipe_cover_face_wider(self, pipe: SweepSolid, shift_z: float = 0, offset_z: float = 0, skip_height: float = 0) -> Face:
        dim = self.dim.pipe

        pencil = Pencil((0, 0, shift_z), pipe.create_path_plane())
        if skip_height < dim.length_straight:
            pencil.up(dim.length_straight - skip_height)
            skip_angle = 0
        else:
            skip_angle = degrees(asin((skip_height - dim.length_straight) / self.dim.pipe.bend_radius))

        pencil.arc_with_radius(dim.bend_radius, -90 - skip_angle, -dim.bend_angle + skip_angle)
        pencil.draw(self.dim.pipe_extra_distance, -dim.bend_angle)
        pencil.down(pencil.location.Y - offset_z)
        return pencil.create_face()

    def create_pipe_cover(self, inlet_pipe_outer: SweepSolid, outlet_pipe_outer: SweepSolid, tube: SmartSolid) -> SmartSolid:
        middle_part_faces = [self.create_pipe_cover_face_middle(pipe) for pipe in [inlet_pipe_outer, outlet_pipe_outer]]
        middle_part = SmartSolid(loft(middle_part_faces))

        face1 = self.create_pipe_cover_face_wider(inlet_pipe_outer, self.dim.pipe.radius_outer)
        face2 = self.create_pipe_cover_face_wider(outlet_pipe_outer, -self.dim.pipe.radius_outer)
        wider_part = SmartSolid(loft([face1, face2]))

        return wider_part.fuse(middle_part).intersect(tube.scaled(2, 2, 1))

    def create_inlet_connector_top(self, inlet_pipe_outer: SweepSolid) -> SmartSolid:
        connector_top = self.host_connector_factory.create_hose_connector(self.dim.pipe.diameter_outer, 3)

        plane = inlet_pipe_outer.create_plane_end()

        connector_top.solid.location = Location(plane)
        connector_top.rotate((180, 0, 0), plane)
        connector_top.align_z(inlet_pipe_outer, Alignment.RR, 0, plane)

        return connector_top

    def create_pipe(self, inlet_connector_bottom: SmartSolid) -> tuple[SweepSolid, SweepSolid]:
        dim = self.dim.pipe

        plane = create_plane((0, 0, 0), (-inlet_connector_bottom.x_mid, -inlet_connector_bottom.y_mid, 0), (0, 0, 1))

        path = Pencil(plane=plane)
        path.up(dim.length_straight)
        path.arc_with_radius(dim.bend_radius, -90, -dim.bend_angle)
        path.draw(self.dim.pipe_extra_distance, -dim.bend_angle)
        wire = path.create_wire(False)

        pipe_outer = SweepSolid(Circle(dim.radius_outer), wire, plane)

        pipe_outer.align_x(inlet_connector_bottom, Alignment.CR, -dim.radius_outer, plane)
        pipe_outer.align_z(inlet_connector_bottom, Alignment.RR)

        pipe_inner = SweepSolid(Circle(dim.diameter_inner / 2), wire, plane)
        pipe_inner.solid.position = pipe_outer.solid.position

        return pipe_inner, pipe_outer

    def create_hose_holder(self, inlet_pipe: SweepSolid, inlet_connector_top: SmartSolid, tube: SmartSolid) -> SmartSolid:
        plane_connector_end = inlet_pipe.create_plane_end()
        plane_connector_end = plane_connector_end.offset(inlet_connector_top.get_bound_box(plane_connector_end).size.Z)

        plane_path = inlet_pipe.create_path_plane()
        plane_path = plane_path.shift_origin(plane_connector_end.origin)

        x = tube.get_bound_box(plane_path).center().X

        path = Pencil(plane=plane_path)
        path.draw(x / sin(self.dim.pipe.bend_angle_rad) - self.dim.hose_holder.bend_radius * tan(self.dim.pipe.bend_angle_rad / 2), -self.dim.pipe.bend_angle)
        path.arc_with_radius(self.dim.hose_holder.bend_radius, 90 - self.dim.pipe.bend_angle, self.dim.pipe.bend_angle)
        wire = path.create_wire(False)

        circle = Wire.make_circle(self.dim.hose_holder.diameter_outer / 2, plane_connector_end)
        hose = SweepSolid(Face(circle), wire, plane_connector_end)

        hole = SmartSolid(Solid.make_cylinder(self.dim.hose_holder.hole_radius, self.dim.hose_holder.central_holder_radius * 2, plane_path))
        hole.align_z(plane=plane_path)
        hole.align_x(shift=x, plane=plane_path)
        hole.align_z(tube, Alignment.RL, -self.dim.hose_holder.hole_distance)

        return hose.fuse(hole)

    def create_connector_bottom(self, tube: SmartSolid, direction: Direction) -> SmartSolid:
        assert direction in [Direction.S, Direction.N]
        inlet_connector_bottom = self.host_connector_factory.create_hose_connector(self.dim.pipe.diameter_outer, self.dim.hose_connector.pipe_length)
        inlet_connector_bottom.align_z(tube, Alignment.LL, self.dim.hose_connector.connector_offset_z)
        inlet_connector_bottom.align_x(tube, Alignment.LL, -self.dim.hose_connector.connector_offset_x)
        inlet_connector_bottom.align_y(tube, Alignment.C, self.dim.hose_connector.distance_between_pipe_centres / 2 * (1 if direction == Direction.N else -1))
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

        return etches.align_z(tube, Alignment.RL, -self.dim.etches_inner.distance_from_top + self.dim.tube_top_cut_offset)

    def create_handles(self, tube: SmartSolid):
        shapes = []
        for i in range(self.dim.handles.count):
            plane = create_plane(x_axis=create_vector(1, i * 360 / self.dim.handles.count), y_axis=(0, 0, 1))
            pencil = Pencil(plane=plane)
            pencil.right(self.dim.tube_internal_diameter / 2 + self.dim.tube_wall_thickness + self.dim.handles.thickness)
            pencil.double_arc((-self.dim.handles.thickness * 1.01, self.dim.handles.height))
            pencil.left()
            handle = SmartSolid(pencil.extrude(self.dim.handles.width))
            handle.align_z(plane=plane)
            shapes.append(handle)

        return SmartSolid(shapes).align_zxy(tube, Alignment.LR).cut(tube)

    def create_outlet_hole(self, outlet_pipe_inner: SweepSolid):
        skip_height = -self.dim.hose_connector.connector_offset_z
        face = self.create_pipe_cover_face_wider(outlet_pipe_inner, skip_height=skip_height)
        outlet_hole = SmartSolid(extrude(face, self.dim.pipe.diameter_inner))

        plane = outlet_pipe_inner.create_plane_end()
        outlet_hole.align_x(None, Alignment.CR, plane=plane)
        outlet_hole.align_y(plane=plane)
        outlet_hole.align_z(None, Alignment.CL, plane=plane)

        return outlet_hole

    def create_magic_surface(self, tube: SmartSolid, tube_inside: SmartSolid, outlet_pipe_outer: SweepSolid, pipe_cover: SmartSolid, outlet_hole: SmartSolid):
        radius = self.dim.tube_internal_diameter / 2 + self.dim.tube_wall_thickness + self.dim.hose_connector.connector_offset_x + self.dim.hose_connector.diameter_outer_max / 2

        bottom = SmartCone.create_cone(90 - self.dim.support_free_angle, radius, self.dim.hose_holder.central_holder_radius)
        bottom.align_zxy(tube, Alignment.LR)

        outlet_hole.cut(bottom)

        bottom_cut = bottom.pad_outer(-self.dim.tube_floor_thickness, radius * 2)

        top = SmartSolid(Solid.make_cylinder(self.dim.hose_holder.central_holder_radius, self.dim.tube_height))
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


dimensions = StandDimensions()
hydroponics = HydroponicsStand(dimensions)

component = hydroponics.create_stand()
# component = hydroponics.create_empty_cone(30, 50, 5)
# component = hydroponics.create_magic_surface()
# component = hydroponics.create_pipe(dimensions.pipe.countertop_thickness)
# solid.orientation = (90, 0, -90)
# component = hydroponics.create_hose_connector(2, 23)
print(component.bound_box.size)
Exporter(component).export()
