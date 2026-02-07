from copy import copy

from build123d import Axis, Face, Plane, revolve, Vector

from sava.csg.build123d.common.smartsolid import SmartSolid


def _rotate_plane_around_axis(plane: Plane, axis: Axis, angle: float) -> Plane:
    """Rotate a plane around an arbitrary axis by a given angle.

    Args:
        plane: The plane to rotate
        axis: The axis to rotate around
        angle: The rotation angle in degrees

    Returns:
        A new plane rotated around the axis
    """
    new_x = plane.x_dir.rotate(axis, angle)
    new_z = plane.z_dir.rotate(axis, angle)
    new_origin = plane.origin.rotate(axis, angle) if plane.origin != Vector(0, 0, 0) else plane.origin
    return Plane(origin=new_origin, x_dir=new_x, z_dir=new_z)


class SmartRevolve(SmartSolid):
    """A SmartSolid created by revolving a face around an axis.

    Tracks the original sketch plane and axis through transformations,
    allowing retrieval of planes at any angular position along the revolve.
    """

    def __init__(self, sketch: Face, axis: Axis, angle: float, sketch_plane: Plane, label: str = None):
        """Create a SmartRevolve from a face revolved around an axis.

        Args:
            sketch: The face to revolve
            axis: The axis to revolve around
            angle: The revolve angle in degrees
            sketch_plane: The plane of the original sketch (used for tracking)
            label: Optional label for the solid
        """
        self.sketch = sketch
        self.axis = copy(axis)
        self.angle = angle
        self.sketch_plane = copy(sketch_plane)

        super().__init__(revolve(sketch, axis, angle), label=label)

    def copy(self, label: str = None) -> 'SmartRevolve':
        """Create a deep copy of this SmartRevolve.

        Args:
            label: Optional new label for the copy

        Returns:
            A new SmartRevolve with copied fields
        """
        result = SmartRevolve.__new__(SmartRevolve)
        self._copy_base_fields(result, label)
        result.sketch = self.sketch
        result.axis = copy(self.axis)
        result.angle = self.angle
        result.sketch_plane = copy(self.sketch_plane)
        return result

    def create_plane_at(self, t: float) -> Plane:
        """Get plane of original face revolved to angle * t.

        Uses SmartSolid's origin and _orientation to account for transformations.

        Args:
            t: Position along revolve (0.0 = start, 1.0 = end)

        Returns:
            Plane at the specified angular position, correctly transformed
        """
        # 1. Rotate original plane by angle * t around original axis
        rotation_angle = self.angle * t
        plane = _rotate_plane_around_axis(self.sketch_plane, self.axis, rotation_angle)

        # 2. Apply current orientation (from SmartSolid._orientation)
        if self._orientation.length > 1e-10:
            plane = plane.rotated(self._orientation)

        # 3. Apply current position offset (from SmartSolid.origin)
        plane.origin = plane.origin + self.origin

        return plane
