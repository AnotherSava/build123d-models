from dataclasses import dataclass

from build123d import Plane, Ellipse, extrude

from sava.csg.build123d.common.exporter import export_3mf, export_stl
from sava.csg.build123d.common.geometry import Alignment, Direction
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartercone import SmarterCone
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass(frozen=True)
class CableChannelDimensions:
    length: float = 30.0
    width: float = 15.0
    wall_thickness: float = 1.5
    pin_radius: float = 1
    pin_delta: float = 0.7

    # Total Z height of the channel. The rim section sits at the top (fixed
    # height = rim_height); below it the outer wall and inner cavity wall make
    # up the rest. Increasing total_height stretches the inner cavity wall
    # (default 5.105 mm) and lifts the shoulder accordingly.
    total_height: float = 12.9
    rim_height: float = 3.4

    # V-shaped snap-fit groove cut into the rim's outer face. The apex sits
    # rim_groove_depth inward from the rim outer face, rim_groove_apex_dz above
    # the shoulder. The lower (long) edge of the V drops from the apex straight
    # down to the shoulder; the upper edge is a 45° ramp (rise = run = depth) —
    # see the rim_groove_upper_dz property.
    rim_groove_depth: float = 0.674
    rim_groove_apex_dz: float = 1.75

    # Z extent of the rim's inner face straight section (Y=width/2 - 2*wall_thickness),
    # from rim top down to the start of the inner diagonal.
    rim_inner_face_length: float = 2.4

    @property
    def inner_width(self) -> float:
        return self.width - 2 * self.wall_thickness

    @property
    def outer_wall_height(self) -> float:
        return self.total_height - self.rim_height

    @property
    def rim_outer_offset(self) -> float:
        """Y offset of the rim outer face outward from its default position
        (Y = width/2 - wall_thickness + rim_outer_offset). Positive = toward the
        outer wall — narrows the shoulder ledge and thickens the rim wall at the
        top by the same amount. The cap's inner wall shifts the same way so the
        V-ridge still seats into the V-groove. Default = rim_groove_depth / 2."""
        return self.rim_groove_depth / 2

    @property
    def rim_groove_upper_dz(self) -> float:
        """Z of the V-groove's upper edge above the shoulder. The short ramp is
        45° (rise = run = rim_groove_depth), so this equals apex_dz + depth."""
        return self.rim_groove_apex_dz + self.rim_groove_depth

    @property
    def inner_diag_dz(self) -> float:
        """Z extent of the inner diagonal — parallel to the external V groove lower edge."""
        return self.wall_thickness * self.rim_groove_apex_dz / self.rim_groove_depth

    @property
    def inner_cavity_wall_height(self) -> float:
        """Vertical length of the inner cavity wall at Y = width/2 - wall_thickness,
        between the floor top and the start of the inner diagonal."""
        value = self.total_height - self.wall_thickness - self.rim_inner_face_length - self.inner_diag_dz
        assert value >= self.wall_thickness, f"inner cavity wall too short ({value}) for end hole cuts"
        return value

    @property
    def lock_x_radius(self) -> float:
        return self.inner_width / 2 - self.wall_thickness / 2

    @property
    def lock_y_radius(self) -> float:
        return self.inner_width / 2


