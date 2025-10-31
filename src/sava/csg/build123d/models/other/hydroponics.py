from copy import copy
from dataclasses import dataclass
from math import radians
from math import tan

from build123d import Solid, Trapezoid, Circle, sweep, Edge, Plane, Location, fillet, Box, loft

from sava.csg.build123d.common.exporter import Exporter
from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass
class HoseConnectorDimensions:
    diameter_outer: float = 17.5
    thickness: float = 2
    length: float = 20.0
    segment_count: int = 3
    diameter_delta: float = 1.5 # diameter gradient will be [diameter_outer - diameter_delta; diameter_outer + diameter_delta]

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
    tube_internal_diameter: float = 142
    tube_wall_thickness: float = 4
    pot_wall_thickness: float = 3.1
    edge_angle: float = 45.0

    test_height: float = 13

    def __post_init__(self):
        self.hose = self.hose or HoseConnectorDimensions()

        self._etches = self._etches or TubeEtchesDimensions()
        self.etches_inner = self._etches.pad_inner()
        self.etches_outer = self._etches.pad_outer()


class Hydroponics:
    def __init__(self, dim: HydroponicsDimensions):
        self.dim = dim

    def create_stand(self) -> SmartSolid:
        tube = SmartSolid(Solid.make_cylinder(self.dim.tube_internal_diameter / 2 + self.dim.tube_wall_thickness, self.dim.test_height))

        handles = self.create_handles()
        tube.fuse(handles.align(tube))

        tube_inside = SmartSolid(Solid.make_cylinder(self.dim.tube_internal_diameter / 2, self.dim.test_height))
        tube.cut(tube_inside.align(tube))

        cut = self.create_side_cut_height()
        cut.align_zxy(tube, Alignment.RL)
        tube.cut(cut)

        etches = self.create_etches()
        etches.align_z(tube, Alignment.RL, -self.dim.etches_inner.distance_from_top)

        return tube.fuse(etches)

    def create_etches(self):
        trapezoid = Trapezoid(self.dim.etches_inner.outer_width, self.dim.etches_inner.thickness, self.dim.etches_inner.side_angle)

        # Fillet two vertices facing inside the tube
        internal_vertices = sorted(trapezoid.vertices(), key=lambda v: v.Y)[-2:]
        trapezoid = fillet(internal_vertices, self.dim.etches_inner.fillet_radius)
        
        trapezoid.orientation = (90, 0, -90)
        trapezoid.position = ((self.dim.etches_inner.thickness - self.dim.tube_internal_diameter) / 2, 0, 0)

        path = Edge.make_circle(self.dim.tube_internal_diameter / 2, Plane.XY, 180, 180 + self.dim.etches_inner.angle_measure)
        single_edge = SmartSolid(sweep(trapezoid, path=path))

        return SmartSolid(single_edge.oriented((0, 0, i * 120)) for i in range(3))

    def create_side_cut_height(self, bottom_radius: float = None, top_radius: float = None, height: float = None):
        bottom = Circle(bottom_radius)
        top = Circle(top_radius).move(Location((0, 0, height)))

        return SmartSolid(loft([bottom, top]))

    def create_side_cut_angle(self, bottom_radius: float = None, top_radius: float = None, angle: float = None):
        bottom_radius = self.dim.tube_internal_diameter / 2 if bottom_radius is None else bottom_radius
        top_radius = self.dim.tube_internal_diameter / 2 + self.dim.tube_wall_thickness if top_radius is None else top_radius
        angle = self.dim.etches_inner.side_angle if angle is None else angle

        height = (top_radius - bottom_radius) / tan(radians(angle))
        return self.create_side_cut_height(bottom_radius, top_radius, height)

    def create_handles(self):
        shapes = []
        for i in range(6):
            box = Box(self.dim.tube_internal_diameter + self.dim.tube_wall_thickness * 3, self.dim.tube_wall_thickness, self.dim.test_height)
            box.orientation = (0, 0, i * 30)
            shapes.append(box)

        return SmartSolid(shapes)

    def create_hose_connector(self):
        dim = self.dim.hose

        result = None

        segment_length = dim.length / dim.segment_count
        print(segment_length)
        for i in range(dim.segment_count):
            diameter_min = dim.diameter_outer - dim.diameter_delta * (1 - i / dim.segment_count)
            diameter_max = dim.diameter_outer + dim.diameter_delta * i / dim.segment_count
            segment = self.create_side_cut_height(diameter_min / 2, diameter_max / 2, segment_length)

            if result is None:
                result = segment
            else:
                segment.align_zxy(result, Alignment.RR)
                result.fuse(segment)

        cap = SmartSolid(Solid.make_cylinder(dim.diameter_outer / 2 + dim.diameter_delta * 2, dim.diameter_delta * 2))
        result.fuse(cap.align_zxy(result, Alignment.RR))

        internal = SmartSolid(Solid.make_cylinder(dim.diameter_outer / 2 - dim.thickness, result.z_size))
        return result.cut(internal.align(result))


dimensions = HydroponicsDimensions()
hydroponics = Hydroponics(dimensions)

# component = hydroponics.create_stand()
component = hydroponics.create_hose_connector()
print(component.bound_box.size)
Exporter(component).export()
