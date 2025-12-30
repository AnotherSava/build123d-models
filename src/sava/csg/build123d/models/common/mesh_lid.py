import math
from copy import copy
from dataclasses import dataclass
from typing import Tuple

from build123d import Vector, Solid, Part, Plane, Compound
from traitlets import HasTraits, Float, Int, TraitError, validate

from sava.common.advanced_math import advanced_round
from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.hexagon import Hexagon, HexagonConfiguration, HexTileVertices, get_distance_y
from sava.csg.build123d.common.primitives import create_tapered_box
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass
class MeshLidHandleDimensions:
    minimal_mesh_height: float
    recess_length_coefficient: float
    recess_width_coefficient: float
    slope_length_coefficient: float
    slope_width_coefficient: float
    handle_radius: float
    minimal_mesh_height: float
    beautify_handle: bool = True
    fill_handle_sides: bool = False
    wall_height: float = None # handle might be taller than the wall


# @dataclass
class MeshLidDimensions(HasTraits):
    width = Float(default_value=None)
    height = Float(default_value=None)
    wall_thickness = Float(default_value=None)
    grid_thickness = Float(default_value=None)
    hex_count_length = Int(default_value=None) # how many hexes does the length fit
    length = Float(default_value=None)
    inner_space_height: float=0.0
    fill_corners: bool =False
    handle: MeshLidHandleDimensions = None

    @validate('hex_count_length')
    def _validate_hex_count_length(self, proposal):
        value = proposal['value']
        if value is not None and value % 2 != 0:
            raise TraitError(f"hex_count_length must be even, got {value}")
        return value

    @property
    def wall_height(self):
        return self.height if self.handle is None or self.handle.wall_height is None else self.handle.wall_height

    def get_mesh_height(self):
        return self.wall_height - (self.inner_space_height or 0)

    def get_hex_short_diagonal(self):
        return (self.length - self.wall_thickness * 2 - self.grid_thickness * (self.hex_count_length - 1)) / self.hex_count_length


