from dataclasses import dataclass

from build123d import Plane

from sava.csg.build123d.common.exporter import export_3mf, export_stl
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass(frozen=True)
class CableChannelDimensions:
    length: float = 20.0
    width: float = 20.0
    wall_thickness: float = 1.5
    cavity_length: float = 11.0
    cavity_slope_run: float = 0.5

    @property
    def cavity_top_width(self) -> float:
        return self.width - 2 * self.wall_thickness

    @property
    def cavity_bottom_width(self) -> float:
        return self.cavity_top_width + 2 * self.cavity_slope_run


class CableChannel:
    def __init__(self, dim: CableChannelDimensions):
        self.dim = dim

    def create(self) -> SmartSolid:
        dim = self.dim
        body = Pencil(Plane.YZ, start=(dim.width / 2, 0))
        body.right(dim.width / 2)            # outer floor (half)
        body.up(9.5)                          # outer right wall
        body.left(dim.wall_thickness)         # step inward at top of outer wall
        body.jump((-0.674, 1.75))             # small jog at upper rim
        body.jump((0.674, 0.35))
        body.up(1.3)
        body.left(dim.wall_thickness)
        body.down(2.4)
        body.jump((dim.wall_thickness, -6))   # diagonal down inner upper rim
        body.down(2 * dim.wall_thickness)     # inner right wall down to floor (corner material added — no slope)
        channel = body.extrude_mirrored_y(dim.length, center=0, label='channel')

        # Trapezoidal cavity cuts at each end: long side along inner floor,
        # non-parallel sides match the source cavity slopes.
        cavity = SmartBox(dim.cavity_length, dim.cavity_bottom_width, dim.wall_thickness,
                          tapered_width=dim.cavity_top_width)
        cavity.move(dim.cavity_length / 2, dim.width / 2, dim.wall_thickness)
        for shift_x in [0, dim.length - dim.cavity_length]:
            channel.cut(cavity.copy().move(shift_x, 0, 0))

        return channel


if __name__ == "__main__":
    dimensions = CableChannelDimensions()
    cable_channel = CableChannel(dimensions)
    model = cable_channel.create()
    export_3mf("models/other/cable_channel/export.3mf", model)
    export_stl("models/other/cable_channel/stl", model)
