from build123d import sweep, Plane, SweepType, Wire, Vector

from sava.csg.build123d.common.geometry import create_wire_tangent_plane
from sava.csg.build123d.common.smartsolid import SmartSolid


class SweepSolid(SmartSolid):
    def __init__(self, sketch: SweepType, path: Wire, path_plane: Plane):
        self.path = path
        self.plane_path = path_plane
        self.plane_drawing_start = create_wire_tangent_plane(path, 0.0)

        self.plane_drawing_end = create_wire_tangent_plane(path, 1.0)

        super().__init__(sweep(sketch, path))
        
        # Store the initial solid center to track movement (center reflects actual global position)
        self.initial_solid_center = self.solid.center()
        
        # Store the initial solid orientation to track rotations (only if solid has orientation)
        if hasattr(self.solid, 'orientation'):
            self.initial_solid_orientation = self.solid.orientation
        else:
            # For ShapeList or objects without orientation, use zero vector
            self.initial_solid_orientation = Vector(0, 0, 0)

    def _create_plane_at_position(self, t: float) -> Plane:
        """Create a plane at position t along the wire with movement and rotation tracking.
        
        Args:
            t: Position along wire (0.0 = start, 1.0 = end)
            
        Returns:
            Plane positioned at the wire location, adjusted for object movement and rotation
        """
        plane = create_wire_tangent_plane(self.path, t)
        
        # Calculate the actual movement by comparing current solid center with initial solid center
        current_solid_center = self.solid.center()
        movement_offset = current_solid_center - self.initial_solid_center
        
        # Calculate rotation offset by comparing current and initial orientations
        if hasattr(self.solid, 'orientation'):
            current_orientation = self.solid.orientation
        else:
            # For ShapeList or objects without orientation, assume no rotation
            current_orientation = Vector(0, 0, 0)
        rotation_offset = current_orientation - self.initial_solid_orientation
        
        # Apply rotation to the plane if the object has been rotated
        if rotation_offset.length > 1e-6:  # Check if there's meaningful rotation
            # Convert degrees to radians and apply rotation
            plane = plane.rotated((rotation_offset.X, rotation_offset.Y, rotation_offset.Z))
        
        # The plane origin should be positioned so that (0,0,0) in plane coordinates
        # maps to the wire position plus the movement offset
        wire_position = self.path.position_at(t)
        target_position = wire_position + movement_offset
        
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
