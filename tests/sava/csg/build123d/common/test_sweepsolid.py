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


if __name__ == '__main__':
    unittest.main()
