import math
from dataclasses import dataclass

from build123d import Axis

from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartercone import SmarterCone
from sava.csg.build123d.common.smartsolid import SmartSolid


# Geometry constants derived from the reference STL `tmp/diaframma/obj_1_Diaf 3.stl`,
# reconstructed via `sava.csg.build123d.reconstruct` (see `docs/code/reconstruct/`).
# The blade is a 2.5D stepped extrusion with three stacked layers along +Z:
#   - 1.5 mm back protrusion (small strip behind the body's back face)
#   - 3 mm main body
#   - 4 mm cylindrical pivot pin extending forward from the body's front face
# The pencil paths in `create_blade` are anchored so the shared body/back-protrusion
# vertex on the datum line sits at local (0, 0); the pivot pin centroid lives at
# (_PIVOT_U, _PIVOT_V) in that same frame.
_BODY_THICKNESS = 3.0
_BACK_PROTRUSION_THICKNESS = 1.5
_PIVOT_PIN_RADIUS = 1.82
_PIVOT_PIN_HEIGHT = 4.0
_PIVOT_U = -3.776
_PIVOT_V = 1.701

# Maximum distance from the pivot to any body silhouette vertex (mm).
# Derived from the source mesh; reaches the tip of the petal at (-3.513, 26.500).
_BODY_MAX_FROM_PIVOT = 24.80

# Total blade Z extent: back protrusion + body + pivot pin.
_BLADE_HEIGHT = _BACK_PROTRUSION_THICKNESS + _BODY_THICKNESS + _PIVOT_PIN_HEIGHT


def _polar(radius: float, angle_deg: float) -> tuple[float, float]:
    """Convert polar coordinates to cartesian (2D)."""
    rad = math.radians(angle_deg)
    return (radius * math.cos(rad), radius * math.sin(rad))


@dataclass(frozen=True)
class IrisDimensions:
    # Defaults derived from the source meshes `obj_1_Diaf 3.stl` (blade) and
    # `obj_8_Diaf 1.stl` (diaphragm plate) so `create_blade(dim)` slots into
    # `create_diaphragm_plate()` without rescaling. See `_LEGACY_DEFAULTS`
    # below for the prior generic defaults — kept for use once the plate
    # becomes parametric and other iris designs are reintroduced.
    blade_count: int = 6                       # 6 polar slots on the plate
    aperture_diameter_min: float = 12.86       # = 2 * (pcd_radius - _BODY_MAX_FROM_PIVOT); blade tip just reaches min radius
    aperture_diameter_max: float = 41.0        # = plate's central bore Ø (2 * 20.5)
    pin_diameter: float = _PIVOT_PIN_RADIUS * 2
    pin_clearance: float = 0.2
    blade_height: float = _BLADE_HEIGHT
    blade_thickness: float = _BODY_THICKNESS
    pcd_radius: float = 31.23                  # places back-protrusion centroid at the plate's slot radius (27.96)
    drive_pin_offset: float = 3.27             # = pcd_radius - slot radius → `drive_pin_radius_from_center` lands on the slot
    drive_pin_height: float = 3.0

    @property
    def aperture_radius_min(self) -> float:
        return self.aperture_diameter_min / 2

    @property
    def aperture_radius_max(self) -> float:
        return self.aperture_diameter_max / 2

    @property
    def blade_angular_span(self) -> float:
        """Angular span of each blade as seen from center, in degrees."""
        return 360.0 / self.blade_count

    @property
    def pivot_hole_radius(self) -> float:
        return self.pin_diameter / 2 + self.pin_clearance

    @property
    def pin_radius(self) -> float:
        return self.pin_diameter / 2

    @property
    def blade_outer_radius(self) -> float:
        """Max radial extent of the blade body from the iris center, in mm."""
        return self.pcd_radius + _BODY_MAX_FROM_PIVOT

    @property
    def rotation_range(self) -> float:
        """Rotation angle in degrees from closed (min aperture) to fully open (max aperture)."""
        lever = self.pcd_radius - self.aperture_radius_min
        cos_delta = (self.pcd_radius ** 2 + lever ** 2 - self.aperture_radius_max ** 2) / (2 * self.pcd_radius * lever)
        return math.degrees(math.acos(max(-1.0, min(1.0, cos_delta))))

    @property
    def drive_slot_arc_length(self) -> float:
        """Arc length traced by the drive pin over the full rotation range."""
        return self.drive_pin_offset * math.radians(self.rotation_range)

    @property
    def drive_pin_radius_from_center(self) -> float:
        """Radial distance of drive pin from iris center (at closed position)."""
        return self.pcd_radius - self.drive_pin_offset


