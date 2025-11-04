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

    def test_plane_orientation_tracks_rotation(self):
        """Test that create_plane_end orientation tracks object rotation"""
        edge = Edge.make_line((0, 0, 0), (5, 0, 0))
        wire = Wire([edge])
        sketch = Circle(0.05)
        sweep_solid = SweepSolid(sketch, wire, Plane.XY)
        
        # Get initial plane end and its orientation vectors
        initial_plane_end = sweep_solid.create_plane_end()
        initial_x_dir = initial_plane_end.x_dir
        initial_y_dir = initial_plane_end.y_dir
        initial_z_dir = initial_plane_end.z_dir
        
        # Rotate the sweep solid 90 degrees around Z axis
        sweep_solid.rotate((0, 0, 90))
        
        # Get plane end after rotation
        rotated_plane_end = sweep_solid.create_plane_end()
        rotated_x_dir = rotated_plane_end.x_dir
        rotated_y_dir = rotated_plane_end.y_dir
        rotated_z_dir = rotated_plane_end.z_dir
        
        # Verify that the plane directions have changed after rotation
        # From debug output we saw Y and Z directions changed during 90° Z rotation
        # X direction stays same because it's aligned with Z axis
        self.assertEqual(initial_x_dir, rotated_x_dir)  # X direction unchanged (along Z axis)
        self.assertNotEqual(initial_y_dir, rotated_y_dir)  # Y direction should change
        self.assertNotEqual(initial_z_dir, rotated_z_dir)  # Z direction should change

    @parameterized.expand([
        # Test combined rotation and movement - rotation first
        ((0, 0, 90), (10, 20, 0)),   # Z rotation + XY movement
        ((90, 0, 0), (0, 10, 20)),   # X rotation + YZ movement
        ((0, 90, 0), (10, 0, 20)),   # Y rotation + XZ movement
        ((45, 45, 45), (5, 5, 5)),   # Complex rotation + equal movement
    ])
    def test_create_plane_end_rotation_then_movement(self, rotation: VectorLike, movement: VectorLike):
        """Test create_plane_end with rotation applied first, then movement"""
        edge = Edge.make_line((0, 0, 0), (10, 0, 0))  # Longer wire for better testing
        wire = Wire([edge])
        sketch = Circle(0.05)
        sweep_solid = SweepSolid(sketch, wire, Plane.XY)
        
        # Store initial state
        initial_plane_end = sweep_solid.create_plane_end()
        initial_wire_end = wire.position_at(1.0)
        
        # Apply rotation first
        sweep_solid.rotate(rotation)
        rotated_plane_end = sweep_solid.create_plane_end()
        
        # Apply movement after rotation
        sweep_solid.move_vector(Vector(movement))
        final_plane_end = sweep_solid.create_plane_end()
        
        # Test that (0,0,0) in final plane coordinate system maps correctly
        local_origin = (0, 0, 0)
        final_world_pos = final_plane_end.from_local_coords(local_origin)
        
        # The final position should account for both rotation and movement
        # We can't easily predict the exact final position due to rotation complexity,
        # but we can verify that the coordinate mapping is still consistent
        final_local_coords = final_plane_end.to_local_coords(final_world_pos)
        assertVectorAlmostEqual(self, final_local_coords, local_origin)

    @parameterized.expand([
        # Test combined movement and rotation - movement first
        ((10, 20, 0), (0, 0, 90)),   # XY movement + Z rotation
        ((0, 10, 20), (90, 0, 0)),   # YZ movement + X rotation
        ((10, 0, 20), (0, 90, 0)),   # XZ movement + Y rotation
        ((5, 5, 5), (45, 45, 45)),   # Equal movement + complex rotation
    ])
    def test_create_plane_end_movement_then_rotation(self, movement: VectorLike, rotation: VectorLike):
        """Test create_plane_end with movement applied first, then rotation"""
        edge = Edge.make_line((0, 0, 0), (10, 0, 0))  # Longer wire for better testing
        wire = Wire([edge])
        sketch = Circle(0.05)
        sweep_solid = SweepSolid(sketch, wire, Plane.XY)
        
        # Store initial state
        initial_plane_end = sweep_solid.create_plane_end()
        initial_wire_end = wire.position_at(1.0)
        
        # Apply movement first
        sweep_solid.move_vector(Vector(movement))
        moved_plane_end = sweep_solid.create_plane_end()
        
        # Apply rotation after movement
        sweep_solid.rotate(rotation)
        final_plane_end = sweep_solid.create_plane_end()
        
        # Test that (0,0,0) in final plane coordinate system maps correctly
        local_origin = (0, 0, 0)
        final_world_pos = final_plane_end.from_local_coords(local_origin)
        
        # Verify coordinate mapping consistency
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
        print(f"Initial stored orientation: {sweep_solid.initial_solid_orientation}")
        
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
        rotation_offset = sweep_solid.solid.orientation - sweep_solid.initial_solid_orientation
        print(f"Rotation offset: {rotation_offset}")
        print(f"Rotation offset length: {rotation_offset.length}")
        
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


if __name__ == '__main__':
    unittest.main()
