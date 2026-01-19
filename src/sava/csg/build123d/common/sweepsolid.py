from copy import copy

from build123d import sweep, Plane, SweepType, Wire, Vector, ShapeList

from sava.csg.build123d.common.geometry import create_wire_tangent_plane, multi_rotate_vector, create_plane_from_planes
from sava.csg.build123d.common.smartsolid import SmartSolid


class SweepSolid(SmartSolid):
    def __init__(self, sketch: SweepType, path: Wire, path_plane: Plane, label: str = None):
        self.sketch = sketch
        self.path = path
        self.plane_path = path_plane

        super().__init__(sweep(sketch, path), label=label)
        
        # Store the initial solid center to track movement (center reflects actual global position)
        self.initial_solid_center = self.solid.center()
        
    def copy(self) -> 'SweepSolid':
        sweep_solid = SweepSolid(self.sketch, self.path, self.plane_path)
        sweep_solid.solid = copy(self.solid)
        return sweep_solid

    def _get_current_orientation(self) -> Vector:
        """Get the current orientation of the solid.
        
        For single shapes, returns the orientation directly.
        For ShapeList, returns the orientation of the first shape.

        Returns:
            Current orientation as Vector(X, Y, Z) in degrees
        """
        return self.solid[0].orientation if isinstance(self.solid, ShapeList) else  self.solid.orientation

    def create_path_plane(self) -> Plane:
        """Create a plane for the sweep path with movement and rotation tracking.

        Returns:
            Plane that contains the wire path, adjusted for object movement and rotation.
            This is the original path plane transformed to account for any changes to the object.
        """
        # Start with a copy of the original path plane
        plane = copy(self.plane_path)
        
        # Calculate the actual movement by comparing current solid center with initial solid center
        current_solid_center = self.solid.center()
        movement_offset = current_solid_center - self.initial_solid_center
        
        # Get current rotation (initial orientation is always (0, 0, 0) for swept solids)
        current_rotation = self._get_current_orientation()
        
        # Apply rotation to the plane orientation
        plane = plane.rotated((current_rotation.X, current_rotation.Y, current_rotation.Z))
        
        # Rotate the plane origin around the solid center
        relative_origin = plane.origin - self.initial_solid_center
        rotated_relative_origin = multi_rotate_vector(relative_origin, Plane.XY, current_rotation)
        plane.origin = self.initial_solid_center + rotated_relative_origin
        
        # Apply movement offset to the plane origin
        plane.origin += movement_offset
        
        return plane


    def _create_plane_at_position(self, t: float) -> Plane:
        """Create a plane at position t along the wire with movement and rotation tracking.
        X-axis is aligned with the path plane.
        
        Args:
            t: Position along wire (0.0 = start, 1.0 = end)
            
        Returns:
            Plane positioned at the wire location, adjusted for object movement and rotation,
            with x-axis aligned to the path plane
        """
        plane = create_wire_tangent_plane(self.path, t)
        
        # Calculate the actual movement by comparing current solid center with initial solid center
        current_solid_center = self.solid.center()
        movement_offset = current_solid_center - self.initial_solid_center
        
        # Get current rotation (initial orientation is always (0, 0, 0) for swept solids)
        current_rotation = self._get_current_orientation()
        
        # Get the original wire position
        wire_position = self.path.position_at(t)
        
        # Account for how the wire position moves relative to the solid center during rotation
        rotation_center = self.initial_solid_center
        
        # Calculate the wire position relative to the rotation center
        relative_wire_position = wire_position - rotation_center
        
        # Apply the rotation to the relative position
        rotated_relative_position = multi_rotate_vector(relative_wire_position, Plane.XY, current_rotation)
        
        # Calculate the final wire position after rotation
        rotated_wire_position = rotation_center + rotated_relative_position
        
        # Apply rotation to the plane orientation as well
        plane = plane.rotated((current_rotation.X, current_rotation.Y, current_rotation.Z))
        
        # Get the transformed path plane for x-axis alignment
        path_plane = self.create_path_plane()
        
        # Align x-axis with the path plane
        plane = create_plane_from_planes(plane, path_plane)
        
        # The target position includes both rotation and movement
        target_position = rotated_wire_position + movement_offset
        
        # Adjust plane origin so that from_local_coords((0,0,0)) equals target_position
        plane.origin = target_position
        return plane

    # Create a plane with the following requirements:
    #  - origin matching the end of the wire coordinates in the original plane, taking into account potential movement of the object after creation
    #  - plane is tangent to the end of the wire, taking into account potential rotations of the object after creation
    def create_plane_end(self) -> Plane:
        return self._create_plane_at_position(1.0)

    # Create a plane with origin matching the start of the wire coordinates in the original plane, taking into account potential movement of the object after creation
    def create_plane_start(self) -> Plane:
        return self._create_plane_at_position(0.0)
