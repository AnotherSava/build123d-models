from build123d import Box, Vector, fillet, Align

from sava.csg.build123d.common.geometry import Direction, Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartsolid import SmartSolid


class SmartBox(SmartSolid):
    def __init__(self, length: float, width: float, height: float, align: Align | tuple[Align, Align, Align] = Align.MIN, flip_xy: bool = False):
        super().__init__(width if flip_xy else length, length if flip_xy else width, height)

        self.solid = Box(self.length, self.width, self.height, align=align)
        self.x, self.y, self.z = self.solid.bounding_box().min

    def addCutout(self, direction: Direction, length: float, radius_bottom: float = 0, radius_top: float | None = None, width: float | None = None, height: float | None = None, shift: float = 0) -> 'SmartBox':
        assert width is not None or height is not None, "Either width or height must be specified"

        distance_from_centre = self.get_other_side_length(direction) / 2

        cutout = SmartBox(length, width or distance_from_centre, height or self.height, Align.CENTER, direction.horizontal)
        cutout.align(self).align_z(self, Alignment.RL)
        cutout.move_in_direction(distance_from_centre, direction.value, shift, direction.value + 90)
        if radius_bottom:
            cutout.fillet_z(radius_bottom)

        self.cut(cutout)
        if radius_bottom or radius_top:
            self.solid = fillet(self.filter_edges_within(cutout.top_half()).filter_by(direction.axis), radius_bottom if radius_top is None else radius_top)

        if height:
            self.solid = fillet(self.filter_edges_within(cutout.bottom_half()).filter_by(direction.axis), radius_bottom)

        return self

    def addNotch(self, direction: Direction, depth: float, length: float):
        notch_height = depth / length * self.get_other_side_length(direction)
        pencil = Pencil().up(notch_height).right(self.get_side_length(direction))
        notch = pencil.extrudeX(self.get_side_length(direction), Vector(0, 0, -depth))

        self.fuse(notch)
