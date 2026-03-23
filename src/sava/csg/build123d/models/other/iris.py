import math
from dataclasses import dataclass

from build123d import Cylinder

from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartsolid import SmartSolid


def _polar(radius: float, angle_deg: float) -> tuple[float, float]:
    """Convert polar coordinates to cartesian (2D)."""
    rad = math.radians(angle_deg)
    return (radius * math.cos(rad), radius * math.sin(rad))


@dataclass(frozen=True)
class IrisDimensions:
    blade_count: int = 5
    aperture_diameter_min: float = 25.0
    aperture_diameter_max: float = 35.0
    pin_diameter: float = 3.0
    pin_clearance: float = 0.2
    blade_height: float = 20.0
    blade_thickness: float = 2.0
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
        """Outer radius of blade profile — extends past pivot to contain the pivot hole."""
        return self.pcd_radius + self.pin_diameter + 1.0

    @property
    def rotation_range(self) -> float:
        """Rotation angle in degrees from closed (min aperture) to fully open (max aperture).

        Derived from the geometry: the inner edge midpoint is at distance lever_arm from the pivot.
        Rotating by this angle moves the midpoint from aperture_radius_min to aperture_radius_max
        distance from the iris center.
        """
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
    """Create a single iris blade in closed position, centered on angle 0.

    The blade is an arc sector with inner edge at aperture_radius_min,
    outer edge beyond pcd_radius. Pivot hole at pcd_radius on angle 0.
    Drive pin on top surface, offset inward from pivot.
    """
    half_span = dim.blade_angular_span / 2
    r_inner = dim.aperture_radius_min
    r_outer = dim.blade_outer_radius

    # Profile vertices in global coords
    a = _polar(r_inner, -half_span)
    b = _polar(r_inner, half_span)
    c = _polar(r_outer, half_span)
    d = _polar(r_outer, -half_span)
    inner_mid = _polar(r_inner, 0)
    outer_mid = _polar(r_outer, 0)

    # Use start=a so local (0,0) maps to vertex a in global coords.
    # Auto-close returns to local (0,0) = vertex a.
    pencil = Pencil(start=a)

    def local(pt: tuple[float, float]) -> tuple[float, float]:
        return (pt[0] - a[0], pt[1] - a[1])

    pencil.jump_to(local(d))
    pencil.arc_abs(local(outer_mid), local(c))
    pencil.jump_to(local(b))
    pencil.arc_abs(local(inner_mid), (0, 0))

    blade = pencil.extrude(dim.blade_height, label="blade")

    # Cut pivot hole through the full blade height
    pivot_xy = _polar(dim.pcd_radius, 0)
    pivot_hole = SmartSolid(Cylinder(dim.pivot_hole_radius, dim.blade_height + 2))
    pivot_hole.move(pivot_xy[0], pivot_xy[1], 0)
    pivot_hole.align_z(blade, Alignment.C)
    blade.cut(pivot_hole)

    # Add drive pin protruding from top surface
    drive_pin = SmartSolid(Cylinder(dim.pin_radius, dim.drive_pin_height))
    drive_pin.move(dim.drive_pin_radius_from_center, 0, 0)
    drive_pin.align_z(blade, Alignment.RR)
    blade.fuse(drive_pin)

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
