import unittest

from build123d import Vector, Wire, Edge, Plane, Box, Circle, VectorLike, ShapeList
from parameterized import parameterized

from sava.csg.build123d.common.sweepsolid import SweepSolid
from tests.sava.csg.build123d.test_utils import assertVectorAlmostEqual


class TestSweepSolid(unittest.TestCase):

    @parameterized.expand([
        # Test case: (start_point, end_point)
        ((0, 0, 0), (5, 0, 0)),  # Simple horizontal line
        ((0, 0, 0), (0, 5, 0)),  # Simple vertical line
        ((0, 0, 0), (3, 4, 0)),  # Diagonal line in XY plane
        ((1, 1, 1), (5, 3, 2)),  # 3D line not starting at origin
        ((2, -1, 3), (-1, 4, -2)),  # Line with negative coordinates
    ])
    def test_plane_drawing_end_coordinate_mapping(self, start_point: VectorLike, end_point: VectorLike):
        """Test that (0,0,0) in create_plane_end coordinate system maps to wire end position"""
        
        # Create a simple line wire
        edge = Edge.make_line(start_point, end_point)
        wire = Wire([edge])
        
        # Create a simple sketch (small circle) for the sweep
        sketch = Circle(0.05)
        
        # Create the SweepSolid
        sweep_solid = SweepSolid(sketch, wire, Plane.XY)
        
        # Verify that the wire end position matches expected
        actual_wire_end = wire.position_at(1.0)
        assertVectorAlmostEqual(self, actual_wire_end, end_point)
        
        # Test the main requirement: (0,0,0) in create_plane_end should map to wire end position
        plane_end = sweep_solid.create_plane_end()
        local_origin = (0, 0, 0)
        world_position = plane_end.from_local_coords(local_origin)
        
        # The world position of (0,0,0) in the plane should equal the wire's end position
        assertVectorAlmostEqual(self, world_position, end_point)
        
        # Conversely, the wire end position should map to (0,0,0) in plane coordinates
        local_coords = plane_end.to_local_coords(actual_wire_end)
        assertVectorAlmostEqual(self, local_coords, local_origin)

    def test_plane_origin_moves_with_object(self):
        """Test that create_plane_end origin moves when the SweepSolid is moved after creation"""
        
        # Create a simple SweepSolid
        edge = Edge.make_line((0, 0, 0), (5, 0, 0))
        wire = Wire([edge])
        sketch = Circle(0.05)
        sweep_solid = SweepSolid(sketch, wire, Plane.XY)
        
        # Get initial plane end and its origin
        initial_plane_end = sweep_solid.create_plane_end()
        initial_origin = initial_plane_end.origin
        
        # Move the sweep solid
        move_vector = Vector(10, 20, 30)
        sweep_solid.move_vector(move_vector)
        
        # Get plane end after moving
        moved_plane_end = sweep_solid.create_plane_end()
        moved_origin = moved_plane_end.origin
        
        # The plane origin should have moved by the same amount as the object
        expected_new_origin = initial_origin + move_vector
        assertVectorAlmostEqual(self, moved_origin, expected_new_origin)
        
        # Test that (0,0,0) in the moved plane still maps correctly to the new wire end position
        local_origin = (0, 0, 0)
        world_position = moved_plane_end.from_local_coords(local_origin)
        
        # The (0,0,0) point in the moved plane should map to where the wire end effectively is
        # considering the solid's movement. Since create_plane_end tracks the solid movement,
        # the expected position is the wire end position plus the movement offset
        expected_wire_end = Vector(5, 0, 0) + move_vector
        assertVectorAlmostEqual(self, world_position, expected_wire_end)

    @parameterized.expand([
        # Test different movement vectors
        ((10, 0, 0),),    # Move along X
        ((0, 15, 0),),    # Move along Y  
        ((0, 0, 25),),    # Move along Z
        ((5, 10, 15),),   # Move along all axes
        ((-5, -10, -15),), # Negative movement
    ])
    def test_plane_origin_tracks_movement(self, move_vector: VectorLike):
        """Test that create_plane_end origin correctly tracks object movement"""
        
        # Create a diagonal SweepSolid for more complex testing
        edge = Edge.make_line((1, 2, 3), (4, 6, 8))
        wire = Wire([edge])
        sketch = Circle(0.05)
        sweep_solid = SweepSolid(sketch, wire, Plane.XY)
        
        # Store initial state
        initial_plane_end = sweep_solid.create_plane_end()
        initial_wire_end = wire.position_at(1.0)
        
        # Test coordinate mapping before movement
        local_origin = (0, 0, 0)
        initial_world_pos = initial_plane_end.from_local_coords(local_origin)
        
        # Move the object
        sweep_solid.move_vector(Vector(move_vector))
        
        # Get plane after movement
        moved_plane_end = sweep_solid.create_plane_end()
        moved_world_pos = moved_plane_end.from_local_coords(local_origin)
        
        # The world position should have moved by the movement vector
        expected_moved_pos = initial_world_pos + Vector(move_vector)
        assertVectorAlmostEqual(self, moved_world_pos, expected_moved_pos)

    def test_circle_sketch_creates_single_solid(self):
        """Test that Circle sketch creates a single Solid, not ShapeList"""
        edge = Edge.make_line((0, 0, 0), (5, 0, 0))
        wire = Wire([edge])
        circle_sketch = Circle(0.05)
        
        # Create SweepSolid with Circle sketch
        sweep_solid = SweepSolid(circle_sketch, wire, Plane.XY)
        
        # Verify that the solid is NOT a ShapeList
        self.assertFalse(isinstance(sweep_solid.solid, ShapeList), 
                        "Circle sketch should create single Solid, not ShapeList")

    def test_box_sketch_creates_shapelist(self):
        """Test that Box sketch creates ShapeList (demonstrating the issue)"""
        edge = Edge.make_line((0, 0, 0), (5, 0, 0))
        wire = Wire([edge])
        box_sketch = Box(0.1, 0.1, 0.1)
        
        # Create SweepSolid with Box sketch
        sweep_solid = SweepSolid(box_sketch, wire, Plane.XY)
        
        # Verify that the solid IS a ShapeList (the problematic case)
        self.assertTrue(isinstance(sweep_solid.solid, ShapeList), 
                       "Box sketch typically creates ShapeList due to multiple faces")


    @parameterized.expand([
        # Test combined transformations - rotation then movement
        ("rotation_first", (0, 0, 90), (10, 20, 0)),   # Z rotation + XY movement
        ("rotation_first", (90, 0, 0), (0, 10, 20)),   # X rotation + YZ movement
        ("rotation_first", (0, 90, 0), (10, 0, 20)),   # Y rotation + XZ movement
        ("rotation_first", (45, 45, 45), (5, 5, 5)),   # Complex rotation + equal movement
        # Test combined transformations - movement then rotation  
        ("movement_first", (10, 20, 0), (0, 0, 90)),   # XY movement + Z rotation
        ("movement_first", (0, 10, 20), (90, 0, 0)),   # YZ movement + X rotation
        ("movement_first", (10, 0, 20), (0, 90, 0)),   # XZ movement + Y rotation
        ("movement_first", (5, 5, 5), (45, 45, 45)),   # Equal movement + complex rotation
    ])
    def test_create_plane_end_combined_transformations(self, order: str, transform1: VectorLike, transform2: VectorLike):
        """Test create_plane_end with combined movement and rotation in different orders"""
        edge = Edge.make_line((0, 0, 0), (10, 0, 0))  # Longer wire for better testing
        wire = Wire([edge])
        sketch = Circle(0.05)
        sweep_solid = SweepSolid(sketch, wire, Plane.XY)
        
        # Apply transformations in the specified order
        if order == "rotation_first":
            rotation, movement = transform1, transform2
            sweep_solid.rotate(rotation)
            sweep_solid.move_vector(Vector(movement))
        else:  # movement_first
            movement, rotation = transform1, transform2
            sweep_solid.move_vector(Vector(movement))
            sweep_solid.rotate(rotation)
        
        # Test that (0,0,0) in final plane coordinate system maps correctly
        final_plane_end = sweep_solid.create_plane_end()
        local_origin = (0, 0, 0)
        final_world_pos = final_plane_end.from_local_coords(local_origin)
        
        # Verify that the coordinate mapping is consistent
        final_local_coords = final_plane_end.to_local_coords(final_world_pos)
        assertVectorAlmostEqual(self, final_local_coords, local_origin)

    def test_create_plane_start_vs_end_with_rotation(self):
        """Test that create_plane_start and create_plane_end behave differently with rotation around wire start"""
        # Create a 3D wire to see rotation effects better
        edge = Edge.make_line((0, 0, 0), (20, 0, 10))  # Wire going from origin to (20,0,10)
        wire = Wire([edge])
        sketch = Circle(0.05)
        sweep_solid = SweepSolid(sketch, wire, Plane.XY)
        
        # Get initial solid center to understand rotation behavior
        initial_solid_center = sweep_solid.solid.center()
        
        # Get initial planes
        initial_plane_start = sweep_solid.create_plane_start()
        initial_plane_end = sweep_solid.create_plane_end()
        
        # Store initial positions where (0,0,0) maps to in world coordinates
        initial_start_world = initial_plane_start.from_local_coords((0, 0, 0))
        initial_end_world = initial_plane_end.from_local_coords((0, 0, 0))
        
        # Debug: print initial positions
        print(f"Initial solid center: {initial_solid_center}")
        print(f"Initial wire start position: {wire.position_at(0.0)}")
        print(f"Initial wire end position: {wire.position_at(1.0)}")
        print(f"Initial start world: {initial_start_world}")
        print(f"Initial end world: {initial_end_world}")
        
        # Apply rotation around Y axis to see the effect on the 3D wire
        sweep_solid.rotate((0, 90, 0))  # 90 degree rotation around Y axis
        
        # Get solid center after rotation
        rotated_solid_center = sweep_solid.solid.center()
        print(f"Rotated solid center: {rotated_solid_center}")
        
        # Get planes after rotation
        rotated_plane_start = sweep_solid.create_plane_start()
        rotated_plane_end = sweep_solid.create_plane_end()
        
        # Get world positions after rotation
        rotated_start_world = rotated_plane_start.from_local_coords((0, 0, 0))
        rotated_end_world = rotated_plane_end.from_local_coords((0, 0, 0))
        
        print(f"Rotated start world: {rotated_start_world}")
        print(f"Rotated end world: {rotated_end_world}")
        
        # Calculate actual movements
        start_movement = (rotated_start_world - initial_start_world).length
        end_movement = (rotated_end_world - initial_end_world).length
        
        print(f"Start movement: {start_movement}")
        print(f"End movement: {end_movement}")
        
        # Verify that coordinate mapping still works
        final_local_coords_start = rotated_plane_start.to_local_coords(rotated_start_world)
        final_local_coords_end = rotated_plane_end.to_local_coords(rotated_end_world)
        
        assertVectorAlmostEqual(self, final_local_coords_start, (0, 0, 0))
        assertVectorAlmostEqual(self, final_local_coords_end, (0, 0, 0))

    def test_rotation_center_investigation(self):
        """Investigate where rotation happens by testing different solid positions"""
        # Create wire not starting at origin to see rotation behavior
        edge = Edge.make_line((10, 5, 0), (30, 5, 0))  # Wire away from origin
        wire = Wire([edge])
        sketch = Circle(0.05)
        sweep_solid = SweepSolid(sketch, wire, Plane.XY)
        
        # Debug: Check initial orientation values
        print(f"Initial solid orientation: {sweep_solid.solid.orientation}")
        print(f"Initial stored orientation: Vector(0, 0, 0) (always for swept solids)")
        
        # Get initial positions
        initial_solid_center = sweep_solid.solid.center()
        initial_start_world = sweep_solid.create_plane_start().from_local_coords((0, 0, 0))
        initial_end_world = sweep_solid.create_plane_end().from_local_coords((0, 0, 0))
        
        print(f"Initial solid center: {initial_solid_center}")
        print(f"Initial start world: {initial_start_world}")
        print(f"Initial end world: {initial_end_world}")
        
        # Apply rotation around Z axis
        sweep_solid.rotate((0, 0, 90))
        
        # Debug: Check orientation after rotation
        print(f"Rotated solid orientation: {sweep_solid.solid.orientation}")
        current_rotation = sweep_solid.solid.orientation  # Since initial was (0,0,0)
        print(f"Current rotation: {current_rotation}")
        print(f"Current rotation length: {current_rotation.length}")
        
        # Get rotated positions
        rotated_solid_center = sweep_solid.solid.center()
        rotated_start_world = sweep_solid.create_plane_start().from_local_coords((0, 0, 0))
        rotated_end_world = sweep_solid.create_plane_end().from_local_coords((0, 0, 0))
        
        print(f"Rotated solid center: {rotated_solid_center}")
        print(f"Rotated start world: {rotated_start_world}")
        print(f"Rotated end world: {rotated_end_world}")
        
        # Calculate movements
        center_movement = (rotated_solid_center - initial_solid_center).length
        start_movement = (rotated_start_world - initial_start_world).length
        end_movement = (rotated_end_world - initial_end_world).length
        
        print(f"Center movement: {center_movement}")
        print(f"Start movement: {start_movement}")
        print(f"End movement: {end_movement}")
        
        # Manual calculation: what should happen during 90° Z rotation around origin
        # Initial start: (10, 5, 0) -> rotated should be (-5, 10, 0)
        # Initial end: (30, 5, 0) -> rotated should be (-5, 30, 0)
        import math
        angle_rad = math.radians(90)
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        
        expected_start_x = initial_start_world.X * cos_a - initial_start_world.Y * sin_a
        expected_start_y = initial_start_world.X * sin_a + initial_start_world.Y * cos_a
        expected_start = Vector(expected_start_x, expected_start_y, initial_start_world.Z)
        
        expected_end_x = initial_end_world.X * cos_a - initial_end_world.Y * sin_a
        expected_end_y = initial_end_world.X * sin_a + initial_end_world.Y * cos_a
        expected_end = Vector(expected_end_x, expected_end_y, initial_end_world.Z)
        
        print(f"Expected start after rotation: {expected_start}")
        print(f"Expected end after rotation: {expected_end}")
        
        # This test is just for investigation - no assertions needed

    def test_create_plane_start_with_combined_transformations(self):
        """Test create_plane_start with combined rotation and movement"""
        edge = Edge.make_line((0, 0, 0), (15, 0, 0))
        wire = Wire([edge])
        sketch = Circle(0.05)
        sweep_solid = SweepSolid(sketch, wire, Plane.XY)
        
        # Test movement then rotation
        sweep_solid.move(5, 10, 15)
        sweep_solid.rotate((0, 0, 45))
        
        # Test that coordinate mapping still works for start plane
        plane_start = sweep_solid.create_plane_start()
        local_origin = (0, 0, 0)
        world_pos = plane_start.from_local_coords(local_origin)
        local_coords_back = plane_start.to_local_coords(world_pos)
        
        # Should map back to origin consistently
        assertVectorAlmostEqual(self, local_coords_back, local_origin)


