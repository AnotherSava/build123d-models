from dataclasses import dataclass

from build123d import fillet, Axis

from sava.csg.build123d.common.exporter import Exporter
from sava.csg.build123d.common.smartbox import SmartBox


@dataclass
class CelebritiesBoxDimensions:
    internal_length: float = 84.3
    internal_width: float = 47.4
    internal_height: float = 26.0
    gap: float = 1.0
    wall_thickness: float = 0.8
    floor_thickness: float = 0.8
    cube_side: float = 16.15

    @property
    def inner_width(self):
        return max(self.internal_width, self.cube_side * 3) + self.gap

    @property
    def outer_length(self):
        return self.internal_length + self.cube_side + 2 * self.gap + 3 * self.wall_thickness

    @property
    def outer_width(self):
        return self.inner_width + 2 * self.wall_thickness

    @property
    def outer_height(self):
        return self.internal_height + self.floor_thickness


def create_celebrities_box(dim: CelebritiesBoxDimensions):
    outer_box = SmartBox(dim.outer_length, dim.outer_width, dim.outer_height)

    card_box = SmartBox(dim.internal_length + dim.gap, dim.inner_width, dim.internal_height, dim.wall_thickness, dim.wall_thickness, dim.floor_thickness)
    card_box_filleted = fillet(card_box.solid.edges().filter_by(Axis.Z), radius=5)

    cube_box = SmartBox(dim.cube_side + dim.gap, dim.inner_width, dim.cube_side)
    cube_box.move(card_box.x_to + dim.wall_thickness, card_box.y, card_box.z_to - cube_box.height)

    return outer_box.solid - card_box_filleted - cube_box.solid


dimensions = CelebritiesBoxDimensions()
celebrities_box = create_celebrities_box(dimensions)

Exporter(celebrities_box).export()
