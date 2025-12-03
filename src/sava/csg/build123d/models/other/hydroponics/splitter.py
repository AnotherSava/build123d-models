from dataclasses import dataclass

from bd_warehouse.thread import IsoThread
from build123d import Solid, Plane

from sava.csg.build123d.common.exporter import Exporter
from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.smartsolid import SmartSolid
from sava.csg.build123d.models.other.hydroponics.connector import HoseConnectorFactory, HoseConnectorDimensions


@dataclass
class SplitterDimensions:
    hose_connector: HoseConnectorDimensions = None

    major_diameter: float = 12.7
    pitch: float = 1.25
    length: float = 8
    diameter_inner = 9.5
    pipe_length = 40
    side_pipe_length = 25

    def __post_init__(self):
        self.hose_connector = self.hose_connector or HoseConnectorDimensions(diameter_inner=self.diameter_inner, thickness=None)


class HydroponicsSplitterFactory:
    def __init__(self, dim: SplitterDimensions):
        self.dim = dim
        self.host_connector_factory = HoseConnectorFactory(self.dim.hose_connector)

    def create_thread(self) -> SmartSolid:
        thread_bottom = IsoThread(
            major_diameter=self.dim.major_diameter,
            pitch=self.dim.pitch,
            length=self.dim.length,
            external=True,
            end_finishes=("fade", "fade")
        )
        pipe_diameter_outer = thread_bottom.root_radius * 2

        thread_bottom_solid = SmartSolid(thread_bottom)

        connector, connector_inner = self.host_connector_factory.create_hose_connector_parts(pipe_diameter_outer, self.dim.pipe_length)
        for part in (connector, connector_inner):
            part.mirror(Plane.XY).align_zxy(thread_bottom_solid, Alignment.LR)

        side_pipe_outer = SmartSolid(Solid.make_cylinder(pipe_diameter_outer / 2, self.dim.side_pipe_length))
        side_pipe_outer.rotate((0, 90))
        side_pipe_outer.align_x(connector, Alignment.CR)
        side_pipe_outer.align_y(connector)
        side_pipe_outer_z = (self.dim.pipe_length + self.dim.length) / 2
        side_pipe_outer.align_z(connector, Alignment.L, side_pipe_outer_z)

        side_pipe_inner = SmartSolid(Solid.make_cylinder(self.dim.diameter_inner / 2, self.dim.side_pipe_length))
        side_pipe_inner.solid.location = side_pipe_outer.solid.location

        thread_side = IsoThread(
            major_diameter=self.dim.diameter_inner,
            pitch=1,
            length=self.dim.side_pipe_length - pipe_diameter_outer / 2,
            external=False,
            end_finishes=("chamfer", "fade")
        )

        side_hole = SmartSolid(Solid.make_cylinder(thread_side.min_radius, pipe_diameter_outer / 2))
        side_hole.align_zxy(side_pipe_outer, Alignment.CL).align_x(side_pipe_outer, Alignment.C, self.dim.diameter_inner / 4)

        thread_side.location = side_pipe_outer.solid.location
        thread_side_solid = SmartSolid(thread_side).align_x(side_pipe_outer, Alignment.RL)

        result = SmartSolid(thread_bottom_solid, connector, side_pipe_outer).cut(connector_inner, side_pipe_inner).fuse(thread_side_solid).cut(side_hole)

        return result


dimensions = SplitterDimensions()
splitter_factory = HydroponicsSplitterFactory(dimensions)

component = splitter_factory.create_thread()
Exporter(component).export()
