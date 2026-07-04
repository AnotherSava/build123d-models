from dataclasses import dataclass

from build123d import Plane

from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.modelspec import ModelSpec, export_model
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartercone import SmarterCone
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass(frozen=True)
class PipeClampDimensions:
    diameter: float = 13.0
    width: float = 10.0
    thickness: float = 2.0
    holder_length: float = 12
    holder_thickness: float = 1.5
    hole_diameter: float = 6.0
    bump_angle: float = 12.0
    notch_angle: float = 16.0
    bump_width_padding: float = 0.2
    bump_angle_padding: float = 4
    bumo_thickness: float = 1.5

class PipeClamp:
    def __init__(self, dim: PipeClampDimensions) -> None:
        self.dim = dim

    def create_outer_cylinder(self, width: float, angle: float) -> SmartSolid:
        return SmarterCone.cylinder(self.dim.diameter / 2 + self.dim.thickness + self.dim.bumo_thickness, width, inner_radius=self.dim.diameter / 2 + self.dim.thickness, angle=angle, plane=Plane.XZ)


    def create_half_a(self) -> SmartSolid:
        half_a = self.create_half()

        bump = self.create_outer_cylinder(self.dim.width / 3, angle=self.dim.bump_angle)
        bump.align_y(half_a)
        half_a.fuse(bump)

        return half_a

    def create_half_b(self) -> SmartSolid:
        half_b = self.create_half().mirror(Plane.XY)

        pencil = Pencil(Plane.XZ)
        pencil.up(self.dim.thickness)
        pencil.arc_with_radius(self.dim.diameter / 2, 0, 90)
        pencil.right(self.dim.thickness + self.dim.bumo_thickness)
        pencil.spline_abs((0, 0), (-1, 0), start_tangent=(0, -1))
        thick_arc = pencil.extrude(self.dim.width)
        thick_arc.align(half_b).x(Alignment.RL, self.dim.bumo_thickness).z(Alignment.LR)
        half_b.fuse(thick_arc)

        bump = self.create_outer_cylinder(self.dim.width / 3 + self.dim.bump_width_padding * 2, angle=self.dim.bump_angle + self.dim.bump_angle_padding)
        bump.align_y(half_b)
        notch = self.create_outer_cylinder(self.dim.width, self.dim.bump_angle + self.dim.notch_angle)

        return half_b.fuse(notch.cut(bump))

    def create_half(self) -> SmartSolid:
        half_pipe = SmarterCone.cylinder(self.dim.diameter / 2 + self.dim.thickness, self.dim.width, inner_radius=self.dim.diameter / 2, angle=180, plane=Plane.XZ)

        holder = SmartBox(self.dim.holder_length + self.dim.thickness, self.dim.width, self.dim.holder_thickness)
        holder.align(half_pipe).x(Alignment.LL, self.dim.thickness).z(Alignment.LR)

        hole = SmarterCone.cylinder(self.dim.hole_diameter / 2, self.dim.holder_thickness)
        hole.align(holder).x(Alignment.C, -self.dim.thickness / 2)
        holder.cut(hole)

        return half_pipe.fuse(holder)


def build() -> ModelSpec:
    pipe_clamp = PipeClamp(PipeClampDimensions())
    half_a = pipe_clamp.create_half_a()
    half_a.label = "shape_1"
    half_b = pipe_clamp.create_half_b()
    half_b.label = "shape_2"
    return ModelSpec(name="pipe_clamp", output_dir="models/other/pipe_clamp", scene=[half_a, half_b])


if __name__ == "__main__":
    export_model(build())
