from __future__ import annotations

from enum import Enum, IntEnum, auto
from math import cos, sin, radians, atan2, degrees
from typing import TYPE_CHECKING, Tuple

from build123d import Vector, Axis, Wire, Face, Plane, VectorLike, sweep, Solid
from build123d.topology import Mixin1D

# TYPE_CHECKING import for type hints only; runtime import is lazy to avoid circular dependency
if TYPE_CHECKING:
    from sava.csg.build123d.common.smartsolid import SmartSolid


# Ways to align one 2d vector (or another else) to another
class Alignment(IntEnum):
    LL = auto() # left side, attach to the left
    L = auto() # left side, attach to the centre
    LR = auto() # left side, attach to the right
    CL = auto() # centre, attach to the left
    C = auto() # align both centres
    CR = auto() # centre, attach to the right
    RL = auto() # right side, attach to the left
    R = auto() # right side, attach to the centre
    RR = auto() # right side, attach to the right

    def shift_towards_centre(self, value: float) -> float:
        assert self != Alignment.C

        return value if self in (Alignment.LL, Alignment.LR, Alignment.CL) else -value


def calculate_position(left: float, right: float, self_size: float, alignment: Alignment) -> float:
    match alignment:
        case Alignment.LL:
            return left - self_size
        case Alignment.L:
            return left - self_size / 2
        case Alignment.LR:
            return left
        case Alignment.CL:
            return (left + right) / 2 - self_size
        case Alignment.C:
            return (left + right - self_size) / 2
        case Alignment.CR:
            return (left + right) / 2
        case Alignment.RL:
            return right - self_size
        case Alignment.R:
            return right - self_size / 2
        case Alignment.RR:
            return right
    raise RuntimeError(f"Invalid alignment: {alignment.name} = {alignment.value}")


class Direction(Enum):
    N = Vector(0, 1, 0)   # North (+Y)
    S = Vector(0, -1, 0)  # South (-Y)
    E = Vector(1, 0, 0)   # East (+X)
    W = Vector(-1, 0, 0)  # West (-X)
    U = Vector(0, 0, 1)   # Up (+Z)
    D = Vector(0, 0, -1)  # Down (-Z)

    @property
    def axis(self) -> Axis:
        return Axis((0, 0, 0), self.value)

    def rotate(self, angle: int, axis: Axis = Axis.Z) -> 'Direction':
        return Direction.from_vector(self.value.rotate(axis, angle))

    @staticmethod
    def from_vector(vector: VectorLike, threshold: float = 0.9) -> 'Direction':
        # Normalization ensures threshold represents angle, not magnitude × angle
        normalized = to_vector(vector).normalized()
        best = max(Direction, key=lambda d: d.value.dot(normalized))
        if best.value.dot(normalized) < threshold:
            raise ValueError(f"Vector {vector} is not close enough to any cardinal direction")
        return best


def to_vector(vector: VectorLike) -> Vector:
    """Converts a VectorLike to a Vector if it isn't already.

    Args:
        vector: A Vector or tuple/list of coordinates

    Returns:
        A Vector object
    """
    return vector if isinstance(vector, Vector) else Vector(vector)

def snap_to(original_number: float, *round_numbers: float, tolerance: float = 1e-6) -> float:
    """Snaps a number to one of multiple target values if within tolerance.

    Useful for cleaning up floating-point arithmetic by snapping values that are
    very close to specific numbers (e.g., 0, 90, 180) to those exact values.
    Checks each target value in order and returns the first match.

    Args:
        original_number: The number to potentially snap
        *round_numbers: One or more target values to snap to
        tolerance: Maximum difference for snapping (default: 1e-6)

    Returns:
        The first round_number within tolerance, otherwise original_number

    Examples:
        >>> snap_to(0.0000001, 0.0)
        0.0
        >>> snap_to(89.9999999, 90.0)
        90.0
        >>> snap_to(45.5, 90.0)
        45.5
        >>> snap_to(10.0000001, 0.0, 10.0, 20.0)  # Multiple targets
        10.0
        >>> snap_to(5.0, 0.0, 10.0)  # No match within tolerance
        5.0
    """
    for round_number in round_numbers:
        if are_numbers_too_close(original_number, round_number, tolerance):
            return round_number
    return original_number

