from dataclasses import dataclass
from enum import IntEnum
from math import cos, sin, radians, tan

from build123d import Vector, Part, Wire

from sava.csg.build123d.common.geometry import create_vector, extrude_wire, create_closed_wire
from sava.csg.build123d.common.smartsolid import SmartSolid


def get_hex_side(short_diagonal: float):
    return short_diagonal * tan(radians(30))


def get_diagonal(short_diagonal: float = None):
    return short_diagonal / cos(radians(30))


def get_distance_y(short_diagonal: float, short_diagonal_gap: float, diagonal_gap: float = None):
    diagonal_gap = short_diagonal_gap if diagonal_gap is None else diagonal_gap
    return diagonal_gap / cos(radians(30)) - short_diagonal_gap / 2 * tan(radians(30)) + get_diagonal(short_diagonal) / 2 + get_hex_side(short_diagonal) / 2


class HexTileEdges(IntEnum):
    NW = 120
    W = 180
    SW = 240
    SE = 300
    E = 0
    NE = 60

    def get_unit_vector(self, length = 1) -> Vector:
        return create_vector(length, self.value)

    def get_next_counter_clock_wise(self, count: int = 1) -> 'HexTileEdges':
        return HexTileEdges((self.value + 60 * count) % 360)

    def get_next_clock_wise(self, count: int = 1) -> 'HexTileEdges':
        return HexTileEdges((self.value - 60 * count) % 360)

    def get_vertices(self):
        return HexTileVertices((self.value + 240) % 360), HexTileVertices((self.value + 300) % 360)

class HexTileManifestEdges(IntEnum):
    NW = 120
    SW = 180
    S = 240
    SE = 300
    NE = 0
    N = 60


class HexTileVertices(IntEnum):
    N = 0
    NW = 60
    SW = 120
    S = 180
    SE = 240
    NE = 300

    # Unit vector for hexagon vertex from its centre
    def get_unit_vector(self) -> Vector:
        return Vector(-sin(radians(self.value)), cos(radians(self.value)))

    # Unit vector for hexagon edge CCW from this vertex (normalized directions)
    def get_edge_counter_clock_wise(self) -> HexTileEdges:
        return HexTileEdges((self.value + 120) % 360)

    # Unit vector for hexagon edge CW from this vertex (normalized directions)
    def get_edge_clock_wise(self) -> HexTileEdges:
        return HexTileEdges((self.value + 60) % 360)

    # Vertex of the hexagon with a specific width
    def get_vector(self, hex_short_diagonal: float) -> Vector:
        return hex_short_diagonal / 2 / cos(radians(30)) * self.get_unit_vector()

    def get_next_clock_wise(self) -> 'HexTileVertices':
        return HexTileVertices((self.value - 60) % 360)

    def get_next_counter_clock_wise(self) -> 'HexTileVertices':
        return HexTileVertices((self.value + 60) % 360)

    @classmethod
    def iterate(cls, start: 'HexTileVertices' = N):
        sorted_vertices = sorted(cls, key=lambda v: v.value)
        start_index = sorted_vertices.index(start)
        for i in range(len(sorted_vertices)):
            yield sorted_vertices[(start_index + i) % len(sorted_vertices)]


@dataclass
class HexagonWallConfiguration:
    offset_distance: float
    offset_clock_wise: float
    offset_counter_clock_wise: float
    display: bool


@dataclass
class HexagonRayConfiguration:
    offset_distance: float


class HexagonConfiguration:
    def __init__(self, ray_thickness: float = None, wall_thickness: float = None):
        self.ray_thickness = ray_thickness
        self.wall_thickness = wall_thickness
        self.walls = {}
        self.rays = {}

    def with_visible_walls(self, offset_distance: float = 0, offset_clock_wise: float = 0, offset_counter_clock_wise: float = 0, *edges: HexTileEdges) -> 'HexagonConfiguration':
        for edge in edges if len(edges) > 0 else HexTileEdges:
            self.walls[edge] = HexagonWallConfiguration(offset_distance, offset_clock_wise, offset_counter_clock_wise, True)

        return self

    def with_hidden_walls(self, offset_distance: float = 0, *edges: HexTileEdges) -> 'HexagonConfiguration':
        for edge in edges if len(edges) > 0 else HexTileEdges:
            self.walls[edge] = HexagonWallConfiguration(offset_distance, 0, 0, False)

        return self

    def with_rays(self, offset_distance: float = 0, *vertices: HexTileVertices) -> 'HexagonConfiguration':
        for vertex in vertices if len(vertices) > 0 else HexTileVertices:
            self.rays[vertex] = HexagonRayConfiguration(offset_distance)

        return self

    def get_vertex_offset(self, vertex: HexTileVertices, multiplier: float = 1) -> Vector:
        cwEdge = vertex.get_edge_clock_wise()
        ccwEdge = vertex.get_edge_counter_clock_wise()

        cwOffset = 0 if cwEdge not in self.walls else self.walls[cwEdge].offset_distance
        ccwOffset = 0 if ccwEdge not in self.walls else self.walls[ccwEdge].offset_distance

        return (cwEdge.get_unit_vector(ccwOffset) - ccwEdge.get_unit_vector(cwOffset)) / cos(radians(30)) * multiplier

