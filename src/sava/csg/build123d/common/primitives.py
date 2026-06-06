from dataclasses import dataclass

from build123d import Axis, Edge, Location, Vector, VectorLike, Wire

from sava.csg.build123d.common.geometry import create_vector, get_angle, rotate_vector, to_vector
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartercone import SmarterCone
from sava.csg.build123d.common.smartloft import SmartLoft
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass
class GearDimensions:
    """Parameters for `create_gear`'s polar-pattern toothed ring.

    `radius_outer` is the tooth-root circle; tips extend outward to
    `radius_outer + radius_outer_extra`. `radius_inner > 0` cuts a central
    cylindrical bore of that radius through the ring. `sharpness` is the
    fraction of each tooth's angular slot spent on the leaning sides
    (0 = blunt rectangle, 1 = pointed). `spacing` is the angular fraction of
    the tooth pitch left as a gap between adjacent teeth (0 = teeth touch,
    1 = no teeth). All fields are required by design — callers should make
    every gear parameter explicit at the construction site.
    """
    gear_count: int
    thickness: float
    radius_outer: float
    radius_outer_extra: float
    radius_inner: float
    sharpness: float
    spacing: float
    fillet_radius: float


def create_gear(gear: GearDimensions) -> SmartSolid:
    """Build a flat gear-toothed ring around the Z axis from a `GearDimensions`
    spec — see `GearDimensions` for the field semantics. If `radius_inner > 0`,
    a central cylindrical bore of that radius is cut through the ring."""
    angle_total = 360 / gear.gear_count
    angle_spacing = angle_total * gear.spacing
    angle_gear = angle_total - angle_spacing
    gear_side_angle = angle_gear * gear.sharpness / 2

    points = []
    for i in range(gear.gear_count):
        angle_from = angle_total * i
        points.append(create_vector(gear.radius_outer, angle_from))
        if angle_spacing > 0:
            points.append(create_vector(gear.radius_outer, angle_from + angle_spacing))
        points.append(create_vector(gear.radius_outer + gear.radius_outer_extra, angle_from + angle_spacing + gear_side_angle))
        points.append(create_vector(gear.radius_outer + gear.radius_outer_extra, angle_from + angle_total - gear_side_angle))

    result = Pencil.from_points(points).extrude(gear.thickness).fillet_z(gear.fillet_radius)

    if gear.radius_inner:
        cylinder = SmarterCone.cylinder(gear.radius_inner, gear.thickness)
        result.cut(cylinder.align(result))

    return result


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
