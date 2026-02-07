from copy import copy
from typing import Iterable, TYPE_CHECKING

from build123d import Vector, fillet, Axis, Location, ShapePredicate, Plane, GeomType, BoundBox, Compound, VectorLike, scale, mirror, Edge, ShapeList, Shape, Color, Solid, SkipClean, Rotation, Face

from sava.common.common import flatten
from sava.common.logging import logger
from sava.csg.build123d.common.alignmentbuilder import AlignmentBuilder


from sava.csg.build123d.common.edgefilters import PositionalFilter, SurfaceFilter, AxisFilter, EdgeFilter, FilletDebug, AXIS_X, AXIS_Y, AXIS_Z, filter_edges_by_position, filter_edges_by_axis, filter_edges_by_surface
from sava.csg.build123d.common.geometry import Alignment, Direction, calculate_position, rotate_orientation, to_vector, axis_to_string, multi_rotate_vector, convert_orientation_to_rotations


def get_solid(element):
    if isinstance(element, AlignmentBuilder):
        element = element.done()
    return element.solid if isinstance(element, SmartSolid) else element

if TYPE_CHECKING:
    from sava.csg.build123d.common.smartbox import SmartBox

def fuse_two(shape1: Shape | None, shape2: Shape | None):
    if shape1 is None:
        return shape2
    if shape2 is None:
        return shape1
    result = shape2 + shape1 if isinstance(shape1, ShapeList) else shape1 + shape2
    # Workaround for build123d bug: ShapeUpgrade_UnifySameDomain corrupts geometry
    # when fusing tapered shapes with shared edges. Retry without cleaning if invalid.
    # https://github.com/gumyr/build123d/issues/1215
    if not wrap(result).is_valid:
        with SkipClean():
            result = shape2 + shape1 if isinstance(shape1, ShapeList) else shape1 + shape2
    return result

def wrap(element):
    return Compound(element) if isinstance(element, ShapeList) else element

