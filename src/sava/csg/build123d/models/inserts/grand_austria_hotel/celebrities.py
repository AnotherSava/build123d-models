from dataclasses import dataclass

from build123d import Vector

from sava.csg.build123d.common.exporter import Exporter
from sava.csg.build123d.common.geometry import Side, Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartbox import SmartBox


@dataclass
class CelebritiesBoxDimensions:
    gap: float = 1.0
    wall_thickness: float = 0.8
    floor_thickness: float = 0.8

    cards_length: float = 84.3
    cards_width: float = 47.4
    cards_height: float = 26.0
    cards_fillet_radius: float = 5.0

    cube_side: float = 16.15
    cube_cut_length: float = 12.5
    cube_cut_fillet_radius_bottom: float = 2.0
    cube_cut_fillet_radius_top: float = 1.0
    cube_cut_fillet_height: float = 12.5

    tokens_length = 15.35
    tokens_width = 23.1
    tokens_height = 6.4
    token_fillet_radius: float = 7.0
    token_notch_height: float = 3.0
    token_notch_width: float = 8.0

    @property
    def inner_width(self):
        return max(self.cards_width, self.cube_side * 3) + self.gap

    @property
    def outer_length(self):
        return self.cards_length + self.cube_side + 2 * self.gap + 3 * self.wall_thickness

    @property
    def outer_width(self):
        return self.inner_width + 2 * self.wall_thickness

    @property
    def outer_height(self):
        return self.cards_height + self.floor_thickness


def create_celebrities_box(dim: CelebritiesBoxDimensions):
    outer_box = SmartBox(dim.outer_length, dim.outer_width, dim.outer_height)

    card_box = SmartBox(dim.cards_length + dim.gap, dim.inner_width, dim.cards_height)
    card_box.align(outer_box, Alignment.LR, dim.wall_thickness, dim.wall_thickness, dim.floor_thickness)
    card_box.fillet_z(dim.cards_fillet_radius)

    cube_box = SmartBox(dim.cube_side + dim.gap, dim.inner_width, dim.cube_side)
    cube_box.align(outer_box, Alignment.RL, -dim.wall_thickness, -dim.wall_thickness)

    token_box = SmartBox(dim.tokens_length + dim.gap, dim.tokens_width + dim.gap, dim.tokens_height)

    token_notch_height_total = dim.token_notch_height / dim.token_notch_width * token_box.width
    token_notch = Pencil().up(token_notch_height_total).left(token_box.width).extrudeX(token_box.length, Vector(0, 0, -dim.token_notch_height))
    token_box.solid += token_notch
    token_box.align_xy(cube_box).align_z(cube_box, Alignment.LL)
    token_box.fillet_z(dim.token_fillet_radius)

    cube_cut_shift = cube_box.x_mid - outer_box.x_mid
    outer_box.addCutout(Side.S, dim.cube_cut_length, dim.cube_cut_fillet_radius_bottom, height=dim.cube_cut_fillet_height, shift=cube_cut_shift)
    outer_box.addCutout(Side.N, dim.cube_cut_length, dim.cube_cut_fillet_radius_bottom, height=dim.cube_cut_fillet_height, shift=-cube_cut_shift)

    return outer_box.solid - card_box.solid - cube_box.solid - token_box.solid

dimensions = CelebritiesBoxDimensions()
celebrities_box = create_celebrities_box(dimensions)

Exporter(celebrities_box).export()
