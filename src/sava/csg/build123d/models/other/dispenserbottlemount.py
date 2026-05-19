import math
from dataclasses import dataclass

from build123d import Axis

from sava.csg.build123d.common.exporter import export_3mf, export_stl
from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartercone import SmarterCone, InnerMode
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass(frozen=True)
class DispenserBottleMountDimensions:
    # --- Dispenser housing ---
    dispenser_inner_diameter_min: float = 71
    dispenser_inner_diameter_max: float = 71.5
    dispenser_outer_diameter: float = 76
    thickness_wall: float = 2

    # --- Dispenser support wedges + cut_holder tolerances ---
    angle_padding: float = 1            # angular shrink applied to cut_angle for cut_holder
    tight_padding: float = 0.0          # radial shrink applied to cut_length for the supports / cut_holder
    support_bottom_angle: float = 20    # angular full-width of each support_bottom wedge
    support_bottom_height: float = 3.0
    support_middle_angle: float = 30    # angular full-width of each support_middle wedge
    support_top_height: float = 3.0

    # --- Iris diaphragm (the dispenser's bottle-slot mechanism) ---
    blade_thickness: float = 20.0    # blade main body (Z extrusion of the petal silhouette)
    plate_thickness: float = 3.0  # diaphragm plate disc
    plate_min_thickness: float = 0.0      # minimum floor left under the plate slot pocket (can be 0)
    plate_cut_through: bool = True # extend slots all the way to the side
    plate_slot_length_coefficient: float = 0.7 # length of the slot coefficient (1 for full possible length)
    plate_slot_width: float = 2.5   # Y-extent of the plate's slot pockets the blade protrusion rides in
    cover_thickness: float = 2.0    # front cover disc
    pin_diameter: float = 3      # blade pivot pin
    pin_height: float = 4.0         # blade pivot pin
    pin_padding: float = 0.25       # radial clearance between pin and cover stadium walls
    bore_diameter: float = 35.0    # central through-hole, shared by plate and cover
    cut_length: float = 5.0         # radial depth of the six decorative cuts on the plate's outer edge
    cut_angle: float = 10.0         # angular full-width (deg) of each decorative outer-edge cut
    cut_angle_shift: float = 15     # angular offset of decorative notches relative to the slot polar pattern (puts them between adjacent slots)
    wall_padding: float = 0.1           # radial clearance between iris outer rim (plate, cover ring) and dispenser inner wall
    blade_vertical_padding: float = 0.5 # vertical clearance between blade body and support_middle top
    above_dispenser_height: float = 10  # Z extent of the iris stack that protrudes above the dispenser top

    # --- Derived ---
    @property
    def dispenser_outer_radius(self) -> float:
        return self.dispenser_outer_diameter / 2

    @property
    def dispenser_inner_diameter_min_radius(self) -> float:
        return self.dispenser_inner_diameter_min / 2

    @property
    def support_middle_height(self) -> float:
        """Height of each support_middle wedge — covers the portion of the
        blade that sits below the dispenser top (`blade_thickness − above_dispenser_height`)
        plus the top-wall thickness and a vertical clearance over the blade."""
        return self.blade_thickness - self.above_dispenser_height + self.thickness_wall + self.blade_vertical_padding

    @property
    def cut_holder_height(self) -> float:
        """Total Z extent of the cut_holder teardrop — spans support_middle,
        support_top, and the bottom wall thickness so it reaches from below
        the bottom of support_bottom up to the top of support_top."""
        return self.support_middle_height + self.support_top_height + self.thickness_wall

    @property
    def protrusion_thickness(self) -> float:
        """Blade back-protrusion thickness, equal to the depth of the plate
        slot pocket. Derived so the pocket leaves `min_thickness` of plate
        material below it."""
        return self.plate_thickness - self.plate_min_thickness

    @property
    def pin_radius(self) -> float:
        return self.pin_diameter / 2

    @property
    def bore_radius(self) -> float:
        return self.bore_diameter / 2

    @property
    def plate_radius(self) -> float:
        """Iris outer disc radius, sized to fit inside the dispenser inner
        wall with `wall_padding` radial clearance (so the iris doesn't bind
        against the dispenser housing)."""
        return self.dispenser_inner_diameter_min_radius - self.thickness_wall - self.wall_padding

    @property
    def cover_slot_width(self) -> float:
        """Width of the cover stadium slot, sized so the pin has `pin_padding`
        of clearance on each side."""
        return self.pin_diameter + self.pin_padding


