from build123d import Solid, Box, Vector, fillet, Axis

from sava.csg.build123d.common.geometry import Side, createVector
from sava.csg.build123d.common.smartsolid import SmartSolid


class SmartBox(SmartSolid):
    def __init__(self, length: float, width: float, height: float, x: float = 0, y: float = 0, z: float = 0):
        super().__init__(length, width, height, x, y, z)

        self.solid = Solid.make_box(length, width, height)
        self.solid.position = (x, y, z)

    @property
    def centre(self) -> tuple[float, float, float]:
        return self.x + self.length / 2, self.y + self.width / 2, self.z + self.height / 2

    def addCut(self, side: Side, length: float, radius: float, width: float = None, height: float = None, shift: float = 0) -> 'SmartBox':
        assert width is not None or height is not None, "Either width or height must be specified"

        distance_from_centre = self.length / 2 if side.horizontal else self.width / 2

        actual_height = (height or self.height) * 2
        cut = Box(length, width or distance_from_centre, actual_height)
        cut.position = Vector(self.centre) + createVector(distance_from_centre, side.value) + Vector(0, 0, self.height / 2) + createVector(shift, side.value + 90)
        cut.orientation = (0, 0, side)

        if width:
            cut = fillet(cut.edges().filter_by(Axis.Z), radius)
        else:
            cut = fillet(cut.edges().filter_by(Axis.Y), radius)

        self.solid = self.solid - cut

        return self
