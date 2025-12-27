from dataclasses import dataclass
from math import cos, radians

from bd_warehouse.thread import IsoThread
from build123d import Solid

from sava.csg.build123d.common.exporter import export, save_3mf
from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartsolid import SmartSolid
from sava.csg.build123d.models.hydroponics.connector import HoseConnectorFactory, HoseConnectorDimensions


@dataclass
class SplitterDimensions:
    hose_connector: HoseConnectorDimensions = None

    major_diameter: float = 12.7
    pipe_diameter_outer: float = 14
    pitch: float = 1.25
    length: float = 8
    diameter_inner: float = 9
    thread_diameter_delta: float = 0.2
    pipe_length: float = 30
    side_pipe_length: float = 25

    handle_length: float = 15
    handle_height: float = 3

    def __post_init__(self):
        self.hose_connector = self.hose_connector or HoseConnectorDimensions(diameter_inner=self.diameter_inner, thickness=None)


class HydroponicsSplitterFactory:
    def __init__(self, dim: SplitterDimensions):
        self.dim = dim
        self.host_connector_factory = HoseConnectorFactory(self.dim.hose_connector)

    def create_splitter(self) -> SmartSolid:
        thread_bottom = self.create_thread_bottom()

        pipe_diameter_outer = thread_bottom.root_radius * 2

        thread_bottom_solid = SmartSolid(thread_bottom)
        core = SmartSolid(Solid.make_cylinder(thread_bottom.root_radius, self.dim.length)).align(thread_bottom_solid)

        connector = self.host_connector_factory.create_hose_connector(self.dim.pipe_diameter_outer, self.dim.pipe_length)
        connector.align_zxy(core, Alignment.LL)

        connector_inner = SmartSolid(Solid.make_cylinder(self.dim.diameter_inner / 2, self.dim.length + connector.z_size))
        connector_inner.align_zxy(connector, Alignment.LR)
        # show_red(connector_inner)

        side_pipe_outer = SmartSolid(Solid.make_cylinder(pipe_diameter_outer / 2, self.dim.side_pipe_length))
        side_pipe_outer.rotate((0, 90))
        side_pipe_outer.align_x(connector, Alignment.CR)
        side_pipe_outer.align_y(connector)
        side_pipe_outer_z = (self.dim.pipe_length + self.dim.length) / 2
        side_pipe_outer.align_z(connector, Alignment.R, -side_pipe_outer_z)

        side_pipe_inner = SmartSolid(Solid.make_cylinder(self.dim.diameter_inner / 2, self.dim.side_pipe_length)).colocate(side_pipe_outer)

        thread_side = IsoThread(
            major_diameter=self.dim.diameter_inner,
            pitch=1,
            length=self.dim.side_pipe_length - pipe_diameter_outer / 2,
            external=False,
            end_finishes=("chamfer", "fade")
        )

        side_hole = SmartSolid(Solid.make_cylinder(thread_side.min_radius, pipe_diameter_outer / 2))
        side_hole.align_zxy(side_pipe_outer, Alignment.CR).align_x(side_pipe_outer, Alignment.C, self.dim.diameter_inner / 4)

        thread_side_solid = SmartSolid(thread_side).colocate(side_pipe_outer).align_x(side_pipe_outer, Alignment.RL)

        result = SmartSolid(core, thread_bottom_solid, connector, side_pipe_outer)
        result.cut(connector_inner, side_pipe_inner)
        result.fuse(thread_side_solid)
        result.cut(side_hole)

        return result

    def create_thread_bottom(self) -> IsoThread:
        return IsoThread(
            major_diameter=self.dim.major_diameter,
            pitch=self.dim.pitch,
            length=self.dim.length,
            external=True,
            end_finishes=("fade", "fade")
        )

    def create_screw(self) -> SmartSolid:
        pipe_radius_outer = self.create_thread_bottom().root_radius

        screw_length = self.dim.side_pipe_length - pipe_radius_outer

        thread_screw = IsoThread(
            major_diameter=self.dim.diameter_inner - self.dim.thread_diameter_delta,
            pitch=1,
            length=screw_length,
            external=True,
            end_finishes=("fade", "fade")
        )

        thread_screw_solid = SmartSolid(thread_screw)
        core_screw = SmartSolid(Solid.make_cylinder(thread_screw.min_radius, screw_length))

        width = thread_screw.major_diameter * cos(radians(45))

        handle = SmartBox(self.dim.handle_length, width, self.dim.handle_height)
        handle.fillet_z(width / 2 - 0.01)
        handle.align_zxy(core_screw, Alignment.LL)

        handle2 = handle.oriented((0, 0, 90)).align_zxy(core_screw, Alignment.LL)

        result = SmartSolid(thread_screw_solid, core_screw, handle, handle2)

        return result


dimensions = SplitterDimensions()
splitter_factory = HydroponicsSplitterFactory(dimensions)

splitter = splitter_factory.create_splitter()
screw = splitter_factory.create_screw().move_x(-30).align_z(splitter, Alignment.LR)
export(splitter, "splitter")
export(screw, "screw")
save_3mf()
