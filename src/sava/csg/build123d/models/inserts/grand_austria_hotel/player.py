from dataclasses import dataclass

from sava.csg.build123d.common.exporter import export, save_3mf
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass
class PlayerComponentsDimensions:
    couple_length_top: float = 12.5

    @property
    def length(self) -> float:
        return 43.0

    @property
    def width(self) -> float:
        return 160.0

    @property
    def height(self) -> float:
        return 2


class PlayerComponents(SmartBox):
    def __init__(self, dim: PlayerComponentsDimensions):
        super().__init__(dim.length, dim.width, dim.height)
        self.dim = dim

    def create_single_couple(self) -> SmartSolid:
        pencil = Pencil()
        pencil.arc_with_radius(self.dim.couple_length_top / 2, 180, 90)
        pencil.down(3.1)
        pencil.draw(4.5, 144)
        pencil.down(9.4)
        return pencil.extrude_mirrored_y(self.dim.height)



dimensions = PlayerComponentsDimensions()
player_components = PlayerComponents(dimensions)

component = player_components.create_single_couple()
export(component.molded())
save_3mf()
