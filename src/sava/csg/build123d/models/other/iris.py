import math
from dataclasses import dataclass

from build123d import Axis

from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartercone import SmarterCone
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass(frozen=True)
class IrisDimensions:
    blade_thickness: float = 10.0    # blade main body (Z extrusion of the petal silhouette)
    plate_thickness: float = 3.0  # diaphragm plate disc
    plate_min_thickness: float = 0.0      # minimum floor left under the plate slot pocket (can be 0)
    plate_cut_through: bool = True # extend slots all the way to the side
    plate_slot_length_coefficient: float = 0.7 # length of the slot coefficient (1 for full possible length)
    plate_slot_width: float = 2.5
    cover_thickness: float = 2.0    # front cover disc
    pin_diameter: float = 3      # blade pivot pin
    pin_height: float = 4.0         # blade pivot pin
    pin_padding: float = 0.25       # radial clearance between pin and cover stadium walls
    bore_diameter: float = 35.0    # central through-hole, shared by plate and cover
    outer_diameter: float = 71.0    # outer disc, shared by plate and cover
    cut_length: float = 5.0
    cut_angle: float = 10.0

    # aperture_diameter_min: float = 25.0
    # aperture_diameter_max: float = 35.0
    # pcd_radius: float = 30.0

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
    def outer_radius(self) -> float:
        return self.outer_diameter / 2

    @property
    def cover_slot_width(self) -> float:
        """Width of the cover stadium slot, sized so the pin has `pin_padding`
        of clearance on each side."""
        return self.pin_diameter + 2 * self.pin_padding

def _create_protrusion(width: float, thickness: float, align_to: SmartSolid) -> SmartSolid:
    length_base = 14.07

    back_protrusion = Pencil()
    back_protrusion.down(width)
    back_protrusion.right(length_base)
    angle = -38.7829
    back_protrusion.up_to(0, angle)
    back_protrusion_body = back_protrusion.extrude(thickness)
    back_protrusion_body.align(align_to).x(Alignment.LR).y(Alignment.LR).z(Alignment.LL)
    return back_protrusion_body

def create_blade(dim: IrisDimensions, slot: SmartBox, slot_position: float) -> SmartSolid:
    """Create a single iris blade aligned into the given plate slot.

    The blade is a 2.5D stepped extrusion with three stacked layers along +Z:
      - back protrusion (small strip behind the body's back face)
      - main body
      - cylindrical pivot pin extending forward from the body's front face

    The petal silhouette, back protrusion, and pivot pin geometry are reconstructed
    from the reference STL via `sava.csg.build123d.reconstruct`. The XY shape is
    fixed by the source mesh; Z thicknesses come from `dim`. `create_blades` handles
    arrangement around the iris axis. Z layout (before slot alignment):
    - Back protrusion: Z in [-dim.protrusion_thickness, 0].
    - Main body:       Z in [0, dim.blade_thickness].
    - Pivot pin:       Z in [dim.blade_thickness, dim.blade_thickness + dim.pin_height].
    """
    # Main body (front-cap silhouette, the 6-gon)
    body = Pencil()
    body.jump((6.1722, 7.6824))
    body.draw(18.6687, 30)
    body.left(0.5193)
    body.draw(20.7846, 150)
    body.down()
    blade = body.extrude(dim.blade_thickness, label='blade')

    protrusion_width = dim.plate_slot_width - 2 * dim.pin_padding
    back_protrusion_body = _create_protrusion(protrusion_width, dim.protrusion_thickness, blade)
    blade.fuse(back_protrusion_body)

    if dim.plate_cut_through:
        blade.fuse(_create_protrusion(protrusion_width, dim.pin_padding * 2, blade))
        blade.fuse(_create_protrusion(dim.plate_slot_width * 1.5, protrusion_width, blade))

    # Cylindrical pivot pin standing on the body's front face
    pivot_pin = SmarterCone.cylinder(dim.pin_radius, dim.pin_height)
    pivot_pin.align(blade).y(Alignment.LR).z(Alignment.RR)
    blade.fuse(pivot_pin)
    blade.rotate_z(180)

    blade.align(slot).x(Alignment.RL, slot_position * (back_protrusion_body.x_size - slot.x_size)).y(Alignment.RL).z(Alignment.RL, dim.pin_height + dim.blade_thickness)

    return blade


