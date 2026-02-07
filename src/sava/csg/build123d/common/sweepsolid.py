from copy import copy

from build123d import sweep, Plane, SweepType, Wire, Vector, Location, Axis, VectorLike

from sava.csg.build123d.common.geometry import create_wire_tangent_plane, create_plane_from_planes, multi_rotate_vector
from sava.csg.build123d.common.smartsolid import SmartSolid


class SweepSolid(SmartSolid):
    def __init__(self, sketch: SweepType, path: Wire, path_plane: Plane, label: str = None):
        self.sketch = sketch
        self.path = copy(path)
        self.plane_path = copy(path_plane)

        super().__init__(sweep(sketch, path), label=label)

    def copy(self, label: str = None) -> 'SweepSolid':
        result = SweepSolid.__new__(SweepSolid)
        self._copy_base_fields(result, label)
        result.sketch = self.sketch
        result.path = copy(self.path)
        result.plane_path = copy(self.plane_path)
        return result

    def move(self, x: float, y: float = 0, z: float = 0, plane: Plane = None) -> 'SweepSolid':
        super().move(x, y, z, plane=plane)
        # Convert plane-local offsets to global coordinates if plane is specified
        if plane is not None:
            global_offset = plane.x_dir * x + plane.y_dir * y + plane.z_dir * z
        else:
            global_offset = Vector(x, y, z)
        location = Location(global_offset)
        self.path = self.path.move(location)
        self.plane_path.origin += global_offset
        return self

    def rotate(self, axis: Axis, angle: float) -> 'SweepSolid':
        super().rotate(axis, angle)
        self.path = self.path.rotate(axis, angle)
        self.plane_path = self.plane_path.rotated(axis, angle)
        return self

    def orient(self, rotations: VectorLike) -> 'SweepSolid':
        # Get solid center before orientation change for rotating plane origin around it
        solid_center = self.solid.center()

        super().orient(rotations)
        self.path.orientation = rotations

        # Rotate plane direction vectors
        self.plane_path = self.plane_path.rotated(rotations)

        # Rotate plane origin around the solid center
        relative_origin = self.plane_path.origin - solid_center
        rotated_origin = multi_rotate_vector(relative_origin, Plane.XY, Vector(*rotations))
        self.plane_path.origin = solid_center + rotated_origin

        return self

    def create_path_plane(self) -> Plane:
        """Return the path plane, already transformed with the object.

        Returns:
            Plane that contains the wire path, matching the object's current position and rotation.
        """
        return copy(self.plane_path)

    def _create_plane_at_position(self, t: float) -> Plane:
        """Create a plane at position t along the wire with movement and rotation tracking.
        X-axis is aligned with the path plane.

        Args:
            t: Position along wire (0.0 = start, 1.0 = end)

        Returns:
            Plane positioned at the wire location, matching the object's current position and rotation,
            with x-axis aligned to the path plane
        """
        # Create tangent plane from the transformed path (already tracks movement/rotation)
        plane = create_wire_tangent_plane(self.path, t)

        # Align x-axis with the path plane
        plane = create_plane_from_planes(plane, self.plane_path)

        return plane

    # Create a plane with the following requirements:
    #  - origin matching the end of the wire coordinates in the original plane, taking into account potential movement of the object after creation
    #  - plane is tangent to the end of the wire, taking into account potential rotations of the object after creation
    def create_plane_end(self) -> Plane:
        return self._create_plane_at_position(1.0)

    # Create a plane with origin matching the start of the wire coordinates in the original plane, taking into account potential movement of the object after creation
    def create_plane_start(self) -> Plane:
        return self._create_plane_at_position(0.0)
