import logging
from dataclasses import dataclass
from enum import Enum
from math import radians, tan, cos
from typing import Callable, Tuple

from build123d import Axis, Plane

from sava.csg.build123d.common.exporter import clear, export, save_3mf, save_stl, show_red, show_blue
from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartercone import SmarterCone
from sava.csg.build123d.common.smartsolid import SmartSolid, PositionalFilter


class ConnectorRecesses:
    def __init__(self, dim: 'CableStorageDimensions'):
        self.dim = dim

    def generic(self, length: float, width: float, height: float) -> Tuple[SmartSolid, SmartBox]:
        extra_width = height / tan(radians(self.dim.cable_holder_angle))
        connector_cut = SmartBox.with_base_angles_and_height(length + extra_width, width + extra_width, -height, 90, self.dim.cable_holder_angle)
        connector_offset = connector_cut.create_offset(self.dim.cable_holder_width, up=0, down=0)
        return connector_cut, connector_offset

    def dvi(self, length: float, width: float, height: float) -> Tuple[SmartSolid, SmartBox]:
        connector_cut, connector_fuse = self.generic(length, width, height)

        extra_holes = []
        for x_offset in [0, 33]:
            for y_offset in [0, 15]:
                extra_holes.append(SmarterCone.cylinder(7.7 / 2, 16.5).move(x_offset, y_offset))

        holes = SmartSolid(extra_holes)
        holes.align(connector_cut).z(Alignment.RL)
        connector_cut.fuse(holes)

        return connector_cut, connector_fuse


# Type alias for recess functions (unbound method signature)
RecessFn = Callable[['ConnectorRecesses', float, float, float], Tuple[SmartSolid, SmartBox]]


@dataclass(frozen=True)
class SidewaysConnectorDimensions:
    cable_diameter: float # ~1 mm gap
    holder_length: float # max length of the connectors, no gap
    cable_hole_length: float # max length on the cable level, no gap
    cable_hole_width: float # max width on the cable level, no gap
    cable_hole_height: float # depth of the cable holder compartment
    cable_hole_x_alignment: Alignment = Alignment.C
    cable_hole_x_shift_custom: float = 0
    recess_fn: RecessFn = ConnectorRecesses.generic


class SidewayConnector(Enum):
    TYPE_E_ANGLED_TO_EIC_C13 = SidewaysConnectorDimensions(7, 63, 28, 13.8, 19, Alignment.LR) # Type E angled - PSU female
    EIC_C14_TO_EIC_C13 = SidewaysConnectorDimensions(7.5, 36, 32, 13.8, 22) # PSU female - PSU male
    DVI_TO_DVI = SidewaysConnectorDimensions(6, 41, 13, 26, 9, recess_fn=ConnectorRecesses.dvi)
    # NEMA_5_15P (Type A grounded male)
    # NEMA_1_15P (Type A male)
    # EIC_C7 (Barrel)
    # EIC_C5 (Cloverleaf)


class CableStorageDimensions:
    width: float = 42.0
    height: float = 8.0
    cable_holder_width: float = 2
    cable_holder_angle: float = 87.5
    length_padding: float = 2.0
    railing_width: float = 2
    railing_offset: float = 2
    railing_ceiling_thickness: float = 2
    cable_diameter_gap: float = 1
    cable_hole_fillet_radius: float = 0.9
    railing_fillet_radius: float = 1

    railing_gap_between_rails: float = 0.1
    railing_handle_height: float = 5
    railing_gap: float = 0.05