class Hexagon:
    def __init__(self, short_diagonal: float, height: float = 0, centre: Vector = Vector()):
        self.short_diagonal = short_diagonal
        self.height = height
        self.centre = centre

        self.ray_length = short_diagonal / 2 / cos(radians(30))
        self.side = get_hex_side(short_diagonal)

    def get_side(self):
        return get_hex_side(self.short_diagonal)

    def get_diagonal(self):
        return get_diagonal(self.short_diagonal)

    def create_ray_solid(self, configuration: HexagonConfiguration) -> Part:
        vertices = [self.get_offset_vertex(vertex, configuration.rays[vertex].offset_distance if vertex in configuration.rays else 0) for vertex in HexTileVertices.iterate()]
        return extrude_wire(create_closed_wire(*vertices), self.height)

    def create_solid(self, multiplier: float = 1) -> Part:
        wire = create_closed_wire(*(self.get_vertex(vertex, multiplier) for vertex in HexTileVertices.iterate()))
        return extrude_wire(wire, self.height)

    def create_walled_wire(self, config: HexagonConfiguration = None) -> Wire:
        return create_closed_wire(*(self.get_walls_intersection(vertex, config) for vertex in HexTileVertices.iterate()))

    def create_walled_solid(self, config: HexagonConfiguration) -> Part:
        return extrude_wire(self.create_walled_wire(config), self.height)

    def get_walls_intersection(self, vertex: HexTileVertices, config: HexagonConfiguration = None, multiplier: float = 1) -> Vector:
        return self.get_vertex(vertex, multiplier) + Vector() if config is None else config.get_vertex_offset(vertex, multiplier)

    def get_vertex(self, vertex: HexTileVertices, multiplier: float = 1) -> Vector:
        return self.get_vertex_vector(vertex, multiplier) + self.centre

    def get_offset_vertex(self, vertex: HexTileVertices, offset: float) -> Vector:
        return self.get_offset_vertex_vector(vertex, offset) + self.centre

    def get_vertex_vector(self, vertex: HexTileVertices, multiplier: float = 1) -> Vector:
        return create_vector(self.ray_length * multiplier, vertex.value)

    def get_offset_vertex_vector(self, vertex: HexTileVertices, offset: float) -> Vector:
        return create_vector(self.ray_length + offset, vertex.value)

    def get_ray_multiplier_for_edge_offset(self, offset: float) -> float:
        return offset / sin(radians(60)) / self.ray_length

    def create_grid(self, configuration: HexagonConfiguration) -> SmartSolid:
        grid = SmartSolid()

        # rays
        for vertex, config in configuration.rays.items():
            multiplier = 1 + config.offset_distance / self.ray_length
            v = self.get_vertex_vector(vertex, multiplier)
            perp = create_vector(configuration.ray_thickness / 2, vertex.value + 90)
            wire = create_closed_wire(perp, v + perp, v - perp, -perp)
            wire.translate(self.centre)
            ray = extrude_wire(wire, self.height)
            cut_ray = ray & self.create_solid(multiplier) if multiplier > 1 else ray & self.create_walled_solid(configuration)
            grid.fuse(cut_ray)

        # walls
        for edge, config in configuration.walls.items():
            if not config.display:
                continue

            v1, v2 = edge.get_vertices()

            ccw_wall_thickness_shift = edge.get_next_counter_clock_wise().get_unit_vector(configuration.wall_thickness * cos(radians(30)))
            cw_wall_thickness_shift = -edge.get_next_clock_wise().get_unit_vector(configuration.wall_thickness * cos(radians(30)))

            v1_vertex = self.get_walls_intersection(v1, configuration) - edge.get_unit_vector(config.offset_clock_wise)
            v2_vertex = self.get_walls_intersection(v2, configuration) + edge.get_unit_vector(config.offset_counter_clock_wise)

            wire = create_closed_wire(v1_vertex, v2_vertex, v2_vertex + ccw_wall_thickness_shift, v1_vertex + cw_wall_thickness_shift)
            grid.fuse(extrude_wire(wire, self.height))

        # central hex
        delta = self.get_ray_multiplier_for_edge_offset(configuration.ray_thickness / 2)
        grid.fuse(self.create_solid(0.5 + delta))
        grid.cut(self.create_solid(0.5 - delta))

        return grid
