from copy import copy

from build123d import Axis, Face, Plane, revolve

from sava.csg.build123d.common.geometry import rotate_plane, orient_plane
from sava.csg.build123d.common.smartsolid import SmartSolid


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
        plane = rotate_plane(self.sketch_plane, self.axis, rotation_angle)

        # 2. Apply current orientation (from SmartSolid._orientation)
        if self._orientation.length > 1e-10:
            plane = orient_plane(plane, self._orientation)

        # 3. Apply current position offset (from SmartSolid.origin)
        plane.origin = plane.origin + self.origin

        return plane