# Generic 5-blade iris configuration used before defaults were aligned with the
# `Diaf 3 + Diaf 1` source-mesh pair. Preserved for re-use once the diaphragm
# plate becomes parametric (so we can drive other iris designs from the same code).
_LEGACY_DEFAULTS = IrisDimensions(
    blade_count=5,
    aperture_diameter_min=25.0,
    aperture_diameter_max=35.0,
    pcd_radius=30.0,
    drive_pin_offset=5.0,
)


def create_blade(dim: IrisDimensions) -> SmartSolid:
    """Create a single iris blade with its pivot pin axis at (pcd_radius, 0, 0) along +Z.

    The petal silhouette, back protrusion, and pivot pin geometry are reconstructed
    from the reference STL via `sava.csg.build123d.reconstruct`. Only the placement
    (pcd_radius) is parametric; the blade shape itself is fixed by the source mesh.

    The blade is assembled in default Plane.XY local coords, then translated so the
    pivot pin lands at (pcd_radius, 0) in world XY. Final Z layout:
    - Back protrusion: Z in [-_BACK_PROTRUSION_THICKNESS, 0].
    - Main body:       Z in [0, _BODY_THICKNESS].
    - Pivot pin:       Z in [_BODY_THICKNESS, _BODY_THICKNESS + _PIVOT_PIN_HEIGHT].
    """
    # Main body (front-cap silhouette, the 6-gon)
    body = Pencil()
    body.jump((6.858, 8.536))
    body.draw(20.743, 30)
    body.left(0.577)
    body.draw(23.094, 150)
    body.down()
    blade = body.extrude(_BODY_THICKNESS, label='blade')

    # Back protrusion (thin strip behind the body's back face)
    back_protrusion = Pencil()
    back_protrusion.jump((1.366, 1.7))
    back_protrusion.left(16.167)
    back_protrusion.down()
    back_protrusion_body = back_protrusion.extrude(_BACK_PROTRUSION_THICKNESS)
    back_protrusion_body.move(0, 0, -_BACK_PROTRUSION_THICKNESS)
    blade.fuse(back_protrusion_body)

    # Cylindrical pivot pin standing on the body's front face
    pivot_pin = SmarterCone.cylinder(_PIVOT_PIN_RADIUS, _PIVOT_PIN_HEIGHT)
    pivot_pin.move(_PIVOT_U, _PIVOT_V, _BODY_THICKNESS)
    blade.fuse(pivot_pin)

    blade.move(dim.pcd_radius - _PIVOT_U, -_PIVOT_V, 0)
    return blade


# Source-mesh local-frame coordinates of the plate's aperture centre. Applied as
# a final shift in `build_diaphragm_plate_pieces` so the assembled plate's
# aperture sits at (0, 0) — matching `create_blades` which builds blades around
# the origin. The reconstruction emitted these positions because the source mesh
# placed the aperture there; that's an artefact, not part of the design.
_PLATE_APERTURE_U = 45.923
_PLATE_APERTURE_V = 45.811


