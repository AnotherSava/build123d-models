
from build123d import Solid, Vector

from sava.csg.build123d.common.smartsolid import SmartSolid


class SmartBox(SmartSolid):
    def __init__(self, length: float, width: float, height: float, x: float = 0, y: float = 0, z: float = 0):
        super().__init__(length, width, height, x, y, z)

        self.solid = Solid.make_box(length, width, height)
        self.solid = self.solid.translate(Vector(x, y, z))
