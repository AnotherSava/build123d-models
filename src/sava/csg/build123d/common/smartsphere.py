from copy import copy

from build123d import Location, Plane, Solid, Vector

from sava.csg.build123d.common.smartsolid import SmartSolid


class SmartSphere(SmartSolid):
    """
    A sphere primitive with optional hollow interior.

    Examples:
        # Solid sphere
        sphere = SmartSphere(50)

        # Hollow sphere (internal radius 40)
        hollow = SmartSphere(50, internal_radius=40)

        # Partial sphere (hemisphere)
        half = SmartSphere(50, angle=180)

        # Create shell on external surface
        shell = sphere.create_shell(5)  # 5mm thick shell outside
    """

    def __init__(self, radius: float, internal_radius: float = None, angle: float = 360, plane: Plane = Plane.XY, label: str = None):
        """
        Creates a sphere, optionally hollow.

        Args:
            radius: External radius of the sphere
            internal_radius: Internal radius (None = solid sphere)
            angle: Longitude sweep angle in degrees (360 = full sphere, 180 = hemisphere)
            plane: Plane to create the sphere in (center at plane origin)
            label: Optional label for export
        """
        self.radius = radius
        self.internal_radius = internal_radius
        self.angle = angle
        self.plane = plane

        solid = Solid.make_sphere(radius, angle3=angle)
        if internal_radius:
            solid -= Solid.make_sphere(internal_radius, angle3=angle)

        if plane != Plane.XY:
            solid.locate(Location(plane))

        super().__init__(solid, label=label)

    @staticmethod
    def create_hollow(radius1: float, radius2: float, angle: float = 360, plane: Plane = Plane.XY, label: str = None) -> 'SmartSphere':
        """
        Creates a hollow sphere from two radii, automatically determining which is external/internal.

        Args:
            radius1: First radius
            radius2: Second radius
            angle: Longitude sweep angle in degrees (360 = full sphere, 180 = hemisphere)
            plane: Plane to create the sphere in (center at plane origin)
            label: Optional label for export

        Returns:
            SmartSphere with larger radius as external, smaller as internal
        """
        external = max(radius1, radius2)
        internal = min(radius1, radius2)
        return SmartSphere(external, internal, angle, plane, label)

    def create_offset(self, offset: float, external: bool = True, label: str = None) -> 'SmartSphere':
        """
        Creates a new sphere with one radius adjusted by offset.

        Args:
            offset: Amount to adjust radius (positive = larger, negative = smaller)
            external: If True (default), adjusts external radius; if False, adjusts internal radius
            label: Optional label for the new sphere (defaults to original label)

        Returns:
            New SmartSphere with adjusted radius, aligned to same center
        """
        if external:
            new_radius = self.radius + offset
            new_internal = self.internal_radius
        else:
            if self.internal_radius is None:
                raise ValueError("Cannot adjust internal radius of solid sphere")
            new_radius = self.radius
            new_internal = self.internal_radius + offset

        return SmartSphere(new_radius, new_internal, self.angle, self.plane, label or self.label).colocate(self)

    def create_shell(self, offset: float, external: bool = True, label: str = None) -> 'SmartSphere':
        """
        Creates a new SmartSphere with shell geometry.

        Args:
            offset: Shell thickness (positive = outward from surface, negative = inward)
            external: If True (default), shell on external surface; if False, shell on internal surface
            label: Optional label for the new sphere (defaults to original label)

        Returns:
            New SmartSphere with shell geometry

        Examples:
            # 5mm shell outside solid sphere
            shell = sphere.create_shell(5)

            # 5mm shell inside solid sphere (creates hollow interior)
            shell = sphere.create_shell(-5)

            # For hollow sphere, shell on internal surface
            shell = hollow.create_shell(5, external=False)
        """
        if not external and self.internal_radius is None:
            raise ValueError("Cannot create shell on internal surface of solid sphere")

        radius = self.radius if external else self.internal_radius
        return SmartSphere.create_hollow(radius, radius + offset, self.angle, self.plane, label or self.label).colocate(self)

    def copy(self, label: str = None) -> 'SmartSphere':
        """Deep copy returning SmartSphere."""
        result = SmartSphere.__new__(SmartSphere)
        self._copy_base_fields(result, label)
        result.radius = self.radius
        result.internal_radius = self.internal_radius
        result.angle = self.angle
        result.plane = self.plane
        return result
