from dataclasses import dataclass

from build123d import Text, extrude

from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartsolid import SmartSolid

BACKGROUND_THICKNESS = 0.01

@dataclass
class TextDimensions:
    font_size: float
    font: str
    height: float

class TextSolid(SmartSolid):
    def __init__(self, element):
        super().__init__(element)

    def connected(self):
        background = SmartBox(self.x_size, self.y_size, BACKGROUND_THICKNESS)
        background.align_zxy(self)
        result = background.fuse(self)
        return result.same_color(self)


def create_text(dim: TextDimensions, text: str, color: str = None) -> TextSolid:
    text_wire = Text(text, font_size=dim.font_size, font=dim.font)

    return TextSolid(extrude(text_wire, amount=dim.height)).color(color)
