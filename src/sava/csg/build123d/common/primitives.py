from math import tan, radians

from build123d import Location, fillet, Wire, Solid, VectorLike, Axis, Vector, Edge, Face

from sava.csg.build123d.common.geometry import to_vector, rotate_vector, get_angle, create_vector
from sava.csg.build123d.common.smartloft import SmartLoft
from sava.csg.build123d.common.smartsolid import SmartSolid


def create_tapered_box(base_length: float, base_width: float, height: float, top_length: float, top_width: float, radius = None) -> SmartSolid:
    base = create_filleted_rect(base_length, base_width, radius)
    top = create_filleted_rect(top_length, top_width, radius)

    return SmartLoft.create(base, top, height=height)

def create_tapered_box_delta(base_length: float, base_width: float, height: float, delta: float, radius = None) -> SmartSolid:
    return create_tapered_box(base_length, base_width, height, base_length + delta * 2, base_width + delta * 2, radius)

def create_filleted_rect(length: float, width: float, radius: float) -> Face:
    wire = Wire.make_rect(length, width)
    if radius:
        wire = fillet(wire.vertices(), radius)
    return Face(wire)

def create_cone_with_angle_and_height(bottom_radius: float, height: float, angle: float) -> SmartSolid:
    top_radius = height * tan(radians(angle)) + bottom_radius
    return SmartSolid(Solid.make_cone(bottom_radius, top_radius, height))

def create_handle_wire(radius: float, arc_angle: float, width: float, centre: VectorLike = (0, 0, 0)) -> Wire:
    """Create a curved handle wire as a spline arc.

    Args:
        radius: Radial distance from centre to the arc.
        arc_angle: Angular span in degrees (CCW rotation around Z axis).
        width: Additional radial distance for the middle point (creates outward bulge).
        centre: Center point of the circular arc.

    Returns:
        Wire: Spline wire forming the handle curve.
    """
    centre = to_vector(centre)
    start = create_vector(radius, -arc_angle / 2)
    offset = 1.0001 if width < 0 else 0.9999
    start = start * offset

    # Calculate the three points
    start_point = centre + start

    # Rotate start vector by arc_angle around Z axis to get end point
    start_rotated = rotate_vector(start, Axis.Z, arc_angle)
    end_point = centre + start_rotated

    # Rotate start vector by arc_angle/2 and increase length by width for middle point
    start_rotated_half = rotate_vector(start, Axis.Z, arc_angle / 2)
    middle_direction = start_rotated_half.normalized()
    middle_point = centre + middle_direction * (start.length + width)

    # Calculate tangents perpendicular to radial directions (CCW in XY plane)
    # For a radial vector (x, y, z), the tangent for CCW motion is (-y, x, 0)
    start_tangent = Vector(-start.Y, start.X, 0).normalized()
    end_tangent = Vector(-start_rotated.Y, start_rotated.X, 0).normalized()

    # Middle tangent is the average of start and end tangents in terms of direction, but twice as long
    middle_tangent = start_tangent + end_tangent

    # Create spline through the three points with specified tangents at each point
    points = [start_point, middle_point, end_point]
    tangents = [start_tangent, middle_tangent, end_tangent]

    edge = Edge.make_spline(points, tangents, scale=False)

    # return edge along the circle
    back = Edge.make_circle(start.length * offset, start_angle = get_angle(start) + 90, end_angle = get_angle(start) + arc_angle + 90).move(Location(centre))

    # At least a minimal offset is needed for a shape to be valid
    offset_a = Edge.make_line(centre + start_rotated, centre + start_rotated * offset)
    offset_b = Edge.make_line(centre + start * offset, start_point)

    return Wire([edge, offset_a, back, offset_b])

def create_handle_solid(radius: float, arc_angle: float, width: float, height: float, centre: VectorLike = (0, 0, 0)) -> SmartLoft:
    """Create a handle solid by lofting two curved wires.

    Args:
        radius: Radial distance from centre. If height > 0, this is the inner (smaller) radius.
            If height < 0, this is the outer (larger) radius.
        arc_angle: Angular span in degrees.
        width: Radial width/bulge of the handle.
        height: Radial thickness of the handle (difference between outer and inner radius).
            Sign determines direction: positive = upward, negative = downward.
        centre: Center point of the circular arc.

    Returns:
        SmartLoft: The handle solid. base_profile is always at z_min, target_profile at z_max.
    """
    base = create_handle_wire(radius, arc_angle, -width, centre)
    target = create_handle_wire(radius + height, arc_angle, -width - height, centre)
    return SmartLoft.create(base, target, height)