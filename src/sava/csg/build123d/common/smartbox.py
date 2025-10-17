from build123d import Box, Vector, fillet, Axis, Align

from build123d import Box, Vector, fillet, Axis, Align

from sava.csg.build123d.common.geometry import Side, Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartsolid import SmartSolid


class SmartBox(SmartSolid):
    def __init__(self, length: float, width: float, height: float, align: Align | tuple[Align, Align, Align] = Align.MIN):
        super().__init__(length, width, height)

        self.solid = Box(length, width, height, align=align)
        self.x, self.y, self.z = self.solid.bounding_box().min

    def addCutout(self, side: Side, length: float, radius_bottom: float, radius_top: float = None, width: float = None, height: float = None, shift: float = 0) -> 'SmartBox':
        assert width is not None or height is not None, "Either width or height must be specified"

        distance_from_centre = self.get_side_length(side) / 2

        cutout = SmartBox(length, width or distance_from_centre, height or self.height, Align.CENTER).with_orientation(Vector(0, 0, side.value))
        cutout.align(self).align_z(self, Alignment.RL)
        cutout.move_in_direction(distance_from_centre, side.value, shift, side.value + 90)

        self.solid -= cutout.solid
        self.solid = fillet(self.filter_edges_within(cutout.bottom_half()).filter_by(Axis.Y), radius_bottom)
        self.solid = fillet(self.filter_edges_within(cutout.top_half()).filter_by(Axis.Y), radius_bottom if radius_top is None else radius_top)

        return self

    def get_side_length(self, side: Side):
        return self.length if side.horizontal else self.width

    def get_other_side_length(self, side: Side):
        return self.width if side.horizontal else self.length

    def addNotch(self, side: Side, height: float, length: float):
        notch_height_total = height / self.get_side_length(side) * length
        pencil = Pencil().up(notch_height_total).left(self.get_side_length(side))
        notch = pencil.extrudeX(self.get_other_side_length(side), Vector(0, 0, -height))

        self.solid += notch
