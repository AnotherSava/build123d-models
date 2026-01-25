from dataclasses import dataclass, field
from math import tan, radians
from typing import Tuple

from build123d import Vector, Plane, Axis, Location, Face, Polyline, extrude

from sava.csg.build123d.common.exporter import export, save_3mf, clear, save_stl, show_red, show_blue
from sava.csg.build123d.common.geometry import create_vector, Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.primitives import create_tapered_box, create_tapered_box_delta
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartsolid import SmartSolid
from sava.csg.build123d.common.sweepsolid import SweepSolid
from sava.csg.build123d.common.text import TextDimensions, create_text


class RecessDimensions:
    top_angle: float = 77.0
    top_length: float = 39.2
    top_length_flat: float = 21.7

    side_flat_length: float = 23.6
    side_angle: float = -10.0

    bottom_length: float = 24.5
    bottom_length_flat: float = 15.6

    depth_bottom: float = 7
    depth_top: float = 3
    top_fillet_radius: float = 7.0


class LockDimensions:
    length: float = 20.0  # snap lock length at top
    length_bottom: float = 16.0  # snap lock length at bottom (tapered)
    length_padding: float = 0.3  # gap between cantilever and lid, and between protrusion on box and lid

    reinforcement_thickness: float = 1.6  # thickness of reinforcement bulge
    cantilever_thickness: float = 1.6  # thickness of flexible cantilever arm
    tip_thickness: float = 1.5  # thickness of the catch tip
    slot_thickness_coefficient: float = 1.2  # multiplier for slot width clearance
    slot_radius: float = 2.5  # rounded corner radius in lock slot

    height: float =15  # height of the lock mechanism above the box level
    reinforcement_height: float = 10.0  # height of reinforcement bulge
    reinforcement_height_extra: float = 3  # height of reinforcement bulge thinning down
    cantilever_attachment_height: float = 3  # distance between box and cantilever getting flat along the wall
    tip_distance: float = 4.0  # distance from box top to catch point
    tip_height: float = None  # height of catch point from box bottom (computed)
    hook_gap: float = 0.3  # clearance between hook and catch point
    tip_gap: float = 0.3  # minimal clearance tip end and bottom of the box

    hook_angle: float = 30

    reinforcement_length_extra: float = 10.0  # length of reinforcement bulge thinning to the sides (combined)



@dataclass
class PowerAdapterBoxDimensions:
    recess: RecessDimensions = field(default_factory=RecessDimensions)
    lock: LockDimensions = field(default_factory=LockDimensions)
    text: TextDimensions = field(default_factory=lambda: TextDimensions(font_size=24, font="Liberation Sans", height=0.552))
    socket_text: TextDimensions = field(default_factory=lambda: TextDimensions(font_size=12, font="Liberation Sans", height=0.8))

    label: str = "Travel Adapter Set"
    socket_side: float = 36.0
    socket_padding: float = 4.0
    box_length_padding: float = 6
    sockets_per_row: int = 6
    floor_thickness: float = 2
    box_fillet_radius: float = 5.0
    protrusion_side_delta: float = 4.0
    protrusion_fillet_radius: float = 1.0
    lid_fillet_radius: float = 0.3
    box_taper_diff: float = 0.6

    lid_internal_height: float = 63.0
    lid_ceiling_thickness: float = 1.012

    lid_wall_thickness: float = 2

    box_width: float = 100.0

    @property
    def lock_shift_from_centre(self) -> float:
        # Centre of the first socket recess
        row_half_width = self.get_side_length(self.sockets_per_row) / 2
        first_socket_centre = self.socket_padding + self.socket_side / 2
        return row_half_width - first_socket_centre

    def __post_init__(self):
        box_max = self.box_height - self.lock.tip_distance - self.lock.tip_gap
        tip_max = (self.lock.tip_thickness + self.lock.cantilever_thickness) / tan(radians(self.lock.hook_angle))

        self.lock.tip_height = min(box_max, tip_max)

    @property
    def lid_length_internal(self):
        return self.box_length - self.lid_wall_thickness * 2

    @property
    def lid_width_internal(self):
        return self.box_width - self.lid_wall_thickness * 2

    @property
    def lid_cutout_height(self):
        return self.box_height / 8 * 7

    @property
    def lid_height(self):
        return self.lid_cutout_height + self.lid_internal_height + self.lid_ceiling_thickness

    @property
    def box_length(self):
        return self.get_side_length(self.sockets_per_row) + self.box_length_padding

    @property
    def box_height(self):
        return self.floor_thickness + self.recess.depth_bottom + self.recess.depth_top

    @property
    def box_wider_height(self):
        return self.box_height - self.lid_cutout_height

    def get_side_length(self, socket_count: int):
        return self.socket_side * socket_count + self.socket_padding * (socket_count + 1)