class MeshLid(SmartBox):
    def __init__(self, dimensions: MeshLidDimensions):
        super().__init__(dimensions.length, dimensions.width, dimensions.height)

        self.dimensions = dimensions

        self.internal_mesh = SmartBox(self.dimensions.length - self.dimensions.wall_thickness * 2, self.dimensions.width - self.dimensions.wall_thickness * 2, self.dimensions.get_mesh_height())
        self.internal_mesh.move(self.dimensions.wall_thickness, self.dimensions.wall_thickness, self.dimensions.height - self.dimensions.wall_height)

        self.internal_mesh_hex = Hexagon(self.dimensions.get_hex_short_diagonal(), self.dimensions.get_mesh_height())

        base_distance_y = get_distance_y(self.dimensions.get_hex_short_diagonal(), self.dimensions.grid_thickness)
        self.full_row_count = math.floor(self.internal_mesh.y_size / base_distance_y)
        self.full_row_count += self.full_row_count % 2
        self.distance_y = self.internal_mesh.y_size / self.full_row_count
        offset_y = self.distance_y - base_distance_y

        self.hexes_covered_y = None
        self.hex_configuration = HexagonConfiguration().with_rays(offset_y, HexTileVertices.N, HexTileVertices.S)

    def create_mesh_hex(self, row: int = 0, column: int = 0) -> Part:
        solid = self.internal_mesh_hex.create_ray_solid(self.hex_configuration)
        solid.position = self.create_hex_coordinates(row, column)
        return solid

    def create_hex_coordinates(self, row: int, column: int) -> Vector:
        starting_hex_x = self.internal_mesh.x_min - self.dimensions.grid_thickness / 2
        x = starting_hex_x + (self.dimensions.get_hex_short_diagonal() + self.dimensions.grid_thickness) * (column + row % 2 / 2)
        y = self.internal_mesh.y_min + self.distance_y * row

        return Vector(x, y, self.internal_mesh.z_min)

    def create_lid_mesh(self) -> SmartSolid:
        print(f"Mesh lid: rows = {self.full_row_count}, columns = {self.dimensions.hex_count_length}")
        solid = self.create_mesh_hex()
        hexes = []
        for row in range(self.full_row_count + 1):
            for column in range(self.dimensions.hex_count_length + 1):
                if not self.dimensions.fill_corners or row not in [0, self.full_row_count] or column not in [0, self.dimensions.hex_count_length]:
                    solid_copy = copy(solid)
                    solid_copy.position = self.create_hex_coordinates(row, column)
                    hexes.append(solid_copy)

        return self.internal_mesh.intersected(Compound(hexes))

    def create_lid(self) -> SmartSolid:
        lid = SmartBox(self.dimensions.length, self.dimensions.width, self.dimensions.wall_height)
        lid.align_xy(self).align_z(self, Alignment.LR, self.dimensions.height - self.dimensions.wall_height)

        if self.dimensions.inner_space_height:
            space_below = SmartBox(self.dimensions.length - self.dimensions.wall_thickness * 2, self.dimensions.width - self.dimensions.wall_thickness * 2, self.dimensions.inner_space_height)
            space_below.align(self).align_z(self, Alignment.RL)
            lid.cut(space_below)

        lid.cut(self.create_lid_mesh())

        if self.dimensions.handle:
            recess_inner, handle = self.create_handle()
            lid.cut(recess_inner).fuse(handle)

        return lid

    def create_recess(self, length: float, width: float, height) -> SmartSolid:
        base_slope_length = length * self.dimensions.handle.slope_length_coefficient
        full_hexes_covered_x = max(1, int(2 * base_slope_length / self.internal_mesh_hex.short_diagonal))
        slopeLength = full_hexes_covered_x * (self.internal_mesh_hex.short_diagonal + self.dimensions.grid_thickness) / 2 - self.dimensions.grid_thickness / 2

        base_slope_width = width * self.dimensions.handle.slope_width_coefficient
        hexes_covered_y = int(base_slope_width / self.distance_y)
        rest = base_slope_width - hexes_covered_y * self.distance_y

        if full_hexes_covered_x % 2 == 0:
            half_hexes_covered_y = 0
            hexes_covered_y = max(1, hexes_covered_y)
        else:
            back = self.internal_mesh_hex.side - self.distance_y
            forward = self.internal_mesh_hex.side
            if abs(-back - rest) < abs(forward - rest):
                hexes_covered_y = max(hexes_covered_y - 1, 0)
            half_hexes_covered_y = 1

        slope_width = hexes_covered_y * self.distance_y + half_hexes_covered_y * self.internal_mesh_hex.get_side()
        taper_box = create_tapered_box(length, width, height, length - slopeLength * 2, width - slope_width * 2)

        return taper_box.move_vector(Vector(self.dimensions.length / 2, self.dimensions.width / 2, self.dimensions.height - self.dimensions.wall_height))

    def get_recess_dimensions(self) -> Tuple[float, float]:
        base_recess_length = self.dimensions.length * self.dimensions.handle.recess_length_coefficient
        base_recess_width = self.dimensions.width * self.dimensions.handle.recess_width_coefficient

        if not self.dimensions.handle.beautify_handle:
            return base_recess_length, base_recess_width

        self.hexes_covered_y = advanced_round(base_recess_width / self.distance_y, 4, self.dimensions.hex_count_length * 2 + self.full_row_count + 2, 0, self.full_row_count - 1)
        recess_width = self.hexes_covered_y * self.distance_y + self.internal_mesh_hex.side

        hexes_covered_x = min(advanced_round(base_recess_length / (self.internal_mesh_hex.short_diagonal + self.dimensions.grid_thickness), 2, 1), self.dimensions.hex_count_length)
        recess_length = hexes_covered_x * (self.internal_mesh_hex.short_diagonal + self.dimensions.grid_thickness) - self.dimensions.grid_thickness

        return recess_length, recess_width

    def create_handle(self) -> Tuple[SmartSolid, SmartSolid]:
        recess_length, recess_width = self.get_recess_dimensions()

        recess = self.create_recess(recess_length, recess_width, self.dimensions.get_mesh_height() - self.dimensions.handle.minimal_mesh_height)

        handle_width = recess_width + self.internal_mesh_hex.get_side()
        handle_starting_position = Vector(self.x_size / 2, (self.dimensions.width - handle_width) / 2, self.dimensions.handle.handle_radius / 3 * 2)

        rounded_handle = SmartSolid(Solid.make_sphere(self.dimensions.handle.handle_radius).translate(Vector(0, shiftY, 0)) for shiftY in [0, handle_width])
        rounded_handle.fuse(Solid.make_cylinder(self.dimensions.handle.handle_radius, handle_width, Plane.XZ))
        rounded_handle.move_vector(handle_starting_position)
        rounded_handle.intersect(self.solid)

        handle = SmartBox(self.dimensions.wall_thickness, handle_width, self.z_size)
        handle.move(-handle.x_size / 2, 0, -self.dimensions.handle.handle_radius / 3 * 2)
        handle.move_vector(handle_starting_position)

        full_handle = SmartSolid(handle, rounded_handle)

        delta_hexes = (self.full_row_count - self.hexes_covered_y) / 2
        hex_bottom = self.create_mesh_hex(delta_hexes - 1, self.dimensions.hex_count_length / 2)
        hex_top = self.create_mesh_hex(self.full_row_count - delta_hexes + 1, self.dimensions.hex_count_length / 2)

        if self.dimensions.handle.fill_handle_sides:
            full_handle.fuse(hex_top, hex_bottom).intersect(self)
        else:
            full_handle.cut(hex_top, hex_bottom)

        return recess, full_handle