def are_numbers_too_close(num1: float, num2: float, tolerance: float = 1e-6) -> bool:
    """Checks if two numbers are too close together.

    Args:
        num1: First number
        num2: Second number
        tolerance: Minimum allowed difference between numbers. Default is 1e-6.

    Returns:
        True if numbers are closer than tolerance, False otherwise
    """
    return abs(num1 - num2) < tolerance

def are_points_too_close(pt1: VectorLike, pt2: VectorLike, tolerance: float = 1e-6) -> bool:
    """Checks if two points are too close together.

    Args:
        pt1: First point
        pt2: Second point
        tolerance: Minimum allowed distance between points. Default is 1e-6.

    Returns:
        True if points are closer than tolerance, False otherwise
    """
    pt1 = to_vector(pt1)
    pt2 = to_vector(pt2)
    return (pt1 - pt2).length < tolerance

def validate_points_unique(points: list[VectorLike], tolerance: float = 1e-6, labels: list[str] | None = None) -> None:
    """Validates that no two points in the list are too close together.

    Args:
        points: List of points to check
        tolerance: Minimum allowed distance between points. Default is 1e-6.
        labels: Optional labels for points to use in error messages

    Raises:
        ValueError: If any two points are too close together
    """
    # Convert all points to Vector first
    points_vec = [to_vector(pt) for pt in points]

    for i, pt1 in enumerate(points_vec):
        for j, pt2 in enumerate(points_vec[i+1:], start=i+1):
            if are_points_too_close(pt1, pt2, tolerance):
                label1 = labels[i] if labels else f"point {i}"
                label2 = labels[j] if labels else f"point {j}"
                raise ValueError(f"{label1} and {label2} are too close together")

# angle is measured in degrees CCW from axis Y
def create_vector(length: float, angle: float) -> Vector:
    return Vector(-length * sin(radians(angle)), length * cos(radians(angle)))

# args = series of lengths and angles, where angles are measured in degrees CCW from axis Y
def shift_vector(vector: Vector, *args: float) -> Vector:
    assert len(args) >= 2 and len(args) % 2 == 0
    result = vector
    for i in range(0, len(args), 2):
        result += create_vector(args[i], args[i + 1])

    return result

def get_angle(vector: Vector):
    return -degrees(atan2(vector.X, vector.Y))

def create_plane_from_planes(plane_xy: Plane, axis_x: Plane):
    """Create a plane that matches plane_xy position and z-direction,
    but rotated so the x-axis aligns with the intersection of axis_x plane."""
    # Get the intersection line between plane_xy and axis_x
    # This line will become our new x-axis
    x_direction = plane_xy.z_dir.cross(axis_x.z_dir).normalized()

    assert x_direction.length > 1e-6, "Planes are parallel, cannot create plane with aligned x-axis"

    # Create the new plane with the same position and z-direction as plane_xy,
    # but with x-direction aligned to the intersection
    return Plane(plane_xy.location.position, x_dir=x_direction, z_dir=plane_xy.z_dir)

def create_wire_tangent_plane(wire: Mixin1D, position_at: float) -> Plane:
    """Creates a plane at a specified position along a wire, orthogonal to the wire's direction.
    
    Args:
        wire: The wire to create a tangent plane for
        position_at: Position along the wire as a parameter from 0.0 to 1.0
                    - 0.0 = start of the wire
                    - 1.0 = end of the wire  
                    - 0.5 = middle of the wire
                    - Values can be outside 0-1 range for extrapolation
    
    Returns:
        A Plane object positioned at the specified location with its Z-axis 
        aligned with the wire's tangent direction (orthogonal to the wire)
    """
    # Get position and tangent at the specified parameter along the wire
    position = wire.position_at(position_at)
    tangent = wire.tangent_at(position_at)

    # Create a plane at the position with the tangent as the normal (Z-axis)
    # This makes the plane orthogonal to the wire's direction at that point
    return Plane(origin=position, z_dir=tangent.normalized())


