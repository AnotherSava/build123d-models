from dataclasses import dataclass
from enum import Enum
from math import radians, tan

from build123d import Axis

from sava.csg.build123d.common.exporter import clear, export, save_3mf, save_stl, show_red
from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass(frozen=True)
class ConnectorDimensions:
    length: float
    width: float


class ConnectorType(Enum):
    TYPE_E_ANGLED = ConnectorDimensions(48.0, 36.2)
    TYPE_C = ConnectorDimensions(13.9, 35.4)
    NEMA_1_15P = ConnectorDimensions(19.2, 27) # Type A male
    NEMA_5_15P = ConnectorDimensions(23.2, 24.5) # Type A grounded male
    EIC_C13 = ConnectorDimensions(15.3, 27.3) # PSU female
    EIC_C14 = ConnectorDimensions(16.3, 26.5) # PSU male
    EIC_C7 = ConnectorDimensions(11.9, 16) # Barrel
    EIC_C5 = ConnectorDimensions(16.9, 22.4) # Cloverleaf
    DVI = ConnectorDimensions(15.0, 40.5)
    HDMI = ConnectorDimensions(11.2, 20.9)

class DoubleConnectorDimensions:
    cable_hole_width: float = 14
    cable_hole_length: float = 29
    cable_hole_shift: float = 0
    cable_holder_height: float = 15
    holder_length: float = 63

class SidewaysConnectorDimensions:
    cable_diameter: float = 7
    cable_hole_length: float = 28
    cable_hole_width: float = 13.8
    cable_hole_shift: float = 2
    holder_length: float = 65

class CableStorageDimensions:
    width: float = 42.0
    height: float = 4.0
    cable_holder_width: float = 2
    cable_holder_height: float = 13
    cable_holder_angle: float = 85
    length_padding: float = 1.0
    wall_length_minimal: float = 2.0
    railing_width: float = 1
    railing_depth: float = 1
    cable_diameter_gap: float = 1

class CableStorage:
    def __init__(self, dim: CableStorageDimensions):
        self.dim = dim

    def create_holder(self, dim: DoubleConnectorDimensions) -> SmartSolid:
        box = self.create_top_surface(dim.holder_length)

        pencil = Pencil()
        pencil.right(dim.cable_hole_length + dim.cable_hole_shift + self.dim.length_padding)
        pencil.arc_with_radius(dim.cable_hole_width / 2, 0, 180)
        pencil.left()
        cut = pencil.extrude(self.dim.height)
        cut.align(box).xz(Alignment.LR)

        extra_width = self.dim.cable_holder_height / tan(radians(self.dim.cable_holder_angle)) + 2 * self.dim.cable_holder_width
        cable_holder = SmartBox.with_base_angles_and_height(cut.x_size + extra_width, cut.y_size + extra_width, self.dim.cable_holder_height, -90, -self.dim.cable_holder_angle)
        cable_holder.align(box).x(Alignment.LR).z(Alignment.LL)
        cable_holder = cable_holder.create_shell(north=-self.dim.cable_holder_width, south=-self.dim.cable_holder_width, east=-self.dim.cable_holder_width)

        return SmartSolid(box, cable_holder, label="holder").cut(cut)

    def create_top_surface(self, length: float) -> SmartSolid:
        box_top = SmartBox(length + self.dim.length_padding * 2, self.dim.width, self.dim.railing_depth)
        box_bottom = SmartBox(box_top.length, box_top.width - self.dim.railing_width * 2, self.dim.height - box_top.height)
        box_bottom.align(box_top).z(Alignment.LL)
        return box_top.fuse(box_bottom)

    def create_sideways_holder(self, dim: SidewaysConnectorDimensions) -> SmartSolid:
        box = self.create_top_surface(dim.holder_length)

        extra_width = self.dim.cable_holder_height / tan(radians(self.dim.cable_holder_angle))
        print(f"extra_width: {extra_width}")
        connector_cut = SmartBox.with_base_angles_and_height(dim.cable_hole_length + extra_width, dim.cable_hole_width + extra_width, -self.dim.cable_holder_height, 90, self.dim.cable_holder_angle, "connector_cut")
        connector_cut.align(box).x(Alignment.LR, dim.cable_hole_shift).z(Alignment.RL)

        cable_cut = SmartBox(dim.cable_diameter, self.dim.width / 2, self.dim.cable_holder_height, label="cable_cut")
        cable_cut.align(connector_cut).y(Alignment.CR)

        connector_offset = connector_cut.create_offset(self.dim.cable_holder_width, up=0, down=0)

        result = SmartSolid(box, connector_offset, label="holder").cut(connector_cut, cable_cut)
        result.fillet_z(0.5, Axis.X, inclusive=(False, False), angle_tolerance=(90 - self.dim.cable_holder_angle) * 1.01)

        return result


dimensions = CableStorageDimensions()
cable_storage = CableStorage(dimensions)

def export_3mf(holder: SmartSolid):
    export(holder)
    save_3mf("models/other/cable_storage/export.3mf", True)

def export_stl(holder: SmartSolid):
    clear()
    export(holder)
    save_stl("models/other/cable_storage/stl")


holder_solid = cable_storage.create_sideways_holder(SidewaysConnectorDimensions())
# holder_solid = cable_storage.create_holder(DoubleConnectorDimensions())
export_3mf(holder_solid)
export_stl(holder_solid)

