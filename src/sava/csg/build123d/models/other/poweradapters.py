from typing import Tuple

from build123d import Vector, mirror, Plane, Solid, Axis

from sava.csg.build123d.common.exporter import export, save_3mf, clear, save_stl, show_red
from sava.csg.build123d.common.geometry import create_vector, Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.primitives import create_tapered_box, create_tapered_box_delta
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartsolid import SmartSolid
from sava.csg.build123d.common.text import TextDimensions, create_text


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
    distance_between_top_centres: float = 19.0
    distance_between_top_and_bottom_centres_y: float = 20.2

    bottom_diameter: float = 7.1
    bottom_shift_y: float = 4.6

    height: float = 10


class PowerAdapterBoxDimensions:
    recess: RecessDimensions = RecessDimensions()
    prongs: ProngDimensions = ProngDimensions()

    text: TextDimensions = TextDimensions(
        font_size = 24,
        font = "Liberation Sans",
        height = 0.8,
    )

    label: str = "Travel Adapter Set"
    socket_side: float = 36.0
    socket_padding: float = 4.0
    box_length_padding: float = 6
    sockets_per_row: int = 6
    floor_thickness: float = 2
    box_fillet_radius: float = 5.0
    protrusion_side_delta = 4.0
    protrusion_fillet_radius: float = 1.0
    lid_fillet_radius: float = 0.3
    box_taper_diff: float = 0.6

    lid_internal_height: float = 63.0
    lid_ceiling_thickness: float = 2
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

    lid_wall_thickness: float = 2.4

    box_width: float = 100.0

    @property
    def lid_length_internal(self):
     return self.box_length - self.lid_wall_thickness * 2

    @property
    def lid_width_internal(self):
        return self.box_width - self.lid_wall_thickness * 2

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
    def box_height(self):
        return self.floor_thickness + self.recess.depth

    @property
    def box_wider_height(self):
        return self.box_height - self.lid_cutout_height

    def get_side_length(self, socket_count: int):
        return self.socket_side * socket_count + self.socket_padding * (socket_count + 1)

class PowerAdapterBase:
    def __init__(self, dim: PowerAdapterBoxDimensions):
        self.dim = dim

    # Creates tapered box protrusion that connects box and lid
    def create_protrusion(self, filleted: bool):
        protrusion_bottom_width = self.dim.lock_length + self.dim.lock_padding * 2 + self.dim.protrusion_side_delta
        radius = self.dim.protrusion_fillet_radius if filleted else 0
        return create_tapered_box(self.dim.box_length, protrusion_bottom_width, self.dim.lid_cutout_height, self.dim.box_length, protrusion_bottom_width - self.dim.box_taper_diff * 2, radius)


