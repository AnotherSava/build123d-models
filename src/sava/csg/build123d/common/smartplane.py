from build123d import Plane, Solid

from sava.csg.build123d.common.smartsolid import SmartSolid


class SmartPlane(SmartSolid):
    def __init__(self, plane: Plane, size: float = 200):
        box = Solid.make_box(size, size, 0.01, plane)
        super().__init__(box)
        self.align(plane=plane)
