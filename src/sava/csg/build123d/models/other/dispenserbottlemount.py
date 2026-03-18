import math
from dataclasses import dataclass

from sava.csg.build123d.common.exporter import export_3mf, export_stl
from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.smartercone import SmarterCone, InnerMode
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass(frozen=True)
class DispenserBottleMountDimensions:
    bottle_outer_diameter_max: float = 32.3
    bottle_hole_angle: float = 5
    bottle_hole_depth: float = 20

    dispenser_inner_diameter_min: float = 71
    dispenser_inner_diameter_max: float = 71.5
    dispenser_outer_diameter: float = 76
    bottle_mount_wall_depth: float = 10
    thickness_wall: float = 2

    @property
    def bottle_outer_diameter_min(self) -> float:
        return self.bottle_outer_diameter_max - self.bottle_hole_depth * math.sin(math.radians(self.bottle_hole_angle))


class DispenserBottleMount:
    def __init__(self, dim: DispenserBottleMountDimensions):
        self.dim = dim

    def create(self) -> SmartSolid:
        outer = SmarterCone.base(self.dim.dispenser_inner_diameter_min / 2).inner(self.dim.dispenser_inner_diameter_min / 2 - self.dim.thickness_wall)
        outer.extend(height=self.dim.bottle_mount_wall_depth, radius=self.dim.dispenser_inner_diameter_max / 2)
        outer.extend(radius=self.dim.dispenser_outer_diameter / 2).inner(mode=InnerMode.RADIUS)
        outer.extend(height=self.dim.thickness_wall)

        bottle_holder = SmarterCone.base(self.dim.bottle_outer_diameter_min / 2 + self.dim.thickness_wall).inner(self.dim.bottle_outer_diameter_min / 2)
        bottle_holder.extend(height=self.dim.bottle_hole_depth, radius=self.dim.bottle_outer_diameter_max / 2 + self.dim.thickness_wall)
        bottle_holder.extend(radius=self.dim.dispenser_outer_diameter / 2).inner(mode=InnerMode.RADIUS)
        bottle_holder.extend(height=self.dim.thickness_wall)
        bottle_holder.align(outer).z(Alignment.RL)

        return SmartSolid(bottle_holder, outer, label="mount")


if __name__ == "__main__":
    dimensions = DispenserBottleMountDimensions()
    dispenser_bottle_mount = DispenserBottleMount(dimensions)
    model = dispenser_bottle_mount.create()
    export_3mf("models/other/dispenser_bottle_mount/export.3mf", model)
    export_stl("models/other/dispenser_bottle_mount/stl", model)