def rotate_vector(vector: VectorLike, axis: Axis, angle: float) -> Vector:
    """Rotates a vector around a specified axis by a given angle.

    Args:
        vector: The vector to rotate
        axis: The axis to rotate around (use Axis.X/Y/Z or create custom with Axis(origin, direction))
        angle: The angle to rotate by, in degrees

    Returns:
        The rotated vector
    """
    vector = to_vector(vector)
    angle_rad = radians(angle)
    cos_a = cos(angle_rad)
    sin_a = sin(angle_rad)
    
    # Get the normalized axis direction vector
    axis_vector = axis.direction
    ux, uy, uz = axis_vector.X, axis_vector.Y, axis_vector.Z
    
    # Rodrigues' rotation formula
    # v_rot = v*cos(θ) + (k × v)*sin(θ) + k*(k·v)*(1-cos(θ))
    # where k is the unit axis vector, v is the input vector, θ is the angle
    
    # Dot product k·v
    dot_product = ux * vector.X + uy * vector.Y + uz * vector.Z
    
    # Cross product k × v
    cross_x = uy * vector.Z - uz * vector.Y
    cross_y = uz * vector.X - ux * vector.Z
    cross_z = ux * vector.Y - uy * vector.X
    
    # Apply Rodrigues' formula
    one_minus_cos = 1 - cos_a

    vector_x = vector.X * cos_a + cross_x * sin_a + ux * dot_product * one_minus_cos
    vector_y = vector.Y * cos_a + cross_y * sin_a + uy * dot_product * one_minus_cos
    vector_z = vector.Z * cos_a + cross_z * sin_a + uz * dot_product * one_minus_cos

    return Vector(vector_x, vector_y, vector_z)

def multi_rotate_vector(vector: VectorLike, plane: Plane, rotations: VectorLike) -> Vector:
    """ Takes a vector and sequentially rotates it by rotations.X degrees around X axis of a specified plane,
    then by rotations.Y degrees around Y axis, and finally by rotations.Z degrees around Z axis.

    Args:
        vector: The vector to rotate
        plane: The plane to take axis from
        rotations: The rotations to apply, defined by a vector with x, y, z components

    Returns:
        The rotated vector
    """
    # Convert inputs to Vector if needed
    vector = to_vector(vector)
    rotations = to_vector(rotations)
    
    # Get the plane's axes
    x_axis = Axis(plane.location.position, plane.x_dir)
    y_axis = Axis(plane.location.position, plane.y_dir) 
    z_axis = Axis(plane.location.position, plane.z_dir)
    
    # Apply rotations sequentially: X, then Y, then Z
    result = vector
    result = rotate_vector(result, x_axis, rotations.X)
    result = rotate_vector(result, y_axis, rotations.Y)
    result = rotate_vector(result, z_axis, rotations.Z)
    
    return result

def rotate_axis(axis_to_rotate: Axis, axis_rotate_around: Axis, angle: float) -> Axis:
    return Axis(axis_to_rotate.position, axis_to_rotate.direction.rotate(axis_rotate_around, angle))

def convert_orientation_to_rotations(orientation: VectorLike) -> Vector:
    """ Converts an orientation vector to a rotations vector:

    Take a default XY plane, rotate it by orientation.X degree around its axis X, then rotate it by orientation.Y degree around its _new_ axis Y, and finally by orientation.Z degree around its _new_ axis Z.
    Then find what angle "a" you need to rotate this new plate around original axis Z to make its X axis be in XZ plane on the original coordinate system. Perform this rotation.
    Then find what angle "b" you need to rotate this new plate around original axis Y to make its X axis match axis X of the original coordinate system. Perform this rotation.
    And finally find what angle "c" you need to rotate this new plate around original axis X to make its Y axis match axis Y of the original coordinate system.
    return those three angles as a Vector(c, b, a)
    """
    x_axis, y_axis, z_axis = orient_axis(orientation)

    # Now we have the final orientation of the plane
    # We need to find the fixed-axis rotations that would achieve this

    # Step 1: Find angle "a" to rotate around original Z to get X-axis in XZ plane
    # Project current_x onto XY plane and find angle from X-axis
    if Vector(x_axis.direction.X, x_axis.direction.Y, 0).length < 1e-10:
        angle_a = 0
    else:
        angle_a = degrees(atan2(x_axis.direction.Y, x_axis.direction.X))

    # Apply this rotation to current axes
    x_axis = rotate_axis(x_axis, Axis.Z, -angle_a)
    y_axis = rotate_axis(y_axis, Axis.Z, -angle_a)

    # Step 2: Find angle "b" to rotate around original Y to align X-axis
    # temp_x should now be in XZ plane, find angle from X-axis
    angle_b = -degrees(atan2(x_axis.direction.Z, x_axis.direction.X))

    # Apply this rotation
    y_axis = rotate_axis(y_axis, Axis.Y, -angle_b)

    # Step 3: Find angle "c" to rotate around original X to align Y-axis
    # final_y should align with (0,1,0), find angle in YZ plane
    angle_c = degrees(atan2(y_axis.direction.Z, y_axis.direction.Y))

    return Vector(angle_c, angle_b, angle_a)