def create_diaphragm_plate(dim: IrisDimensions) -> tuple[SmartSolid, SmartBox]:
    """Diaphragm plate: `dim.outer_diameter` disc with a `dim.bore_diameter`
    central bore and six 39 × 2 × dim.protrusion_thickness slot pockets at
    the top, in a 6-fold polar pattern around the iris axis. Z thickness from
    `dim.plate_thickness`.

    Simplified from the source-mesh reconstruction: the 42-gon source body is
    replaced by its enclosing disc, and the slot polar pattern is centred
    exactly on the iris axis (the source mesh had a ~0.4 mm offset that was
    likely tessellation noise).
    """
    plate = SmarterCone.base(dim.outer_radius, label='diaphragm_plate').inner(dim.bore_radius).extend(height=dim.plate_thickness)

    pencil = Pencil()
    pencil.arc_with_radius(dim.outer_radius, 180, dim.cut_angle / 2)
    pencil.jump_to((0, -dim.cut_length))
    plate_cut = pencil.extrude_mirrored_y(dim.plate_thickness)
    plate_cut.align(plate).y(Alignment.RL)

    # SmartBox is Z-base-aligned, so the slot's bottom sits at min_thickness
    # above the plate base, making the pocket flush with the plate's top face
    # and leaving `min_thickness` of plate material below. Slot 0 lies along +X
    # (source-mesh slot orientation -76.955° + 76.955° world rotation = 0°);
    # centre rotated by the same 76.955°.
    slot_length = 35.1 * dim.plate_slot_length_coefficient
    slot = SmartBox(slot_length, dim.plate_slot_width, dim.protrusion_thickness).move(slot_length / 2 - 24.4233, 23.8221, dim.plate_min_thickness)
    for i in range(6):
        plate.cut(plate_cut.rotated(Axis.Z, i * 60 + 15))
        plate.cut(slot.rotated(Axis.Z, i * 60))
        if dim.plate_cut_through:
            plate.cut(slot.aligned(slot).x(Alignment.LL).done().rotate(Axis.Z, i * 60))


    return plate, slot


# Source-mesh anchor for stadium 0 in cover-local frame: slot 0 long axis lies
# along +X by construction; the anchor is rotated by -12.928° from the raw
# source-mesh (28.999, -5.305) so slot 0 aligns with +X while preserving the
# 23.295° tilt of the slot relative to its radial direction, then scaled by
# 0.9 to match the rest of the model's XY shrink. The actual centre used by
# `create_cover` is shifted along the long axis (+X) by `_cover_stadium_center`
# so the pin travel is symmetric around it.
_COVER_STADIUM_ANCHOR = (24.3702, -10.4949)


def _pin_axis_in_iris_frame(dim: IrisDimensions, slot_position: float) -> tuple[float, float]:
    """Iris-frame XY of the blade 0 pivot pin axis for `slot_position`.
    Derived from `create_blade`'s placement chain: pin centred on body X mid,
    flush with body's back edge in Y, then blade rotated 180° and aligned to
    the plate slot — yielding a 19.8 mm slide in X and a constant Y."""
    return (0.5535 - 19.8 * slot_position, 24.7221 - dim.pin_radius)


def _cover_stadium_center(dim: IrisDimensions) -> tuple[float, float]:
    """Stadium 0 centre in cover-local frame, shifted along the long axis so
    the pin travel between sp=0 and sp=1 is symmetric around it (equal
    clearance at both stadium ends). The shift preserves perpendicular
    distance to the long axis, so the cover rotation is unaffected."""
    _, sc_y = _COVER_STADIUM_ANCHOR
    px0, pin_y = _pin_axis_in_iris_frame(dim, 0.0)
    px1, _ = _pin_axis_in_iris_frame(dim, 1.0)
    perp_sq = pin_y ** 2 - sc_y ** 2
    sc_x = (math.sqrt(px0 ** 2 + perp_sq) + math.sqrt(px1 ** 2 + perp_sq)) / 2
    return (sc_x, sc_y)


