from dataclasses import dataclass

from build123d import Axis, Plane, fillet

from sava.csg.build123d.common.edgefilters import filter_edges_by_axis, filter_edges_by_position
from sava.csg.build123d.common.exporter import export_3mf, export_stl
from sava.csg.build123d.common.geometry import Alignment, Direction
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartloft import SmartLoft
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass(frozen=True)
class CableChannelDimensions:
    length: float = 15.0
    width: float = 15.0
    wall_thickness: float = 1.2

    # Puzzle-piece floor connector: each end terminates in an interlocking
    # dovetail (tab on one half, socket on the other) so adjacent channels snap
    # together. The profile is point-symmetric about the end-edge midpoint, so
    # any end mates with any end, in either orientation (genderless). The lock
    # region is built up to lock_thickness (2x floor) and rises into the channel.
    # The joint assembles vertically (one piece drops onto the other) with near-zero
    # clearance, so the top and bottom of the lock height (lock_lead_in_fraction
    # each) are graded as insertion lead-ins: the tab pulls in by lock_lead_in per side toward its
    # top and bottom edges, and the socket opens out by the same amount toward
    # both mouths. Every contact pair then has lead-ins on both parts: the
    # descending tab's tapered bottom meets a flared socket top, and the
    # descending socket's flared bottom passes over a tapered tab top.
    lock_protrusion: float = 3.0   # dovetail depth beyond the joint plane
    lock_offset_y: float = 3.0     # tab/socket centre offset from the channel centreline
    lock_root_half: float = 1.2    # half-width at the root (joint)
    lock_tip_half: float = 2.5     # half-width at the tip (wider -> undercut)
    lock_fillet: float = 0.8       # corner fillet (no sharp stress risers)
    lock_clearance: float = 0.05   # tab<->socket gap for fit
    lock_pad_margin: float = 1.5   # pad reach inboard of the deepest socket point
    lock_lead_in: float = 0.3      # per-side lead-in at the top and bottom edges (tab -, socket +)
    lock_lead_in_fraction: float = 0.25  # fraction of the lock height each lead-in is graded over

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

    # Experimental: fillet radius for the cross-section corners A-D (see the
    # dimensioned draft) — the rim shoulder, V-groove apex, groove upper edge,
    # and rim top corner. Applied to the same trace segments in both the channel
    # and the cap, so the mating profiles stay congruent and the fit stays tight.
    # Keep below ~0.69: the C->D segment (0.976) must fit both corners' trims.
    rim_fillet: float = 0.4

    # Z extent of the rim's inner face straight section (Y=width/2 - 2*wall_thickness),
    # from rim top down to the start of the inner diagonal.
    rim_inner_face_length: float = 2.4

    @property
    def inner_width(self) -> float:
        return self.width - 2 * self.wall_thickness

    @property
    def lock_thickness(self) -> float:
        """Z height of the lock region — twice the floor thickness, so the tab
        and socket are chunky. The extra height rises into the channel interior."""
        return 2 * self.wall_thickness

    @property
    def lock_lead_in_height(self) -> float:
        """Z extent of each graded lead-in zone at the top and bottom of the lock region."""
        return self.lock_lead_in_fraction * self.lock_thickness

    @property
    def lock_pad_inboard(self) -> float:
        """How far the raised lock pad reaches inboard of the joint plane: deep
        enough to fully contain the socket plus a margin of material behind it."""
        return self.lock_protrusion + self.lock_clearance + self.lock_pad_margin

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
        assert value >= self.lock_thickness, f"inner cavity wall too short ({value}) for the lock pad"
        return value


