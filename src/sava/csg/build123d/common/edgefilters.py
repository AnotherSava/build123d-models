from dataclasses import dataclass
from enum import Enum, auto
from math import acos, degrees
from typing import TYPE_CHECKING

from build123d import Axis, Face, Edge, ShapeList, Vertex

from sava.csg.build123d.common.geometry import is_within_interval

if TYPE_CHECKING:
    from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass
class PositionalFilter:
    axis: Axis
    minimum: float = None
    maximum: float = None
    inclusive: tuple[bool, bool] = None


@dataclass
class SurfaceFilter:
    """Filter edges that lie on specific faces or a solid's surface.

    Provide either `solid` (checks all faces) or `faces` (checks specific faces).
    """
    solid: 'SmartSolid' = None
    faces: list[Face] = None
    tolerance: float = 1e-5

    def __post_init__(self):
        if self.solid is None and self.faces is None:
            raise ValueError("SurfaceFilter requires either 'solid' or 'faces'")
        if self.faces is None:
            self.faces = list(self.solid.wrap_solid().faces())


@dataclass
class AxisFilter:
    """Filter edges parallel to an axis."""
    axis: Axis
    angle_tolerance: float = 1e-5


# Convenience constants
AXIS_X = AxisFilter(Axis.X)
AXIS_Y = AxisFilter(Axis.Y)
AXIS_Z = AxisFilter(Axis.Z)

EdgeFilter = PositionalFilter | SurfaceFilter | AxisFilter


class FilletDebug(Enum):
    """Debug mode for fillet_by method."""
    ALL = auto()      # Show all matched edges in red
    PARTIAL = auto()  # Try each edge, show failed in red, succeeded in green


def filter_edges_by_position(edges: ShapeList[Edge], axis: Axis, minimum: float, maximum: float, inclusive: tuple[bool, bool]) -> ShapeList[Edge]:
    """Filter edges by position along an axis with tolerance-aware boundary comparisons.

    Args:
        edges: List of edges to filter
        axis: Axis to measure position along
        minimum: Lower bound of the interval
        maximum: Upper bound of the interval
        inclusive: Tuple of (include_min, include_max) for boundary inclusion

    Returns:
        Filtered list of edges within the interval
    """
    axis_dir = axis.direction.normalized()
    filtered = [edge for edge in edges if is_within_interval(edge.center().dot(axis_dir), minimum, maximum, inclusive)]
    return ShapeList(filtered)


def filter_edges_by_axis(edges: ShapeList[Edge], axis: Axis, angle_tolerance: float = 1e-5, num_samples: int = 10) -> ShapeList[Edge]:
    """Filter edges by alignment to an axis, checking tangents at multiple points.

    For an edge to pass, the tangent at every sampled point must be within the
    angle tolerance of the axis. This correctly handles arcs and curved edges.

    Args:
        edges: List of edges to filter
        axis: Axis to filter by (edges parallel to this axis are selected)
        angle_tolerance: Maximum angle deviation from axis in degrees. Default is 1e-5.
        num_samples: Number of points along the edge to check tangent. Default is 10.

    Returns:
        Filtered list of edges aligned with the axis
    """
    axis_dir = axis.direction.normalized()
    filtered = []
    for edge in edges:
        max_angle = 0.0
        for i in range(num_samples):
            t = i / (num_samples - 1) if num_samples > 1 else 0.5
            tangent = edge.tangent_at(t).normalized()
            dot = abs(tangent.dot(axis_dir))
            angle = degrees(acos(min(1.0, dot)))
            max_angle = max(max_angle, angle)
            if angle > angle_tolerance:
                break  # No need to check more points
        if max_angle <= angle_tolerance:
            filtered.append(edge)
    return ShapeList(filtered)


def filter_edges_by_surface(edges: ShapeList[Edge], surface_filter: SurfaceFilter) -> ShapeList[Edge]:
    """Filter edges that lie on the given faces.

    Args:
        edges: List of edges to filter
        surface_filter: SurfaceFilter containing faces and tolerance

    Returns:
        Filtered list of edges that lie on any of the faces
    """
    result = []
    for edge in edges:
        vertices = [Vertex(edge.position_at(t)) for t in [0, 0.25, 0.5, 0.75, 1.0]]
        # Check if all points lie on any single face
        for face in surface_filter.faces:
            if all(face.distance(v) < surface_filter.tolerance for v in vertices):
                result.append(edge)
                break
    return ShapeList(result)
