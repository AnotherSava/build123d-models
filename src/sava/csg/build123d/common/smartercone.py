from math import radians, tan

from build123d import Plane, Solid

from sava.common.advanced_math import advanced_mod
from sava.csg.build123d.common.geometry import are_numbers_too_close
from sava.csg.build123d.common.smartsolid import SmartSolid


class SmarterCone(SmartSolid):
    def __init__(self, base_radius: float, top_radius: float, height: float, plane: Plane = Plane.XY, angle: float = 360):
        self.base_radius = base_radius
        self.height = height
        self.plane = plane
        self.angle = angle

        if are_numbers_too_close(top_radius, base_radius):
            self.top_radius = base_radius
            solid = Solid.make_cylinder(base_radius, height, plane, angle)
        else:
            self.top_radius = top_radius
            solid = Solid.make_cone(base_radius, top_radius, height, plane, angle)

        super().__init__(solid)

    @classmethod
    def with_base_angle_and_height(cls, base_radius: float, height: float, base_angle: float = 90, plane: Plane = Plane.XY, angle: float = 360) -> SmartSolid:
        assert not are_numbers_too_close(advanced_mod(base_angle, 180, -90, 90), 0), f"Base angle is invalid: {base_angle}"

        base_angle = advanced_mod(base_angle, 360, -180, 180)
        top_radius = base_radius - height / tan(radians(abs(base_angle)))
        assert top_radius >= 0, f"With base radius {base_radius}, base angle {base_angle}, and height {height}, top radius ends up being negative: {top_radius}"

        if base_angle < 0:
            return SmarterCone(top_radius, base_radius, height, plane, angle)
        else:
            return SmarterCone(base_radius, top_radius, height, plane, angle)
