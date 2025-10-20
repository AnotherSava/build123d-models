from copy import copy

from build123d import Vector, fillet, Axis, Location, Shape, ShapePredicate, Plane, GeomType, BoundBox, Compound, VectorLike, scale

from sava.csg.build123d.common.geometry import Alignment, shift_vector, Direction
from sava.csg.build123d.common.pencil import Pencil


def get_solid(element):
    return element.solid if isinstance(element, SmartSolid) else element


class SmartSolid:
    def __init__(self, *args):
        if len(args) == 0:
            self.solid = None
        elif len(args) == 1:
            self.solid = get_solid(args[0])
        else:
            self.solid = Compound([get_solid(arg) for arg in args])

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

    def get_size(self, axis: Axis):
        match axis:
            case Axis.X:
                return self.x_size
            case Axis.Y:
                return self.y_size
            case Axis.Z:
                return self.z_size
        raise RuntimeError(f"Invalid axis: {axis}")

    @property
    def parent(self):
        return self.solid.parent

    @parent.setter
    def parent(self, parent: Shape):
        self.solid.parent = parent

    def move_in_direction(self, *args: float):
        return self.move_vector(shift_vector(Vector(), *args))

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

    def fuse(self, element) -> 'SmartSolid':
        if self.solid:
            self.solid = self.solid.fuse(get_solid(element))
        else:
            self.solid = get_solid(element)
        return self

    def align_axis(self, solid: 'SmartSolid | None', axis: Axis, alignment: Alignment = Alignment.C, shift: float = 0) -> 'SmartSolid':
        distance = SmartSolid._calculate_position(solid.get_from(axis) if solid else 0, solid.get_to(axis) if solid else 0, self.get_size(axis), alignment) + shift - self.get_from(axis)
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
        if axis_positional is not None:
            if minimum is None:
                actual_min = self.get_from(axis_positional)
                actual_max = self.get_to(axis_positional)
                actual_inclusive = (False, False) if inclusive is None else inclusive
            else:
                actual_min = minimum
                actual_max = actual_min if maximum is None else maximum
                actual_inclusive = (True, True) if inclusive is None else inclusive

            edges = edges.filter_by_position(axis_positional, actual_min, actual_max, actual_inclusive)

        self.solid = fillet(edges, radius)
        return self

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

    def addNotch(self, direction: Direction, depth: float, length: float):
        notch_height = depth / length * self.get_side_length(direction)

        pencil = Pencil().up(notch_height).left(self.get_side_length(direction))
        notch = SmartSolid(pencil.extrude(self.get_side_length(direction)))
        notch.orient((90, 90 + direction.value, 0))
        notch.align_z(self, Alignment.LR, -depth).align_axis(self, direction.axis, direction.alignment_closer).align_axis(self, direction.orthogonal_axis)

        extended_shape = SmartSolid(scale(self.solid, (1, 1, depth / self.z_size)))
        extended_shape.align_xy(self).align_z(self, Alignment.LL)

        self.fuse(notch.intersect(extended_shape))

    def copy(self):
        return SmartSolid(copy(self.solid))

    @classmethod
    def _calculate_position(cls, left: float, right: float, self_size: float, alignment: Alignment):
        match alignment:
            case Alignment.LL:
                return left - self_size
            case Alignment.L:
                return left - self_size / 2
            case Alignment.LR:
                return left
            case Alignment.C:
                return (left + right - self_size) / 2
            case Alignment.RL:
                return right - self_size
            case Alignment.R:
                return right - self_size / 2
            case Alignment.RR:
                return right
        raise RuntimeError(f"Invalid alignment: {alignment.name} = {alignment.value}")
