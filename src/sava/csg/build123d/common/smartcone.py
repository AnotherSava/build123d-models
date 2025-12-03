from math import radians, sin, tan, pi, cos

from build123d import Plane, Axis, Shape, Vector, Solid

from sava.csg.build123d.common.geometry import create_vector, multi_rotate_vector
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartsolid import SmartSolid


class SmartCone(SmartSolid):
    def __init__(self, solid: Shape, radius_outer: float, radius_top: float, cone_angle: float, thickness: float = None, base_angle: float = None):
        assert (thickness is None) == (base_angle is None), f"Illegal combination: thickness={thickness}, base_angle={base_angle}"
        assert base_angle is None or 0 < base_angle < 180

        self.radius_outer = radius_outer
        self.radius_top = radius_top
        self.cone_angle = cone_angle
        self.thickness = thickness
        self.base_angle = base_angle

        super().__init__(solid)

    @property
    def base_angle_rad(self):
        return radians(self.base_angle)

    @property
    def cone_angle_rad(self):
        return radians(self.cone_angle)

    @property
    def base_width(self):
        return self.thickness / sin(self.base_angle_rad)

    # z distance from the apex of the outer cone to the apex of the inner cone
    @property
    def height_higher_lower(self):
        return self.thickness / sin(self.cone_angle_rad)

    # z distance from the apex of the outer cone to the bottom of the outer cone
    @property
    def height_higher_outer(self):
        return self.radius_outer / tan(self.cone_angle_rad)

    # z distance from the apex of the outer cone to the bottom of the inner cone
    @property
    def height_higher_inner(self):
        return self.height_higher_outer - self.base_width * tan(pi / 2 - self.cone_angle_rad - self.base_angle_rad)

    # z distance from the apex of the inner cone to the bottom of the outer cone
    @property
    def height_lower_outer(self):
        return self.height_higher_outer - self.height_higher_lower

    # z distance from the apex of the inner cone to the bottom of the inner cone
    @property
    def height_lower_inner(self):
        return self.height_higher_inner - self.height_higher_lower

    @property
    def radius_inner(self):
        return self.height_lower_inner * tan(self.cone_angle_rad)

    @property
    def height_apex_higher(self):
        return self.radius_top / tan(self.cone_angle_rad)

    @classmethod
    def create_empty(cls, cone_angle: float, radius: float, thickness: float, base_angle: float = None) -> 'SmartCone':
        angle_rad = radians(cone_angle)

        base_angle = 90 - cone_angle if base_angle is None else base_angle

        outer_length = radius / sin(angle_rad)
        inner_length = outer_length - thickness * (1 / tan(angle_rad) + 1 / tan(radians(base_angle)))

        first_segment = create_vector(outer_length, -cone_angle)

        pencil = Pencil(-first_segment, Plane.XZ)
        pencil.jump(first_segment)
        pencil.down(thickness / sin(angle_rad))
        pencil.draw(inner_length, 180 - cone_angle)
        shape = pencil.revolve(axis=Axis.Z, enclose=True)

        return SmartCone(shape, radius, 0, cone_angle, thickness, base_angle)

    @classmethod
    def create_cone(cls, cone_angle: float, radius: float, top_radius: float = 0):
        height  = radius / tan(radians(cone_angle))
        plane = Plane((0, 0, -height), z_dir=(0, 0, 1))
        cone = Solid.make_cone(radius, top_radius, (radius - top_radius) / tan(radians(cone_angle)), plane)
        return SmartCone(cone, radius, top_radius, cone_angle)

    def create_outer_cone(self, radius: float = None, radius_top: float = None):
        cone = SmartCone.create_cone(self.cone_angle, radius or self.radius_outer, self.radius_top if radius_top is None else radius_top)
        return cone.colocate(self)

    def create_inner_cone(self, radius: float = None, radius_top: float = None):
        cone = SmartCone.create_cone(self.cone_angle, radius or self.radius_inner, self.radius_top if radius_top is None else radius_top)
        cone.colocate(self).move_vector(create_vector(self.height_higher_lower, self.create_axis().direction))
        return cone

    def scale_radius_outer(self, factor: float | None, radius: float = None):
        assert factor is None != radius is None

        new_radius = self.radius_outer * factor if factor else radius
        cone = SmartCone.create_cone(self.cone_angle, new_radius, self.radius_top)
        return cone.colocate(self).move_vector(create_vector(self.height_higher_lower, self.create_axis().direction))

    def pad_outer(self, padding: float, radius: float = None):
        side_padding_x = padding / cos(self.cone_angle_rad)
        print(f"side_padding_x: {side_padding_x}")
        new_radius_top = self.radius_top - 2 * padding * tan(self.cone_angle_rad) + 2 * side_padding_x
        print(self.cone_angle, radius or (self.radius_outer - 2 * side_padding_x), new_radius_top)
        cone = SmartCone.create_cone(self.cone_angle, radius or (self.radius_outer - 2 * side_padding_x), new_radius_top)
        cone.colocate(self).move_vector(self.create_axis().direction * (self.height_apex_higher - cone.height_apex_higher - padding))
        return cone

    def create_axis(self, inner: bool = False):
        """Create an axis for an outer or inner cone, taking cone position and orientation into account

        Args:
            inner: create an axis for the inner cone

        Returns:
            Axis for the specified cone
        """
        position = Vector(0, 0, -self.height_higher_lower if inner else 0) + self.solid.position
        orientation = multi_rotate_vector((0, 0, -1), Plane.XY, self.solid.orientation)
        return Axis(position, orientation)

    def _create_plane_with_offset(self, offset: float) -> Plane:
        """Create a plane perpendicular to the cone axis at a specific offset distance.
        
        Creates a plane that is perpendicular to the cone's central axis and positioned
        at the specified offset distance along that axis. The plane's position and 
        orientation account for any transformations applied to the cone (movement and rotation).
        
        Args:
            offset: Distance along the cone axis from the outer cone apex. 
                   Positive values move toward the base of the cone.
                   
        Returns:
            Plane perpendicular to the cone axis at the specified offset position,
            with proper position and orientation accounting for cone transformations.
        """
        # Get the cone's axis (for outer cone, starting at apex)
        cone_axis = self.create_axis()
        
        # Calculate the plane position by moving along the axis direction
        plane_position = cone_axis.position + cone_axis.direction * offset
        
        # Create plane perpendicular to the axis direction
        # The axis direction points downward (-Z), so the plane normal should be the same
        return Plane(plane_position, z_dir=cone_axis.direction)