class PowerAdapterBase:
    def __init__(self, dim: PowerAdapterBoxDimensions):
        self.dim = dim

    # Creates tapered box protrusion that connects box and lid
    def create_protrusions(self, filleted: bool):
        protrusion_base_length = self.dim.lock.length + self.dim.lock.length_padding * 2 + self.dim.protrusion_side_delta
        radius = self.dim.protrusion_fillet_radius if filleted else 0
        protrusion = create_tapered_box(protrusion_base_length, self.dim.box_width, self.dim.lid_cutout_height, protrusion_base_length - self.dim.box_taper_diff * 2, self.dim.box_width, radius)
        return protrusion.clone(2, (self.dim.lock_shift_from_centre * 2, 0))

    def orient(self, solid: SmartSolid, base: SmartSolid):
        result = []
        solid.align_z(base, Alignment.LR)
        for orientation, alignment in [[270, Alignment.LR], [90, Alignment.RL]]:
            for direction in [-1, 1]:
                copy = solid.oriented((0, 0, orientation)).align_x(base, Alignment.C, self.dim.lock_shift_from_centre * direction).align_y(base, alignment)
                result.append(copy)
        return SmartSolid(result)


class PowerAdapterLid(PowerAdapterBase):
    # Creates main lid structure with snap locks and text cutout
    def create_lid(self) -> Tuple[SmartSolid, SmartSolid, SmartSolid]:

        lid = SmartBox(self.dim.box_length, self.dim.box_width, self.dim.lid_height, label="lid")
        lid_internal = SmartBox(lid.x_size - self.dim.lid_wall_thickness * 2, lid.y_size - self.dim.lid_wall_thickness * 2, lid.z_size - self.dim.lid_ceiling_thickness)
        lid_internal.align_xy(lid).align_z(lid, Alignment.LR)

        lid.cut(lid_internal).fillet_z(self.dim.box_fillet_radius)

        lock_bottom = SmartBox(self.dim.lid_wall_thickness, self.dim.lock.length + self.dim.lock.length_padding * 2, self.dim.lock.height + self.dim.lid_cutout_height)
        lid.cut(self.orient(lock_bottom, lid))

        box_protrusions = self.create_protrusions(False)
        box_protrusions.align_old(lid).align_z(lid, Alignment.LR)
        lid.cut(box_protrusions)

        lid.fillet_positional(self.dim.lid_fillet_radius, Axis.X, *box_protrusions.create_positional_filters_plane(Plane.YZ))

        thinning = self.create_snap_thinning()
        snap = self.create_snap().align_zxy(thinning, Alignment.LR).intersect(thinning)

        snaps = SmartSolid(self.orient(snap, lid), label="snaps").align_z(lid, Alignment.LR, self.dim.lid_cutout_height -self.dim.lock.tip_distance - self.dim.lock.tip_height)

        text = create_text(self.dim.text, self.dim.label, "text")
        text.align_zxy(lid, Alignment.RL)

        # return lid.cut(snaps), snaps, text.connected()
        return lid.cut(snaps, text), snaps, text

    # Creates profile for thinning snap lock cantilever
    def create_snap_thinning(self) -> SmartSolid:
        dim = self.dim.lock

        pencil = Pencil(Plane.YZ)
        pencil.right(dim.length_bottom / 2)
        pencil.up(dim.tip_distance + dim.tip_height)
        pencil.double_arc(Vector((dim.length - dim.length_bottom) / 2, dim.height - dim.reinforcement_height / 2))

        pencil.up(dim.reinforcement_height / 2 - self.dim.lock.length_padding / 4)
        pencil.arc_with_radius(self.dim.lock.length_padding / 2, -90, -180)
        pencil.down(self.dim.lock.reinforcement_height / 2 - self.dim.lock.length_padding / 4)
        pencil.right(dim.reinforcement_length_extra / 2 - self.dim.lock.length_padding)
        pencil.up(self.dim.lock.reinforcement_height)
        pencil.left()
        thickness = max(dim.reinforcement_thickness + self.dim.lid_wall_thickness, dim.slot_radius + dim.cantilever_thickness)
        return pencil.extrude_mirrored_y(thickness)

    # Creates cantilever snap lock that clips into box
    def create_snap(self) -> SmartSolid:
        # Sketch (XZ plane):
        #
        #       G--F
        #       |  |
        #       |  |
        #       H  E
        #      /  /
        #     /  /     <- box top level
        #    I  D
        #    |  |
        #    |  C-B
        #    |   /
        #    J--A
        #

        dim = self.dim.lock
        pencil = Pencil(Plane.XZ)

        # A → B: from origin to tip base
        pencil.jump(Vector(self.dim.lock.tip_height * tan(radians(dim.hook_angle)), self.dim.lock.tip_height))
        # B → C: tip bottom edge
        pencil.left(dim.tip_thickness)
        # C → D: tip outer edge / catch surface
        pencil.up(dim.tip_distance - dim.slot_radius)

        # D → E: S-curve to cantilever base
        arc_destination_vector = Vector(dim.slot_radius, dim.slot_radius + dim.cantilever_attachment_height)
        pencil.double_arc(arc_destination_vector)

        # E → F: cantilever vertical arm
        pencil.up(dim.height - dim.cantilever_attachment_height - dim.reinforcement_height / 2 - dim.reinforcement_height_extra)
        # F → G: lid wall attachment
        pencil.left(dim.cantilever_thickness)

        # G → H: inner cantilever vertical arm
        pencil.down(dim.height - dim.cantilever_attachment_height - dim.reinforcement_height / 2 - dim.reinforcement_height_extra)

        # H → I: S-curve back towards inner edge, tension=0.57
        pencil.double_arc(-arc_destination_vector, 0.75)

        # I → J: inner edge down to base
        pencil.down()

        solid = pencil.extrude(dim.length)

        reinforcement = self.create_reinforcement(dim.length, dim.reinforcement_length_extra, dim.cantilever_thickness, self.dim.lid_wall_thickness, dim.reinforcement_thickness, dim.reinforcement_height, dim.reinforcement_height_extra)
        reinforcement.orient((0, 0, 180)).align_y(solid).align_z(solid, Alignment.RR).align_x(solid, Alignment.RL)

        return solid.fuse(reinforcement)

    def create_reinforcement(self, length: float, length_extra: float, thickness_bottom: float, thickness_top: float, thickness_extra: float, height: float, height_extra: float) -> SmartSolid:

        pencil = Pencil(Plane.XZ)
        pencil.right(thickness_bottom)
        pencil.up(height_extra)
        pencil.double_arc(Vector(thickness_extra + (thickness_top - thickness_bottom) / 2, height / 2))
        pencil.double_arc(Vector(-thickness_extra + (thickness_top - thickness_bottom) / 2, height / 2))
        pencil.left(thickness_top)
        side = pencil.create_face()

        left = (0, 0, 0)
        extra_left = (0, -length_extra / 2, 0)
        middle = (0, length / 2, -height_extra)
        right = (0, length, 0)
        extra_right = (0, length + length_extra / 2, 0)

        top_sweep = SweepSolid(side, Polyline(extra_left, extra_right), Plane.YZ)
        bottom_sweep = SweepSolid(side, Polyline(left, middle, right), Plane.YZ)


        middle_face = Face(Polyline(left, middle, right, close=True))
        middle_section = extrude(middle_face, thickness_extra + (thickness_top + thickness_bottom) / 2, (1, 0, 0)).move(Location((0, 0, height_extra + height / 2)))

        cut = SmartBox(thickness_bottom, length, height_extra)
        cut.align_xz(bottom_sweep, Alignment.LR).align_y(bottom_sweep)

        return SmartSolid(bottom_sweep, top_sweep, middle_section).cut(cut)


