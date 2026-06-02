from dataclasses import dataclass

from build123d import Plane

from sava.csg.build123d.common.exporter import export_3mf, export_stl
from sava.csg.build123d.common.geometry import Alignment, Direction
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass(frozen=True)
class CableChannelDimensions:
    length: float = 30.0
    width: float = 15.0
    wall_thickness: float = 1.5
    cavity_length: float = 11.0
    cavity_slope_run: float = 0.5

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
    def cavity_top_width(self) -> float:
        return self.width - 2 * self.wall_thickness

    @property
    def cavity_bottom_width(self) -> float:
        return self.cavity_top_width + 2 * self.cavity_slope_run

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
        assert value >= self.wall_thickness, f"inner cavity wall too short ({value}) for end cavity cuts"
        return value


class CableChannel:
    """Cable channel and matching snap-on cap. The cap wraps the channel's rim
    section and closes the top opening into a rectangular outer profile; the
    cap's inner V-ridge mates with the V-groove cut into the rim outer face."""

    def __init__(self, dim: CableChannelDimensions):
        self.dim = dim

    def create_straight(self, length: float, cavities: bool = False) -> tuple[SmartSolid, SmartSolid]:
        channel = self.create_channel(length, cavities)
        cap = self.create_cap(length)
        cap.align(channel).z(Alignment.RL, self.dim.wall_thickness)
        return channel, cap


    def create_channel(self, length: float, cavities: bool = False) -> SmartSolid:
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
        channel = body.extrude_mirrored_y(length, center=0, label='channel')

        if cavities:
            # Trapezoidal cavity cuts at each end: long side along inner floor,
            # non-parallel sides match the source cavity slopes.
            cavity = SmartBox(dim.cavity_length, dim.cavity_bottom_width, dim.wall_thickness, tapered_width=dim.cavity_top_width)
            cavity.move(dim.cavity_length / 2, dim.width / 2, dim.wall_thickness)
            for shift_x in [0, dim.length - dim.cavity_length]:
                channel.cut(cavity.copy().move(shift_x, 0, 0))

        return channel


    def bend_right(self, before: SmartSolid, after: SmartSolid):
        before.bevel(Direction.E, Direction.S, 45)
        after.bevel(Direction.W, Direction.S, 45).rotate_z(-90)
        after.align(before).x(Alignment.RL).y(Alignment.RL)
        return before.fuse(after)

    def create_corder_right(self, length_before: float, length_after: float) -> tuple[SmartSolid, SmartSolid]:
        channel_before, cap_before = self.create_straight(length_before)
        channel_after, cap_after = self.create_straight(length_after)

        return self.bend_right(channel_before, channel_after), self.bend_right(cap_before, cap_after)

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
        cap = body.extrude_mirrored_y(length, center=0, label='cap')
        cap.bed_orientation = (180, 0, 0)

        return cap


if __name__ == "__main__":
    dimensions = CableChannelDimensions()
    cable_channel = CableChannel(dimensions)
    # channel_model, cap_model = cable_channel.create_straight(dimensions.length)
    channel_model, cap_model = cable_channel.create_corder_right(dimensions.length, dimensions.length * 1.5)

    # Assembled visualization scene first (3MF), then slicer-ready STLs — the cap's
    # bed_orientation flips it flat onto the bed during the STL pass.
    # cable_channel.arrange_scene(channel_model, cap_model)
    export_3mf("models/other/cable_channel/export.3mf", channel_model, cap_model)
    export_stl("models/other/cable_channel/stl", channel_model, cap_model)