class CableChannel:
    """Cable channel and matching snap-on cap. The cap wraps the channel's rim
    section and closes the top opening into a rectangular outer profile; the
    cap's inner V-ridge mates with the V-groove cut into the rim outer face."""

    def __init__(self, dim: CableChannelDimensions):
        self.dim = dim

    def create_straight(self, length: float, connector_start: bool = False, connector_end: bool = False) -> tuple[SmartSolid, SmartSolid]:
        channel = self.create_channel(length, connector_start, connector_end)
        cap = self.create_cap(length)
        # z only: cap and channel already share x/y natively, and the full align()
        # chain would re-centre the cap onto the channel's bbox — which a connector
        # tab extends asymmetrically, shifting the cap off the rim
        cap.align_z(channel, Alignment.RL, self.dim.wall_thickness)
        return channel, cap

    def create_channel(self, length: float, connector_start: bool = False, connector_end: bool = False) -> SmartSolid:
        dim = self.dim
        body = Pencil(Plane.YZ, start=(dim.width / 2, 0))
        body.right(dim.width / 2)                                                            # outer floor
        body.up(dim.outer_wall_height)                                                       # outer wall up
        body.left(dim.wall_thickness - dim.rim_outer_offset)                                 # → A
        body.fillet(dim.rim_fillet)
        body.jump((-dim.rim_groove_depth, dim.rim_groove_apex_dz))                           # A → B
        body.fillet()
        body.jump((dim.rim_groove_depth, dim.rim_groove_upper_dz - dim.rim_groove_apex_dz))  # B → C
        body.fillet()
        body.up(dim.rim_height - dim.rim_groove_upper_dz)                                    # C → D
        body.fillet()
        body.left(dim.wall_thickness + dim.rim_outer_offset)                                 # D → E
        body.down(dim.rim_inner_face_length)                                                 # E → F
        body.jump((dim.wall_thickness, -dim.inner_diag_dz))                                  # F → G
        body.down(dim.inner_cavity_wall_height)                                              # G → H
        channel = body.extrude_mirrored_y(length, label=f"channel_{length}mm")

        # The tab protrudes outward (East at the +X end, West at the start); the
        # socket is its 180° image cut into the body on the opposite lateral half,
        # so either end mates with any other end.
        if connector_end:
            self._apply_connector(channel, Direction.E)
        if connector_start:
            self._apply_connector(channel, Direction.W)

        return channel

    def _create_dovetail(self, clearance: float = 0) -> SmartBox:
        """The bare dovetail bump in its default pose: width tapers from the root to
        the (wider) tip over the protrusion depth, grown on every side by `clearance`
        (0 for the tab, the fit clearance for the socket). Used by `_create_lock_plate`,
        which rotates, rounds, and mounts it on a slab."""
        dim = self.dim
        return SmartBox(dim.lock_thickness, 2 * (dim.lock_root_half + clearance), dim.lock_protrusion + clearance, tapered_width=2 * (dim.lock_tip_half + clearance))

    def _create_lock_plate(self, sign: int, slab_depth: float, slab_half_width: float, bump_offset: float, clearance: float = 0, lead_in: float = 0) -> SmartSolid:
        """Build, at the origin, a lock-height slab carrying a dovetail bump, rounded so
        the bump's tip corners are convex (outward) while its root corners — where it
        meets the slab — are concave (inward), exactly as the dimensioned draft shows.
        The bump points along `sign`*X and sits `bump_offset` off the slab centreline;
        `clearance` grows it on every side. Returned in a canonical pose — bump root on
        the x=0 plane, slab centred on y=0, base on z=0 — so the caller just moves it.

        `lead_in` grades the bump over the lead-in zones at both ends of the lock
        height: its footprint at the very top and bottom edges is grown by
        `clearance + lead_in` per side, blending linearly to `clearance` over
        lock_lead_in_height. Negative shrinks the tab into an insertion taper;
        positive opens the socket cutter into flared mouths. The slab footprint
        is unaffected (the lofted lead sections keep its walls vertical).

        Rounding happens here at the origin on purpose: the bump is an axis-rotated
        SmartBox, and moving such a solid injects ~1e-7 transform error that makes a
        later fillet fail outright — so it must be rounded before it is placed."""
        dim = self.dim
        slab = SmartBox(slab_depth, 2 * slab_half_width, dim.lock_thickness)
        bump = self._create_dovetail(clearance).rotate_y(90 * sign)
        bump.align(slab).x(Alignment.RR if sign > 0 else Alignment.LL).y(Alignment.C, bump_offset).z(Alignment.C)
        plate = slab.fuse(bump)
        plate.move(x=-sign * slab_depth / 2)   # bump root onto the x=0 plane

        z_edges = filter_edges_by_axis(plate.solid.edges(), Axis.Z)
        tip_x = sign * (dim.lock_protrusion + clearance)
        tip = filter_edges_by_position(z_edges, Axis.X, tip_x - 0.1, tip_x + 0.1, (True, True))
        root_half = dim.lock_root_half + clearance
        root = filter_edges_by_position(z_edges, Axis.X, -0.1, 0.1, (True, True))
        root = filter_edges_by_position(root, Axis.Y, bump_offset - root_half - 0.2, bump_offset + root_half + 0.2, (True, True))
        plate.solid = fillet(list(tip) + list(root), dim.lock_fillet)

        if lead_in:
            # Replace the plate's top and bottom lead-in zones with lofts between the
            # offset footprint (a same-topology plate, bump grown by lead_in) and the
            # nominal footprint — the graded entries from the dimensioned draft.
            offset_plate = self._create_lock_plate(sign, slab_depth, slab_half_width, bump_offset, clearance + lead_in)
            nominal_foot = plate.solid.faces().sort_by(Axis.Z)[0]
            offset_foot = offset_plate.solid.faces().sort_by(Axis.Z)[0]
            lead_bottom = SmartLoft.create(offset_foot, nominal_foot, height=dim.lock_lead_in_height)
            lead_top = SmartLoft.create(nominal_foot, offset_foot, height=dim.lock_lead_in_height).move(z=dim.lock_thickness - dim.lock_lead_in_height)
            plate.cut_z(cut=dim.lock_lead_in_height).cut_z(cut=-dim.lock_lead_in_height).fuse(lead_bottom).fuse(lead_top)
        return plate

    def _apply_connector(self, channel: SmartSolid, direction: Direction) -> None:
        """Add the puzzle connector at the channel end facing `direction`
        (Direction.E = the +X end, Direction.W = the start). Fuse the raised pad +
        dovetail tab, then cut the socket — the tab's 180° image, grown by the fit
        clearance — as a full-depth pocket the mating tab seats into. Tab and socket
        share `_create_lock_plate`: the tab's slab is the raised pad (channel-wide, with
        the bump offset to one half); the socket's slab is a sacrificial flange sitting
        in empty space just outboard of the joint, there only to give its bump a concave
        root so the pocket mouth rounds convex and its interior concave — the exact
        complement of the mating tab."""
        dim = self.dim
        sign = direction.value.X    # +1 East / -1 West
        joint = channel.x_max if direction == Direction.E else channel.x_min

        tab = self._create_lock_plate(sign, dim.lock_pad_inboard, dim.inner_width / 2, sign * dim.lock_offset_y, lead_in=-dim.lock_lead_in)
        tab.move(x=joint, y=channel.y_mid)
        channel.fuse(tab)

        flange_half_width = dim.lock_tip_half + dim.lock_clearance + dim.lock_fillet
        socket = self._create_lock_plate(-sign, dim.lock_protrusion, flange_half_width, 0, dim.lock_clearance, lead_in=dim.lock_lead_in)
        socket.move(x=joint, y=channel.y_mid - sign * dim.lock_offset_y)
        channel.cut(socket)

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
        else:
            before_bevel = before.intersected(before_bevel)
            after_bevel = after.intersected(after_bevel).rotate_z(-90)

        after_bevel.align(before_bevel).x(Alignment.RL).y(Alignment.RL)
        return after_bevel.fuse(before_bevel)

    def bend_down(self, before: SmartSolid, after: SmartSolid, chamfer: float = 0, seam_offset: float = None):
        """Mitre `before`'s end against `after` turned to run downward — the same
        construction as `bend_right`, with the 45° seam in the X-Z plane (about Y):
        the after piece is rotated about Y, so its opening faces +X.

        The seam plane is x - z = `seam_offset`, defaulting to the plane through
        `before`'s outer corner (x_max, z_max). Unlike the right turn, the down
        turn rotates the cap's radial axis (Z) into the alignment axis (X), so a
        cap must be bent with its channel's seam — pass the channel's value —
        or its legs end up radially displaced against the rim.

        `chamfer` cuts the outer corner with a 45° plane perpendicular to the
        seam, spanning `chamfer` along the rim top and down the outer face.
        Unlike bend_right's lap, both legs' width directions coincide (Y) here,
        so no cap wall crosses the other leg's rim — the rim bands can meet at
        the plain seam, and the chamfer only trims the joined outer corner."""
        k = before.x_max - before.z_max if seam_offset is None else seam_offset
        margin = before.x_size + before.z_size
        before_bevel = before.create_bound_box().cut(self._create_corner_prism(
            [(k + before.z_min, before.z_min), (before.x_max + margin, before.z_min), (before.x_max + margin, before.z_max), (k + before.z_max, before.z_max)], before))
        # The after cut stops where the seam exits the before piece (x_max): the
        # before piece cannot reach past its own end, so above that level the
        # after piece keeps the outer corner (matters when z_max > x_max - k,
        # e.g. a cap riding wall_thickness above its channel's seam).
        cut_top = min(after.z_max, before.x_max - k)
        after_bevel = after.create_bound_box().cut(self._create_corner_prism(
            [(after.x_min - 1, after.z_min), (after.x_min + before.z_max - after.z_min, after.z_min), (after.x_min + before.z_max - cut_top, cut_top), (after.x_min - 1, cut_top)], after))

        before_bevel = before.intersected(before_bevel)
        after_bevel = after.intersected(after_bevel).rotate_y(90)

        # Place the down leg so the mirror seam maps levels 1:1 — the after
        # piece's pre-rotation z levels land at x = z + k, its top at before's
        # top. Anchored on the leg's far end and floor bottom, which always
        # survive the plain miter.
        after_bevel.move(x=after.z_min + k - after_bevel.x_min, z=before.z_max - (after.x_max - after.x_min) - after_bevel.z_min)
        corner = after_bevel.fuse(before_bevel)

        if chamfer:
            # Wedge x + z >= x_max + z_max - chamfer: a triangle prism past the
            # 45° chamfer line from (x_max - chamfer, z_max) to (x_max, z_max - chamfer)
            c = before.x_max + before.z_max - chamfer
            z_top, x_out = before.z_max + 1, before.x_max + 1
            corner.cut(self._create_corner_prism([(c - z_top, z_top), (x_out, z_top), (x_out, c - x_out)], corner))
        return corner

    def _create_corner_prism(self, points: list[tuple[float, float]], reference: SmartSolid) -> SmartSolid:
        """Prism over an X-Z polygon (the 45° corner cutter for bend_down),
        spanning the reference solid's full Y extent."""
        pencil = Pencil(Plane.XZ, start=points[0])
        for prev, nxt in zip(points, points[1:]):
            pencil.jump((nxt[0] - prev[0], nxt[1] - prev[1]))
        prism = pencil.extrude(reference.y_size + 2)
        return prism.move(y=reference.y_mid - prism.y_mid)

    def create_corner_right(self, length_before: float, length_after: float) -> tuple[SmartSolid, SmartSolid]:
        channel_before, cap_before = self.create_straight(length_before, connector_start=True)
        channel_after, cap_after = self.create_straight(length_after, connector_end=True)

        label_suffix = f"_right_{length_before}mm_{length_after}mm"
        channel_right = SmartSolid(self.bend_right(channel_before, channel_after, self.dim.rim_inner_face_length, self.dim.rim_inner_face_length), label=f"channel_{label_suffix}")
        cap_right = SmartSolid(self.bend_right(cap_before, cap_after), label=f"cap_{label_suffix}")
        cap_right.bed_orientation = (180, 0, 0)   # like the straight cap: ceiling flat on the bed

        return channel_right, cap_right

    def create_corner_down(self, length_before: float, length_after: float) -> tuple[SmartSolid, SmartSolid]:
        channel_before, cap_before = self.create_straight(length_before, connector_start=True)
        channel_after, cap_after = self.create_straight(length_after, connector_end=True)

        label_suffix = f"_down_{length_before}mm_{length_after}mm"
        # The cap shares the channel's seam plane — see the bend_down docstring on
        # why the down turn couples cap and channel.
        seam_offset = channel_before.x_max - channel_before.z_max
        channel_down = SmartSolid(self.bend_down(channel_before, channel_after, chamfer=2 * self.dim.rim_inner_face_length), label=f"channel_{label_suffix}")
        cap_down = SmartSolid(self.bend_down(cap_before, cap_after, seam_offset=seam_offset), label=f"cap_{label_suffix}")

        # Rest on the 45° outer-corner chamfer face — it becomes the lowest plane
        # (everything past x + z = const is cut away), with both legs rising at 45°
        channel_down.bed_orientation = (0, 135, 0)
        cap_down.bed_orientation = (0, 135, 0)

        return channel_down, cap_down

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
        body.fillet(dim.rim_fillet)
        body.jump((-dim.rim_groove_depth, dim.rim_groove_apex_dz))                             # A → B
        body.fillet()
        body.jump((dim.rim_groove_depth, dim.rim_groove_upper_dz - dim.rim_groove_apex_dz))    # B → C
        body.fillet()
        body.up(dim.rim_height - dim.rim_groove_upper_dz)                                       # C → D
        body.fillet()                                                                           # applies on the mirror builder's closing segment
        # The trace winds clockwise, so the mirrored face's normal points -X and the
        # extrusion runs backwards; shift to the scene pose spanning x 0..length.
        cap = body.extrude_mirrored_y(length, label=f"cap_{length}mm").move(x=length)
        cap.bed_orientation = (180, 0, 0)

        return cap