class PowerAdapterBox(PowerAdapterBase):
    # Assembles complete box with socket recesses and lock slots
    def create_box(self) -> tuple[SmartSolid, SmartSolid]:
        box_top = create_tapered_box_delta(self.dim.lid_length_internal, self.dim.lid_width_internal, self.dim.lid_cutout_height, -self.dim.box_taper_diff, self.dim.box_fillet_radius)

        box_protrusions = self.create_protrusions(True)
        box_protrusions.align_old(box_top)

        box_bottom = SmartBox(self.dim.box_length, self.dim.box_width, self.dim.box_wider_height).fillet_z(self.dim.box_fillet_radius)
        box_bottom.align_zxy(box_top, Alignment.LL)

        box = SmartSolid(box_top, box_bottom, box_protrusions, label="box")

        recesses, texts = self.create_socket_recesses(box)
        box.cut(recesses, texts)

        slots = self.orient(self.create_lock_slot(), box)
        box.cut(slots)

        socket_texts = SmartSolid(texts, label="socket types")
        return box, socket_texts

    # Creates all socket recesses with type labels (12 international socket types)
    def create_socket_recesses(self, box: SmartSolid) -> tuple[list[SmartSolid], list[SmartSolid]]:
        socket_types = [["A", "B", "C", "D", "E/F", "G"], ["N", "M", "L", "J", "I", "H"]]
        recesses = []
        texts = []
        for row, row_types in enumerate(socket_types):
            for col, label in enumerate(row_types):
                recess, text = self.create_socket_recess_at(row, col, label, box)
                recesses.append(recess)
                texts.append(text)
        return recesses, texts

    # Creates shaped recess for one power adapter socket, positioned relative to box
    def create_socket_recess_at(self, row: int, col: int, label: str, box: SmartSolid) -> tuple[SmartSolid, SmartSolid]:
        dim = self.dim.recess

        pencil = Pencil()
        pencil.right(dim.top_length_flat / 2)
        pencil.arc_with_vector_to_intersection(Vector((dim.top_length - dim.top_length_flat) / 2, 0, 0), dim.top_angle)
        pencil.arc_with_destination(create_vector(dim.side_flat_length, dim.top_angle + 90), dim.side_angle)
        pencil.arc_with_vector_to_intersection(create_vector((dim.bottom_length - dim.bottom_length_flat) / 2, dim.top_angle + 90), 180 - dim.top_angle)
        pencil.left(pencil.location.X)
        recess_bottom = pencil.extrude_mirrored_y(dim.depth_bottom)

        recess_top = SmartBox(self.dim.socket_side, self.dim.socket_side, dim.depth_top).fillet_z(dim.top_fillet_radius)
        recess_top.align_zxy(recess_bottom, Alignment.RR)

        recess = SmartSolid(recess_bottom, recess_top)
        text = create_text(self.dim.socket_text, label)
        if row == 1:
            recess.orient((0, 0, 180))
            text.rotate(Axis.Z, 180)

        # Position recess relative to box based on row/col
        x_offset = (self.dim.socket_padding + self.dim.socket_side) * (col - 2.5)
        y_offset = (self.dim.socket_padding + self.dim.socket_side) * (row - 0.5)
        recess.align_x(box, Alignment.C, x_offset).align_y(box, Alignment.C, y_offset).align_z(box, Alignment.RL)

        # Create socket type text centred on the recess floor (engraved)
        text.align_zxy(recess, Alignment.LL)
        # show_red(text.connected().orient((0, 0, 180)))

        return recess, text

    # Creates slot in box for snap lock tip
    def create_lock_slot(self) -> SmartSolid:
        pencil = Pencil(Plane.XZ)

        pencil.arc_with_radius(self.dim.lock.slot_radius, 180, 90)
        pencil.down_to(self.dim.lock.hook_gap - self.dim.lock.tip_distance)
        pencil.right(self.dim.lock.slot_radius)
        pencil.down_to(-self.dim.box_height)
        pencil.left(self.dim.lock.slot_radius + (self.dim.lock.tip_thickness + self.dim.lock.cantilever_thickness) * self.dim.lock.slot_thickness_coefficient)
        pencil.up()

        return pencil.extrude(self.dim.lock.length_bottom + self.dim.box_taper_diff * 2)


