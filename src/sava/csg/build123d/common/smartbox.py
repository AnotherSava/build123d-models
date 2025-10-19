from build123d import Box, Vector, Align, Edge, Axis

from sava.csg.build123d.common.geometry import Direction, Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartsolid import SmartSolid

FILLET_ENABLER_COEFFICIENT = 1.01 # coefficient between side length and fillet radius (operation fails when 1.0)


class SmartBox(SmartSolid):
    def __init__(self, length: float, width: float, height: float, align: Align | tuple[Align, Align, Align] = Align.MIN, flip_xy: bool = False):
        super().__init__(width if flip_xy else length, length if flip_xy else width, height)

        self.solid = Box(self.length, self.width, self.height, align=align)
        self.x, self.y, self.z = self.solid.bounding_box().min

    def addCutout(self, direction: Direction, length: float, radius_bottom: float = 0, radius_top: float | None = None, width: float | None = None, height: float | None = None, shift: float = 0) -> 'SmartBox':
        assert width is not None or height is not None, "Either width or height must be specified"


        width_actual = width or self.get_other_side_length(direction)
        height_actual = (height or self.height)

        cutout_bottom = SmartBox(length, width_actual, height_actual, Align.CENTER, direction.horizontal)

        if radius_bottom:
            if height: # cutout doesn't go all the way to the bottom
                cutout_bottom._fillet(direction.axis, radius_bottom, Axis.Z, cutout_bottom.z)
            else: # cutout goes all the way to the bottom
                cutout_bottom._fillet(Axis.Z, radius_bottom)

        radius_top_actual = radius_bottom if radius_top is None else radius_top
        if radius_top_actual:
            cutout_top = SmartBox(length, width_actual, radius_top_actual * FILLET_ENABLER_COEFFICIENT, Align.CENTER, direction.horizontal)
            cutout_bottom.align_xy(cutout_top).align_z(cutout_top, Alignment.RL)

            cutout_cap = SmartBox(length + radius_top_actual * 2 * FILLET_ENABLER_COEFFICIENT, width_actual, radius_top_actual, Align.CENTER, direction.horizontal)
            cutout_cap.align_xy(cutout_top).align_z(cutout_top, Alignment.RR)
            cutout_top.fuse(cutout_cap)
            cutout_top.fillet_edges(Edge.is_interior, radius_top_actual)

            cutout_bottom = cutout_top.fuse(cutout_bottom)

        cutout_bottom.align_z(self, Alignment.RL).align_axis(self, direction.orthogonal_axis, Alignment.C, shift).align_axis(self, direction.axis, direction.alignment_closer if height else direction.alignment_middle)

        return self.cut(cutout_bottom)

    def addNotch(self, direction: Direction, depth: float, length: float):
        notch_height = depth / length * self.get_other_side_length(direction)
        pencil = Pencil().up(notch_height).right(self.get_side_length(direction))
        notch = pencil.extrudeX(self.get_side_length(direction), Vector(0, 0, -depth))

        self.fuse(notch)
