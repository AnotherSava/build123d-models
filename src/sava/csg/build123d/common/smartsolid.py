from build123d import Vector, fillet, Axis, Location, ShapeList, Edge, Shape, ShapePredicate, Plane, GeomType

from sava.csg.build123d.common.geometry import Alignment, shift_vector, Direction


def get_solid(element):
    return element.solid if isinstance(element, SmartSolid) else element


class SmartSolid:
    def __init__(self, length: float, width: float, height: float):
        self.length = length
        self.width = width
        self.height = height

        self.x = self.y = self.z = 0

        self.solid = None

    @classmethod
    def create(cls, shape: Shape):
        bounding_box = shape.bounding_box()
        solid = SmartSolid(bounding_box.size.X, bounding_box.size.Y, bounding_box.size.Z)
        solid.solid = shape
        solid.x = bounding_box.min.X
        solid.y = bounding_box.min.Y
        solid.z = bounding_box.min.Z

        return solid

    @property
    def x_to(self):
        return self.x + self.length

    @property
    def y_to(self):
        return self.y + self.width

    @property
    def z_to(self):
        return self.z + self.height

    @property
    def x_mid(self):
        return self.x + self.length / 2

    @property
    def y_mid(self):
        return self.y + self.width / 2

    @property
    def z_mid(self):
        return self.z + self.height / 2

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
        self.x += x
        self.y += y
        self.z += z

        if self.solid:
            self.solid.move(Location(Vector(x, y, z)))

        return self

    def get_from(self, axis: Axis) -> float:
        return self.get_bounds(axis)[0]

    def get_to(self, axis: Axis) -> float:
        return self.get_bounds(axis)[1]

    def get_side_length(self, direction: Direction):
        return self.width if direction.horizontal else self.length

    def get_other_side_length(self, direction: Direction):
        return self.length if direction.horizontal else self.width

    def get_size(self, axis: Axis):
        match axis:
            case Axis.X:
                return self.length
            case Axis.Y:
                return self.width
            case Axis.Z:
                return self.height
        raise RuntimeError(f"Invalid axis: {axis}")

    def get_bounds(self, axis: Axis) -> tuple[float, float]:
        match axis:
            case Axis.X:
                return self.x, self.x_to
            case Axis.Y:
                return self.y, self.y_to
            case Axis.Z:
                return self.z, self.z_to
        raise RuntimeError(f"Invalid axis: {axis}")

    def top_half(self) -> 'SmartSolid':
        return SmartSolid(self.length, self.width, self.height / 2).move(self.x, self.y, self.z_mid)

    def bottom_half(self) -> 'SmartSolid':
        return SmartSolid(self.length, self.width, self.height / 2).move(self.x, self.y, self.z)

    def cut(self, element) -> 'SmartSolid':
        self.solid -= get_solid(element)
        return self

    def fuse(self, element) -> 'SmartSolid':
        self.solid += get_solid(element)
        return self

    def align_x(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift: float = 0) -> 'SmartSolid':
        position = SmartSolid._calculate_position(solid.x, solid.x_to, self.length, alignment) + shift
        return self.move(position - self.x, 0, 0)

    def align_y(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift: float = 0) -> 'SmartSolid':
        position = SmartSolid._calculate_position(solid.y, solid.y_to, self.width, alignment) + shift
        return self.move(0, position - self.y, 0)

    def align_z(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift: float = 0) -> 'SmartSolid':
        position = SmartSolid._calculate_position(solid.z, solid.z_to, self.height, alignment) + shift
        return self.move(0, 0, position - self.z)

    def align_xy(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift_x: float = 0, shift_y: float = 0) -> 'SmartSolid':
        return self.align_x(solid, alignment, shift_x).align_y(solid, alignment, shift_y)

    def align_xz(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift_x: float = 0, shift_z: float = 0) -> 'SmartSolid':
        return self.align_x(solid, alignment, shift_x).align_z(solid, alignment, shift_z)

    def align_yz(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift_y: float = 0, shift_z: float = 0) -> 'SmartSolid':
        return self.align_y(solid, alignment, shift_y).align_z(solid, alignment, shift_z)

    def align(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift_x: float = 0, shift_y: float = 0, shift_z: float = 0) -> 'SmartSolid':
        return self.align_x(solid, alignment, shift_x).align_y(solid, alignment, shift_y).align_z(solid, alignment, shift_z)

    def align_axis(self, solid: 'SmartSolid', axis: Axis, alignment: Alignment = Alignment.C, shift: float = 0) -> 'SmartSolid':
        distance = SmartSolid._calculate_position(solid.get_from(axis), solid.get_to(axis), self.get_size(axis), alignment) + shift - self.get_from(axis)
        return self.move_vector(axis.direction * distance)

    def filter_edges_within(self, solid: 'SmartSolid') -> ShapeList[Edge]:
        return self.solid.edges().filter_by_position(Axis.X, solid.x, solid.x_to).filter_by_position(Axis.Y, solid.y, solid.y_to).filter_by_position(Axis.Z, solid.z, solid.z_to)

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
