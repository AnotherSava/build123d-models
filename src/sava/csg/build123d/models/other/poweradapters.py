from build123d import Vector, mirror, Plane, Solid, Axis, Text, extrude

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

class TextDimensions:
    text: str = "Travel Adapter Set"
    font_size: float = 20
    font: str = "Liberation Sans"
    height: float = 4.0

class PowerAdapterBoxDimensions:
    recess: RecessDimensions = RecessDimensions()
    prongs: ProngDimensions = ProngDimensions()
    text: TextDimensions = TextDimensions()

    socket_side: float = 36.0
    # socket_padding: float = 5.0
    socket_padding: float = 4.0
    box_length_padding: float = 6
    # sockets_per_row: int = 6
    sockets_per_row: int = 1
    floor_thickness: float = 2
    box_fillet_radius: float = 5.0
    protrusion_side_delta = 4.0
    protrusion_fillet_radius: float = 1.0
    lid_fillet_radius: float = 0.3
    box_taper_diff: float = 0.6

    lid_internal_height: float = 57.0
    lid_ceiling_thickness: float = 1.2
    lid_cutout_thickness: float = 1.2
    lock_gap: float = 0.3

    lock_length: float = 20.0
    lock_length_bottom: float = 16.0
    lock_height: float = 35.0
    lock_padding: float = 0.2
    lock_tip_thickness: float = 3
    lock_tip_distance: float = 4.0
    lock_cantilever_attachment_height: float = 15
    lock_cantilever_thickness: float = 2
    lock_slot_thickness_coefficient: float = 1.1
    lock_slot_radius: float = 2.5

    lock_hardening_height: float = 20.0
    lock_hardening_thickness: float = 1.5

    lid_wall_thickness: float = 1.2

    @property
    def lock_tip_height(self):
        return self.box_height - self.lock_tip_distance - self.lock_gap

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
        return self.get_side_length(2)

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

    def create_text(self) -> SmartSolid:
        # Create a wire object for text using direct API
        text_wire = Text(self.dim.text.text, font_size=self.dim.text.font_size, font=self.dim.text.font)

        # You can immediately extrude this wire to make a 3D object
        solid_text = extrude(text_wire, amount=self.dim.text.height)
        return SmartSolid(solid_text)

    def create_lid(self) -> SmartSolid:

        lid = SmartBox(self.dim.box_length, self.dim.box_width, self.dim.lid_height)
        lid_internal = SmartBox(lid.x_size - self.dim.lid_wall_thickness * 2, lid.y_size - self.dim.lid_wall_thickness * 2, lid.z_size - self.dim.lid_ceiling_thickness)
        lid_internal.align_xy(lid).align_z(lid, Alignment.LR)

        lid.cut(lid_internal).fillet_z(self.dim.box_fillet_radius)

        lock_bottom = SmartBox(lid.x_size, self.dim.lock_length + self.dim.lock_padding * 2, self.dim.lock_height).align_xy(lid).align_z(lid, Alignment.LR)
        lid.cut(lock_bottom)

        box_protrusion = self.create_protrusion(False)
        box_protrusion.align(lid).align_z(lid, Alignment.LR)
        lid.cut(box_protrusion)

        lid.fillet_positional(Axis.X, self.dim.lid_fillet_radius, *box_protrusion.create_positional_filters_plane(Plane.YZ))

        box = self.create_box()
        box.align_xy(lid).align_z(lid, Alignment.LR, self.dim.lid_cutout_height - self.dim.box_height)

        snap = self.create_snap()

        snap_thinning = self.create_snap_thinning().orient((90, 90, 0))
        snap_thinning.align(lid).align_z(box, Alignment.LR)

        for orientation, alignment in [[180, Alignment.LR], [0, Alignment.RL]]:
            snap.orient((90, orientation, 0))
            snap.align_x(lid, alignment).align_y(lid).align_z(box, Alignment.LR, self.dim.lock_gap)
            lid.solid += snap.solid & snap_thinning.solid

        slot = self.create_lock_slot()
        for orientation, alignment in [[180, Alignment.LR], [0, Alignment.RL]]:
            slot.orient((90, orientation, 0))
            slot.align_x(lid, alignment).align_y(lid).align_z(box, Alignment.LR)
            # show_red(slot)
            box.cut(slot)

        # show_red(snap)
        # show_green(box)
        # show_green(lid)

        return box
        # return lid

    def create_snap_thinning(self) -> SmartSolid:
        pencil = Pencil(Vector(5, 0))
        pencil.right(self.dim.lock_length_bottom / 2)
        pencil.up(self.dim.box_height)
        pencil.double_arc(Vector((self.dim.lock_length - self.dim.lock_length_bottom) / 2, (self.dim.lock_cantilever_attachment_height - self.dim.lock_tip_height)))
        pencil.up(self.dim.lid_height - self.dim.lock_cantilever_attachment_height)
        pencil.left(1) # no idea why single left doesn't work here
        pencil.left(self.dim.lock_length / 2 - 1)
        return SmartSolid(pencil.extrude_mirrored(self.dim.box_length, Axis.Y))

    def create_snap(self) -> SmartSolid:
        pencil = Pencil()

        pencil.jump(Vector(self.dim.lock_tip_thickness + self.dim.lock_cantilever_thickness, self.dim.lock_tip_height))
        pencil.left(self.dim.lock_tip_thickness)
        pencil.up(self.dim.lock_tip_distance)

        arc_destination_vector = Vector(self.dim.lock_tip_thickness, self.dim.lock_cantilever_attachment_height - self.dim.lid_cutout_height)
        pencil.double_arc(arc_destination_vector)

        pencil.up(self.dim.lock_height - self.dim.lock_cantilever_attachment_height + self.dim.lock_hardening_height / 2)
        pencil.left(self.dim.lid_wall_thickness)
        pencil.double_arc(Vector(-self.dim.lock_hardening_thickness, -self.dim.lock_hardening_height / 2))
        pencil.double_arc(Vector(self.dim.lock_hardening_thickness - self.dim.lock_cantilever_thickness + self.dim.lid_wall_thickness, -self.dim.lock_hardening_height / 2))

        pencil.down(self.dim.lock_height - self.dim.lock_cantilever_attachment_height - self.dim.lock_hardening_height / 2)

        pencil.double_arc(-arc_destination_vector, 0.57)

        return SmartSolid(pencil.extrude_y(self.dim.lock_length))

    def create_lock_slot(self) -> SmartSolid:
        pencil = Pencil()

        pencil.arc_with_radius(self.dim.lock_slot_radius, 180, 90)
        pencil.down(self.dim.lock_tip_distance - self.dim.lock_gap - self.dim.lock_slot_radius)
        pencil.right(self.dim.lock_tip_thickness)
        pencil.down(self.dim.box_height - self.dim.lock_tip_distance + self.dim.lock_gap)
        pencil.left((self.dim.lock_tip_thickness * 2 + self.dim.lock_cantilever_thickness) * self.dim.lock_slot_thickness_coefficient)
        pencil.up(self.dim.box_height)

        return SmartSolid(pencil.extrude_y(self.dim.lock_length_bottom + self.dim.box_taper_diff * 2))


    def create_protrusion(self, filleted: bool):
        protrusion_bottom_width = self.dim.lock_length + self.dim.lock_padding * 2 + self.dim.protrusion_side_delta
        radius = self.dim.protrusion_fillet_radius if filleted else 0
        return create_tapered_box(self.dim.box_length, protrusion_bottom_width, self.dim.lid_cutout_height, self.dim.box_length, protrusion_bottom_width - self.dim.box_taper_diff * 2, radius)

    def create_box(self) -> SmartSolid:
        length_narrow = self.dim.box_length - self.dim.lid_wall_thickness * 2
        width_narrow = self.dim.box_width - self.dim.lid_wall_thickness * 2
        box_top = create_tapered_box(length_narrow, width_narrow, self.dim.lid_cutout_height, length_narrow - self.dim.box_taper_diff * 2, width_narrow - self.dim.box_taper_diff * 2, self.dim.box_fillet_radius)

        box_protrusion = self.create_protrusion(True)
        box_protrusion.align(box_top)

        box_bottom = SmartBox(self.dim.box_length, self.dim.box_width, self.dim.box_height - self.dim.lid_cutout_height).fillet_z(self.dim.box_fillet_radius)
        box_bottom.align_xy(box_top).align_z(box_top, Alignment.LL)

        box = SmartSolid(box_top.solid + box_bottom.solid + box_protrusion.solid)

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
        pencil.arc_with_vector_to_intersection(Vector((self.dim.recess.top_length - self.dim.recess.top_length_flat) / 2, 0, 0), self.dim.recess.top_angle)
        pencil.arc_with_destination(create_vector(self.dim.recess.side_flat_length, self.dim.recess.top_angle + 90), self.dim.recess.side_angle)
        pencil.arc_with_vector_to_intersection(create_vector((self.dim.recess.bottom_length - self.dim.recess.bottom_length_flat) / 2, self.dim.recess.top_angle + 90), 180 - self.dim.recess.top_angle)
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
Exporter(power_adapter_box.create_text()).export()
# Exporter(power_adapter_box.create_lid()).export()
# Exporter(power_adapter_box.create_snap_thinning()).export()
# Exporter(power_adapter_box.create_box()).export()
# Exporter(power_adapter_box.create_single()).export()