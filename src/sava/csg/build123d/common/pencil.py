from __future__ import annotations

from math import radians, degrees, sin, cos, tan, atan
from typing import TYPE_CHECKING

from build123d import Vector, ThreePointArc, Line, Face, extrude, Wire, Plane, Location, mirror, Axis, revolve, VectorLike, Edge

from sava.common.advanced_math import advanced_mod
from sava.csg.build123d.common.geometry import shift_vector, get_angle, to_vector, validate_points_unique, snap_to

# TYPE_CHECKING import for type hints only; runtime import is lazy to avoid circular dependency
if TYPE_CHECKING:
    from sava.csg.build123d.common.smartsolid import SmartSolid


def _reconstruct_edge(edge: Edge) -> Edge:
    """
    Reconstruct an edge from its geometry to avoid OCCT issues with mirrored edges.

    This fixes a freeze in OCCT's extrusion algorithm when a face contains two adjacent
    circular arcs created through mirroring and edge reversal. By reconstructing the edge,
    we create a fresh edge object without the problematic internal state from mirroring.

    Args:
        edge: The edge to reconstruct

    Returns:
        A new edge with the same geometry but fresh internal state
    """
    start = edge.position_at(0)
    end = edge.position_at(1)

    if edge.geom_type.name == 'LINE':
        return Line(start, end)
    elif edge.geom_type.name == 'CIRCLE':
        mid = edge.position_at(0.5)
        return ThreePointArc(start, mid, end)
    else:
        # For other edge types, return as-is
        return edge


