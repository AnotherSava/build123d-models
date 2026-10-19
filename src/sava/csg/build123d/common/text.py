from dataclasses import dataclass
from typing import Any

from build123d import Location, Plane, Text, extrude

from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartsolid import SmartSolid

BACKGROUND_THICKNESS = 0.01


@dataclass
class TextDimensions:
    font_size: float
    font: str
    height: float
    font_path: str | None = None  # a font file to load instead of looking `font` up among the installed fonts


class TextSolid(SmartSolid):
    def __init__(self, element: Any, plane: Plane = Plane.XY, label: str = None) -> None:
        if plane != Plane.XY:
            element = element.locate(Location(plane))
        super().__init__(element, label=label)

    # Joins the letters into one solid, and so one object in an exported 3MF, over a pane under them too thin to print.
    def connected(self) -> SmartSolid:
        background = SmartBox(self.x_size, self.y_size, BACKGROUND_THICKNESS, label=self.label)
        background.align_zxy(self)
        return background.fuse(self)


def create_text(dim: TextDimensions, text: str, plane: Plane = Plane.XY, label: str = None) -> TextSolid:
    # some glyph outlines come out as faces OCCT itself rejects (Caveat's «н»), and extruding one gives an invalid solid; fix() leaves valid text untouched
    text_wire = Text(text, font_size=dim.font_size, font=dim.font, font_path=dim.font_path).fix()
    return TextSolid(extrude(text_wire, amount=dim.height), plane, label)
