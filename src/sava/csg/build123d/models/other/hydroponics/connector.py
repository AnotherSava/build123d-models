from dataclasses import dataclass

from build123d import Solid

from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.primitives import create_cone_with_angle
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass
class HoseConnectorDimensions:
    pipe_length: float = 0
    diameter_outer: float = 18.0
    thickness: float = 1.6
    length: float = 20.0
    segment_count: int = 3
    diameter_delta: float = 1.5 # diameter gradient will be [diameter_outer - diameter_delta; diameter_outer + diameter_delta]
    distance_between_connectors: float = 10
    connector_offset_x: float = 5
    connector_offset_z: float = -5

    @property
    def diameter_inner(self) -> float:
        return self.diameter_outer - 2 * self.thickness - self.diameter_delta

    @property
    def diameter_outer_max(self) -> float:
        return self.diameter_outer + self.diameter_delta

    @property
    def distance_between_pipe_centres(self):
        return self.distance_between_connectors + self.diameter_outer_max


class HoseConnectorFactory:
    def __init__(self, dim: HoseConnectorDimensions):
        self.dim = dim

    def create_hose_connector(self, pipe_diameter: float, pipe_length: float = None):
        result = None

        segment_length = self.dim.length / self.dim.segment_count
        last_segment = None
        for i in range(self.dim.segment_count):
            diameter_min = self.dim.diameter_outer - self.dim.diameter_delta * (1 - i / (self.dim.segment_count - 1))
            diameter_max = self.dim.diameter_outer + self.dim.diameter_delta * i / (self.dim.segment_count - 1)
            bottom_radius = diameter_min / 2
            radius1 = diameter_max / 2
            segment = SmartSolid(Solid.make_cone(bottom_radius, radius1, segment_length))
            radius = diameter_max / 2
            top_radius = min(pipe_diameter, diameter_min) / 2
            angle = -45
            cap = create_cone_with_angle(radius, top_radius, angle)

            if result is None:
                result = segment.copy()  # segment shouldn't be modified (reused as last_segment)
            else:
                segment.align_zxy(last_segment, Alignment.RR)
                result.fuse(segment)

            cap.align_zxy(result, Alignment.RR)
            result.fuse(cap)

            last_segment = segment

        if pipe_length:
            cap = SmartSolid(Solid.make_cylinder(pipe_diameter / 2, pipe_length))
            result.fuse(cap.align_zxy(result, Alignment.RR))

        internal = SmartSolid(Solid.make_cylinder(self.dim.diameter_inner / 2, result.z_size))
        return result.cut(internal.align(result))
