from build123d import Vector, fillet, Axis, Location, ShapeList, Edge

from sava.csg.build123d.common.geometry import Alignment, shift_vector


class SmartSolid:
    def __init__(self, length: float, width: float, height: float):
        self.length = length
        self.width = width
        self.height = height

        self.x = self.y = self.z = 0

        self.solid = None

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
    def orientation(self):
        return self.solid.orientation

    def with_orientation(self, orientation) -> 'SmartSolid':
        self.solid.orientation = orientation
        return self

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

    def align_x(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift: float = 0) -> 'SmartSolid':
        position = self._calculate_position(solid.x, solid.x_to, self.length, alignment) + shift
        return self.move(position - self.x, 0, 0)

    def align_y(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift: float = 0) -> 'SmartSolid':
        position = self._calculate_position(solid.y, solid.y_to, self.width, alignment) + shift
        return self.move(0, position - self.y, 0)

    def align_z(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift: float = 0) -> 'SmartSolid':
        position = self._calculate_position(solid.z, solid.z_to, self.height, alignment) + shift
        return self.move(0, 0, position - self.z)

    def align_xy(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift_x: float = 0, shift_y: float = 0) -> 'SmartSolid':
        return self.align_x(solid, alignment, shift_x).align_y(solid, alignment, shift_y)

    def align_xz(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift_x: float = 0, shift_z: float = 0) -> 'SmartSolid':
        return self.align_x(solid, alignment, shift_x).align_z(solid, alignment, shift_z)

    def align_yz(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift_y: float = 0, shift_z: float = 0) -> 'SmartSolid':
        return self.align_y(solid, alignment, shift_y).align_z(solid, alignment, shift_z)

    def align(self, solid: 'SmartSolid', alignment: Alignment = Alignment.C, shift_x: float = 0, shift_y: float = 0, shift_z: float = 0) -> 'SmartSolid':
        return self.align_x(solid, alignment, shift_x).align_y(solid, alignment, shift_y).align_z(solid, alignment, shift_z)

    def filter_edges_within(self, solid: 'SmartSolid') -> ShapeList[Edge]:
        return self.solid.edges().filter_by_position(Axis.X, solid.x, solid.x_to).filter_by_position(Axis.Y, solid.y, solid.y_to).filter_by_position(Axis.Z, solid.z, solid.z_to)

    def _fillet(self, axis_orientational: Axis, radius: float, axis_positional: Axis = None, minimum: float = None, maximum: float = None, inclusive: tuple[bool, bool] = (False, False)) -> 'SmartSolid':
        edges = self.solid.edges().filter_by(axis_orientational)
        if axis_positional is not None:
            edges = edges.filter_by_position(axis_positional, self.get_from(axis_positional) if minimum is None else minimum, self.get_to(axis_positional) if maximum is None else maximum, inclusive)
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

    def _calculate_position(self, left: float, right: float, self_size: float, alignment: Alignment):
        match alignment:
            case Alignment.LL:
                return left - self_size
            case Alignment.LR:
                return left
            case Alignment.C:
                return (left + right - self_size) / 2
            case Alignment.RL:
                return right - self_size
            case Alignment.RR:
                return right