dimensions = PowerAdapterBoxDimensions()
power_adapter_box = PowerAdapterBox(dimensions)
power_adapter_lid = PowerAdapterLid(dimensions)

def export_3mf(box: SmartSolid, socket_texts: SmartSolid, lid: SmartSolid, snaps: SmartSolid, text: SmartSolid):
    # clear()
    export(lid.fuse(snaps), "lid")
    export(text)

    box.align_zxy(lid, Alignment.RR, -dimensions.lid_height - dimensions.box_wider_height)
    socket_texts.colocate(box)

    export(box)
    export(socket_texts)

    save_3mf("models/other/power_adapters/export.3mf", True)

def export_stl(box: SmartSolid, socket_texts: SmartSolid, lid: SmartSolid, snaps: SmartSolid, text: SmartSolid):
    clear()

    lid.orient((180, 0, 0))
    snaps.colocate(lid)
    text.colocate(lid)

    export(box)
    export(socket_texts)
    export(lid.fuse(snaps), "lid")
    export(text)

    save_stl("models/other/power_adapters/stl")


box_solid, socket_texts_solid = power_adapter_box.create_box()
lid_solid, snaps_solid, text_solid = power_adapter_lid.create_lid()

export_3mf(box_solid, socket_texts_solid, lid_solid, snaps_solid, text_solid)
export_stl(box_solid, socket_texts_solid, lid_solid, snaps_solid, text_solid)
