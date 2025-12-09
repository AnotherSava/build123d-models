from dataclasses import dataclass

from sava.csg.build123d.common.exporter import export, save_3mf
from sava.csg.build123d.common.geometry import Direction, Alignment
from sava.csg.build123d.common.smartbox import SmartBox


@dataclass
class CelebritiesBoxDimensions:
    gap: float = 1.0
    wall_thickness: float = 0.8
    floor_thickness: float = 0.8

    cards_length: float = 84.3
    cards_width: float = 47.4
    cards_height: float = 26.0
    cards_cut_length: float = 20.0
    cards_cut_width: float = 15.0

    cube_side: float = 16.15
    cube_cut_length: float = 12.5
    cube_cut_fillet_radius_bottom: float = 2.0
    cube_cut_fillet_radius_top: float = 1.0
    cube_cut_fillet_height: float = 12.5

    tokens_length = 15.35
    tokens_width = 23.1
    tokens_height = 6.4
    token_fillet_radius: float = 6.5
    token_notch_max_depth: float = 4.0
    token_notch_length: float = 10.0

    @property
    def token_notch_depth(self):
        return min(self.token_notch_max_depth, self.cards_height - self.cube_side - self.tokens_height)

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

    cube_box = SmartBox(dim.cube_side + dim.gap, dim.inner_width, dim.cube_side)
    cube_box.align(outer_box, Alignment.RL, -dim.wall_thickness, -dim.wall_thickness)

    token_box = SmartBox(dim.tokens_length + dim.gap, dim.tokens_width + dim.gap, dim.tokens_height)

    token_box.add_notch(Direction.S, dim.token_notch_depth, dim.token_notch_length)
    token_box.align_xy(cube_box).align_z(cube_box, Alignment.LL)
    token_box.fillet_z(dim.token_fillet_radius)

    outer_box.add_cutout(Direction.S, dim.cube_cut_length, dim.cube_cut_fillet_radius_bottom, None, None, dim.cube_cut_fillet_height, cube_box.x_mid - outer_box.x_mid)

    outer_box.add_cutout(Direction.W, dim.cards_cut_length, dim.cube_cut_fillet_radius_bottom, width=dim.cards_cut_width)

    return outer_box.cut(card_box, cube_box, token_box)

dimensions = CelebritiesBoxDimensions()
celebrities_box = create_celebrities_box(dimensions)

export(celebrities_box)
save_3mf()