class CableStorage:
    def __init__(self, dim: CableStorageDimensions):
        self.dim = dim

    def create_top_surface(self, length: float) -> SmartSolid:
        dim = self.dim

        pencil = Pencil(Plane.YZ)
        pencil.right(dim.width / 2)
        pencil.down(dim.height)
        pencil.jump((-dim.railing_offset, dim.railing_offset))
        pencil.up_to(-dim.railing_ceiling_thickness - dim.railing_width / 2)
        pencil.arc_with_radius(dim.railing_width / 2, 90, 180)
        pencil.down_to(dim.railing_offset - dim.height)
        pencil.jump((-dim.railing_offset, -dim.railing_offset))
        solid = pencil.extrude_mirrored_y(length + self.dim.length_padding * 2)
        solid.fillet_x(self.dim.railing_fillet_radius, Axis.Z, dim.railing_offset - dim.height)
        return solid

    def get_cable_holder_x_offset(self, dim: SidewaysConnectorDimensions) -> float:
        if dim.cable_hole_x_alignment == Alignment.LR:
            return max(dim.cable_hole_x_shift_custom, self.dim.length_padding)

        if dim.cable_hole_x_alignment == Alignment.RL:
            return -max(dim.cable_hole_x_shift_custom, self.dim.length_padding)

        return dim.cable_hole_x_shift_custom

    def create_sideways_holder(self, connector: SidewayConnector) -> SmartSolid:
        dim = connector.value
        box = self.create_top_surface(dim.holder_length)

        recesses = ConnectorRecesses(self.dim)
        connector_cut, connector_fuse = dim.recess_fn(recesses, dim.cable_hole_length, dim.cable_hole_width, dim.cable_hole_height)

        connector_cut.align(box).x(dim.cable_hole_x_alignment, self.get_cable_holder_x_offset(dim)).z(Alignment.RL)
        connector_fuse.align(connector_cut).z(Alignment.RL)

        cable_cut = SmartBox(dim.cable_diameter, self.dim.width / 2, dim.cable_hole_height, label="cable_cut")
        cable_cut.align(connector_cut).y(Alignment.CR).z(Alignment.RL)

        result = SmartSolid(box, connector_fuse, label=f"holder {connector.name.lower()}").cut(connector_cut, cable_cut)
        result.fillet_positional(self.dim.cable_hole_fillet_radius, Axis.Z, PositionalFilter(Axis.Y, box.y_max), PositionalFilter(Axis.X))
        connector_fuse_filters = [PositionalFilter(Axis.Y, connector_fuse.y_min, connector_fuse.y_max), PositionalFilter(Axis.X, connector_fuse.x_min, connector_fuse.x_max)]
        result.fillet_positional(self.dim.cable_hole_fillet_radius, Axis.Z, *connector_fuse_filters, angle_tolerance=(90 - self.dim.cable_holder_angle))

        return result

    def create_rail(self, length: float) -> SmartSolid:
        dim = self.dim

        pencil = Pencil(Plane.YZ)
        pencil.right(dim.railing_gap_between_rails / 2 + dim.railing_gap)
        pencil.jump((dim.railing_offset, dim.railing_offset))
        pencil.fillet(self.dim.railing_fillet_radius)
        pencil.up_to(dim.height - dim.railing_ceiling_thickness - dim.railing_width / 2)
        pencil.arc_with_radius(dim.railing_width / 2 - dim.railing_gap, -90, -180)
        pencil.down_to(dim.railing_offset-dim.railing_offset * cos(radians(45)))
        pencil.fillet(self.dim.railing_fillet_radius)
        pencil.jump((-dim.railing_offset, -dim.railing_offset))
        pencil.fillet(self.dim.railing_fillet_radius)
        pencil.down(dim.railing_handle_height)
        pencil.left()
        return pencil.extrude_mirrored_y(length)


    def create_rails(self, length: float) -> SmartSolid:
        offset = self.dim.width + self.dim.railing_gap_between_rails - dimensions.railing_gap * 2

        rails = SmartSolid(self.create_rail(length).move_y(offset * i) for i in range(3))

        wall_thickness = 3
        wall = rails.create_bound_box().create_shell(east=wall_thickness, west=wall_thickness)

        return rails.fuse(wall)


# logging.getLogger('sava').setLevel(logging.DEBUG)

dimensions = CableStorageDimensions()
cable_storage = CableStorage(dimensions)

holder = cable_storage.create_sideways_holder(SidewayConnector.DVI_TO_DVI)
export(holder)
rails = cable_storage.create_rails(150)
rails.align(holder).z(Alignment.RL, -dimensions.railing_ceiling_thickness - dimensions.railing_gap).y(Alignment.LR, -dimensions.railing_width * 2 - dimensions.railing_gap_between_rails / 2 + dimensions.railing_gap)
export(rails)
save_3mf("models/other/cable_storage/export.3mf", True)

clear()
for connector in SidewayConnector:
    export(cable_storage.create_sideways_holder(connector))
export(rails)

save_stl("models/other/cable_storage/stl")