class CableChannel:
    """Cable channel and matching snap-on cap. The cap wraps the channel's rim
    section and closes the top opening into a rectangular outer profile; the
    cap's inner V-ridge mates with the V-groove cut into the rim outer face."""

    def __init__(self, dim: CableChannelDimensions):
        self.dim = dim

    def create_straight(self, length: float, hole_start: bool = False, hole_end: bool = False) -> tuple[SmartSolid, SmartSolid]:
        channel = self.create_channel(length, hole_start, hole_end)
        cap = self.create_cap(length)
        cap.align(channel).z(Alignment.RL, self.dim.wall_thickness)
        return channel, cap

    def create_channel(self, length: float, hole_start: bool = False, hole_end: bool = False) -> SmartSolid:
        dim = self.dim
        body = Pencil(Plane.YZ, start=(dim.width / 2, 0))
        body.right(dim.width / 2)                                                            # outer floor
        body.up(dim.outer_wall_height)                                                       # outer wall up
        body.left(dim.wall_thickness - dim.rim_outer_offset)                                 # → A
        body.jump((-dim.rim_groove_depth, dim.rim_groove_apex_dz))                           # A → B
        body.jump((dim.rim_groove_depth, dim.rim_groove_upper_dz - dim.rim_groove_apex_dz))  # B → C
        body.up(dim.rim_height - dim.rim_groove_upper_dz)                                    # C → D
        body.left(dim.wall_thickness + dim.rim_outer_offset)                                 # D → E
        body.down(dim.rim_inner_face_length)                                                 # E → F
        body.jump((dim.wall_thickness, -dim.inner_diag_dz))                                  # F → G
        body.down(dim.inner_cavity_wall_height)                                              # G → H
        channel = body.extrude_mirrored_y(length, label=f"channel_{length}mm")

        if hole_end:
            hole = self.create_hole()
            hole.align(channel).x(Alignment.RR, -dim.lock_x_radius - dim.pin_delta).y(Alignment.CL, dim.pin_radius + dim.pin_delta / 2).z(Alignment.LR)
            channel.cut(hole)

        if hole_start:
            hole = self.create_hole().rotate_z(180)
            hole.align(channel).x(Alignment.LL, dim.lock_x_radius + dim.pin_delta).y(Alignment.CR, -dim.pin_radius - dim.pin_delta / 2).z(Alignment.LR)
            channel.cut(hole)

        return channel

    def bend_right(self, before: SmartSolid, after: SmartSolid, top_cut_height: float = 0, top_cut_length: float = 0):
        before_bevel = before.create_bound_box().bevel(Direction.E, Direction.S, 45)
        after_bevel = after.create_bound_box().bevel(Direction.W, Direction.S, 45)

        if top_cut_height:
            before_bottom = before.intersected(before_bevel.moved(z=-top_cut_height))
            before_top = before.intersected(before_bevel.moved(x=-top_cut_length, z=before.z_size - top_cut_height))
            before_bevel = SmartSolid(before_bottom, before_top)

            after_bottom = after.intersected(after_bevel.moved(z=-top_cut_height)).rotate_z(-90)
            after_top = after.intersected(after_bevel.moved(x=top_cut_length, z=after.z_size - top_cut_height)).rotate_z(-90)
            after_bevel = SmartSolid(after_bottom, after_top)

        after_bevel.align(before_bevel).x(Alignment.RL).y(Alignment.RL)
        return after_bevel.fuse(before_bevel)

    def create_corner_right(self, length_before: float, length_after: float) -> tuple[SmartSolid, SmartSolid]:
        channel_before, cap_before = self.create_straight(length_before, hole_start=True)
        channel_after, cap_after = self.create_straight(length_after, hole_end=True)

        label_suffix = f"_right_{length_before}mm_{length_after}mm"
        channel_right = SmartSolid(self.bend_right(channel_before, channel_after, self.dim.rim_inner_face_length, self.dim.rim_inner_face_length), label=f"channel_{label_suffix}")
        cap_right = SmartSolid(self.bend_right(cap_before, cap_after), label=f"cap_{label_suffix}")

        return channel_right, cap_right

    def create_cap(self, length: float) -> SmartSolid:
        # Built natively in scene orientation: ceiling on top, walls and V-ridges facing down
        # to wrap the channel rim — how the cap sits in the assembled view. It prints best
        # flipped (ceiling flat on the bed, no overhangs), so `bed_orientation` carries that
        # flip and is applied only when exporting STL.
        dim = self.dim
        body = Pencil(Plane.YZ, start=(dim.width / 2, dim.rim_height))
        body.up(dim.wall_thickness)                                                            # ceiling (inner → top)
        body.right(dim.width / 2)                                                              # ceiling → outer
        body.down(dim.rim_height + dim.wall_thickness)                                         # outer wall down
        body.left(dim.wall_thickness - dim.rim_outer_offset)                                   # → A
        body.jump((-dim.rim_groove_depth, dim.rim_groove_apex_dz))                             # A → B
        body.jump((dim.rim_groove_depth, dim.rim_groove_upper_dz - dim.rim_groove_apex_dz))    # B → C
        body.up(dim.rim_height - dim.rim_groove_upper_dz)                                       # C → D
        cap = body.extrude_mirrored_y(length, label=f"cap_{length}mm")
        cap.bed_orientation = (180, 0, 0)

        return cap

    def create_lock(self):
        profile = Ellipse(self.dim.lock_x_radius, self.dim.lock_y_radius)
        lock = SmartSolid(extrude(profile, amount=self.dim.wall_thickness), label='lock')

        cut = SmartBox(self.dim.wall_thickness, lock.y_size - self.dim.wall_thickness * 2, lock.z_size * 0.7)
        cut.align(lock).z(Alignment.RL)
        lock.cut(cut)

        pin = SmarterCone.cylinder(self.dim.pin_radius, self.dim.wall_thickness)
        pin.align(lock).z(Alignment.LL)

        for alignment in [Alignment.RL, Alignment.LR]:
            lock.fuse(pin.align_x(lock, alignment))

        lock.bed_orientation = (180, 0, 0)

        return lock

    def create_hole(self):
        pencil = Pencil()

        extra_angle = 15

        pencil.arc_with_radius(self.dim.pin_radius + self.dim.pin_delta / 2, -90, -180 - extra_angle)
        pencil.arc_with_radius(self.dim.lock_x_radius - self.dim.pin_radius * 2, -80, 25)
        pencil.arc_with_radius(self.dim.lock_x_radius - self.dim.pin_radius * 2 - self.dim.pin_delta, -38, 15)
        pencil.arc_with_radius(self.dim.pin_radius + self.dim.pin_delta / 2, 150, -180)
        pencil.spline_abs((0, 0), (0, 1))

        return pencil.extrude(self.dim.wall_thickness)


if __name__ == "__main__":
    dimensions = CableChannelDimensions()
    cable_channel = CableChannel(dimensions)
    channel_model, _cap_model = cable_channel.create_corner_right(dimensions.length, dimensions.length * 1.5)

    channel_straight_model, _cap_straight_model = cable_channel.create_straight(dimensions.length, True, True)
    channel_straight_model.align(channel_model).x(Alignment.LL).y(Alignment.RL)

    lock_model = cable_channel.create_lock()
    lock_model.align(channel_straight_model).x(Alignment.R).z(Alignment.LR)

    lock_model.rotate_z(50)
    lock_model.align(channel_straight_model).x(Alignment.R).z(Alignment.LR)

    # Assembled visualization scene first (3MF), then slicer-ready STLs — each part's
    # bed_orientation flips it flat onto the bed during the STL pass.
    export_3mf("models/other/cable_channel/export.3mf", channel_model, lock_model, channel_straight_model)
    export_stl("models/other/cable_channel/stl", channel_model, lock_model, channel_straight_model)
