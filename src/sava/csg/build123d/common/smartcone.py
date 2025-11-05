from math import radians, sin, tan, pi

from build123d import Plane, Axis, Shape, Vector

from sava.csg.build123d.common.geometry import create_vector, multi_rotate_vector
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartsolid import SmartSolid


class SmartCone(SmartSolid):
    def __init__(self, solid: Shape, radius_outer: float, cone_angle: float, thickness: float | None, base_angle: float | None):
        assert base_angle is None or 0 < base_angle < 180
        assert thickness is not None or base_angle is None

        self.radius_outer = radius_outer
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

    @classmethod
    def create_empty(cls, cone_angle: float, radius: float, thickness: float, base_angle: float = None) -> SmartSolid:
        angle_rad = radians(cone_angle)

        base_angle = 90 - cone_angle if base_angle is None else base_angle

        inner_length = radius / sin(angle_rad) - thickness / tan(radians(base_angle))

        outer_length = thickness / tan(angle_rad) + radius / sin(angle_rad)
        first_segment = create_vector(outer_length, -cone_angle)

        pencil = Pencil(-first_segment, Plane.XZ)
        pencil.jump(first_segment)
        pencil.down(thickness / sin(angle_rad))
        pencil.draw(inner_length, 180 - cone_angle)
        shape = pencil.revolve(axis=Axis.Z, enclose=True)

        return SmartCone(shape, radius, cone_angle, thickness, base_angle)

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
        # pane tangent to axis with a specific offset along that axis
        pass