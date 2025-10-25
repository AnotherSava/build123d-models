from copy import copy
from dataclasses import dataclass
from typing import Iterable

from build123d import Vector, fillet, Axis, Location, ShapePredicate, Plane, GeomType, BoundBox, Compound, VectorLike, scale, mirror, Edge, ShapeList

from sava.csg.build123d.common.geometry import Alignment, Direction, calculate_position
from sava.csg.build123d.common.pencil import Pencil


@dataclass
class PositionalFilter:
    axis: Axis
    minimum: float = None
    maximum: float = None
    inclusive: tuple[bool, bool] = None


def get_solid(element):
    return element.solid if isinstance(element, SmartSolid) else element

def fuse(*args):
    elements = []

    for arg in args:
        if isinstance(arg, Iterable):
            elements += [get_solid(sub_arg) for sub_arg in arg]
        else:
            elements.append(get_solid(arg))

    return elements[0] if len(elements) == 1 else Compound(elements)


class SmartSolid:
    def __init__(self, *args):
        self.solid = fuse(*args) if len(args) > 0 else None

    @property
    def bound_box(self) -> BoundBox:
        return self.solid.bounding_box()

    @property
    def x_min(self) -> float:
        return self.bound_box.min.X

    @property
    def x_mid(self):
        return self.bound_box.center().X

    @property
    def x_max(self) -> float:
        return self.bound_box.max.X

    @property
    def x_size(self) -> float:
        return self.bound_box.size.X

    @property
    def y_min(self) -> float:
        return self.bound_box.min.Y

    @property
    def y_mid(self):
        return self.bound_box.center().Y

    @property
    def y_max(self):
        return self.bound_box.max.Y

    @property
    def y_size(self) -> float:
        return self.bound_box.size.Y

    @property
    def z_min(self) -> float:
        return self.bound_box.min.Z

    @property
    def z_mid(self):
        return self.bound_box.center().Z

    @property
    def z_max(self):
        return self.bound_box.max.Z

    @property
    def z_size(self) -> float:
        return self.bound_box.size.Z

    def create_positional_filter_axis(self, axis: Axis, inclusive: tuple[bool, bool] = None) -> 'PositionalFilter':
        return PositionalFilter(axis, self.get_from(axis), self.get_to(axis), (True, True) if inclusive is None else inclusive)

    def create_positional_filters_plane(self, plane: Plane, inclusive: tuple[bool, bool] = None) -> Iterable['PositionalFilter']:
        result = []
        if plane in [Plane.XZ, Plane.ZX, Plane.XY, Plane.YX]:
            result.append(self.create_positional_filter_axis(Axis.X, inclusive))
        if plane in [Plane.YX, Plane.YZ, Plane.XY, Plane.ZY]:
            result.append(self.create_positional_filter_axis(Axis.Y, inclusive))
        if plane in [Plane.ZX, Plane.ZY, Plane.XZ, Plane.YZ]:
            result.append(self.create_positional_filter_axis(Axis.Z, inclusive))
        return result

    def get_size(self, axis: Axis):
        match axis:
            case Axis.X:
                return self.x_size
            case Axis.Y:
                return self.y_size
            case Axis.Z:
                return self.z_size
        raise RuntimeError(f"Invalid axis: {axis}")

    def move_vector(self, vector: Vector):
        return self.move(vector.X, vector.Y, vector.Z)

    def move(self, x: float, y: float = 0, z: float = 0) -> 'SmartSolid':
        self.solid.move(Location(Vector(x, y, z)))
        return self

    def move_x(self, x: float) -> 'SmartSolid':
        self.solid.move(Location(Vector(x, 0, 0)))
        return self

    def move_y(self, y: float) -> 'SmartSolid':
        self.solid.move(Location(Vector(0, y, 0)))
        return self

    def move_z(self, z: float) -> 'SmartSolid':
        self.solid.move(Location(Vector(0, 0, z)))
        return self

    def get_from(self, axis: Axis) -> float:
        return self.get_bounds(axis)[0]

    def get_to(self, axis: Axis) -> float:
        return self.get_bounds(axis)[1]

    def orient(self, rotations: VectorLike) -> 'SmartSolid':
        self.solid.orientation = rotations
        return self

    def get_side_length(self, direction: Direction):
        return self.y_size if direction.horizontal else self.x_size

    def get_other_side_length(self, direction: Direction):
        return self.x_size if direction.horizontal else self.y_size

    def get_bounds(self, axis: Axis) -> tuple[float, float]:
        match axis:
            case Axis.X:
                return self.bound_box.min.X, self.bound_box.max.X
            case Axis.Y:
                return self.bound_box.min.Y, self.bound_box.max.Y
            case Axis.Z:
                return self.bound_box.min.Z, self.bound_box.max.Z
        raise RuntimeError(f"Invalid axis: {axis}")

    def cut(self, element) -> 'SmartSolid':
        self.solid -= get_solid(element)
        return self

    def fuse(self, *args) -> 'SmartSolid':
        self.solid = fuse(self.solid, *args)
        return self

    def align_axis(self, solid: 'SmartSolid | None', axis: Axis, alignment: Alignment = Alignment.C, shift: float = 0) -> 'SmartSolid':
        distance = calculate_position(solid.get_from(axis) if solid else 0, solid.get_to(axis) if solid else 0, self.get_size(axis), alignment) + shift - self.get_from(axis)
        return self.move_vector(axis.direction * distance)

    def align_x(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift: float = 0) -> 'SmartSolid':
        return self.align_axis(solid, Axis.X, alignment, shift)

    def align_y(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift: float = 0) -> 'SmartSolid':
        return self.align_axis(solid, Axis.Y, alignment, shift)

    def align_z(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift: float = 0) -> 'SmartSolid':
        return self.align_axis(solid, Axis.Z, alignment, shift)

    def align_xy(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift_x: float = 0, shift_y: float = 0) -> 'SmartSolid':
        return self.align_x(solid, alignment, shift_x).align_y(solid, alignment, shift_y)

    def align_xz(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift_x: float = 0, shift_z: float = 0) -> 'SmartSolid':
        return self.align_x(solid, alignment, shift_x).align_z(solid, alignment, shift_z)

    def align_yz(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift_y: float = 0, shift_z: float = 0) -> 'SmartSolid':
        return self.align_y(solid, alignment, shift_y).align_z(solid, alignment, shift_z)

    def align(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift_x: float = 0, shift_y: float = 0, shift_z: float = 0) -> 'SmartSolid':
        return self.align_x(solid, alignment, shift_x).align_y(solid, alignment, shift_y).align_z(solid, alignment, shift_z)

    def _fillet(self, axis_orientational: Axis, radius: float, axis_positional: Axis = None, minimum: float = None, maximum: float = None, inclusive: tuple[bool, bool] | None = None) -> 'SmartSolid':
        edges = self.solid.edges().filter_by(axis_orientational)
        edges = self._filter_positional(edges, PositionalFilter(axis_positional, minimum, maximum, inclusive))
        self.solid = fillet(edges, radius)
        return self

    def fillet_positional(self, axis_orientational: Axis, radius: float, *position_filters: PositionalFilter) -> 'SmartSolid':
        edges = self.solid.edges().filter_by(axis_orientational)
        for position_filter in position_filters:
            edges = self._filter_positional(edges, position_filter)
        print(f"Edges filleted: {len(edges)}")
        self.solid = fillet(edges, radius)
        return self

    def _filter_positional(self, edges: ShapeList[Edge], positional_filter: PositionalFilter) -> ShapeList[Edge]:
        if positional_filter.axis is None:
            return edges

        if positional_filter.minimum is None:
            actual_min = self.get_from(positional_filter.axis)
            actual_max = self.get_to(positional_filter.axis)
            actual_inclusive = (False, False) if positional_filter.inclusive is None else positional_filter.inclusive
        else:
            actual_min = positional_filter.minimum
            actual_max = actual_min if positional_filter.maximum is None else positional_filter.maximum
            actual_inclusive = (True, True) if positional_filter.inclusive is None else positional_filter.inclusive

        return edges.filter_by_position(positional_filter.axis, actual_min, actual_max, actual_inclusive)

    def fillet_x(self, radius: float, axis: Axis = None, minimum: float = None, maximum: float = None, inclusive: tuple[bool, bool] = (True, True)) -> 'SmartSolid':
        return self._fillet(Axis.X, radius, axis, minimum, maximum, inclusive)

    def fillet_y(self, radius: float, axis: Axis = None, minimum: float = None, maximum: float = None, inclusive: tuple[bool, bool] = (True, True)) -> 'SmartSolid':
        return self._fillet(Axis.Y, radius, axis, minimum, maximum, inclusive)

    def fillet_z(self, radius: float, axis: Axis = None, minimum: float = None, maximum: float = None, inclusive: tuple[bool, bool] = (True, True)) -> 'SmartSolid':
        return self._fillet(Axis.Z, radius, axis, minimum, maximum, inclusive)

    def fillet_xy(self, radius_x: float, radius_y: float = None) -> 'SmartSolid':
        return self.fillet_x(radius_x).fillet_y(radius_y or radius_x)

    def fillet_xz(self, radius_x: float, radius_z: float = None) -> 'SmartSolid':
        return self.fillet_x(radius_x).fillet_z(radius_z or radius_x)

    def fillet_yz(self, radius_y: float, radius_z: float = None) -> 'SmartSolid':
        return self.fillet_y(radius_y).fillet_z(radius_z or radius_y)

    def fillet(self, radius_x: float, radius_y: float = None, radius_z: float = None) -> 'SmartSolid':
        return self.fillet_x(radius_x).fillet_y(radius_y or radius_x).fillet_z(radius_z or radius_y or radius_x)

    def fillet_edges(self, filter_by: ShapePredicate | Axis | Plane | GeomType | property, radius: float, reverse: bool = False) -> 'SmartSolid':
        edges = self.solid.edges().filter_by(filter_by, reverse)
        self.solid = fillet(edges, radius)
        return self

    def intersect(self, shape) -> 'SmartSolid':
        self.solid = self.solid.intersect(get_solid(shape))
        return self

    def add_notch(self, direction: Direction, depth: float, length: float):
        notch_height = depth / length * self.get_side_length(direction)

        pencil = Pencil().up(notch_height).left(self.get_side_length(direction))
        notch = SmartSolid(pencil.extrude(self.get_side_length(direction)))
        notch.orient((90, 90 + direction.value, 0))
        notch.align_z(self, Alignment.LR, -depth).align_axis(self, direction.axis, direction.alignment_closer).align_axis(self, direction.orthogonal_axis)

        extended_shape = self.scaled(1, 1, depth / self.z_size)
        extended_shape.align_xy(self).align_z(self, Alignment.LL)

        self.fuse(notch.intersect(extended_shape))

    def copy(self):
        return SmartSolid(copy(self.solid))

    def _pad_solid(self, pad_x: float, pad_y: float, pad_z: float):
        factor_x = 1 + pad_x / self.x_size
        factor_y = 1 + (pad_x if pad_y is None else pad_y) / self.y_size
        factor_z = 1 + ((pad_x if pad_y is None else pad_y) if pad_z is None else pad_z) / self.z_size

        return self._scale_solid(factor_x, factor_y, factor_z)

    def _scale_solid(self, factor_x: float, factor_y: float, factor_z: float):
        return scale(self.solid, (factor_x, factor_y or factor_x, factor_z or factor_y or factor_x))

    def pad(self, pad_x: float = 0, pad_y: float = None, pad_z: float = None):
        self.solid = self._pad_solid(pad_x, pad_y, pad_z)
        return self

    def padded(self, pad_x: float = 0, pad_y: float = None, pad_z: float = None):
        return SmartSolid(self._pad_solid(pad_x, pad_y, pad_z))

    def scale(self, factor_x: float = 1, factor_y: float = None, factor_z: float = None):
        self.solid = self._scale_solid(factor_x, factor_y, factor_z)
        return self

    def scaled(self, factor_x: float = 1, factor_y: float = None, factor_z: float = None):
        return SmartSolid(self._scale_solid(factor_x, factor_y, factor_z))

    def mirror(self, about: Plane = Plane.XZ) -> 'SmartSolid':
        self.solid = mirror(self.solid, about)
        return self

    def mirrored(self, about: Plane = Plane.XZ) -> 'SmartSolid':
        return SmartSolid(mirror(self.solid, about))
