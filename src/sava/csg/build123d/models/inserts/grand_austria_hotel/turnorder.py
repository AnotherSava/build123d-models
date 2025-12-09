from dataclasses import dataclass

from build123d import Vector, extrude, import_svg, scale

from sava.csg.build123d.common.exporter import export, save_3mf, get_path
from sava.csg.build123d.common.geometry import Direction, Alignment
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass
class TurnOrderBoxDimensions:
    gap: float = 1.0
    wall_thickness: float = 0.8
    floor_thickness: float = 0.8

    turn_order_length: float = 45.0
    turn_order_width: float = 26.0
    turn_order_height: float = 2.15
    turn_order_cutout_length = 17.0
    turn_order_cutout_radius: float = 2.0
    turn_order_cutout_width: float = 5.0

    insert_width: float = 217

    key_svg_file: str = "input/inserts/grand_austria_hotel/key.svg"
    key_rotation: float = 45.0
    key_scale_y: float = 1.05
    key_length: float = 50
    key_notch_depth: float = 3
    key_notch_length: float = 15.0

    @property
    def turn_order_box_length(self):
        return self.turn_order_length + self.gap

    @property
    def turn_order_box_width(self):
        return self.turn_order_width + self.gap

    @property
    def outer_box_height(self):
        return self.turn_order_height * 4 + self.floor_thickness

    @property
    def outer_box_length(self):
        return self.turn_order_box_length + self.wall_thickness * 2


class TurnOrder:
    def __init__(self, dim: TurnOrderBoxDimensions):
        self.dim = dim

    def create_box(self):
        box = SmartBox(self.dim.outer_box_length, self.dim.insert_width, self.dim.outer_box_height)

        key_box = self.create_key()
        key_box.align_xy(box).align_z(box, Alignment.RL)
        box.cut(key_box)

        turn_order_boxes = self.create_turn_order_boxes().align_z(box, Alignment.RL)
        box.cut(turn_order_boxes.align_x(box).align_y(box, Alignment.RL, -self.dim.wall_thickness))
        box.cut(turn_order_boxes.orient((0, 0, 180)).align_x(box).align_y(box, Alignment.LR, self.dim.wall_thickness))

        for side in [Direction.E, Direction.W]:
            for i in range(3):
                for direction in [-1, 1]:
                    shift = self.dim.insert_width / 2 - self.dim.wall_thickness * (i + 1) - self.dim.turn_order_box_width * (i + 0.5)
                    box.add_cutout(side, self.dim.turn_order_cutout_length, self.dim.turn_order_cutout_radius, None, self.dim.turn_order_cutout_width, None, shift * direction)

        return box

    def create_turn_order_boxes(self) -> SmartSolid:
        box_2p = self.create_turn_order_box(2, None) # aligns to the origin, which we don't care much about
        box_3p = self.create_turn_order_box(3, box_2p)
        box_4p = self.create_turn_order_box(4, box_3p)

        return SmartSolid(box_2p, box_3p, box_4p)

    def create_turn_order_box(self, count: int, align_to: SmartSolid | None) -> SmartSolid:
        box = SmartBox(self.dim.turn_order_box_length, self.dim.turn_order_box_width, self.dim.turn_order_height * count)
        return box.align_x(align_to).align_y(align_to, Alignment.RR, self.dim.wall_thickness).align_z(align_to, Alignment.RL)

    def create_key(self) -> SmartSolid:
        svg_shapes = import_svg(get_path(self.dim.key_svg_file))

        shape2d = svg_shapes[0]
        shape2d = shape2d.scale((self.dim.key_length + self.dim.gap * 2) / shape2d.bounding_box().size.X)
        extruded_key = extrude(shape2d, self.dim.turn_order_height, Vector(0, 0, 1))
        solid = SmartSolid(scale(extruded_key, (1, self.dim.key_scale_y, 1)))
        solid.add_notch(Direction.E, self.dim.key_notch_depth, self.dim.key_notch_length)

        return solid.orient((0, 0, self.dim.key_rotation))


dimensions = TurnOrderBoxDimensions()
key = TurnOrder(dimensions)
export(key.create_box())
save_3mf()
