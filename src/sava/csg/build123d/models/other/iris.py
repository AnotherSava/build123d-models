import math
from dataclasses import dataclass

from sava.csg.build123d.common.pencil import Pencil
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
    blade_count: int = 5
    aperture_diameter_min: float = 25.0
    aperture_diameter_max: float = 35.0
    pin_diameter: float = _PIVOT_PIN_RADIUS * 2
    pin_clearance: float = 0.2
    blade_height: float = _BLADE_HEIGHT
    blade_thickness: float = _BODY_THICKNESS
    pcd_radius: float = 30.0
    drive_pin_offset: float = 5.0
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
