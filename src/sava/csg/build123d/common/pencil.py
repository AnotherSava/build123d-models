from math import asin
from math import radians, degrees, acos, sin, cos, tan, atan

from build123d import Vector, ThreePointArc, Line, Face, extrude, Wire, Plane, Location, mirror, Compound, Axis, make_face, Part, revolve, VectorLike

from sava.csg.build123d.common.advanced_math import advanced_mod
from sava.csg.build123d.common.geometry import shift_vector, create_vector, get_angle
from sava.csg.build123d.common.sweepsolid import SweepSolid


class Pencil:
    sweep_path_for: 'Pencil'  # pencil we are creating a sweep path for (if any)
    def __init__(self, start: VectorLike = (0, 0), plane: Plane = Plane.XY):
        self.curves = []
        self.start = start if isinstance(start, Vector) else Vector(*start)
        self.location = start
        self.plane = plane

    def check_destination(self, destination: Vector) -> Vector:
        tolerance = 1e-7
        return self.start if (destination - self.start).length < tolerance else destination

    def double_arc(self, destination: Vector, shift_coefficient: float = 0.5, angle: float = None):
        angle_actual = 180 - degrees(2 * atan(destination.Y / destination.X)) if angle is None else angle
        angle_actual = advanced_mod(angle_actual, 360, -180)
        return self.arc_with_destination(destination * (1 - shift_coefficient), -angle_actual).arc_with_destination(destination * shift_coefficient, angle_actual)

    def arc_with_radius(self, radius: float, centre_angle: float, arc_degrees: float):
        centre = shift_vector(self.location, radius, centre_angle)
        degrees_destination_from_centre = ((arc_degrees + centre_angle + 180) % 360)
        degrees_middle_from_centre = ((arc_degrees / 2 + centre_angle + 180) % 360)
        destination = self.check_destination(shift_vector(centre, radius, degrees_destination_from_centre))
        middle = shift_vector(centre, radius, degrees_middle_from_centre)
        return self.arc_abs(middle, destination)

    def arc_abs(self, midpoint: Vector, destination: Vector):
        self.curves.append(ThreePointArc(self.location, midpoint, destination))
        self.location = destination
        return self

    def arc_from_start(self, midpoint_vector: Vector, destination_vector: Vector):
        return self.arc_abs(self.start + midpoint_vector, self.start + destination_vector)

    def arc(self, midpoint_vector: Vector, destination_vector: Vector):
        return self.arc_abs(self.location + midpoint_vector, self.location + destination_vector)

    def arc_with_angle_to_centre(self, angle_to_centre: float, destination_vector: Vector):
        return self.arc_with_centre_direction(create_vector(1, angle_to_centre), destination_vector)

    def arc_with_vector_to_intersection(self, vector_to_tangents_intersection: Vector, angle: float):
        direction_to_centre = get_angle(vector_to_tangents_intersection) + 90 * (-1 if angle % 360 < 180 else 1)
        radius = vector_to_tangents_intersection.length * tan(radians(angle / 2))
        return self.arc_with_radius(radius, direction_to_centre, angle - 180)

    def arc_with_angle_to_centre_abs(self, angle_to_centre: float, destination: Vector):
        return self.arc_with_centre_direction_abs(create_vector(1, angle_to_centre), destination)

    def arc_with_destination_and_radius(self, destinationVector: Vector, radius: float):
        angle = 2 * degrees(asin(destinationVector.length / 2 / radius))
        return self.arc_with_destination(destinationVector, angle)

    def arc_with_centre_direction(self, centre_direction: Vector, destination_vector: Vector):
        # Create copies and normalize to preserve original vectors
        # Calculate an angle between vectors using dot product
        dot_product = Vector(centre_direction).normalized().dot(Vector(destination_vector).normalized())
        # Clamp dot product to [-1, 1] to handle floating point precision errors
        dot_product = max(-1.0, min(1.0, dot_product))
        a = degrees(acos(dot_product))

        return self.arc_with_destination(destination_vector, 2 * a - 180)

    def arc_with_centre_direction_abs(self, centre_direction: Vector, destination: Vector):
        return self.arc_with_centre_direction(centre_direction, destination - self.location)

    # create arc with specific destination and angle measure
    def arc_with_destination_abs(self, destination: Vector, angle: float):
        # Calculate chord (straight line distance between start and end)
        destination = self.check_destination(destination)
        chord = destination - self.location
        chord_length = chord.length
        
        chord_midpoint = (self.location + destination) / 2
        
        # Calculate radius using chord length and arc angle
        # For an arc with angle θ, radius = chord_length / (2 * sin(θ/2))
        half_angle_rad = radians(abs(angle) / 2)
        if half_angle_rad == 0:
            return self.jump_to(destination)  # Straight line for 0° angle
            
        radius = chord_length / (2 * sin(half_angle_rad))
        
        # Distance from chord midpoint to arc center
        center_distance = radius * cos(half_angle_rad)
        
        # Direction perpendicular to chord (for center calculation)
        # Positive angle goes counter-clockwise (left side of chord)
        perp_direction = Vector(-chord.Y, chord.X).normalized()
        if angle < 0:
            perp_direction = -perp_direction  # Clockwise for negative angles
            
        center = chord_midpoint + perp_direction * center_distance
        
        # Calculate midpoint of arc for Part.Arc
        # The arc midpoint is on the arc, perpendicular to the chord at center
        arc_midpoint = center - perp_direction * radius
        
        return self.arc_abs(arc_midpoint, destination)

    # create arc with specific destination and angle measure
    def arc_with_destination_from_start(self, destination_vector: Vector, angle: float):
        return self.arc_with_destination_abs(destination_vector + self.start, angle)

    # create arc with specific destination and angle measure
    def arc_with_destination(self, destination_vector: Vector, angle: float):
        return self.arc_with_destination_abs(destination_vector + self.location, angle)

    def jump_to(self, abs_destination: Vector):
        abs_destination = self.check_destination(abs_destination)
        self.curves.append(Line(self.location, abs_destination))
        self.location = abs_destination
        return self

    def jump(self, destination: Vector):
        return self.jump_to(destination + self.location)

    def jump_from_start(self, destination: Vector):
        return self.jump_to(destination + self.start)

    def draw(self, length: float, angle: float):
        abs_destination = shift_vector(self.location, length, angle)
        return self.jump_to(abs_destination)

    def up(self, length: float = None):
        length = length or self.start.Y - self.location.Y
        return self.draw(length, 0)

    def left(self, length: float = None):
        length = length or self.location.X - self.start.X
        return self.draw(length, 90)

    def down(self, length: float = None):
        length = length or self.location.Y - self.start.Y
        return self.draw(length, 180)

    def right(self, length: float = None):
        length = length or self.start.X - self.location.X
        return self.draw(length, -90)

    def extrude(self, height: float):
        face = self.create_face()
        return extrude(face, height)

    def extrude_x(self, height: float, transpose: Vector = Vector()):
        solid = self.extrude(height)
        solid.orientation = (90, 90, 0)
        solid.position = transpose
        return solid

    def extrude_y(self, height: float, transpose: Vector = Vector()):
        solid = self.extrude(height)
        solid.orientation = (90, 180, 0)
        solid.position = transpose
        return solid

    def create_face(self, enclose: bool = True) -> Face:
        return Face(self.create_wire(enclose))

    def create_wire(self, enclose: bool = True) -> Wire:
        curves = self.curves.copy()
        if enclose and self.location != self.start:
            curves.append(Line(self.location, self.start))

        return self.plane.from_local_coords(Wire(curves))

    def extrude_mirrored(self, height: float, axis: Axis = Axis.Y):
        face = self.create_mirrored_face(axis)
        return extrude(face, height)

    def complete_wire_for_mirror(self, axis: Axis):
        if Axis.Y == axis and self.location.X != self.start.X:
            self.right(self.start.X - self.location.X)
        if Axis.X == axis and self.location.Y != self.start.Y:
            self.up(self.start.Y - self.location.Y)

    def create_mirrored_face(self, axis: Axis) -> Compound:
        self.complete_wire_for_mirror(axis)
        return make_face([self.create_wire(False), self.mirror_wire(axis)])

    def mirror_wire(self, axis: Axis) -> Wire:
        wire = self.create_wire(False)
        match axis:
            case Axis.Y:
                return mirror(wire, Plane.YZ).move(Location(Vector(self.location.X * 2, 0)))
            case Axis.X:
                return mirror(wire, Plane.XZ).move(Location(Vector(0, self.location.Y * 2)))
        raise "Invalid axis"

    def create_sweep_path(self, plane: Plane = Plane.YZ) -> 'Pencil':
        pencil = Pencil(self.start, plane)
        pencil.sweep_path_for = self
        return pencil

    def sweep(self) -> SweepSolid:
        face = self.sweep_path_for.create_face()
        return SweepSolid(face, self.create_wire(False), self.plane)

    def revolve(self, angle: float = 360, axis: Axis = Axis.Y, enclose: bool = True) -> Part:
        return revolve(self.create_face(enclose), axis, angle)