class PowerAdapterLid(PowerAdapterBase):
    # Creates main lid structure with snap locks and text cutout
    def create_lid(self) -> Tuple[SmartSolid, SmartSolid]:

        lid = SmartBox(self.dim.box_length, self.dim.box_width, self.dim.lid_height, label="lid")
        lid_internal = SmartBox(lid.x_size - self.dim.lid_wall_thickness * 2, lid.y_size - self.dim.lid_wall_thickness * 2, lid.z_size - self.dim.lid_ceiling_thickness)
        lid_internal.align_xy(lid).align_z(lid, Alignment.LR)

        lid.cut(lid_internal).fillet_z(self.dim.box_fillet_radius)

        lock_bottom = SmartBox(lid.x_size, self.dim.lock_length + self.dim.lock_padding * 2, self.dim.lock_height).align_xy(lid).align_z(lid, Alignment.LR)
        lid.cut(lock_bottom)

        box_protrusion = self.create_protrusion(False)
        box_protrusion.align(lid).align_z(lid, Alignment.LR)
        lid.cut(box_protrusion)

        lid.fillet_positional(self.dim.lid_fillet_radius, Axis.X, *box_protrusion.create_positional_filters_plane(Plane.YZ))

        snap = self.create_snap()

        snap_thinning = self.create_snap_thinning()
        snap_thinning.align(lid).align_z(lid, Alignment.LR, self.dim.lock_gap - self.dim.box_wider_height)

        for orientation, alignment in [[180, Alignment.LR], [0, Alignment.RL]]:
            snap.orient((0, 0, orientation)).align_x(lid, alignment).align_y(lid).align_z(snap_thinning, Alignment.LR)
            lid.fuse(snap.intersected(snap_thinning))

        text = create_text(self.dim.text, self.dim.label, "text")
        text.align_zxy(lid, Alignment.RL)

        return lid.cut(text), text.connected()

    # Creates profile for thinning snap lock cantilever
    def create_snap_thinning(self) -> SmartSolid:
        pencil = Pencil(plane=Plane.YZ)
        pencil.right(self.dim.lock_length_bottom / 2)
        pencil.up(self.dim.box_height)
        pencil.double_arc(Vector((self.dim.lock_length - self.dim.lock_length_bottom) / 2, self.dim.lock_cantilever_attachment_height - self.dim.lock_tip_height))
        pencil.up(self.dim.lid_height - self.dim.lock_cantilever_attachment_height)
        pencil.left()
        return SmartSolid(pencil.extrude_mirrored_y(self.dim.box_length))

    # Creates cantilever snap lock that clips into box
    def create_snap(self) -> SmartSolid:
        # Sketch (XZ plane):
        #
        #      G--F
        #     /   |
        #     H   |
        #     \   |
        #      I  E
        #      | /
        #      J |
        #     / /
        #    /  D
        #    |  |
        #    |  C----B
        #    |    __/
        #    A___/
        #

        pencil = Pencil(plane=Plane.XZ)

        # A → B: from origin to tip base (5.0, 3.7)
        pencil.jump(Vector(self.dim.lock_tip_thickness + self.dim.lock_cantilever_thickness, self.dim.lock_tip_height))
        # B → C: tip bottom edge (2.0, 3.7)
        pencil.left(self.dim.lock_tip_thickness)
        # C → D: tip outer edge / catch surface (2.0, 7.7)
        pencil.up(self.dim.lock_tip_distance)

        # D → E: S-curve to cantilever base (5.0, 16.7)
        arc_destination_vector = Vector(self.dim.lock_tip_thickness, self.dim.lock_cantilever_attachment_height - self.dim.lid_cutout_height)
        pencil.double_arc(arc_destination_vector)

        # E → F: cantilever vertical arm (5.0, 46.7)
        pencil.up(self.dim.lock_height - self.dim.lock_cantilever_attachment_height + self.dim.lock_hardening_height / 2)
        # F → G: lid wall attachment (2.6, 46.7)
        pencil.left(self.dim.lid_wall_thickness)
        # G → H: hardening bulge curving out (1.1, 36.7)
        pencil.double_arc(Vector(-self.dim.lock_hardening_thickness, -self.dim.lock_hardening_height / 2))
        # H → I: hardening bulge curving back (3.0, 26.7)
        pencil.double_arc(Vector(self.dim.lock_hardening_thickness - self.dim.lock_cantilever_thickness + self.dim.lid_wall_thickness, -self.dim.lock_hardening_height / 2))

        # I → J: inner cantilever edge (3.0, 16.7)
        pencil.down(self.dim.lock_height - self.dim.lock_cantilever_attachment_height - self.dim.lock_hardening_height / 2)

        # J → A: S-curve closing back to (0.0, 7.7), tension=0.57
        pencil.double_arc(-arc_destination_vector, 0.57)

        return SmartSolid(pencil.extrude(self.dim.lock_length))


