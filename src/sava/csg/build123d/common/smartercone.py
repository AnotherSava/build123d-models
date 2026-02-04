from copy import copy
from math import radians, sqrt, tan

from build123d import Plane, Solid, Vector

from sava.common.advanced_math import advanced_mod
from sava.csg.build123d.common.geometry import are_numbers_too_close, Alignment, snap_to
from sava.csg.build123d.common.smartsolid import SmartSolid


class SmarterCone(SmartSolid):
    def __init__(self, base_radius: float, top_radius: float, height: float, plane: Plane = Plane.XY, angle: float = 360, label: str = None):
        self.base_radius = base_radius
        self.height = height
        self.plane = plane
        self.angle = angle
        self.thickness_radius = None
        self.thickness_base = None
        self.thickness_top = None
        self.inner_cone = None
        self.top_radius = snap_to(top_radius, base_radius)

        if top_radius == base_radius:
            solid = Solid.make_cylinder(base_radius, height, plane, angle)
        else:
            solid = Solid.make_cone(base_radius, top_radius, height, plane, angle)

        super().__init__(solid, label=label)

    @property
    def slope(self) -> float:
        """
        Calculate the cone's slope (rate of radius change per unit height).

        Returns:
            The slope as (top_radius - base_radius) / height
            - Negative slope: cone narrows (typical cone shape)
            - Zero slope: cylinder
            - Positive slope: cone widens (inverted cone)
        """
        return (self.top_radius - self.base_radius) / self.height

    def center(self, height_fraction: float = 1) -> Vector:
        """
        Get the center point at any height along the cone in global coordinates.

        Args:
            height_fraction: Position along the cone's height (0.0 = base, 1.0 = top, 0.5 = middle)

        Returns:
            The center point at the specified height fraction along the cone's z-direction

        Examples:
            cone.center(0.0)   # Base center (same as base_center)
            cone.center(1.0)   # Top center
            cone.center(0.5)   # Middle center (halfway up the cone)
        """
        return self.base_center + self.plane.z_dir * self.height * height_fraction

    def radius(self, height_fraction: float = 1) -> float:
        """
        Get the radius at any height along the cone.

        Args:
            height_fraction: Position along the cone's height (0.0 = base, 1.0 = top, 0.5 = middle)

        Returns:
            The radius at the specified height fraction (linearly interpolated between base and top)

        Examples:
            cone.radius(0.0)   # Base radius
            cone.radius(1.0)   # Top radius
            cone.radius(0.5)   # Middle radius (halfway between base and top)
        """
        return self.base_radius + (self.top_radius - self.base_radius) * height_fraction

    @property
    def base_center(self) -> Vector:
        """
        Get the center point of the cone's base surface in global coordinates.

        Returns:
            The center of the base of the cone
        """
        return self.plane.origin

    @classmethod
    def with_base_angle(cls, base_radius: float, base_angle: float, top_radius: float = 0, plane: Plane = Plane.XY, angle: float = 360, label: str = None) -> 'SmarterCone':
        height = abs((top_radius - base_radius) / tan(radians(base_angle)))
        return SmarterCone.with_base_angle_and_height(base_radius, height, base_angle, plane, angle, label)

    @classmethod
    def with_base_angle_and_height(cls, base_radius: float, height: float, base_angle: float, plane: Plane = Plane.XY, angle: float = 360, label: str = None) -> 'SmarterCone':
        assert not are_numbers_too_close(advanced_mod(base_angle, 180, -90, 90), 0), f"Base angle is invalid: {base_angle}"

        if height < 0:
            height = -height
            base_angle += 180

        base_angle = advanced_mod(base_angle, 360, -180, 180)

        top_radius = snap_to(base_radius - height / tan(radians(abs(base_angle))), 0)
        assert top_radius >= 0, f"With base radius {base_radius}, base angle {base_angle}, and height {height}, top radius ends up being negative: {top_radius}"

        if base_angle < 0:
            return SmarterCone(top_radius, base_radius, height, plane, angle, label)
        else:
            return SmarterCone(base_radius, top_radius, height, plane, angle, label)

    @classmethod
    def cylinder(cls, radius: float, height: float, plane: Plane = Plane.XY, angle: float = 360, label: str = None) -> 'SmarterCone':
        return SmarterCone(radius, radius, height, plane, angle, label)

    def create_offset(self, thickness_radius: float = None, thickness_side: float = None, thickness_base: float = 0, thickness_top: float = 0, label: str = None) -> 'SmarterCone':
        """
        Creates an offset cone by adjusting radii and height based on thickness parameters.

        Args:
            thickness_radius: Radial offset applied uniformly along the cone wall (horizontal offset)
            thickness_side: Offset perpendicular to the cone's slanted side (specify either this OR thickness_radius, not both)
            thickness_base: Vertical offset at the base (extends cone downward/upward)
            thickness_top: Vertical offset at the top (extends cone downward/upward)

        Returns:
            A new SmarterCone with adjusted dimensions, aligned to this cone

        Behavior:
            - Calculates offset radii based on cone slope and thickness parameters
            - Positive thickness creates larger cone, negative creates smaller
            - If radius would be negative and corresponding thickness is 0, adjusts thickness to make radius 0 (pointed cone)
            - Resulting cone is aligned to the base of the original cone

        Example:
            cone = SmarterCone(50, 30, 100)
            outer = cone.create_offset_cone(thickness_radius=2, thickness_base=1, thickness_top=1)
            # Creates larger cone with 2mm radial offset + 1mm base/top offsets

            outer2 = cone.create_offset_cone(thickness_side=2)
            # Creates larger cone with 2mm offset perpendicular to the slanted side

            pointed = cone.create_offset_cone(thickness_radius=-30)
            # Creates pointed cone (top_radius = 0, base_radius = 20)
        """
        # Ensure exactly one thickness parameter is specified
        assert (thickness_radius is None) != (thickness_side is None), "Must specify exactly one of thickness_radius or thickness_side"

        # Convert thickness_side to thickness_radius if needed
        if thickness_side is not None:
            # thickness_radius = thickness_side * cos(angle_from_horizontal)
            # where tan(angle) = slope, so cos(angle) = 1 / sqrt(1 + slope²)
            thickness_radius = thickness_side / sqrt(1 + self.slope * self.slope)

        # Calculate offset cone dimensions
        # Extend the cone along its slope for thickness_base/top, then add thickness_radius
        offset_base_radius = self.base_radius - self.slope * thickness_base + thickness_radius
        offset_top_radius = self.top_radius + self.slope * thickness_top + thickness_radius
        adjusted_thickness_base = thickness_base
        adjusted_thickness_top = thickness_top

        # If base radius would be negative and thickness_base is 0, adjust thickness_base to make radius 0
        if offset_base_radius < 0 and thickness_base == 0:
            adjusted_thickness_base = (self.base_radius + thickness_radius) / self.slope
            offset_base_radius = 0

        # If top radius would be negative and thickness_top is 0, adjust thickness_top to make radius 0
        if offset_top_radius < 0 and thickness_top == 0:
            adjusted_thickness_top = -(self.top_radius + thickness_radius) / self.slope
            offset_top_radius = 0

        offset_height = self.height + adjusted_thickness_base + adjusted_thickness_top

        # Create and align the offset cone
        offset_cone = SmarterCone(offset_base_radius, offset_top_radius, offset_height, self.plane, self.angle, label)
        offset_cone.align_z(self, Alignment.LR, -adjusted_thickness_base, self.plane)

        return offset_cone

    def copy(self, label: str = None) -> 'SmarterCone':
        """Override copy to return a SmarterCone instead of SmartSolid"""
        result = SmarterCone.__new__(SmarterCone)
        self._copy_base_fields(result, label)
        result.base_radius = self.base_radius
        result.top_radius = self.top_radius
        result.height = self.height
        result.plane = self.plane
        result.angle = self.angle
        result.thickness_radius = self.thickness_radius
        result.thickness_base = self.thickness_base
        result.thickness_top = self.thickness_top
        result.inner_cone = None if self.inner_cone is None else self.inner_cone.copy()
        return result

    def create_shell(self, thickness_radius: float = None, thickness_base: float = 0, thickness_top: float = 0, thickness_side: float = None) -> 'SmarterCone':
        """
        Creates a hollow shell from the cone.

        Args:
            thickness_radius: Radial thickness applied uniformly along the cone wall (horizontal offset)
            thickness_side: Thickness perpendicular to the cone's slanted side (specify either this OR thickness_radius, not both)
            thickness_base: Vertical thickness at the base (extends cone downward/upward)
            thickness_top: Vertical thickness at the top (extends cone downward/upward)

        Returns:
            Self for method chaining

        Behavior:
            - Thickness_base/top create vertical offsets, radii adjust based on cone slope
            - Offset radii calculated by extending cone slope at offset heights, then adding/subtracting thickness
            - Shell height = original height + thickness_base + thickness_top
            - Positive thickness: Creates outer shell (material outside original cone)
            - Negative thickness: Creates inner shell (material inside, hollow from within)

        Example:
            cone = SmarterCone(50, 30, 100)
            cone.shell(thickness_radius=2, thickness_base=1, thickness_top=1)
            # Creates outer shell with 2mm radial wall + 1mm base/top thickness

            cone.shell(thickness_side=2, thickness_base=1, thickness_top=1)
            # Creates outer shell with 2mm wall perpendicular to slanted side + 1mm base/top thickness
        """
        assert self.thickness_radius is None, "Already a shell"
        assert (thickness_radius is None) != (thickness_side is None), "Must specify exactly one of thickness_radius or thickness_side"

        # Convert thickness_side to thickness_radius if needed
        if thickness_side is not None:
            thickness_radius = thickness_side / sqrt(1 + self.slope * self.slope)

        assert thickness_radius != 0, "thickness must be non-zero"
        assert thickness_base == 0 or thickness_base * thickness_radius > 0, "thickness_base must have the same sign as thickness (or be zero)"
        assert thickness_top == 0 or thickness_top * thickness_radius > 0, "thickness_top must have the same sign as thickness (or be zero)"

        # Create the offset cone
        offset_cone = self.create_offset(thickness_radius=thickness_radius, thickness_base=thickness_base, thickness_top=thickness_top)

        if thickness_radius >= 0:
            # Positive thickness: outer shell - subtract self from larger offset cone
            cone_copy = self.copy()
            result = offset_cone.cut(self)
            self.solid = result.solid
            # Update dimensional properties to match the new geometry
            self.base_radius = offset_cone.base_radius
            self.top_radius = offset_cone.top_radius
            self.height = offset_cone.height
            self.inner_cone = cone_copy
        else:
            # Negative thickness: inner shell - subtract smaller offset cone from self
            self.cut(offset_cone)
            self.inner_cone = offset_cone

        # Store thickness info
        self.thickness_radius = thickness_radius
        self.thickness_base = thickness_base
        self.thickness_top = thickness_top

        return self