def build_diaphragm_plate_pieces() -> dict[str, list[SmartSolid]]:
    """Build each cut/fuse component of the diaphragm plate as a separate solid.

    Reverse-engineered verbatim from `tmp/diaframma/obj_8_Diaf 1.stl` via
    `sava.csg.build123d.reconstruct`. All pieces are re-centred so the aperture
    sits at (0, 0).

    Returns a dict of labelled solid lists:
    - `plate_body`: the raw 42-gon extruded body (no cuts applied).
    - `aperture`: Ø41 × 2.999 cylinder — the central through-bore cutter.
    - `slot`: six SmartBox cutters (39 × 2 × 1.5) in a 6-fold polar pattern.
    - `collar`: Ø79.4 × 4.8 cylinder fused above the body (outer collar).
    - `collar_bore`: Ø77 × 4.8 cylinder — the inner cut that turns the collar
      into a thin ring.

    `create_diaphragm_plate()` consumes these pieces to produce the assembled
    solid; `__main__` exports them separately for visualization.
    """
    body = Pencil(start=(49.166, 0))
    body.jump((3.35, 3.024))
    body.jump((4.105, -1.876))
    body.jump((12.101, 4.795))
    body.jump((1.706, 4.178))
    body.jump((4.512, 0.091))
    body.jump((8.822, 9.571))
    body.jump((-0.276, 4.504))
    body.jump((4.026, 2.04))
    body.jump((3.796, 12.451))
    body.jump((-2.203, 3.939))
    body.jump((2.742, 3.584))
    body.jump((-1.982, 12.865))
    body.jump((-3.694, 2.593))
    body.jump((0.915, 4.419))
    body.jump((-7.368, 10.731))
    body.jump((-4.453, 0.733))
    body.jump((-1.093, 4.379))
    body.jump((-11.294, 6.471))
    body.jump((-4.33, -1.271))
    body.jump((-2.884, 3.471))
    body.jump((-12.983, 0.93))
    body.jump((-3.35, -3.024))
    body.jump((-4.105, 1.876))
    body.jump((-12.101, -4.795))
    body.jump((-1.706, -4.178))
    body.jump((-4.512, -0.091))
    body.jump((-8.822, -9.571))
    body.jump((0.276, -4.504))
    body.jump((-4.026, -2.04))
    body.jump((-3.796, -12.451))
    body.jump((2.203, -3.939))
    body.jump((-2.742, -3.584))
    body.jump((1.982, -12.865))
    body.jump((3.694, -2.593))
    body.jump((-0.915, -4.419))
    body.jump((7.368, -10.731))
    body.jump((4.453, -0.733))
    body.jump((1.093, -4.379))
    body.jump((11.294, -6.471))
    body.jump((4.33, 1.271))
    body.jump((2.884, -3.471))
    plate_body = body.extrude(2.999)

    aperture = SmarterCone.cylinder(20.5, 2.999)
    aperture.move(_PLATE_APERTURE_U, _PLATE_APERTURE_V, 0)

    # Six blade slots — 6-fold polar pattern around (45.915, 46.211).
    # `SmartBox` is Z-base-aligned, so `.move(_, _, 1.499)` puts the slot at
    # Z=1.499 to 2.999 — the 1.5 mm deep cavity at the top of the plate body.
    slot_pivot = Axis((45.915, 46.211, 0), (0, 0, 1))
    slot_template = SmartBox(39, 2, 1.5).rotate_z(-76.955).move(69.668, 60.567, 1.499)
    slots = [slot_template.copy().rotate(slot_pivot, i * 60) for i in range(6)]

    collar = SmarterCone.cylinder(39.7, 4.8)
    collar.move(_PLATE_APERTURE_U, _PLATE_APERTURE_V, 2.999)

    collar_bore = SmarterCone.cylinder(38.5, 4.8)
    collar_bore.move(_PLATE_APERTURE_U, _PLATE_APERTURE_V, 2.999)

    # Re-centre every piece so the assembled aperture sits at (0, 0).
    for piece in (plate_body, aperture, *slots, collar, collar_bore):
        piece.move(-_PLATE_APERTURE_U, -_PLATE_APERTURE_V, 0)

    return {
        'plate_body': [plate_body],
        'aperture': [aperture],
        'slot': slots,
        'collar': [collar],
        'collar_bore': [collar_bore],
    }


def create_diaphragm_plate() -> SmartSolid:
    """Assembled diaphragm plate: body minus aperture and six blade slots,
    with the collar ring fused on top. See `build_diaphragm_plate_pieces`
    for the per-piece breakdown."""
    pieces = build_diaphragm_plate_pieces()
    plate = pieces['plate_body'][0]
    plate.label = 'diaphragm_plate'
    plate.cut(pieces['aperture'][0])
    for slot in pieces['slot']:
        plate.cut(slot)
    plate.fuse(pieces['collar'][0])
    plate.cut(pieces['collar_bore'][0])
    return plate


def create_blades(dim: IrisDimensions, rotation_angle: float = 0.0) -> list[SmartSolid]:
    """Create all iris blades at the given rotation angle.

    rotation_angle: 0.0 = closed (min aperture), dim.rotation_range = fully open (max aperture).
    Each blade rotates around its own pivot post on the PCD.
    """
    blade = create_blade(dim)
    blades = []
    pivot_x, pivot_y = _polar(dim.pcd_radius, 0)

    for i in range(dim.blade_count):
        b = blade.copy()

        if rotation_angle != 0:
            b.move(-pivot_x, -pivot_y, 0)
            b.rotate_z(rotation_angle)
            b.move(pivot_x, pivot_y, 0)

        b.rotate_z(i * dim.blade_angular_span)
        blades.append(b)

    return blades


if __name__ == '__main__':
    from sava.csg.build123d.common.exporter import export_3mf, export_stl

    dim = IrisDimensions()
    # Half-open so both layers are visible and the polar geometry reads at a glance.
    blades = create_blades(dim, rotation_angle=dim.rotation_range / 2)
    plate = create_diaphragm_plate()

    # 3MF: show the full assembly with plate and blades as separately-labelled
    # groups (distinct colours). STL: just one blade — that's the printable unit
    # (the plate is one part and each of the six identical blades is another).
    export_3mf('models/other/iris/iris.3mf', plate, *blades)
    export_stl('models/other/iris/stl', create_blade(dim))
