from copy import copy
from dataclasses import dataclass
from typing import Iterable

from build123d import Vector, fillet, Axis, Location, ShapePredicate, Plane, GeomType, BoundBox, Compound, VectorLike, scale, mirror, Edge, ShapeList, Shape, Color, Solid

from sava.common.common import flatten
from sava.csg.build123d.common.geometry import Alignment, Direction, calculate_position, rotate_orientation


@dataclass
class PositionalFilter:
    axis: Axis
    minimum: float = None
    maximum: float = None
    inclusive: tuple[bool, bool] = None

def get_solid(element):
    return element.solid if isinstance(element, SmartSolid) else element

def fuse_two(shape1: Shape | None, shape2: Shape | None):
    if shape1 is None:
        return shape2
    if shape2 is None:
        return shape1
    return shape2 + shape1 if isinstance(shape1, ShapeList) else shape1 + shape2

def wrap(element):
    return Compound(element) if isinstance(element, ShapeList) else element

def fuse(*args):
    result = None

    for arg in flatten(args):
        result = fuse_two(result, get_solid(arg))

    return result

def list_shapes(*args) -> 'SmartSolid':
    result = SmartSolid()
    result.solid = ShapeList(get_solid(arg) for arg in args)
    return result

class SmartSolid:
    def __init__(self, *args, label: str = None):
        """Create a SmartSolid from one or more solid objects.

        Args:
            *args: Solid objects to fuse together
            label: Optional label for the solid (keyword-only argument)
        """
        self.label = label
        self.solid = fuse(*args) if len(args) > 0 else None
        self.assert_valid()

    @property
    def bound_box(self) -> BoundBox:
        return self.wrap_solid().bounding_box()

    @property
    def shapes(self) -> ShapeList:
        return self.solid if isinstance(self.solid, ShapeList) else [self.solid]

    def get_bound_box(self, plane: Plane = Plane.XY) -> BoundBox:
        solid = self.wrap_solid()
        if plane == Plane.XY:
            return solid.bounding_box()
        
        # Transform solid to the plane's coordinate system
        transformed = solid.moved(plane.location.inverse())
        return transformed.bounding_box()

    def create_bound_box(self, plane: Plane = Plane.XY) -> 'SmartSolid':
        bound_box = self.get_bound_box(plane)
        box_solid = Solid.make_box(bound_box.size.X, bound_box.size.Y, bound_box.size.Z, plane)
        return SmartSolid(box_solid).align(self, plane=plane)

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

    def assert_valid(self):
        assert self.solid is None or self.wrap_solid().is_valid, "Shape is invalid"

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

    def color(self, color: str):
        self.solid.color = Color(color) if color else None
        self.solid.label = color
        return self

    def same_color(self, element):
        return self.color(get_solid(element).label)

    def move_vector(self, vector: Vector):
        return self.move(vector.X, vector.Y, vector.Z)

    def move(self, x: float, y: float = 0, z: float = 0) -> 'SmartSolid':
        # Move each shape separately if it's a ShapeList, otherwise move the single shape
        location = Location(Vector(x, y, z))
        
        if isinstance(self.solid, ShapeList):
            # Move each shape in the list separately
            moved_shapes = []
            for shape in self.solid:
                moved_shapes.append(shape.move(location))
            self.solid = ShapeList(moved_shapes)
        else:
            # Move single shape
            self.solid = self.solid.move(location)
        
        return self

    def move_x(self, x: float) -> 'SmartSolid':
        return self.move(x, 0, 0)

    def move_y(self, y: float) -> 'SmartSolid':
        return self.move(0, y, 0)

    def move_z(self, z: float) -> 'SmartSolid':
        return self.move(0, 0, z)

    def get_from(self, axis: Axis) -> float:
        return self.get_bounds_along_axis(axis)[0]

    def get_to(self, axis: Axis) -> float:
        return self.get_bounds_along_axis(axis)[1]

    def orient(self, rotations: VectorLike) -> 'SmartSolid':
        self.solid.orientation = rotations
        return self

    def rotate_with_axis(self, axis: Axis, angle: float) -> 'SmartSolid':
        self.solid = self.solid.rotate(axis, angle)
        return self

    def rotated_with_axis(self, axis: Axis, angle: float) -> 'SmartSolid':
        return self.copy().rotate_with_axis(axis, angle)

    # Orientation in build123d works a bit weird:
    # (a, b, c) input does rotate "a" degrees around axis X, then "b" degrees around axis Y, then "c" degrees around axis Z.
    # But those axes are not in the original coordinate system (plane), but in a coordinate system attached to the object itself.
    # Let's assume that the object original plane matches a standard one, and input param is (90, 90, 0)
    # First, it will rotate 90 degrees around X axis - as expected. After that it will rotate 90 degree around Y axis.
    # But it will not be the Y axis in the global coordinate system - it will be Y axis of the object, which after the first rotation turned to match Z axis in the global coordinate system.
    # Also, orientation is not incremental, it just sets to specified value each time.
    # This method helps to navigate those complexities with the following set of rules:
    #  - while following the same order of rotations, axis are not attached to the object, but fixed to a plane specified as a parameter
    #  - rotations are incremental, and (0,0,0) param will not change orientation no matter what
    def rotate(self, rotations: VectorLike, plane: Plane = Plane.XY) -> 'SmartSolid':
        self.orient(rotate_orientation(self.solid.orientation, rotations, plane))
        return self

    def rotated(self, rotations: VectorLike, plane: Plane = Plane.XY) -> 'SmartSolid':
        return self.copy().rotate(rotations, plane)

    def oriented(self, rotations: VectorLike) -> 'SmartSolid':
        return self.copy().orient(rotations)

    def get_side_length(self, direction: Direction):
        return self.y_size if direction.horizontal else self.x_size

    def get_other_side_length(self, direction: Direction):
        return self.x_size if direction.horizontal else self.y_size

    def get_bounds_along_axis(self, axis: Axis) -> tuple[float, float]:
        """Get min and max coordinates of the solid along the specified axis direction.
        
        This method creates a plane where the axis direction becomes the Z-axis,
        then uses get_bound_box() to get bounds in that coordinate system.
        
        Args:
            axis: Axis defining the direction to measure bounds along
            
        Returns:
            Tuple of (min_coord, max_coord) along the axis direction
        """
        if self.solid is None:
            raise RuntimeError("Cannot get bounds of None solid")
            
        # Create a plane where the axis direction becomes the Z-axis
        axis_direction = axis.direction.normalized()
        
        # Create plane with axis origin and axis direction as Z-axis
        plane = Plane(axis.position, z_dir=axis_direction)
        
        # Get bounding box in the plane's coordinate system
        bound_box = self.get_bound_box(plane)
        
        # Return Z bounds since the axis direction is aligned with Z in this plane
        return bound_box.min.Z, bound_box.max.Z

    def cut(self, *args) -> 'SmartSolid':
        self.solid = wrap(self.solid) - fuse(args)
        self.assert_valid()
        return self

    def cutted(self, *args) -> 'SmartSolid':
        return self.copy().cut(*args)

    def fuse(self, *args) -> 'SmartSolid':
        self.solid = fuse(self.solid, *args)
        self.assert_valid()
        return self

    def fused(self, *args) -> 'SmartSolid':
        return self.copy().fuse(*args)

    def is_simple(self):
        return not isinstance(self.solid, ShapeList)

    def colocate(self, solid: 'SmartSolid') -> 'SmartSolid':
        assert solid.is_simple()

        for shape in self.shapes:
            shape.location = solid.solid.location

        return self

    def align_axis(self, solid: 'SmartSolid | None', axis: Axis, alignment: Alignment = Alignment.C, shift: float = 0) -> 'SmartSolid':
        self_from, self_to = self.get_bounds_along_axis(axis)
        solid_from, solid_to = (0, 0) if solid is None else solid.get_bounds_along_axis(axis)

        distance = calculate_position(solid_from, solid_to, self_to - self_from, alignment) + shift - self_from

        return self.move_vector(axis.direction * distance)

    def align_x(self, solid: 'SmartSolid' = None, alignment: Alignment = Alignment.C, shift: float = 0, plane: Plane = Plane.XY) -> 'SmartSolid':
        return self.align_axis(solid, Axis(plane.location.position, plane.x_dir), alignment, shift)

    def align_y(self, solid: 'SmartSolid' = None, alignment: Alignment = Alignment.C, shift: float = 0, plane: Plane = Plane.XY) -> 'SmartSolid':
        return self.align_axis(solid, Axis(plane.location.position, plane.y_dir), alignment, shift)

    def align_z(self, solid: 'SmartSolid' = None, alignment: Alignment = Alignment.C, shift: float = 0, plane: Plane = Plane.XY) -> 'SmartSolid':
        return self.align_axis(solid, Axis(plane.location.position, plane.z_dir), alignment, shift)

    def align_zxy(self, solid: 'SmartSolid' = None, alignment_z: Alignment = Alignment.LR, shift_z: float = 0, alignment_x: Alignment = Alignment.C, shift_x: float = 0, alignment_y: Alignment = Alignment.C, shift_y: float = 0, plane: Plane = Plane.XY) -> 'SmartSolid':
        return self.align_z(solid, alignment_z, shift_z, plane).align_x(solid, alignment_x, shift_x, plane).align_y(solid, alignment_y, shift_y, plane)

    def align_xy(self, solid: 'SmartSolid' = None, alignment: Alignment = Alignment.C, shift_x: float = 0, shift_y: float = 0, plane: Plane = Plane.XY) -> 'SmartSolid':
        return self.align_x(solid, alignment, shift_x, plane).align_y(solid, alignment, shift_y, plane)

    def align_xz(self, solid: 'SmartSolid' = None, alignment: Alignment = Alignment.C, shift_x: float = 0, shift_z: float = 0, plane: Plane = Plane.XY) -> 'SmartSolid':
        return self.align_x(solid, alignment, shift_x, plane).align_z(solid, alignment, shift_z, plane)

    def align_yz(self, solid: 'SmartSolid' = None, alignment: Alignment = Alignment.C, shift_y: float = 0, shift_z: float = 0, plane: Plane = Plane.XY) -> 'SmartSolid':
        return self.align_y(solid, alignment, shift_y, plane).align_z(solid, alignment, shift_z, plane)

    def align(self, solid: 'SmartSolid' = None, alignment: Alignment = Alignment.C, shift_x: float = 0, shift_y: float = 0, shift_z: float = 0, plane: Plane = Plane.XY) -> 'SmartSolid':
        return self.align_x(solid, alignment, shift_x, plane).align_y(solid, alignment, shift_y, plane).align_z(solid, alignment, shift_z, plane)

    def _fillet(self, axis_orientational: Axis, radius: float, axis_positional: Axis = None, minimum: float = None, maximum: float = None, inclusive: tuple[bool, bool] | None = None) -> 'SmartSolid':
        edges = self.solid.edges().filter_by(axis_orientational)
        edges = self._filter_positional(edges, PositionalFilter(axis_positional, minimum, maximum, inclusive))
        self.solid = fillet(edges, radius)
        return self

    def fillet_positional(self, radius: float, axis_orientational: Axis | None, *position_filters: PositionalFilter) -> 'SmartSolid':
        edges = self.solid.edges()
        if axis_orientational is not None:
            edges = edges.filter_by(axis_orientational)
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

    def intersect(self, *args) -> 'SmartSolid':
        self.solid = self.solid & fuse(args)
        self.assert_valid()
        return self

    def intersected(self, *args) -> 'SmartSolid':
        return self.copy().intersect(args)

    def add_notch(self, direction: Direction, depth: float, length: float):
        raise NotImplementedError("Remove dependency on pencil")
        # notch_height = depth / length * self.get_side_length(direction)
        #
        # pencil = Pencil().up(notch_height).left(self.get_side_length(direction))
        # notch = SmartSolid(pencil.extrude(self.get_side_length(direction)))
        # notch.orient((90, 90 + direction.value, 0))
        # notch.align_z(self, Alignment.LR, -depth).align_axis(self, direction.axis, direction.alignment_closer).align_axis(self, direction.orthogonal_axis)
        #
        # extended_shape = self.scaled(1, 1, depth / self.z_size)
        # extended_shape.align_xy(self).align_z(self, Alignment.LL)
        #
        # self.fuse(notch.intersect(extended_shape))

    def copy(self):
        return SmartSolid(copy(self.solid), label=self.label)

    def _scale_solid(self, factor_x: float, factor_y: float, factor_z: float):
        return scale(self.solid, (factor_x, factor_y or factor_x, factor_z or factor_y or factor_x))

    def pad(self, pad_x: float = 0, pad_y: float = None, pad_z: float = None):
        pad_y = pad_x if pad_y is None else pad_y
        pad_z = pad_x if pad_z is None else pad_z

        self.solid = self._scale_solid(1 + pad_x / self.x_size, 1 + pad_y / self.y_size, 1 + pad_z / self.z_size)
        return self

    def padded(self, pad_x: float = 0, pad_y: float = None, pad_z: float = None):
        return self.copy().pad(pad_x, pad_y, pad_z)

    def scale(self, factor_x: float = 1, factor_y: float = None, factor_z: float = None):
        self.solid = self._scale_solid(factor_x, factor_y, factor_z)
        return self

    def scaled(self, factor_x: float = 1, factor_y: float = None, factor_z: float = None):
        return self.copy().scale(factor_x, factor_y, factor_z)

    def mirror(self, about: Plane = Plane.XZ) -> 'SmartSolid':
        self.solid = mirror(self.solid, about)
        return self

    def mirrored(self, about: Plane = Plane.XZ) -> 'SmartSolid':
        return self.copy().mirror(about)

    def molded(self, padding: float = 2) -> 'SmartSolid':
        outer = self.padded(padding)
        outer.align_zxy(self, Alignment.RL)
        return outer.cut(self)

    def wrap_solid(self):
        return wrap(self.solid)