def _rotate_single_axis(axis: Axis, rotations: Vector, plane: Plane) -> Axis:
    axis = rotate_axis(axis, plane.location.x_axis, rotations.X)
    axis = rotate_axis(axis, plane.location.y_axis, rotations.Y)
    return rotate_axis(axis, plane.location.z_axis, rotations.Z)

def rotate_orientation(orientation: VectorLike, rotations: VectorLike, plane: Plane) -> Vector:
    rotations = to_vector(rotations)
    x_axis, y_axis, z_axis = orient_axis(orientation)

    x_axis = _rotate_single_axis(x_axis, rotations, plane)
    y_axis = _rotate_single_axis(y_axis, rotations, plane)
    z_axis = _rotate_single_axis(z_axis, rotations, plane)

    return calculate_orientation(x_axis, y_axis, z_axis)

def orient_axis(orientation: VectorLike) -> Tuple[Axis, Axis, Axis]:
    """ Converts an orientation vector to a rotations vector:

    Take a default XY plane, rotate it by orientation.X degree around its axis X, then rotate it by orientation.Y degree around its _new_ axis Y, and finally by orientation.Z degree around its _new_ axis Z.
    """
    orientation = to_vector(orientation)

    # Start with standard XY plane vectors
    # Apply the orientation transformation using object-attached axes
    # This simulates the build123d orientation behavior

    # First rotation: around X-axis
    y_axis = rotate_axis(Axis.Y, Axis.X, orientation.X)
    z_axis = rotate_axis(Axis.Z, Axis.X, orientation.X)


    # Second rotation: around the NEW Y-axis (object-attached)
    x_axis = rotate_axis(Axis.X, y_axis, orientation.Y)
    z_axis = rotate_axis(z_axis, y_axis, orientation.Y)

    # Third rotation: around the NEW Z-axis (object-attached)
    x_axis = rotate_axis(x_axis, z_axis, orientation.Z)
    y_axis = rotate_axis(y_axis, z_axis, orientation.Z)

    return x_axis, y_axis, z_axis