class PowerAdapterBox(PowerAdapterBase):
    # Assembles complete box with socket recesses and lock slots
    def create_box(self) -> Tuple[SmartSolid, SmartSolid]:
        box_top = create_tapered_box_delta(self.dim.lid_length_internal, self.dim.lid_width_internal, self.dim.lid_cutout_height, -self.dim.box_taper_diff, self.dim.box_fillet_radius)

        box_protrusion = self.create_protrusion(True)
        box_protrusion.align(box_top)

        box_bottom = SmartBox(self.dim.box_length, self.dim.box_width, self.dim.box_wider_height).fillet_z(self.dim.box_fillet_radius)
        box_bottom.align_zxy(box_top, Alignment.LL)

        box = SmartSolid(box_top, box_bottom, box_protrusion, label="box")

        recess_row = self.create_row(self.create_socket_recess()).align_z(box, Alignment.RL)
        prongs_row = self.create_row(self.create_prongs()).align_z(recess_row, Alignment.LR)

        prongs = []

        for orientation, alignment in [[0, Alignment.LR], [180, Alignment.RL]]:
            recess_row.orient((0, 0, orientation))
            recess_row.align_xy(box).move_vector(create_vector(recess_row.y_size / 2 + self.dim.socket_padding / 2, 180 - orientation))

            prongs_row.orient((0, 0, orientation))
            prongs_row.align_x(box).align_y(recess_row, alignment, alignment.shift_towards_centre(self.dim.prongs.bottom_shift_y))
            box.cut(recess_row.copy())
            prongs.append(prongs_row.copy())

        slot = self.create_lock_slot()
        for orientation, alignment in [[180, Alignment.LR], [0, Alignment.RL]]:
            slot.orient((0, 0, orientation)).align_x(box, alignment).align_y(box).align_z(box, Alignment.LR)
            box.cut(slot)
        return box, SmartSolid(prongs, label="prongs")

    # Creates shaped recess for one power adapter socket
    def create_socket_recess(self):
        pencil = Pencil()
        pencil.right(self.dim.recess.top_length_flat / 2)
        pencil.arc_with_vector_to_intersection(Vector((self.dim.recess.top_length - self.dim.recess.top_length_flat) / 2, 0, 0), self.dim.recess.top_angle)
        pencil.arc_with_destination(create_vector(self.dim.recess.side_flat_length, self.dim.recess.top_angle + 90), self.dim.recess.side_angle)
        pencil.arc_with_vector_to_intersection(create_vector((self.dim.recess.bottom_length - self.dim.recess.bottom_length_flat) / 2, self.dim.recess.top_angle + 90), 180 - self.dim.recess.top_angle)
        pencil.left(pencil.location.X)
        solid = pencil.extrude(self.dim.recess.depth)
        return SmartSolid(solid, mirror(solid, Plane.YZ))

    # Creates 3-prong pattern for visualizing adapter fit
    def create_prongs(self) -> SmartSolid:
        top_left_prong = self.create_prong(self.dim.prongs.top_diameter)
        top_right_prong = self.create_prong(self.dim.prongs.top_diameter).move(self.dim.prongs.distance_between_top_centres)
        top_prongs = SmartSolid(top_left_prong, top_right_prong)
        bottom_prong = self.create_prong(self.dim.prongs.bottom_diameter)

        bottom_prong.align_x(top_prongs).align_z(top_prongs, Alignment.LR).align_y(top_prongs, Alignment.C, -self.dim.prongs.distance_between_top_and_bottom_centres_y)

        return SmartSolid(top_prongs, bottom_prong)

    # Creates single cylindrical prong with hemisphere tip
    def create_prong(self, diameter: float) -> SmartSolid:
        cylinder = SmartSolid(Solid.make_cylinder(diameter / 2, self.dim.prongs.height))
        hemisphere = SmartSolid(Solid.make_sphere(diameter / 2, angle1 = 0))
        hemisphere.align_xy(cylinder).align_z(cylinder, Alignment.RR)
        return SmartSolid(cylinder, hemisphere)

    # Creates slot in box for snap lock tip
    def create_lock_slot(self) -> SmartSolid:
        pencil = Pencil(plane=Plane.XZ)

        pencil.arc_with_radius(self.dim.lock_slot_radius, 180, 90)
        pencil.down(self.dim.lock_tip_distance - self.dim.lock_gap - self.dim.lock_slot_radius)
        pencil.right(self.dim.lock_tip_thickness)
        pencil.down(self.dim.box_height - self.dim.lock_tip_distance + self.dim.lock_gap)
        pencil.left((self.dim.lock_tip_thickness * 2 + self.dim.lock_cantilever_thickness) * self.dim.lock_slot_thickness_coefficient)
        pencil.up(self.dim.box_height)

        return SmartSolid(pencil.extrude(self.dim.lock_length_bottom + self.dim.box_taper_diff * 2))

    # Clones element to create a row of sockets
    def create_row(self, element: SmartSolid) -> SmartSolid:
        return element.clone(self.dim.sockets_per_row, Vector(self.dim.socket_side + self.dim.socket_padding, 0))

dimensions = PowerAdapterBoxDimensions()
power_adapter_box = PowerAdapterBox(dimensions)
power_adapter_lid = PowerAdapterLid(dimensions)

def export_3mf(box: SmartSolid, prongs, lid: SmartSolid, text: SmartSolid):
    export(lid)
    # export(text)

    # box.align_zxy(lid, Alignment.RR, -dimensions.lid_height - dimensions.box_wider_height)
    # export(box)
    # export(prongs)

    save_3mf("models/other/power_adapters/export.3mf", True)

def export_stl(box: SmartSolid, prongs: SmartSolid, lid: SmartSolid, text: SmartSolid):
    clear()

    lid.orient((180, 0, 0))
    text.orient((180, 0, 0)).align_zxy(lid, Alignment.LR)

    export(box)
    export(prongs)
    export(lid)
    export(text)

    save_stl("models/other/power_adapters/stl")


box_solid, prongs_solid = power_adapter_box.create_box()
lid_solid, text_solid = power_adapter_lid.create_lid()

export_3mf(box_solid, prongs_solid, lid_solid, text_solid)
# export_stl(box_solid, prongs_solid, lid_solid, text_solid)