class DispenserBottleMount:
    # Source-mesh anchor for stadium 0 in cover-local frame: slot 0 long axis lies
    # along +X by construction; the anchor is rotated by -12.928° from the raw
    # source-mesh (28.999, -5.305) so slot 0 aligns with +X while preserving the
    # 23.295° tilt of the slot relative to its radial direction, then scaled by
    # 0.9 to match the rest of the model's XY shrink. The actual centre used by
    # `_cover_stadium_center` is shifted along the long axis (+X) so the pin
    # travel is symmetric around it.
    _COVER_STADIUM_ANCHOR = (24.3702, -10.4949)

    def __init__(self, dim: DispenserBottleMountDimensions):
        self.dim = dim

    @property
    def _slot(self) -> SmartBox:
        """Plate slot pocket geometry (also the anchor used to align blades).

        The slot's inner X edge is anchored at x = -24.4233 (radially inner);
        `slot_length` grows the slot outward. Slot 0 lies along +X (source-mesh
        slot orientation -76.955° + 76.955° world rotation = 0°); centre rotated
        by the same 76.955°.
        """
        dim = self.dim
        slot_length = 35.1 * dim.plate_slot_length_coefficient
        return SmartBox(slot_length, dim.plate_slot_width, dim.protrusion_thickness).move(slot_length / 2 - 24.4233, 23.8221, dim.plate_min_thickness)

    # ------------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------------

    @staticmethod
    def _create_protrusion(width: float, thickness: float, align_to: SmartSolid) -> SmartSolid:
        """Build a back-protrusion slab and attach it under the back of `align_to`.

        The XY footprint is a right trapezoid: `length_base` long along +X, `width`
        deep along -Y, with the trailing edge canted at `angle` so it tracks the
        body's B-C edge (28.78° off the Y axis). `thickness` is the Z extrusion.

        Alignment is x(LR) y(LR) z(LL): the slab's left-X and low-Y line up with
        `align_to`'s left-X and low-Y, and its top-Z sits at `align_to`'s bottom-Z
        — i.e. the slab hangs below `align_to`. Stacking via repeated calls (used
        by `create_blade` when `plate_cut_through` is on) keeps stepping further
        down because each fuse moves `align_to.z_min` down.
        """
        length_base = 14.07
        angle = -38.7829

        back_protrusion = Pencil()
        back_protrusion.down(width)
        back_protrusion.right(length_base)
        back_protrusion.up_to(0, angle)
        back_protrusion_body = back_protrusion.extrude(thickness)
        back_protrusion_body.align(align_to).x(Alignment.LR).y(Alignment.LR).z(Alignment.LL)
        return back_protrusion_body

    @staticmethod
    def _create_outer_edge_cutter(outer_radius: float, cut_angle: float, cut_length: float, thickness: float) -> SmartSolid:
        """Decorative outer-edge cutter: an arc along a disc of `outer_radius`
        spanning `cut_angle` degrees, mirrored across Y into a teardrop reaching
        `cut_length` inward from the rim, extruded `thickness` along Z."""
        pencil = Pencil()
        pencil.arc_with_radius(outer_radius, 180, cut_angle / 2)
        pencil.jump_to((0, -cut_length))
        return pencil.extrude_mirrored_y(thickness)

    # ------------------------------------------------------------------------
    # Iris diaphragm (bottle-slot mechanism)
    # ------------------------------------------------------------------------

    def create_blade(self, slot_position: float) -> SmartSolid:
        """Create a single iris blade aligned into `self._slot`.

        The blade is a 2.5D stepped extrusion with three stacked layers along +Z:
          - back protrusion (small strip behind the body's back face)
          - main body
          - cylindrical pivot pin extending forward from the body's front face

        The petal silhouette, back protrusion, and pivot pin geometry are reconstructed
        from the reference STL via `sava.csg.build123d.reconstruct`. The XY shape is
        fixed by the source mesh; Z thicknesses come from `self.dim`. `create_blades`
        handles arrangement around the iris axis. Z layout (before slot alignment):
        - Back protrusion: Z in [-dim.protrusion_thickness, 0].
        - Main body:       Z in [0, dim.blade_thickness].
        - Pivot pin:       Z in [dim.blade_thickness, dim.blade_thickness + dim.pin_height].

        When `dim.plate_cut_through` is on, two extra slabs are stacked further
        below the back protrusion to form a captive tab — see the cut-through block.
        """
        dim = self.dim
        # Main body (front-cap silhouette, the 6-gon)
        body = Pencil()
        body.jump((6.1722, 7.6824))
        body.draw(18.6687, 30)
        body.left(0.5193)
        body.draw(20.7846, 150)
        body.down()
        blade = body.extrude(dim.blade_thickness, label='blade')

        protrusion_width = dim.plate_slot_width - 2 * dim.pin_padding
        back_protrusion_body = self._create_protrusion(protrusion_width, dim.protrusion_thickness, blade)
        blade.fuse(back_protrusion_body)

        if dim.plate_cut_through:
            # Captive tab below the plate: a `pin_padding * 2` shim that clears the
            # plate floor, then a wider slab (Y wider than the plate slot) that
            # latches under the plate so the blade can't lift back through the slot.
            blade.fuse(self._create_protrusion(protrusion_width, dim.pin_padding * 2, blade))
            blade.fuse(self._create_protrusion(dim.plate_slot_width * 1.5, protrusion_width, blade))

        # Cylindrical pivot pin standing on the body's front face
        pivot_pin = SmarterCone.cylinder(dim.pin_radius, dim.pin_height)
        pivot_pin.align(blade).y(Alignment.LR).z(Alignment.RR)
        blade.fuse(pivot_pin)
        blade.rotate_z(180)

        slot = self._slot
        blade.align(slot).x(Alignment.RL, slot_position * (back_protrusion_body.x_size - slot.x_size)).y(Alignment.RL).z(Alignment.RL, dim.pin_height + dim.blade_thickness)

        return blade

    def create_blades(self, slot_position: float = 0.5) -> list[SmartSolid]:
        """Create all iris blades at the given protrusion-in-slot position.

        `slot_position` is linear in [0, 1]: 0 = innermost slot end, 1 = outermost.
        The blade does NOT rotate around its own pivot — the entire blade slides
        with the protrusion, so the cover is rotated by `_aligned_cover_rotation`
        to keep its stadium holes following the pins.
        """
        blade = self.create_blade(slot_position)
        return [blade.rotated(Axis.Z, i * 60) for i in range(6)]

    def create_diaphragm_plate(self) -> SmartSolid:
        """Diaphragm plate: disc of radius `dim.plate_radius` with a `dim.bore_diameter`
        central bore and six `dim.plate_slot_width × dim.protrusion_thickness` slot
        pockets at the top, in a 6-fold polar pattern around the iris axis. Z thickness
        from `dim.plate_thickness`. Six decorative notches are carved into the outer
        edge between the slot positions, offset by `dim.cut_angle_shift` so they sit
        between adjacent slots (see `cut_length`, `cut_angle`).

        Simplified from the source-mesh reconstruction: the 42-gon source body is
        replaced by its enclosing disc, and the slot polar pattern is centred
        exactly on the iris axis (the source mesh had a ~0.4 mm offset that was
        likely tessellation noise).

        SmartBox is Z-base-aligned, so the slot's bottom sits at `plate_min_thickness`
        above the plate base, making the pocket flush with the plate's top face
        and leaving `plate_min_thickness` of plate material below.
        """
        plate = SmarterCone.base(self.dim.plate_radius, label='diaphragm_plate').inner(self.dim.bore_radius).extend(height=self.dim.plate_thickness)

        plate_cut = self._create_outer_edge_cutter(self.dim.plate_radius, self.dim.cut_angle, self.dim.cut_length, self.dim.plate_thickness)
        plate_cut.align(plate).y(Alignment.RL)

        slot = self._slot
        for i in range(6):
            plate.cut(plate_cut.rotated(Axis.Z, i * 60 + self.dim.cut_angle_shift))
            plate.cut(slot.rotated(Axis.Z, i * 60))
            if self.dim.plate_cut_through:
                # Extend the slot outward past the plate edge so the blade
                # protrusion can be slid in radially during assembly.
                plate.cut(slot.aligned(slot).x(Alignment.LL).done().rotate(Axis.Z, i * 60))

        return plate

    def _pin_axis_in_iris_frame(self, slot_position: float) -> tuple[float, float]:
        """Iris-frame XY of the blade 0 pivot pin axis for `slot_position`.
        Derived from `create_blade`'s placement chain: pin centred on body X mid,
        flush with body's back edge in Y, then blade rotated 180° and aligned to
        the plate slot — yielding a 19.8 mm slide in X and a constant Y."""
        return (0.5535 - 19.8 * slot_position, 24.7221 - self.dim.pin_radius)

    def _cover_stadium_center(self) -> tuple[float, float]:
        """Stadium 0 centre in cover-local frame, shifted along the long axis so
        the pin travel between sp=0 and sp=1 is symmetric around it (equal
        clearance at both stadium ends). The shift preserves perpendicular
        distance to the long axis, so the cover rotation is unaffected."""
        _, sc_y = self._COVER_STADIUM_ANCHOR
        px0, pin_y = self._pin_axis_in_iris_frame(0.0)
        px1, _ = self._pin_axis_in_iris_frame(1.0)
        perp_sq = pin_y ** 2 - sc_y ** 2
        sc_x = (math.sqrt(px0 ** 2 + perp_sq) + math.sqrt(px1 ** 2 + perp_sq)) / 2
        return (sc_x, sc_y)

    def _pin_along_stadium_axis(self, slot_position: float) -> float:
        """Signed distance from stadium 0 centre to the pivot pin axis along the
        (rotated) stadium long axis. Symmetric: `(0) == -(1)`."""
        pin_x, pin_y = self._pin_axis_in_iris_frame(slot_position)
        sc_x, sc_y = self._cover_stadium_center()
        return math.sqrt(pin_x ** 2 + pin_y ** 2 - sc_y ** 2) - sc_x

    def _aligned_cover_rotation(self, slot_position: float) -> float:
        """Degrees to rotate the cover around iris Z so each blade's pivot pin
        lies on the long axis of its corresponding stadium hole.

        The stadium long axis in cover-local frame is the line y=sc_y; its
        perpendicular distance |sc_y| from the cover origin is preserved under
        rotation. Solving for R such that the pin at iris-frame polar
        (pin_r, pin_polar) lies on the rotated line gives
        `R = pin_polar + asin(|sc_y| / pin_r)`.
        """
        pin_x, pin_y = self._pin_axis_in_iris_frame(slot_position)
        pin_r = math.hypot(pin_x, pin_y)
        _, sc_y = self._COVER_STADIUM_ANCHOR
        return math.degrees(math.atan2(pin_y, pin_x) + math.asin(-sc_y / pin_r))

    def create_cover(self) -> SmartSolid:
        """Iris front cover — the cone-stack that caps the housing above the blades.

        Two-stage profile along +Z:
          1. Inner ring (radius = `dim.dispenser_outer_radius − thickness_wall − wall_padding`,
             inner = `dispenser_inner_diameter_max/2 − thickness_wall`) of height
             `above_dispenser_height − thickness_wall − cover_thickness` — fits inside the
             dispenser support's top opening.
          2. Top disc that flares out to `dim.dispenser_outer_radius` and drops the inner
             radius to `dim.bore_radius`, extruded by `dim.cover_thickness`.

        Six stadium clearance slots are cut into the top disc in a 6-fold polar pattern.
        Stadium centre and length come from `_cover_stadium_center` /
        `_pin_along_stadium_axis` so each slot fits the pin's sp=0..1 travel with exactly
        `dim.pin_padding` clearance at each end. Caller is expected to follow up with
        `cover.rotate_z(mount._aligned_cover_rotation(slot_position))` so each stadium
        follows its blade's pivot pin.
        """
        dim = self.dim

        cover = SmarterCone.base(dim.dispenser_outer_radius - dim.thickness_wall - dim.wall_padding, label='cover').inner(dim.dispenser_inner_diameter_max / 2 - dim.thickness_wall)
        cover.extend(height=dim.above_dispenser_height - dim.thickness_wall - dim.cover_thickness)

        cover.extend(radius=dim.dispenser_outer_radius).inner(dim.bore_radius)
        cover.extend(height=dim.cover_thickness)

        slot_length = 2 * abs(self._pin_along_stadium_axis(0.0)) + dim.cover_slot_width
        # Fillet at width/2 minus epsilon (OCCT refuses fillet at exactly half-width).
        slot = SmartBox(slot_length, dim.cover_slot_width, dim.cover_thickness).fillet_z(dim.cover_slot_width / 2 - 0.0001)
        slot.move(*self._cover_stadium_center(), 0)
        slot.align_z(cover, Alignment.RL)
        for i in range(6):
            cover.cut(slot.rotated(Axis.Z, i * 60))

        return cover

    # ------------------------------------------------------------------------
    # Dispenser housing
    # ------------------------------------------------------------------------

    def create_diaphragm_support(self) -> SmartSolid:
        """Dispenser-side housing that the iris diaphragm sits in. Stacks
        three Z layers fused in a 6-fold polar pattern:
          1. `support_bottom` — short wedge that captures the plate's outer rim.
          2. `support_middle` — taller wedge that runs alongside the blade body.
          3. `support_top` — full ring that flares out to `dispenser_outer_diameter`,
             extrudes the top wall thickness, and continues as an inner-only ring
             up to `above_dispenser_height` to receive the cover.

        Six `cut_holder` teardrops (the same outer-edge cutter shape used for the
        plate's decorative notches, but used here as positive geometry) hug the
        support stack on the outer side at each polar position. The whole support
        is rotated by `dim.cut_angle_shift` to align with the plate's decorative
        notch positions.
        """
        dim = self.dim
        cut_length = dim.cut_length - dim.tight_padding

        support_bottom = SmarterCone.base(dim.dispenser_inner_diameter_min_radius, angle=dim.support_bottom_angle)
        support_bottom.inner(dim.dispenser_inner_diameter_min_radius - dim.thickness_wall - cut_length)
        support_bottom.extend(height=dim.support_bottom_height)
        support_bottom.rotate_z(-dim.support_bottom_angle / 2 + 90)

        support_middle = SmarterCone.base(dim.dispenser_inner_diameter_min_radius, angle=dim.support_middle_angle).inner(dim.dispenser_inner_diameter_min_radius - dim.thickness_wall)
        support_middle.extend(height=dim.support_middle_height)
        support_middle.rotate_z(-dim.support_middle_angle / 2 + 90)
        support_middle.align_z(support_bottom, Alignment.RR)

        support_top = SmarterCone.base(dim.dispenser_inner_diameter_min_radius, label="support").inner(dim.dispenser_inner_diameter_min_radius - dim.thickness_wall, mode=InnerMode.RADIUS)
        support_top.extend(height=dim.support_top_height, radius=dim.dispenser_inner_diameter_max / 2)

        support_top.extend(radius=dim.dispenser_outer_radius)
        support_top.extend(height=dim.thickness_wall)

        support_top.extend().inner(dim.dispenser_outer_radius - dim.thickness_wall)
        support_top.extend(height=dim.above_dispenser_height - dim.thickness_wall - dim.cover_thickness)

        support_top.align_z(support_middle, Alignment.RR)

        cut_holder = self._create_outer_edge_cutter(dim.dispenser_inner_diameter_min_radius, dim.cut_angle - dim.angle_padding, cut_length, dim.cut_holder_height)
        cut_holder.align(support_bottom).y(Alignment.RL, -dim.thickness_wall).z(Alignment.RR)

        for i in range(6):
            support_top.fuse(support_bottom.rotated_z(i * 60))
            support_top.fuse(support_middle.rotated_z(i * 60))
            support_top.fuse(cut_holder.rotated_z(i * 60))

        return support_top.rotate_z(dim.cut_angle_shift)


if __name__ == "__main__":
    dim = DispenserBottleMountDimensions()
    slot_position = 1
    mount = DispenserBottleMount(dim)

    # Iris diaphragm (bottle-slot mechanism)
    diaphragm_plate = mount.create_diaphragm_plate()
    blades = mount.create_blades(slot_position=slot_position)

    # Dispenser housing on top of the iris
    diaphragm_support = mount.create_diaphragm_support()
    diaphragm_support.align_z(diaphragm_plate, Alignment.LR, -dim.support_bottom_height)

    cover = mount.create_cover()
    # Lift the cover onto the top of the blade body and rotate it so each
    # stadium hole follows the pivot pin it's tracking.
    cover.rotate_z(mount._aligned_cover_rotation(slot_position))
    cover.align_z(diaphragm_support, Alignment.RL, dim.cover_thickness)


    export_3mf("models/other/dispenser_bottle_mount/export.3mf", diaphragm_plate, *blades, cover, diaphragm_support)
    export_stl("models/other/dispenser_bottle_mount/stl", diaphragm_plate, blades[0], cover, diaphragm_support)