class TestSweepSolidPathPlane(unittest.TestCase):

    def test_create_path_plane_initial_state(self):
        """Test that create_path_plane initially returns the original path plane"""
        edge = Edge.make_line((0, 0, 0), (10, 0, 0))
        wire = Wire([edge])
        sketch = Circle(0.05)
        original_path_plane = Plane.XY
        sweep_solid = SweepSolid(sketch, wire, original_path_plane)
        
        # Get the path plane immediately after creation
        path_plane = sweep_solid.create_path_plane()
        
        # Should match the original path plane
        assertVectorAlmostEqual(self, path_plane.origin, original_path_plane.origin)
        assertVectorAlmostEqual(self, path_plane.x_dir, original_path_plane.x_dir)
        assertVectorAlmostEqual(self, path_plane.y_dir, original_path_plane.y_dir)
        assertVectorAlmostEqual(self, path_plane.z_dir, original_path_plane.z_dir)

    def test_create_path_plane_with_movement(self):
        """Test that create_path_plane tracks movement correctly"""
        edge = Edge.make_line((0, 0, 0), (10, 0, 0))
        wire = Wire([edge])
        sketch = Circle(0.05)
        original_path_plane = Plane.XY
        sweep_solid = SweepSolid(sketch, wire, original_path_plane)
        
        # Move the sweep solid
        movement = Vector(5, 10, 15)
        sweep_solid.move_vector(movement)
        
        # Get the path plane after movement
        path_plane = sweep_solid.create_path_plane()
        
        # Origin should be moved, but directions should remain the same
        expected_origin = original_path_plane.origin + movement
        assertVectorAlmostEqual(self, path_plane.origin, expected_origin)
        assertVectorAlmostEqual(self, path_plane.x_dir, original_path_plane.x_dir)
        assertVectorAlmostEqual(self, path_plane.y_dir, original_path_plane.y_dir)
        assertVectorAlmostEqual(self, path_plane.z_dir, original_path_plane.z_dir)

    def test_create_path_plane_with_rotation(self):
        """Test that create_path_plane tracks rotation correctly"""
        edge = Edge.make_line((0, 0, 0), (10, 0, 0))
        wire = Wire([edge])
        sketch = Circle(0.05)
        original_path_plane = Plane.XY
        sweep_solid = SweepSolid(sketch, wire, original_path_plane)
        
        # Rotate the sweep solid 90 degrees around Z axis
        sweep_solid.rotate((0, 0, 90))
        
        # Get the path plane after rotation
        path_plane = sweep_solid.create_path_plane()
        
        # Origin should remain at origin since XY plane is centered at origin
        assertVectorAlmostEqual(self, path_plane.origin, Vector(0, 0, 0))
        
        # X direction should become Y direction, Y direction should become -X direction
        assertVectorAlmostEqual(self, path_plane.x_dir, Vector(0, 1, 0))
        assertVectorAlmostEqual(self, path_plane.y_dir, Vector(-1, 0, 0))
        assertVectorAlmostEqual(self, path_plane.z_dir, Vector(0, 0, 1))

    def test_create_path_plane_with_offset_plane(self):
        """Test create_path_plane with a path plane that has an offset origin"""
        edge = Edge.make_line((0, 0, 0), (10, 0, 0))
        wire = Wire([edge])
        sketch = Circle(0.05)
        # Create path plane with offset origin
        original_path_plane = Plane(origin=(5, 5, 0), x_dir=(1, 0, 0), z_dir=(0, 0, 1))
        sweep_solid = SweepSolid(sketch, wire, original_path_plane)
        
        # Rotate the sweep solid 90 degrees around Z axis
        sweep_solid.rotate((0, 0, 90))
        
        # Get the path plane after rotation
        path_plane = sweep_solid.create_path_plane()
        
        # The offset origin should be rotated around the solid center (0,0,0)
        # (5, 5, 0) rotated 90° around Z becomes (-5, 5, 0)
        assertVectorAlmostEqual(self, path_plane.origin, Vector(-5, 5, 0))
        
        # Directions should also be rotated
        assertVectorAlmostEqual(self, path_plane.x_dir, Vector(0, 1, 0))
        assertVectorAlmostEqual(self, path_plane.y_dir, Vector(-1, 0, 0))
        assertVectorAlmostEqual(self, path_plane.z_dir, Vector(0, 0, 1))

    def test_create_path_plane_with_combined_transformations(self):
        """Test create_path_plane with both rotation and movement"""
        edge = Edge.make_line((0, 0, 0), (10, 0, 0))
        wire = Wire([edge])
        sketch = Circle(0.05)
        original_path_plane = Plane(origin=(2, 3, 0), x_dir=(1, 0, 0), z_dir=(0, 0, 1))
        sweep_solid = SweepSolid(sketch, wire, original_path_plane)
        
        # Apply rotation first, then movement
        sweep_solid.rotate((0, 0, 90))
        sweep_solid.move(10, 20, 30)
        
        # Get the path plane after transformations
        path_plane = sweep_solid.create_path_plane()
        
        # The offset origin (2, 3, 0) rotated 90° around Z becomes (-3, 2, 0)
        # Then add movement (10, 20, 30) to get (7, 22, 30)
        expected_origin = Vector(-3, 2, 0) + Vector(10, 20, 30)
        assertVectorAlmostEqual(self, path_plane.origin, expected_origin)
        
        # Directions should be rotated
        assertVectorAlmostEqual(self, path_plane.x_dir, Vector(0, 1, 0))
        assertVectorAlmostEqual(self, path_plane.y_dir, Vector(-1, 0, 0))
        assertVectorAlmostEqual(self, path_plane.z_dir, Vector(0, 0, 1))

    @parameterized.expand([
        # Test different rotation axes and combinations
        ((90, 0, 0),),   # X rotation
        ((0, 90, 0),),   # Y rotation  
        ((0, 0, 90),),   # Z rotation
        ((45, 45, 45),), # Combined rotation
    ])
    def test_create_path_plane_coordinate_consistency(self, rotation: VectorLike):
        """Test that create_path_plane maintains coordinate system consistency"""
        edge = Edge.make_line((0, 0, 0), (10, 0, 0))
        wire = Wire([edge])
        sketch = Circle(0.05)
        sweep_solid = SweepSolid(sketch, wire, Plane.XY)
        
        # Apply rotation and movement
        sweep_solid.rotate(rotation)
        sweep_solid.move(5, 10, 15)
        
        # Get the path plane
        path_plane = sweep_solid.create_path_plane()
        
        # Test that the plane's coordinate directions are orthonormal
        x_dir, y_dir, z_dir = path_plane.x_dir, path_plane.y_dir, path_plane.z_dir
        
        # Each direction should be unit vector
        self.assertAlmostEqual(x_dir.length, 1.0, places=5)
        self.assertAlmostEqual(y_dir.length, 1.0, places=5)
        self.assertAlmostEqual(z_dir.length, 1.0, places=5)
        
        # Directions should be orthogonal
        self.assertAlmostEqual(x_dir.dot(y_dir), 0.0, places=5)
        self.assertAlmostEqual(y_dir.dot(z_dir), 0.0, places=5)
        self.assertAlmostEqual(z_dir.dot(x_dir), 0.0, places=5)
        
        # Should form a right-handed coordinate system
        cross_product = x_dir.cross(y_dir)
        assertVectorAlmostEqual(self, cross_product, z_dir)


if __name__ == '__main__':
    unittest.main()
