from dataclasses import dataclass

from build123d import Plane, Axis

from sava.csg.build123d.common.exporter import export_3mf, export_stl
from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartercone import SmarterCone
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass(frozen=True)
class DispenserBottleMountDimensions:
    dispenser_inner_diameter: float = 70
    dispenser_outer_diameter: float = 76
    bottle_inner_diameter_max: float = 26
    bottle_inner_diameter_min: float = 10
    bottle_mount_gradient_height: float = 70
    bottle_mount_wall_depth: float = 10
    bottle_mount_holder_recess_angle: float = 45
    thickness_wall: float = 2
    thickness_leg: float = 3
    section_count: int = 3
    bottle_holder_top_angle: float = 45

    @property
    def bottle_outer_diameter_max(self) -> float:
        return self.bottle_inner_diameter_max * 1.3


class DispenserBottleMount:
    def __init__(self, dim: DispenserBottleMountDimensions):
        self.dim = dim

    def create_holder_part(self) -> SmartSolid:
        pencil = Pencil(Plane.XZ)
        pencil.right(self.dim.bottle_outer_diameter_max / 2)
        pencil.jump((self.dim.thickness_leg, self.dim.thickness_leg))
        pencil.left_to(self.dim.bottle_inner_diameter_max / 2)
        pencil.jump_to((self.dim.bottle_inner_diameter_min / 2, self.dim.bottle_mount_gradient_height))
        return pencil.extrude_mirrored_y(self.dim.thickness_wall)

    def _validate(self) -> None:
        if self.dim.section_count <= 0:
            raise ValueError(f"section_count must be positive, got {self.dim.section_count}")

    def create(self) -> SmartSolid:
        self._validate()
        slope = SmarterCone.base(self.dim.bottle_outer_diameter_max / 2 + self.dim.thickness_wall).inner(self.dim.bottle_outer_diameter_max / 2)
        slope.extend(radius=self.dim.dispenser_inner_diameter / 2, angle=self.dim.bottle_mount_holder_recess_angle)
        slope.extend(height=self.dim.bottle_mount_wall_depth)
        slope.extend(radius=self.dim.dispenser_outer_diameter / 2)
        slope.extend(height=self.dim.thickness_wall).inner(self.dim.dispenser_inner_diameter / 2 - self.dim.thickness_wall)

        part = self.create_holder_part()
        part.align(slope).z(Alignment.LR)
        parts = [part.rotated(Axis.Z, 360 / self.dim.section_count * i) for i in range(self.dim.section_count)]

        mount = SmartSolid(parts, label="mount")

        parts_cone = SmarterCone.base(0).extend(height=-mount.z_size, angle=-self.dim.bottle_holder_top_angle).aligned(mount)

        return mount.intersect(parts_cone).fuse(slope)


if __name__ == "__main__":
    dimensions = DispenserBottleMountDimensions()
    dispenser_bottle_mount = DispenserBottleMount(dimensions)
    model = dispenser_bottle_mount.create()
    export_3mf("models/other/dispenser_bottle_mount/export.3mf", model)
    export_stl("models/other/dispenser_bottle_mount/stl", model)
