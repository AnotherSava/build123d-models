from build123d import Vector, mirror, Plane, Solid

from sava.csg.build123d.common.exporter import Exporter, show_green
from sava.csg.build123d.common.geometry import create_vector, Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.primitives import create_tapered_box
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
    box_length_padding: float = 3
    # sockets_per_row: int = 6
    sockets_per_row: int = 1
    floor_thickness: float = 2
    box_fillet_radius: float = 5.0
    box_taper_diff: float = 0.5

    # lid_internal_height: float = 57.0
    lid_internal_height: float = 40.0
    lid_ceiling_thickness: float = 1.2
    lid_cutout_thickness: float = 1.2
    gap: float = 0.2
    lock_gap: float = 0.1

    lock_length: float = 20.0
    lock_height: float = 35.0
    lock_padding: float = 0.2
    lock_tip_thickness: float = 2.2
    lock_tip_distance: float = 2
    lock_cantilever_attachment_height: float = 15
    lock_cantilever_thickness: float = 2
    lock_slot_thickness_coefficient: float = 1.1

    lock_hardening_height: float = 20.0
    lock_hardening_thickness: float = 1.5

    lid_wall_thickness: float = 1.2

    @property
    def lock_cantilever_distance(self):
        return self.lock_tip_thickness + self.lid_wall_thickness

    @property
    def lock_tip_height(self):
        return self.lid_cutout_height - self.lock_tip_distance

    @property
    def lid_cutout_height(self):
        return self.box_height / 4 * 3

    @property
    def lid_height(self):
        return self.lid_cutout_height + self.lid_internal_height + self.lid_ceiling_thickness

    @property
    def box_length(self):
        return self.get_side_length(self.sockets_per_row) + self.box_length_padding * 2

    @property
    def box_width(self):
        # return self.get_side_length(2)
        return 40

    @property
    def box_height(self):
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

    def create_lid(self) -> SmartSolid:

        lid = SmartBox(self.dim.box_length, self.dim.box_width, self.dim.lid_height)
        lid_internal = SmartBox(lid.x_size - self.dim.lid_wall_thickness * 2, lid.y_size - self.dim.lid_wall_thickness * 2, lid.z_size - self.dim.lid_ceiling_thickness)
        lid_internal.align_xy(lid).align_z(lid, Alignment.LR)

        lid.cut(lid_internal).fillet_z(self.dim.box_fillet_radius)

        lock_bottom = SmartBox(lid.x_size, self.dim.lock_length + self.dim.lock_padding * 2, self.dim.lock_height).align_xy(lid).align_z(lid, Alignment.LR)
        lid.cut(lock_bottom)

        box = self.create_box()
        box.align_xy(lid).align_z(lid, Alignment.LR, self.dim.lid_cutout_height - self.dim.box_height)

        snap = self.create_snap()
        for orientation, alignment in [[180, Alignment.LR], [0, Alignment.RL]]:
            snap.orient((90, orientation, 0))
            snap.align_x(lid, alignment).align_y(lid).align_z(lid, Alignment.LR)
            # show_green(snap)
            lid.solid += snap.solid
            # lid.fuse(snap)

        slot = self.create_lock_slot()
        for orientation, alignment in [[180, Alignment.LR], [0, Alignment.RL]]:
            slot.orient((90, orientation, 0))
            slot.align_x(lid_internal, alignment, alignment.shift_towards_centre(self.dim.lock_cantilever_distance - self.dim.lock_tip_thickness)).align_y(lid).align_z(lid, Alignment.LR, -self.dim.lock_gap)
            box.cut(slot)

        # show_green(box)

        return box
        # return lid

    def create_snap(self) -> SmartSolid:
        pencil = Pencil()

        pencil.jump(Vector(self.dim.lock_tip_thickness + self.dim.lock_cantilever_thickness, self.dim.lock_tip_height))
        pencil.left(self.dim.lock_tip_thickness)
        pencil.up(self.dim.lock_tip_distance)

        arcDestinationVector = Vector(self.dim.lock_cantilever_distance + self.dim.lid_wall_thickness, self.dim.lock_cantilever_attachment_height - self.dim.lid_cutout_height)
        pencil.doubleArc(arcDestinationVector)

        pencil.up(self.dim.lock_height - self.dim.lock_cantilever_attachment_height + self.dim.lock_hardening_height / 2)
        pencil.left(self.dim.lid_wall_thickness)
        pencil.doubleArc(Vector(-self.dim.lock_hardening_thickness, -self.dim.lock_hardening_height / 2))
        pencil.doubleArc(Vector(self.dim.lock_hardening_thickness - self.dim.lock_cantilever_thickness + self.dim.lid_wall_thickness, -self.dim.lock_hardening_height / 2))

        pencil.down(self.dim.lock_height - self.dim.lock_cantilever_attachment_height - self.dim.lock_hardening_height / 2)

        pencil.doubleArc(-arcDestinationVector, 0.57)

        return SmartSolid(pencil.extrudeY(self.dim.lock_length))

    def create_lock_slot(self) -> SmartSolid:
        pencil = Pencil()

        pencil.down(self.dim.lock_tip_distance - self.dim.lock_gap)
        pencil.right(self.dim.lock_tip_thickness)
        pencil.down(self.dim.lock_tip_height + self.dim.lock_gap * 2)
        pencil.left((self.dim.lock_tip_thickness * 2 + self.dim.lock_cantilever_thickness) * self.dim.lock_slot_thickness_coefficient)
        pencil.up(self.dim.lock_tip_height + self.dim.lock_tip_distance + self.dim.lock_gap)

        return SmartSolid(pencil.extrudeY(self.dim.lock_length + self.dim.gap * 2))


    def create_box(self) -> SmartSolid:
        length_top = self.dim.box_length - self.dim.lid_wall_thickness * 2
        width_top = self.dim.box_width - self.dim.lid_wall_thickness * 2


        box_top = create_tapered_box(length_top, width_top, self.dim.lid_cutout_height, length_top - self.dim.box_taper_diff * 2, width_top - self.dim.box_taper_diff * 2, self.dim.box_fillet_radius)

        box_bottom = SmartBox(self.dim.box_length, self.dim.box_width, self.dim.box_height - self.dim.lid_cutout_height)
        box_bottom.align_xy(box_top).align_z(box_top, Alignment.LL)

        box = SmartSolid(box_top.solid + box_bottom.solid).fillet_z(self.dim.box_fillet_radius)

        # recess_row = self.create_row(self.create_socket_recess())
        # recess_row.fuse(recess_row.mirrored().align_y(recess_row, Alignment.RR, self.dim.socket_padding))
        # recess_row.align_xy(box).align_z(box, Alignment.RL)
        #
        # box.cut(recess_row)
        #
        # for orientation, alignment in [[0, Alignment.LR], [180, Alignment.RL]]:
        #     prongs_row = self.create_row(self.create_prongs()).orient((0, 0, orientation))
        #     prongs_row.align_x(recess_row).align_z(recess_row, Alignment.LR).align_y(recess_row, alignment, alignment.shift_towards_centre(self.dim.prongs.bottom_shift_y))
        #     box.fuse(prongs_row)

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
Exporter(power_adapter_box.create_lid()).export()
# Exporter(create_tapered_box(10, 20, 5, 8, 18)).export()
# Exporter(power_adapter_box.create_box()).export()
# Exporter(power_adapter_box.create_single()).export()