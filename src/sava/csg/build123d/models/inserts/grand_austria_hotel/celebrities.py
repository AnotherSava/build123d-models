from dataclasses import dataclass

from build123d import Axis

from sava.csg.build123d.common.exporter import Exporter
from sava.csg.build123d.common.geometry import Side, Alignment
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
    tokens_length = 15.35
    tokens_width = 23.1
    tokens_height = 6.4
    card_box_fillet_radius: float = 5.0
    token_fillet_radius: float = 7.0
    cube_cut_length: float = 12.5
    cube_cut_fillet_radius: float = 2.0
    cube_cut_fillet_height: float = 12.5

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
    card_box.fillet_z(dim.card_box_fillet_radius)

    cube_box = SmartBox(dim.cube_side + dim.gap, dim.inner_width, dim.cube_side)
    cube_box.align(outer_box, Alignment.RL, -dim.wall_thickness, -dim.wall_thickness)

    token_box = SmartBox(dim.tokens_length + dim.gap, dim.tokens_width + dim.gap, dim.tokens_height)
    token_box.align_xy(cube_box).align_z(cube_box, Alignment.LL)
    token_box.fillet_z(dim.token_fillet_radius)

    cube_cut_shift = (outer_box.length - cube_box.length) / 2
    outer_box.addCut(Side.S, dim.cube_cut_length, dim.cube_cut_fillet_radius, None, dim.cube_cut_fillet_height, cube_cut_shift)
    outer_box.addCut(Side.N, dim.cube_cut_length, dim.cube_cut_fillet_radius, None, dim.cube_cut_fillet_height, -cube_cut_shift)
    outer_box.fillet_y(dim.cube_cut_fillet_radius, Axis.X, outer_box.x, outer_box.x_to, (False, False))

    return outer_box.solid - card_box.solid - cube_box.solid - token_box.solid

dimensions = CelebritiesBoxDimensions()
celebrities_box = create_celebrities_box(dimensions)

Exporter(celebrities_box).export()
