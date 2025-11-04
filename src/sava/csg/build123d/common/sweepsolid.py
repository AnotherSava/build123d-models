import math
from copy import copy

from build123d import sweep, Plane, SweepType, Wire, Vector

from sava.csg.build123d.common.geometry import create_wire_tangent_plane
from sava.csg.build123d.common.smartsolid import SmartSolid


class SweepSolid(SmartSolid):
    def __init__(self, sketch: SweepType, path: Wire, path_plane: Plane):
        self.sketch = sketch
        self.path = path
        self.plane_path = path_plane

        super().__init__(sweep(sketch, path))
        
        # Store the initial solid center to track movement (center reflects actual global position)
        self.initial_solid_center = self.solid.center()
        
        # Store the initial solid orientation to track rotations (only if solid has orientation)
        if hasattr(self.solid, 'orientation'):
            self.initial_solid_orientation = self.solid.orientation
        else:
            # For ShapeList or objects without orientation, use zero vector
            self.initial_solid_orientation = Vector(0, 0, 0)

    def copy(self) -> 'SweepSolid':
        sweep_solid = SweepSolid(self.sketch, self.path, self.plane_path)
        sweep_solid.solid = copy(self.solid)
        return sweep_solid


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
        
        # Get the original wire position
        wire_position = self.path.position_at(t)
        
        # If there's rotation, we need to account for how the wire position moves relative to the solid center
        if rotation_offset.length > 1e-6:  # Check if there's meaningful rotation
            # The rotation happens around the solid center (initial position)
            rotation_center = self.initial_solid_center
            
            # Calculate the wire position relative to the rotation center
            relative_wire_position = wire_position - rotation_center
            
            # Apply the rotation to the relative position
            # Use rotation matrices to properly rotate the vector
            
            # Convert degrees to radians
            rx_rad = math.radians(rotation_offset.X)
            ry_rad = math.radians(rotation_offset.Y) 
            rz_rad = math.radians(rotation_offset.Z)
            
            # Apply Z rotation first (most common case)
            x, y, z = relative_wire_position.X, relative_wire_position.Y, relative_wire_position.Z
            
            if abs(rotation_offset.Z) > 1e-6:
                cos_z, sin_z = math.cos(rz_rad), math.sin(rz_rad)
                new_x = x * cos_z - y * sin_z
                new_y = x * sin_z + y * cos_z
                x, y = new_x, new_y
            
            if abs(rotation_offset.Y) > 1e-6:
                cos_y, sin_y = math.cos(ry_rad), math.sin(ry_rad)
                new_x = x * cos_y + z * sin_y
                new_z = -x * sin_y + z * cos_y
                x, z = new_x, new_z
                
            if abs(rotation_offset.X) > 1e-6:
                cos_x, sin_x = math.cos(rx_rad), math.sin(rx_rad)
                new_y = y * cos_x - z * sin_x
                new_z = y * sin_x + z * cos_x
                y, z = new_y, new_z
            
            rotated_relative_position = Vector(x, y, z)
            
            # Debug: print the rotation transformation (uncomment for debugging)
            # print(f"Relative wire position: {relative_wire_position}")
            # print(f"Rotated relative position: {rotated_relative_position}")
            
            # Calculate the final wire position after rotation
            rotated_wire_position = rotation_center + rotated_relative_position
            
            # Apply rotation to the plane orientation as well
            plane = plane.rotated((rotation_offset.X, rotation_offset.Y, rotation_offset.Z))
            
            # The target position includes both rotation and movement
            target_position = rotated_wire_position + movement_offset
        else:
            # No rotation, just apply movement
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