class Pencil:
    def __init__(self, start: VectorLike = (0, 0), plane: Plane = Plane.XY):
        self.curves = []
        self.start = to_vector(start)
        self.location = self.start
        self.plane = plane

    def process_vector_input(self, vector: VectorLike) -> Vector:
        vector = to_vector(vector)
        vector = Vector(snap_to(vector.X, self.start.X), snap_to(vector.Y, self.start.Y), snap_to(vector.Z, self.start.Z))
        assert vector.Z == self.start.Z
        return vector

    def double_arc(self, destination: VectorLike, shift_coefficient: float = 0.5, angle: float = None):
        """Draw two symmetric arcs to reach the destination.

        Creates a smooth S-curve by drawing two arcs with opposite curvatures. The first arc
        curves in one direction to an intermediate point, and the second arc curves in the
        opposite direction to complete the path to the destination.

        Args:
            destination: Target point relative to current location
            shift_coefficient: Where to split the path (0.0-1.0). 0.5 means equal-length arcs,
                             values closer to 0 make the first arc shorter, closer to 1 make it longer
            angle: Arc angle in degrees for each curve. If None, auto-calculated from destination
                  to create a smooth symmetric curve

        Returns:
            self for method chaining
        """
        destination = to_vector(destination)
        angle_actual = 180 - degrees(2 * atan(destination.Y / destination.X)) if angle is None else angle
        angle_actual = advanced_mod(angle_actual, 360, -180)
        return self.arc_with_destination(destination * (1 - shift_coefficient), -angle_actual).arc_with_destination(destination * shift_coefficient, angle_actual)

    def spline(self, destination: VectorLike, destination_tangent: VectorLike, intermediate_points: list[VectorLike] | None = None, start_tangent: VectorLike | None = None) -> 'Pencil':
        """Draw a smooth spline curve to reach the destination, optionally passing through intermediate points.

        Creates a cubic spline that smoothly transitions from the current location to the
        destination point. The curve is tangent to the previous path at the current location
        and arrives at the destination with the specified tangent direction. Optionally, the
        curve can pass through intermediate points along the way.

        Args:
            destination: Target point relative to current location
            destination_tangent: Tangent direction vector at the destination point (only direction matters,
                    magnitude is normalized by build123d's default behavior)
            intermediate_points: Optional list of points to pass through between current location
                               and destination. Each point is relative to current location.
                               Points are interpolated in order. Default is None (direct spline).
            start_tangent: Optional tangent direction vector at the start point. If None, the tangent
                         is calculated from the previous curve (or from destination if no previous curves).
                         Default is None (auto-calculated).

        Returns:
            self for method chaining

        Examples:
            # Simple spline (existing behavior)
            pencil.spline((50, 50), (1, 0))

            # Spline with intermediate points
            pencil.spline((50, 50), (1, 0), intermediate_points=[(20, 30), (40, 20)])

            # Spline with custom start tangent
            pencil.spline((50, 50), (1, 0), start_tangent=(0, 1))

            # Spline with both intermediate points and custom start tangent
            pencil.spline((50, 50), (1, 0), intermediate_points=[(25, 25)], start_tangent=(0, 1))
        """
        destination = to_vector(destination)
        destination_tangent = to_vector(destination_tangent)

        # Convert relative destination to absolute
        destination_abs = self.process_vector_input(self.location + destination)

        # Calculate or use provided tangent at current location
        if start_tangent is not None:
            current_tangent = to_vector(start_tangent)
        else:
            current_tangent = destination if not self.curves else self.curves[-1].tangent_at(1.0)

        # Convert intermediate points (relative) to absolute coordinates
        intermediate_abs = [self.process_vector_input(self.location + to_vector(pt)) for pt in intermediate_points or []]
        points = [self.location] + intermediate_abs + [destination_abs]

        # Validate that all points are unique
        labels = ["start"] + [f"intermediate point {i}" for i in range(len(intermediate_abs))] + ["destination"]
        validate_points_unique(points, tolerance=1e-6, labels=labels)

        edge = Edge.make_spline(points, [current_tangent, destination_tangent])
        self.curves.append(edge)
        self.location = destination_abs
        return self

    def arc_with_radius(self, radius: float, centre_angle: float, arc_degrees: float):
        centre = shift_vector(self.location, radius, centre_angle)
        degrees_destination_from_centre = ((arc_degrees + centre_angle + 180) % 360)
        degrees_middle_from_centre = ((arc_degrees / 2 + centre_angle + 180) % 360)
        destination = shift_vector(centre, radius, degrees_destination_from_centre)
        middle = shift_vector(centre, radius, degrees_middle_from_centre)
        return self.arc_abs(middle, destination)

    def arc_abs(self, midpoint_abs: VectorLike, destination_abs: VectorLike):
        midpoint_abs = self.process_vector_input(midpoint_abs)
        destination_abs = self.process_vector_input(destination_abs)
        self.curves.append(ThreePointArc(self.location, midpoint_abs, destination_abs))
        self.location = destination_abs
        return self

    def arc(self, midpoint_vector: VectorLike, destination_vector: VectorLike):
        return self.arc_abs(self.location + to_vector(midpoint_vector), self.location + to_vector(destination_vector))

    def arc_with_vector_to_intersection(self, vector_to_tangents_intersection: Vector, angle: float):
        direction_to_centre = get_angle(vector_to_tangents_intersection) + 90 * (-1 if angle % 360 < 180 else 1)
        radius = vector_to_tangents_intersection.length * tan(radians(angle / 2))
        return self.arc_with_radius(radius, direction_to_centre, angle - 180)

    # create arc with specific destination and angle measure
    def arc_with_destination_abs(self, destination_abs: Vector, angle: float):
        # Calculate chord (straight line distance between start and end)
        destination_abs = self.process_vector_input(destination_abs)
        chord = destination_abs - self.location
        chord_length = chord.length
        
        chord_midpoint_abs = (self.location + destination_abs) / 2
        
        # Calculate radius using chord length and arc angle
        # For an arc with angle θ, radius = chord_length / (2 * sin(θ/2))
        half_angle_rad = radians(abs(angle) / 2)
        if half_angle_rad == 0:
            return self.jump_to(destination_abs)  # Straight line for 0° angle
            
        radius = chord_length / (2 * sin(half_angle_rad))
        
        # Distance from chord midpoint to arc center
        center_distance = radius * cos(half_angle_rad)
        
        # Direction perpendicular to chord (for center calculation)
        # Positive angle goes counter-clockwise (left side of chord)
        perp_direction = Vector(-chord.Y, chord.X).normalized()
        if angle < 0:
            perp_direction = -perp_direction  # Clockwise for negative angles
            
        center_abs = chord_midpoint_abs + perp_direction * center_distance
        
        # Calculate midpoint of arc for Part.Arc
        # The arc midpoint is on the arc, perpendicular to the chord at center
        arc_midpoint = self.process_vector_input(center_abs - perp_direction * radius)
        
        return self.arc_abs(arc_midpoint, destination_abs)

    # create arc with specific destination and angle measure
    def arc_with_destination(self, destination: VectorLike, angle: float):
        destination = to_vector(destination)
        return self.arc_with_destination_abs(destination + self.location, angle)

    def jump_to(self, destination_abs: VectorLike):
        destination_abs = self.process_vector_input(destination_abs)
        self.curves.append(Line(self.location, destination_abs))
        self.location = destination_abs
        return self

    def jump(self, destination: VectorLike):
        return self.jump_to(to_vector(destination) + self.location)

    def jump_from_start(self, destination: VectorLike):
        return self.jump_to(to_vector(destination) + self.start)

    def draw(self, length: float, angle: float):
        abs_destination = shift_vector(self.location, length, angle)
        return self.jump_to(abs_destination)

    def up(self, length: float = None):
        length = length or self.start.Y - self.location.Y
        return self.draw(length, 0)

    def y_to(self, y_pos: float):
        return self.jump_from_start((self.location.X, y_pos))

    def up_to(self, y_pos: float):
        assert y_pos > self.location.Y
        return self.y_to(y_pos)

    def down_to(self, y_pos: float):
        assert y_pos < self.location.Y
        return self.y_to(y_pos)

    def left(self, length: float = None):
        length = length or self.location.X - self.start.X
        return self.draw(length, 90)

    def x_to(self, x_pos: float):
        return self.jump_from_start((x_pos, self.location.Y))

    def right_to(self, x_pos: float):
        assert x_pos > self.location.X
        return self.x_to(x_pos)

    def left_to(self, x_pos: float):
        assert x_pos < self.location.X
        return self.x_to(x_pos)

    def down(self, length: float = None):
        length = length or self.location.Y - self.start.Y
        return self.draw(length, 180)

    def right(self, length: float = None):
        length = length or self.start.X - self.location.X
        return self.draw(length, -90)

    def extrude(self, height: float, label: str = None) -> SmartSolid:
        from sava.csg.build123d.common.smartsolid import SmartSolid
        face = self.create_face()
        return SmartSolid(extrude(face, height), label=label)

    def create_face(self, enclose: bool = True) -> Face:
        return Face(self.create_wire(enclose))

    def create_wire(self, enclose: bool = True) -> Wire:
        curves = self.curves.copy()
        if enclose and self.location != self.start:
            curves.append(Line(self.location, self.start))

        # Create wire in local 2D coordinates
        local_wire = Wire(curves)
        # Transform from local to global using the plane's location
        return local_wire.locate(Location(self.plane))

    def extrude_mirrored_x(self, height: float, center: float = 0, label: str = None) -> SmartSolid:
        """Extrude a face mirrored around the local X axis at the specified Y coordinate."""
        from sava.csg.build123d.common.smartsolid import SmartSolid
        face = self.create_mirrored_face_x(center)
        return SmartSolid(extrude(face, height), label=label)

    def extrude_mirrored_y(self, height: float, center: float = 0, label: str = None) -> SmartSolid:
        """Extrude a face mirrored around the local Y axis at the specified X coordinate."""
        from sava.csg.build123d.common.smartsolid import SmartSolid
        face = self.create_mirrored_face_y(center)
        return SmartSolid(extrude(face, height), label=label)

    def create_mirrored_face_x(self, center: float = 0) -> Face:
        """Create a face mirrored around the local X axis at the specified Y coordinate."""
        wire = self.create_mirrored_wire_x(center)
        return Face(wire)

    def create_mirrored_face_y(self, center: float = 0) -> Face:
        """Create a face mirrored around the local Y axis at the specified X coordinate."""
        wire = self.create_mirrored_wire_y(center)
        return Face(wire)

    def create_mirrored_wire_x(self, center: float = 0) -> Wire:
        """Create a wire mirrored around the local X axis at the specified Y coordinate."""
        return self._create_mirrored_wire_impl(mirror_around_x_axis=True, center=center)

    def create_mirrored_wire_y(self, center: float = 0) -> Wire:
        """Create a wire mirrored around the local Y axis at the specified X coordinate."""
        return self._create_mirrored_wire_impl(mirror_around_x_axis=False, center=center)

    def _create_mirrored_wire_impl(self, mirror_around_x_axis: bool, center: float) -> Wire:
        """Implementation for creating mirrored wires.

        Args:
            mirror_around_x_axis: True to mirror around X axis (at Y=center), False for Y axis (at X=center)
            center: The coordinate of the mirror axis in local plane coordinates
        """
        original_curves = self.curves.copy()

        # Add segments to/from center to create a closed path for mirroring
        if mirror_around_x_axis:
            # Mirroring around X axis at Y=center
            center = snap_to(center, self.start.Y, self.location.Y)
            if self.start.Y != center:
                self.curves.insert(0, Line(Vector(self.start.X, center), self.start))
            if self.location.Y != center:
                self.jump_to((self.location.X, center))
        else:
            # Mirroring around Y axis at X=center
            center = snap_to(center, self.start.X, self.location.X)
            if self.start.X != center:
                self.curves.insert(0, Line(Vector(center, self.start.Y), self.start))
            if self.location.X != center:
                self.jump_to((center, self.location.Y))

        # Create wire and locate it to the plane
        wire_with_start = Wire(self.curves)
        original_wire = wire_with_start.locate(Location(self.plane))

        # Create mirror plane: offset from plane origin along the appropriate axis
        if mirror_around_x_axis:
            # Mirror across plane perpendicular to local Y at Y=center
            mirror_pos = self.plane.origin + self.plane.y_dir * center
            mirror_plane = Plane(mirror_pos, x_dir=self.plane.x_dir, z_dir=self.plane.y_dir)
        else:
            # Mirror across plane perpendicular to local X at X=center
            mirror_pos = self.plane.origin + self.plane.x_dir * center
            mirror_plane = Plane(mirror_pos, x_dir=self.plane.y_dir, z_dir=self.plane.x_dir)

        mirrored = mirror(original_wire, mirror_plane)

        # Restore original curves
        self.curves = original_curves

        # Handle case where mirror returns Curve instead of Wire
        if hasattr(mirrored, 'wires'):
            mirrored_wire = mirrored.wires()[0]
        else:
            mirrored_wire = mirrored

        # Create a closed wire by combining original and reversed mirrored edges
        original_edges = list(original_wire.edges())
        mirrored_edges = list(mirrored_wire.edges())
        mirrored_edges_reversed = [Edge(e.wrapped.Reversed()) for e in reversed(mirrored_edges)]

        # Combine all edges to form closed loop
        all_edges = original_edges + mirrored_edges_reversed

        # Reconstruct edges to avoid OCCT extrusion freeze with mirrored circular arcs
        # This fixes an issue where two adjacent circular arcs from mirroring cause
        # OCCT's extrusion algorithm to freeze indefinitely
        reconstructed_edges = [_reconstruct_edge(e) for e in all_edges]

        return Wire(reconstructed_edges)

    def revolve(self, angle: float = 360, axis: Axis = Axis.Y, enclose: bool = True, label: str = None) -> SmartSolid:
        from sava.csg.build123d.common.smartsolid import SmartSolid
        return SmartSolid(revolve(self.create_face(enclose), axis, angle), label=label)
