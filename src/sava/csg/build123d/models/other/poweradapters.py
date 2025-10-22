from build123d import Vector, mirror, Plane, Solid

from build123d import Vector, mirror, Plane, Solid

from sava.csg.build123d.common.exporter import Exporter, show_green
from sava.csg.build123d.common.geometry import create_vector, Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartsolid import SmartSolid


class RecessDimensions:
    top_angle: float = 77.0
    top_length: float = 39.2
    top_length_flat: float = 21.7

    side_flat_length: float = 23.6
    side_angle: float = -10.0

    bottom_length: float = 24.5
    bottom_length_flat: float = 15.6

    depth: float = 6

class ProngDimensions:
    top_diameter: float = 5.1
    distance_between_top_centres: float = 18.9
    distance_between_top_and_bottom_centres_y: float = 20.2

    bottom_diameter: float = 7.1
    bottom_shift_y: float = 4.6

    height: float = 10

class PowerAdapterBoxDimensions:
    recess: RecessDimensions = RecessDimensions()
    prongs: ProngDimensions = ProngDimensions()

    socket_side: float = 36.0
    socket_padding: float = 5.0
    sockets_per_row: int = 6
    floor_thickness: float = 2
    box_fillet_radius: float = 5.0

    @property
    def get_box_length(self):
        return self.get_side_length(self.sockets_per_row)

    @property
    def get_box_width(self):
        return self.get_side_length(2)

    @property
    def get_box_height(self):
        return self.floor_thickness + self.recess.depth

    def get_side_length(self, socket_count: int):
        return self.socket_side * socket_count + self.socket_padding * (socket_count + 1)

class PowerAdapterBox:
    def __init__(self, dim: PowerAdapterBoxDimensions):
        self.dim = dim

    def create_single(self):
        recess = self.create_socket_recess()

        prongs = self.create_prongs()
        prongs.align_x(recess).align_z(recess, Alignment.LR).align_y(recess, Alignment.LR, self.dim.prongs.bottom_shift_y)

        outer = recess.padded(1.6, 1.6, 0.8)
        outer.align_xy(recess).align_z(recess, Alignment.RL, -0.8)

        show_green(prongs)

        return outer.cut(recess).fuse(prongs)
        # return outer.fuse(prongs)
        # return outer
        # return SmartSolid(outer, prongs)

    def create_box(self):
        box = SmartBox(self.dim.get_box_length, self.dim.get_box_width, self.dim.get_box_height).fillet_z(self.dim.box_fillet_radius)

        recess_row = self.create_row(self.create_socket_recess())
        recess_row.fuse(recess_row.mirrored().align_y(recess_row, Alignment.RR, self.dim.socket_padding))
        recess_row.align_xy(box).align_z(box, Alignment.RL)

        box.cut(recess_row)

        for orientation, alignment in [[0, Alignment.LR], [180, Alignment.RL]]:
            prongs_row = self.create_row(self.create_prongs()).orient((0, 0, orientation))
            prongs_row.align_x(recess_row).align_z(recess_row, Alignment.LR).align_y(recess_row, alignment, alignment.shift_towards_centre(self.dim.prongs.bottom_shift_y))
            box.fuse(prongs_row)

        return box

    def create_row(self, element: SmartSolid) -> SmartSolid:
        return SmartSolid(element.copy().move((self.dim.socket_side + self.dim.socket_padding) * i) for i in range(self.dim.sockets_per_row))

    def create_socket_recess(self):
        pencil = Pencil()
        pencil.right(self.dim.recess.top_length_flat / 2)
        pencil.arcWithVectorToIntersection(Vector((self.dim.recess.top_length - self.dim.recess.top_length_flat) / 2, 0, 0), self.dim.recess.top_angle)
        pencil.arcWithDestination(create_vector(self.dim.recess.side_flat_length, self.dim.recess.top_angle + 90), self.dim.recess.side_angle)
        pencil.arcWithVectorToIntersection(create_vector((self.dim.recess.bottom_length - self.dim.recess.bottom_length_flat) / 2, self.dim.recess.top_angle + 90), 180 - self.dim.recess.top_angle)
        pencil.left(pencil.location.X)
        solid = pencil.extrude(self.dim.recess.depth)
        return SmartSolid(solid, mirror(solid, Plane.YZ))

    def create_prongs(self) -> SmartSolid:
        top_left_prong = self.create_prong(self.dim.prongs.top_diameter)
        top_right_prong = self.create_prong(self.dim.prongs.top_diameter).move(self.dim.prongs.distance_between_top_centres)
        top_prongs = SmartSolid(top_left_prong, top_right_prong)
        bottom_prong = self.create_prong(self.dim.prongs.bottom_diameter)

        bottom_prong.align_x(top_prongs).align_z(top_prongs, Alignment.LR).align_y(top_prongs, Alignment.C, -self.dim.prongs.distance_between_top_and_bottom_centres_y)

        return SmartSolid(top_prongs, bottom_prong)

    def create_prong(self, diameter: float) -> SmartSolid:
        cylinder = SmartSolid(Solid.make_cylinder(diameter / 2, self.dim.prongs.height))
        hemisphere = SmartSolid(Solid.make_sphere(diameter / 2, angle1 = 0))
        hemisphere.align_xy(cylinder).align_z(cylinder, Alignment.RR)
        return SmartSolid(cylinder, hemisphere)

dimensions = PowerAdapterBoxDimensions()
power_adapter_box = PowerAdapterBox(dimensions)
Exporter(power_adapter_box.create_box()).export()
# Exporter(power_adapter_box.create_single()).export()