def calculate_orientation(x_axis: Axis, y_axis: Axis, z_axis: Axis) -> Vector:
    """Calculate the orientation angles that would produce the given axes using object-attached rotations.
    
    This is the reverse of orient_axis - given three axes representing a coordinate system,
    calculate the orientation vector (X, Y, Z) that would produce these axes when applied
    to the standard XYZ axes using object-attached rotations.
    
    Args:
        x_axis: The desired X-axis
        y_axis: The desired Y-axis  
        z_axis: The desired Z-axis
        
    Returns:
        Vector with orientation angles (X, Y, Z) in degrees
    """
    # We need to find angles that when applied via object-attached rotations
    # would transform (1,0,0), (0,1,0), (0,0,1) to the given axes
    
    # Start with the assumption that we apply rotations in order: X, then Y, then Z
    # Working backwards from the final result
    
    # The Z-axis direction tells us about the final orientation
    # After all rotations, the original Z-axis should point in z_axis.direction
    final_z = z_axis.direction
    
    # The Y-axis direction after all rotations should be y_axis.direction
    final_y = y_axis.direction
    
    # The X-axis direction after all rotations should be x_axis.direction
    final_x = x_axis.direction
    
    # To reverse the process, we need to find the angles
    # Let's use the fact that we can extract Euler angles from a rotation matrix
    
    # The rotation matrix is formed by the three axis directions as columns
    # R = [x_axis.direction, y_axis.direction, z_axis.direction]
    
    # For ZYX Euler angles (which matches build123d's X,Y,Z object-attached order in reverse):
    # We extract angles from the rotation matrix
    
    # Extract orientation angles from the rotation matrix
    # The matrix is: [final_x, final_y, final_z] as columns
    
    # For object-attached rotations X, Y, Z, the equivalent is extracting ZYX Euler angles
    # from the transpose of the rotation matrix (since we're going backwards)
    
    # Z rotation angle (around Z-axis) - this affects how X and Y axes are rotated in XY plane
    # After Z rotation, X-axis becomes (cos(Z), sin(Z), 0) and Y-axis becomes (-sin(Z), cos(Z), 0)
    
    # Y rotation angle (around Y-axis) - this affects how X and Z axes are rotated in XZ plane  
    # X-axis becomes (cos(Y), 0, -sin(Y)) and Z-axis becomes (sin(Y), 0, cos(Y))
    
    # X rotation angle (around X-axis) - this affects how Y and Z axes are rotated in YZ plane
    # Y-axis becomes (0, cos(X), sin(X)) and Z-axis becomes (0, -sin(X), cos(X))
    
    # For intrinsic XYZ rotations, we need to extract angles correctly
    # The rotation matrix R is formed by the axis directions as columns: [final_x, final_y, final_z]
    # For intrinsic XYZ rotations, we use the proper extraction formulas
    
    # The rotation matrix elements are:
    # R = [final_x.X  final_y.X  final_z.X]
    #     [final_x.Y  final_y.Y  final_z.Y] 
    #     [final_x.Z  final_y.Z  final_z.Z]
    
    # For intrinsic XYZ rotations, the extraction formulas are:
    # sin(Y) = R[0,2] = final_z.X
    # cos(Y) = sqrt(R[0,0]^2 + R[0,1]^2) = sqrt(final_x.X^2 + final_y.X^2)
    
    sin_y = final_z.X
    cos_y = (final_x.X**2 + final_y.X**2)**0.5
    
    # Check for gimbal lock
    if abs(cos_y) < 1e-6:
        # Gimbal lock - Y rotation is ±90 degrees
        angle_y = 90 if sin_y > 0 else -90
        # Set Z to 0 by convention and extract X differently
        angle_z = 0
        # In gimbal lock, we use different matrix elements
        angle_x = degrees(atan2(final_y.Z, final_y.Y))
    else:
        # Normal case
        angle_y = degrees(atan2(sin_y, cos_y))
        # tan(X) = -R[1,2] / R[2,2] = -final_z.Y / final_z.Z
        angle_x = degrees(atan2(-final_z.Y, final_z.Z))
        # tan(Z) = -R[0,1] / R[0,0] = -final_y.X / final_x.X
        angle_z = degrees(atan2(-final_y.X, final_x.X))
    
    return Vector(angle_x, angle_y, angle_z)

def choose_wire_diameter(wire: Wire) -> float:
    return wire.length / 100

def choose_vertex_diameter(wire: Wire) -> float:
    return choose_wire_diameter(wire) * 2

def solidify_wire(wire: Wire) -> SmartSolid:
    from sava.csg.build123d.common.smartsolid import SmartSolid
    radius = choose_wire_diameter(wire) / 2
    shapes = []

    # Break wire into individual edges and sweep each separately
    # This ensures each segment has a circular profile perpendicular to its direction
    for edge in wire.edges():
        # Create a plane perpendicular to the edge's starting direction
        profile_plane = create_wire_tangent_plane(edge, 0)

        # Create a circle profile in this plane and sweep it along just this edge
        circle_wire = Wire.make_circle(radius, profile_plane)
        shapes.append(sweep(Face(circle_wire), edge))

    # Add spheres at each vertex to smooth the joints between segments
    # Collect all shapes (swept segments + spheres)
    for vertex in wire.vertices():
        sphere = Solid.make_sphere(choose_vertex_diameter(wire) / 2)
        sphere.position = vertex.center()
        shapes.append(sphere)

    return SmartSolid(shapes)