def _pin_along_stadium_axis(dim: IrisDimensions, slot_position: float) -> float:
    """Signed distance from stadium 0 centre to the pivot pin axis along the
    (rotated) stadium long axis. Symmetric: `(dim, 0) == -(dim, 1)`."""
    pin_x, pin_y = _pin_axis_in_iris_frame(dim, slot_position)
    sc_x, sc_y = _cover_stadium_center(dim)
    return math.sqrt(pin_x ** 2 + pin_y ** 2 - sc_y ** 2) - sc_x


def _aligned_cover_rotation(dim: IrisDimensions, slot_position: float) -> float:
    """Degrees to rotate the cover around iris Z so each blade's pivot pin
    lies on the long axis of its corresponding stadium hole.

    The stadium long axis in cover-local frame is the line y=sc_y; its
    perpendicular distance |sc_y| from the cover origin is preserved under
    rotation. Solving for R such that the pin at iris-frame polar
    (pin_r, pin_polar) lies on the rotated line gives
    `R = pin_polar + asin(|sc_y| / pin_r)`.
    """
    pin_x, pin_y = _pin_axis_in_iris_frame(dim, slot_position)
    pin_r = math.hypot(pin_x, pin_y)
    _, sc_y = _COVER_STADIUM_ANCHOR
    return math.degrees(math.atan2(pin_y, pin_x) + math.asin(-sc_y / pin_r))


def create_cover(dim: IrisDimensions) -> SmartSolid:
    """Iris front cover — the disc that caps the housing in front of the blades.

    Reverse-engineered from the source-mesh reconstruction. XY geometry:
    `dim.outer_diameter` body; `dim.bore_diameter` central through-hole; six
    stadium clearance slots in a 6-fold polar pattern. Stadium centre and length come from helper
    functions so the slot fits the pin's sp=0..1 travel with exactly
    `dim.pin_padding` clearance to each end. `_aligned_cover_rotation` then
    rotates the whole cover so each stadium follows its blade's pivot pin.
    """
    cover = SmarterCone.base(dim.outer_radius, label='iris_cover').inner(dim.bore_radius).extend(height=dim.cover_thickness)

    slot_width = dim.cover_slot_width
    slot_length = 2 * abs(_pin_along_stadium_axis(dim, 0.0)) + slot_width
    # Fillet at width/2 minus epsilon (OCCT refuses fillet at exactly half-width).
    slot = SmartBox(slot_length, slot_width, dim.cover_thickness).fillet_z(slot_width / 2 - 0.0001)
    slot.move(*_cover_stadium_center(dim), 0)
    for i in range(6):
        cover.cut(slot.rotated(Axis.Z, i * 60))

    cover.cut(SmarterCone.cylinder(dim.bore_radius, dim.cover_thickness))

    return cover


def create_blades(dim: IrisDimensions, slot: SmartBox, slot_position: float = 0.5) -> list[SmartSolid]:
    """Create all iris blades at the given protrusion-in-slot position.

    `slot_position` is linear in [0, 1]: 0 = innermost slot end, 1 = outermost.
    The blade does NOT rotate around its own pivot — the entire blade slides
    with the protrusion, so the cover is rotated by `_aligned_cover_rotation`
    to keep its stadium holes following the pins.
    """
    blade = create_blade(dim, slot, slot_position)
    return [blade.rotated(Axis.Z, i * 60) for i in range(6)]


if __name__ == '__main__':
    from sava.csg.build123d.common.exporter import export_3mf, export_stl

    dim = IrisDimensions()
    slot_position = 1
    plate, slot = create_diaphragm_plate(dim)
    blades = create_blades(dim, slot, slot_position=slot_position)
    cover = create_cover(dim)
    # Lift the cover onto the top of the blade body and rotate it so each
    # stadium hole follows the pivot pin it's tracking.
    cover.rotate_z(_aligned_cover_rotation(dim, slot_position))
    cover.move_z(dim.plate_thickness + dim.blade_thickness)

    export_3mf('models/other/iris/iris.3mf', plate, *blades, cover)
    export_stl('models/other/iris/stl', plate, blades[0], cover)
