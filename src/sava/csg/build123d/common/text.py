from dataclasses import dataclass

from build123d import Text, extrude, Plane, Location

from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass
class TextDimensions:
    font_size: float
    font: str
    height: float


class TextSolid(SmartSolid):
    def __init__(self, element, plane: Plane = Plane.XY, label: str = None):
        if plane != Plane.XY:
            element = element.locate(Location(plane))
        super().__init__(element, label=label)


def create_text(dim: TextDimensions, text: str, plane: Plane = Plane.XY, label: str = None) -> TextSolid:
    text_wire = Text(text, font_size=dim.font_size, font=dim.font)
    return TextSolid(extrude(text_wire, amount=dim.height), plane, label)