def fuse(*args):
    result = None

    for arg in flatten(args):
        result = fuse_two(result, get_solid(arg))

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
        self.origin = Vector(0, 0, 0)
        self._orientation = Vector(0, 0, 0)
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

    def create_bound_box(self, plane: Plane = Plane.XY) -> 'SmartBox':
        bound_box = self.get_bound_box(plane)
        from sava.csg.build123d.common.smartbox import SmartBox
        return SmartBox(bound_box.size.X, bound_box.size.Y, bound_box.size.Z, plane=plane).align_old(self, plane=plane)

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

    def move_vector(self, vector: Vector, plane: Plane = None) -> 'SmartSolid':
        return self.move(vector.X, vector.Y, vector.Z, plane=plane)

    def moved_vector(self, vector: Vector, plane: Plane = None) -> 'SmartSolid':
        return self.copy().move_vector(vector, plane=plane)

    def move(self, x: float, y: float = 0, z: float = 0, plane: Plane = None) -> 'SmartSolid':
        """Move the solid by the specified offsets.

        Args:
            x: Offset along x-axis (or plane's x_dir if plane is specified)
            y: Offset along y-axis (or plane's y_dir if plane is specified)
            z: Offset along z-axis (or plane's z_dir if plane is specified)
            plane: Optional plane defining the coordinate system for the offsets.
                   If None, uses global XYZ coordinates.

        Returns:
            self for chaining
        """
        # Convert plane-local offsets to global coordinates if plane is specified
        if plane is not None:
            global_offset = plane.x_dir * x + plane.y_dir * y + plane.z_dir * z
        else:
            global_offset = Vector(x, y, z)

        # Move each shape separately if it's a ShapeList, otherwise move the single shape
        location = Location(global_offset)

        if isinstance(self.solid, ShapeList):
            # Move each shape in the list separately
            moved_shapes = []
            for shape in self.solid:
                moved_shapes.append(shape.move(location))
            self.solid = ShapeList(moved_shapes)
        else:
            # Move single shape
            self.solid = self.solid.move(location)

        self.origin += global_offset
        return self

    def moved(self, x: float, y: float = 0, z: float = 0, plane: Plane = None) -> 'SmartSolid':
        return self.copy().move(x, y, z, plane=plane)

    def move_x(self, x: float, plane: Plane = None) -> 'SmartSolid':
        return self.move(x, 0, 0, plane=plane)

    def move_y(self, y: float, plane: Plane = None) -> 'SmartSolid':
        return self.move(0, y, 0, plane=plane)

    def move_z(self, z: float, plane: Plane = None) -> 'SmartSolid':
        return self.move(0, 0, z, plane=plane)

    def get_from(self, axis: Axis) -> float:
        return self.get_bounds_along_axis(axis)[0]

    def get_to(self, axis: Axis) -> float:
        return self.get_bounds_along_axis(axis)[1]

    def orient(self, rotations: VectorLike) -> 'SmartSolid':
        self.solid = self.wrap_solid()
        rotations = to_vector(rotations)
        current_orient = self._orientation

        # Undo current orientation's effect on origin, then apply new orientation
        if current_orient != Vector(0, 0, 0):
            old_fixed = convert_orientation_to_rotations(tuple(current_orient))
            # Apply inverse: negate and reverse order
            self.origin = multi_rotate_vector(self.origin, Plane.XY, (0, 0, -old_fixed.Z))
            self.origin = multi_rotate_vector(self.origin, Plane.XY, (0, -old_fixed.Y, 0))
            self.origin = multi_rotate_vector(self.origin, Plane.XY, (-old_fixed.X, 0, 0))

        if rotations != Vector(0, 0, 0):
            new_fixed = convert_orientation_to_rotations(tuple(rotations))
            # Apply forward
            self.origin = multi_rotate_vector(self.origin, Plane.XY, (new_fixed.X, 0, 0))
            self.origin = multi_rotate_vector(self.origin, Plane.XY, (0, new_fixed.Y, 0))
            self.origin = multi_rotate_vector(self.origin, Plane.XY, (0, 0, new_fixed.Z))

        self.solid.orientation = rotations
        self._orientation = rotations
        return self

    def oriented(self, rotations: VectorLike, label: str = None) -> 'SmartSolid':
        return self.copy(label).orient(rotations)

    def rotate(self, axis: Axis, angle: float) -> 'SmartSolid':
        self.solid = self.wrap_solid()
        # Use moved() with Rotation instead of rotate() to avoid meshing bugs at exact 90° angles
        if axis == Axis.X:
            rotation = Rotation(angle, 0, 0)
            rotations = (angle, 0, 0)
        elif axis == Axis.Y:
            rotation = Rotation(0, angle, 0)
            rotations = (0, angle, 0)
        elif axis == Axis.Z:
            rotation = Rotation(0, 0, angle)
            rotations = (0, 0, angle)
        else:
            # For custom axes, fall back to the original rotate method
            self.solid = self.solid.rotate(axis, angle)
            self.origin = self.origin.rotate(axis, angle)
            return self
        self.solid = self.solid.moved(Location(rotation))
        self.origin = self.origin.rotate(axis, angle)
        # Update stored orientation to track the cumulative effect
        new_orient = rotate_orientation(self._orientation, rotations, Plane.XY)
        self._orientation = new_orient
        return self

    def rotated(self, axis: Axis, angle: float) -> 'SmartSolid':
        return self.copy().rotate(axis, angle)

    def rotate_x(self, angle: float) -> 'SmartSolid':
        return self.rotate(Axis.X, angle)

    def rotate_y(self, angle: float) -> 'SmartSolid':
        return self.rotate(Axis.Y, angle)

    def rotate_z(self, angle: float) -> 'SmartSolid':
        return self.rotate(Axis.Z, angle)

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
    def rotate_multi(self, rotations: VectorLike, plane: Plane = Plane.XY) -> 'SmartSolid':
        self.orient(rotate_orientation(self.solid.orientation, rotations, plane))
        return self

    def rotated_multi(self, rotations: VectorLike, plane: Plane = Plane.XY, label: str = None) -> 'SmartSolid':
        return self.copy(label).rotate_multi(rotations, plane)

    def get_size(self, axis: Axis):
        bounds = self.get_bounds_along_axis(axis)
        return bounds[1] - bounds[0]

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
        original = self.solid
        cutter = fuse(args)
        self.solid = wrap(original) - cutter
        # Workaround for build123d bug: retry without cleaning if invalid
        # https://github.com/gumyr/build123d/issues/1215
        if not self.wrap_solid().is_valid:
            with SkipClean():
                self.solid = wrap(original) - cutter
        self.assert_valid()
        return self

    def cutted(self, *args, label: str = None) -> 'SmartSolid':
        return self.copy(label).cut(*args)

    def fuse(self, *args) -> 'SmartSolid':
        self.solid = fuse(self.solid, *args)
        self.assert_valid()
        return self

    def fused(self, *args, label: str = None) -> 'SmartSolid':
        return self.copy(label).fuse(*args)

    def is_simple(self):
        return not isinstance(self.solid, ShapeList)

    def colocate(self, solid: 'SmartSolid') -> 'SmartSolid':
        assert solid.is_simple()

        self.solid = self.wrap_solid()
        self.solid.location = solid.solid.location

        # Copy origin and orientation from the reference solid
        self.origin = Vector(solid.origin)
        self._orientation = Vector(solid._orientation)

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

    def align_old(self, solid: 'SmartSolid' = None, alignment: Alignment = Alignment.C, shift_x: float = 0, shift_y: float = 0, shift_z: float = 0, plane: Plane = Plane.XY) -> 'SmartSolid':
        return self.align_x(solid, alignment, shift_x, plane).align_y(solid, alignment, shift_y, plane).align_z(solid, alignment, shift_z, plane)

    def align(self, solid: 'SmartSolid' = None, plane: Plane = Plane.XY) -> AlignmentBuilder:
        """Align to reference solid with center alignment on all axes, then allow customization.

        First aligns all three axes (x, y, z) to the reference using Alignment.C (center).
        Returns an AlignmentBuilder for further customization of specific axes.

        Args:
            solid: Reference solid to align to (None = align to origin)
            plane: Coordinate plane for alignment directions

        Returns:
            AlignmentBuilder for chaining .x(), .y(), .z() calls to customize alignment

        Example:
            box.align(ref)  # Centers box on ref (all axes)
            box.align(ref).x(Alignment.LL)  # Centers on ref, then aligns x to left-left
            box.align(ref).x(Alignment.LL).y(10)  # Centers, aligns x, then shifts y by 10
            box.align(ref).then().move(10, 0, 0)  # Centers on ref, then moves
        """
        self.align_old(solid, plane=plane)
        return AlignmentBuilder(self, solid, plane)

    def aligned(self, solid: 'SmartSolid' = None, plane: Plane = Plane.XY) -> AlignmentBuilder:
        return self.copy().align(solid, plane)

    def _fillet(self, axis_orientational: Axis, radius: float, axis_positional: Axis = None, minimum: float = None, maximum: float = None, inclusive: tuple[bool, bool] | None = None, angle_tolerance: float = 1e-5) -> 'SmartSolid':
        edges = filter_edges_by_axis(self.solid.edges(), axis_orientational, angle_tolerance)
        if axis_positional:
            edges = self._filter_positional(edges, PositionalFilter(axis_positional, minimum, maximum, inclusive))
        self.solid = fillet(edges, radius)
        return self

    def fillet_by(self, radius: float, *filters: EdgeFilter, debug: FilletDebug = None) -> 'SmartSolid':
        """Fillet edges matching the given filters.

        Args:
            radius: Fillet radius
            *filters: PositionalFilter, SurfaceFilter, or AxisFilter objects
            debug: Debug mode - ALL shows all edges in red, PARTIAL tests each edge individually

        Returns:
            self for chaining
        """
        edges = self.solid.edges()
        for f in filters:
            if isinstance(f, AxisFilter):
                edges = filter_edges_by_axis(edges, f.axis, f.angle_tolerance)
            elif isinstance(f, PositionalFilter):
                edges = self._filter_positional(edges, f)
            elif isinstance(f, SurfaceFilter):
                edges = filter_edges_by_surface(edges, f)

        if not edges:
            logger.warning("fillet_by: no edges matched the filters")
            return self

        if debug == FilletDebug.ALL:
            from sava.csg.build123d.common.exporter import show_red  # inline to avoid circular import
            show_red(*edges)
        elif debug == FilletDebug.PARTIAL:
            from sava.csg.build123d.common.exporter import show_red, show_green  # inline to avoid circular import
            for edge in edges:
                try:
                    fillet([edge], radius)
                    show_green(edge)
                except Exception:
                    show_red(edge)
        else:
            self.solid = fillet(edges, radius)

        return self

    def _filter_positional(self, edges: ShapeList[Edge], positional_filter: PositionalFilter) -> ShapeList[Edge]:
        if positional_filter.minimum is None:
            actual_min = self.get_from(positional_filter.axis)
            actual_max = self.get_to(positional_filter.axis)
            actual_inclusive = (False, False) if positional_filter.inclusive is None else positional_filter.inclusive
        else:
            actual_min = positional_filter.minimum
            actual_max = actual_min if positional_filter.maximum is None else positional_filter.maximum
            actual_inclusive = (True, True) if positional_filter.inclusive is None or positional_filter.maximum is None else positional_filter.inclusive

        result = filter_edges_by_position(edges, positional_filter.axis, actual_min, actual_max, actual_inclusive)
        logger.debug(f"Fillet positional filter along Axis {axis_to_string(positional_filter.axis)} {'[' if actual_inclusive[0] else '('}{actual_min}, {actual_max}{']' if actual_inclusive[1] else ')'}: {len(edges)} -> {len(result)}")
        return result

    def fillet_x(self, radius: float, axis: Axis = None, minimum: float = None, maximum: float = None, inclusive: tuple[bool, bool] = (True, True), angle_tolerance: float = 1e-5) -> 'SmartSolid':
        return self._fillet(Axis.X, radius, axis, minimum, maximum, inclusive, angle_tolerance)

    def fillet_y(self, radius: float, axis: Axis = None, minimum: float = None, maximum: float = None, inclusive: tuple[bool, bool] = (True, True), angle_tolerance: float = 1e-5) -> 'SmartSolid':
        return self._fillet(Axis.Y, radius, axis, minimum, maximum, inclusive, angle_tolerance)

    def fillet_z(self, radius: float, axis: Axis = None, minimum: float = None, maximum: float = None, inclusive: tuple[bool, bool] = (True, True), angle_tolerance: float = 1e-5) -> 'SmartSolid':
        return self._fillet(Axis.Z, radius, axis, minimum, maximum, inclusive, angle_tolerance)

    def fillet_xy(self, radius_x: float, radius_y: float = None) -> 'SmartSolid':
        return self.fillet_x(radius_x).fillet_y(radius_y or radius_x)

    def fillet_xz(self, radius_x: float, radius_z: float = None) -> 'SmartSolid':
        return self.fillet_x(radius_x).fillet_z(radius_z or radius_x)

    def fillet_yz(self, radius_y: float, radius_z: float = None) -> 'SmartSolid':
        return self.fillet_y(radius_y).fillet_z(radius_z or radius_y)

    def fillet(self, radius_x: float, radius_y: float = None, radius_z: float = None) -> 'SmartSolid':
        return self.fillet_x(radius_x).fillet_y(radius_y or radius_x).fillet_z(radius_z or radius_y or radius_x)

    def fillet_edges(self, filter_by: ShapePredicate | Axis | Plane | GeomType | property, radius: float, reverse: bool = False, angle_tolerance: float = 1e-5) -> 'SmartSolid':
        if isinstance(filter_by, Axis):
            edges = filter_edges_by_axis(self.solid.edges(), filter_by, angle_tolerance)
            if reverse:
                edges = ShapeList([e for e in self.solid.edges() if e not in edges])
        else:
            edges = self.solid.edges().filter_by(filter_by, reverse)
        self.solid = fillet(edges, radius)
        return self

    def intersect(self, *args) -> 'SmartSolid':
        original = self.wrap_solid()
        other = fuse(args)
        self.solid = original & other
        # Workaround for build123d bug: retry without cleaning if invalid
        # https://github.com/gumyr/build123d/issues/1215
        if self.solid is not None and not self.wrap_solid().is_valid:
            with SkipClean():
                self.solid = original & other
        self.assert_valid()
        return self

    def intersected(self, *args, label: str = None) -> 'SmartSolid':
        return self.copy(label).intersect(*args)

    def add_notch(self, direction: Direction, depth: float, length: float):
        raise NotImplementedError("Remove dependency on pencil")
        # notch_height = depth / length * self.get_side_length(direction)
        #
        # pencil = Pencil().up(notch_height).left(self.get_side_length(direction))
        # notch = SmartSolid(pencil.extrude(self.get_side_length(direction)))
        ## notch.orient((90, 90 + direction.(update this)value, 0))
        # notch.align_z(self, Alignment.LR, -depth).align_axis(self, direction.axis, direction.alignment_closer).align_axis(self, direction.orthogonal_axis)
        #
        # extended_shape = self.scaled(1, 1, depth / self.z_size)
        # extended_shape.align_xy(self).align_z(self, Alignment.LL)
        #
        # self.fuse(notch.intersect(extended_shape))

    def copy(self, label: str = None):
        result = SmartSolid(copy(self.solid), label=label or self.label)
        result.origin = Vector(self.origin)
        result._orientation = Vector(self._orientation)
        return result

    def _copy_base_fields(self, target: 'SmartSolid', label: str = None) -> None:
        """Copy base class fields to target. Called by subclass copy() methods."""
        target.solid = copy(self.solid)
        target.label = label or self.label
        target.origin = Vector(self.origin)
        target._orientation = Vector(self._orientation)

    def _scale_solid(self, factor_x: float, factor_y: float, factor_z: float):
        factor_y = factor_y or factor_x
        factor_z = factor_z or factor_y or factor_x
        self.origin = Vector(self.origin.X * factor_x, self.origin.Y * factor_y, self.origin.Z * factor_z)
        return scale(self.solid, (factor_x, factor_y, factor_z))

    def pad(self, pad_x: float = 0, pad_y: float = None, pad_z: float = None):
        pad_y = pad_x if pad_y is None else pad_y
        pad_z = pad_x if pad_z is None else pad_z

        self.solid = self._scale_solid(1 + pad_x / self.x_size, 1 + pad_y / self.y_size, 1 + pad_z / self.z_size)
        return self

    def padded(self, pad_x: float = 0, pad_y: float = None, pad_z: float = None, label: str = None):
        return self.copy(label).pad(pad_x, pad_y, pad_z)

    def scale(self, factor_x: float = 1, factor_y: float = None, factor_z: float = None):
        self.solid = self._scale_solid(factor_x, factor_y, factor_z)
        return self

    def scaled(self, factor_x: float = 1, factor_y: float = None, factor_z: float = None, label: str = None):
        return self.copy(label).scale(factor_x, factor_y, factor_z)

    def mirror(self, about: Plane = Plane.XZ) -> 'SmartSolid':
        self.solid = mirror(self.solid, about)
        # Mirror the origin point about the same plane
        # Reflect origin across the plane: p' = p - 2 * (p - o).dot(n) * n
        # where o is plane origin, n is plane normal
        relative = self.origin - about.origin
        distance = relative.dot(about.z_dir)
        self.origin = self.origin - about.z_dir * (2 * distance)
        return self

    def mirrored(self, about: Plane = Plane.XZ, label: str = None) -> 'SmartSolid':
        return self.copy(label).mirror(about)

    def molded(self, padding: float = 2, label: str = None) -> 'SmartSolid':
        outer = self.padded(padding, label=label)
        outer.align_zxy(self, Alignment.RL)
        return outer.cut(self)

    def wrap_solid(self):
        return wrap(self.solid)

    def clone(self, count: int, shift: VectorLike, label: str = None) -> 'SmartSolid':
        shift = to_vector(shift)
        return SmartSolid((self.moved_vector(shift * i) for i in range(count)), label=label)

    def cut_off(self, x: float = 0, y: float = 0, z: float = 0) -> 'SmartSolid':
        return self.intersect(self.create_bound_box().move(x, y, z))

    def _resolve_cut_offset(self, offset: float | None, fraction: float | None, size: float) -> float:
        """Validate params and return the calculated offset."""
        if offset is None and fraction is None:
            raise ValueError("Either offset or fraction must be provided")
        if offset is not None and fraction is not None:
            raise ValueError("Only one of offset or fraction can be provided, not both")
        if fraction is not None:
            if not (-1 < fraction < 0 or 0 < fraction < 1):
                raise ValueError(f"fraction must satisfy -1 < f < 0 or 0 < f < 1, got {fraction}")
            return size * fraction
        return offset

    def cut_x(self, offset: float = None, fraction: float = None) -> 'SmartSolid':
        return self.cut_off(x=self._resolve_cut_offset(offset, fraction, self.x_size))

    def cut_y(self, offset: float = None, fraction: float = None) -> 'SmartSolid':
        return self.cut_off(y=self._resolve_cut_offset(offset, fraction, self.y_size))

    def cut_z(self, offset: float = None, fraction: float = None) -> 'SmartSolid':
        return self.cut_off(z=self._resolve_cut_offset(offset, fraction, self.z_size))