if __name__ == "__main__":
    dimensions = CableChannelDimensions()
    cable_channel = CableChannel(dimensions)

    channel_model = cable_channel.create_channel(dimensions.length, connector_start=True, connector_end=True)

    # A second piece snapped onto the first end-to-end shows the puzzle joint —
    # B's start end mates with A's end (genderless, so no flipping needed).
    mate_model = cable_channel.create_channel(dimensions.length, connector_start=True, connector_end=True).move(x=dimensions.length)

    # A single double-length cap covers both channels, bridging the puzzle joint.
    cap_model = cable_channel.create_cap(2 * dimensions.length)
    cap_model.align(SmartSolid(channel_model, mate_model)).z(Alignment.RL, dimensions.wall_thickness)

    # Corner pieces with their caps (right in plan, down in elevation), placed
    # beside the straights so the scene bounding boxes stay apart.
    channel_right, cap_right = cable_channel.create_corner_right(30, 45)
    channel_right.move(y=60)
    cap_right.move(y=60)

    channel_down, cap_down = cable_channel.create_corner_down(20, 20)
    channel_down.move(y=90)
    cap_down.move(y=120)

    # Assembled visualization scene first (3MF), then slicer-ready STLs.
    export_3mf("models/other/cable_channel/export.3mf", channel_down)
    # export_3mf("models/other/cable_channel/export.3mf", channel_model, mate_model, channel_right, cap_right, channel_down, cap_down)
    # export_3mf("models/other/cable_channel/export.3mf", channel_model, mate_model, cap_model)
    export_stl("models/other/cable_channel/stl", channel_model, cap_model, channel_right, cap_right, channel_down, cap_down, clean=True)
