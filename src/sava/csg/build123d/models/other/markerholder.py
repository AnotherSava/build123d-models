from dataclasses import dataclass

from build123d import Axis

from sava.csg.build123d.common.edgefilters import PositionalFilter
from sava.csg.build123d.common.geometry import DELTA, Alignment
from sava.csg.build123d.common.modelspec import ModelSpec, export_model
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartercone import SmarterCone
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass(frozen=True)
class MarkerHolderDimensions:
    inner_diameter_middle: float = 14
    inner_diameter_top: float = 20
    inner_diameter_bottom: float = 13
    thickness: float = 2
    height_bottom: float = 30
    height_top: float = 15
    fillet_middle: float = 10
    fillet_top: float = 0.5

    @property
    def radius_middle_outer(self) -> float:
        return self.inner_diameter_middle / 2 + self.thickness

    @property
    def radius_top_outer(self) -> float:
        return self.inner_diameter_top / 2 + self.thickness

    @property
    def shift_bottom_inner(self) -> float:
        return (self.inner_diameter_bottom - self.inner_diameter_middle) / 2

    @property
    def shift_top(self) -> float:
        return (self.inner_diameter_top - self.inner_diameter_middle) / 2


class MarkerHolder:
    def __init__(self, dim: MarkerHolderDimensions) -> None:
        self.dim = dim

    def create(self) -> SmartSolid:
        dim = self.dim
        holder = SmarterCone.base(dim.radius_middle_outer)
        holder.inner(dim.inner_diameter_bottom / 2, shift_x=dim.shift_bottom_inner)
        holder.extend(height=dim.height_bottom)
        holder.inner(dim.inner_diameter_middle / 2)
        holder.extend(radius=dim.radius_top_outer, height=dim.height_top, shift_x=dim.shift_top, fillet=dim.fillet_middle)

        box = SmartBox(dim.radius_middle_outer, dim.radius_middle_outer * 2, holder.height)
        box.align(holder).x(Alignment.LR, -DELTA)

        marker_holder = SmartSolid(box, holder.get_outer_cone(), label="marker_holder").cut(holder.get_inner_cone())

        marker_holder.fillet_by(dim.fillet_top, PositionalFilter(Axis.Z, marker_holder.z_max), PositionalFilter(Axis.X))

        return marker_holder


def build() -> ModelSpec:
    model = MarkerHolder(MarkerHolderDimensions()).create()
    return ModelSpec(name="marker_holder", output_dir="models/other/marker_holder", scene=[model])


if __name__ == "__main__":
    from sava.common.logging import logger
    logger.setLevel("DEBUG")
    export_model(build())
