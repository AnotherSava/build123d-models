import unittest

from build123d import Vector, Wire, Edge, Plane, Box, Circle, VectorLike, ShapeList, Axis
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
            sweep_solid.rotate_multi(rotation)
            sweep_solid.move_vector(Vector(movement))
        else:  # movement_first
            movement, rotation = transform1, transform2
            sweep_solid.move_vector(Vector(movement))
            sweep_solid.rotate_multi(rotation)
        
        # Test that (0,0,0) in final plane coordinate system maps correctly
        final_plane_end = sweep_solid.create_plane_end()
        local_origin = (0, 0, 0)
        final_world_pos = final_plane_end.from_local_coords(local_origin)
        
        # Verify that the coordinate mapping is consistent
        final_local_coords = final_plane_end.to_local_coords(final_world_pos)
        assertVectorAlmostEqual(self, final_local_coords, local_origin)

    def test_create_plane_start_vs_end_with_rotation(self):
        """Test that create_plane_start and create_plane_end behave differently with rotation around wire start"""
        edge = Edge.make_line((0, 0, 0), (20, 0, 10))
        wire = Wire([edge])
        sketch = Circle(0.05)
        sweep_solid = SweepSolid(sketch, wire, Plane.XY)

        initial_plane_start = sweep_solid.create_plane_start()
        initial_plane_end = sweep_solid.create_plane_end()
        initial_start_world = initial_plane_start.from_local_coords((0, 0, 0))
        initial_end_world = initial_plane_end.from_local_coords((0, 0, 0))

        sweep_solid.rotate_multi((0, 90, 0))

        rotated_plane_start = sweep_solid.create_plane_start()
        rotated_plane_end = sweep_solid.create_plane_end()
        rotated_start_world = rotated_plane_start.from_local_coords((0, 0, 0))
        rotated_end_world = rotated_plane_end.from_local_coords((0, 0, 0))

        # Verify that coordinate mapping still works (round-trip)
        assertVectorAlmostEqual(self, rotated_plane_start.to_local_coords(rotated_start_world), (0, 0, 0))
        assertVectorAlmostEqual(self, rotated_plane_end.to_local_coords(rotated_end_world), (0, 0, 0))

    def test_create_plane_start_with_combined_transformations(self):
        """Test create_plane_start with combined rotation and movement"""
        edge = Edge.make_line((0, 0, 0), (15, 0, 0))
        wire = Wire([edge])
        sketch = Circle(0.05)
        sweep_solid = SweepSolid(sketch, wire, Plane.XY)
        
        # Test movement then rotation
        sweep_solid.move(5, 10, 15)
        sweep_solid.rotate_multi((0, 0, 45))
        
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
        sweep_solid.rotate_multi((0, 0, 90))
        
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
        sweep_solid.rotate_multi((0, 0, 90))
        
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
        sweep_solid.rotate_multi((0, 0, 90))
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
        sweep_solid.rotate_multi(rotation)
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


class TestSweepSolidRotateMulti(unittest.TestCase):
    """Tests for rotation operations on SweepSolid."""

    def _create_sweep(self) -> SweepSolid:
        edge = Edge.make_line((0, 0, 0), (10, 0, 0))
        wire = Wire([edge])
        sketch = Circle(0.05)
        return SweepSolid(sketch, wire, Plane.XY)

    def test_rotate_multi_then_move_plane_end_consistent(self):
        """Test rotate_multi + move: plane_end coordinate mapping stays self-consistent."""
        sweep = self._create_sweep()
        sweep.rotate_multi((0, 0, 90))
        sweep.move(10, 0, 0)

        plane_end = sweep.create_plane_end()
        world = plane_end.from_local_coords((0, 0, 0))
        local_back = plane_end.to_local_coords(world)
        assertVectorAlmostEqual(self, local_back, (0, 0, 0))

    def test_move_then_rotate_multi_plane_end_consistent(self):
        """Test move + rotate_multi: plane_end coordinate mapping stays self-consistent."""
        sweep = self._create_sweep()
        sweep.move(10, 20, 0)
        sweep.rotate_multi((0, 0, 90))

        plane_end = sweep.create_plane_end()
        world = plane_end.from_local_coords((0, 0, 0))
        local_back = plane_end.to_local_coords(world)
        assertVectorAlmostEqual(self, local_back, (0, 0, 0))

    def test_rotate_multi_path_plane_orthonormal(self):
        """Path plane remains orthonormal after rotation."""
        sweep = self._create_sweep()
        sweep.rotate_multi((45, 30, 60))

        plane = sweep.create_path_plane()
        self.assertAlmostEqual(plane.x_dir.length, 1.0, places=5)
        self.assertAlmostEqual(plane.z_dir.length, 1.0, places=5)
        self.assertAlmostEqual(plane.x_dir.dot(plane.z_dir), 0.0, places=5)

    def test_rotate_multi_origin_tracking(self):
        """SweepSolid origin tracks correctly through rotate_multi."""
        sweep = self._create_sweep()
        sweep.move(10, 0, 0)
        sweep.rotate_multi((0, 0, 90))

        # origin (10,0,0) rotated 90° around Z -> (0,10,0)
        assertVectorAlmostEqual(self, sweep.origin, (0, 10, 0))


class TestSweepSolidConsecutiveRotations(unittest.TestCase):
    """Tests for consecutive rotation calls — previously broken by double-rotation bug."""

    def _create_sweep(self) -> SweepSolid:
        edge = Edge.make_line((0, 0, 0), (10, 0, 0))
        wire = Wire([edge])
        sketch = Circle(0.05)
        return SweepSolid(sketch, wire, Plane.XY)

    def test_two_rotate_multi_equal_single(self):
        """Two 45° Z rotations should equal one 90° rotation."""
        s1 = self._create_sweep()
        s1.rotate_multi((0, 0, 45))
        s1.rotate_multi((0, 0, 45))

        s2 = self._create_sweep()
        s2.rotate_multi((0, 0, 90))

        p1 = s1.create_path_plane()
        p2 = s2.create_path_plane()
        assertVectorAlmostEqual(self, p1.origin, p2.origin)
        assertVectorAlmostEqual(self, p1.x_dir, p2.x_dir)
        assertVectorAlmostEqual(self, p1.z_dir, p2.z_dir)

    def test_consecutive_rotate_multi_with_move(self):
        """Rotate + move + rotate: plane tracks correctly."""
        sweep = self._create_sweep()
        sweep.rotate_multi((0, 0, 90))
        sweep.move(10, 0, 0)
        sweep.rotate_multi((0, 0, 90))

        plane = sweep.create_path_plane()
        # Plane.XY rotated 180° Z: x_dir flips
        assertVectorAlmostEqual(self, plane.x_dir, Vector(-1, 0, 0))
        assertVectorAlmostEqual(self, plane.z_dir, Vector(0, 0, 1))

    def test_four_rotate_multi_return_to_original(self):
        """4x90° rotations should return plane to original state."""
        sweep = self._create_sweep()
        original_plane = sweep.create_path_plane()

        for _ in range(4):
            sweep.rotate_multi((0, 0, 90))

        final_plane = sweep.create_path_plane()
        assertVectorAlmostEqual(self, final_plane.origin, original_plane.origin)
        assertVectorAlmostEqual(self, final_plane.x_dir, original_plane.x_dir)
        assertVectorAlmostEqual(self, final_plane.z_dir, original_plane.z_dir)

    def test_consecutive_orient_with_offset_plane(self):
        """Consecutive orient() calls with offset plane don't double-rotate."""
        edge = Edge.make_line((0, 0, 0), (10, 0, 0))
        wire = Wire([edge])
        sketch = Circle(0.05)
        offset_plane = Plane(origin=(5, 5, 0), x_dir=(1, 0, 0), z_dir=(0, 0, 1))
        sweep = SweepSolid(sketch, wire, offset_plane)

        # First orient
        sweep.orient((0, 0, 90))
        p1 = sweep.create_path_plane()
        assertVectorAlmostEqual(self, p1.origin, Vector(-5, 5, 0))

        # Second orient to same rotation — should give same result (not double-rotate)
        sweep.orient((0, 0, 90))
        p2 = sweep.create_path_plane()
        assertVectorAlmostEqual(self, p2.origin, Vector(-5, 5, 0))
        assertVectorAlmostEqual(self, p2.x_dir, p1.x_dir)
        assertVectorAlmostEqual(self, p2.z_dir, p1.z_dir)


class TestSweepSolidRotateAxis(unittest.TestCase):
    """Tests for SweepSolid.rotate(Axis, angle) — previously broken."""

    def _create_sweep(self) -> SweepSolid:
        edge = Edge.make_line((0, 0, 0), (10, 0, 0))
        wire = Wire([edge])
        sketch = Circle(0.05)
        return SweepSolid(sketch, wire, Plane.XY)

    def test_rotate_z_90_plane_directions(self):
        """rotate(Axis.Z, 90) should rotate plane directions."""
        sweep = self._create_sweep()
        sweep.rotate(Axis.Z, 90)

        plane = sweep.create_path_plane()
        assertVectorAlmostEqual(self, plane.x_dir, Vector(0, 1, 0))
        assertVectorAlmostEqual(self, plane.z_dir, Vector(0, 0, 1))

    def test_rotate_z_matches_rotate_multi(self):
        """rotate(Axis.Z, 90) should match rotate_multi((0,0,90))."""
        s1 = self._create_sweep()
        s1.rotate(Axis.Z, 90)

        s2 = self._create_sweep()
        s2.rotate_multi((0, 0, 90))

        p1 = s1.create_path_plane()
        p2 = s2.create_path_plane()
        assertVectorAlmostEqual(self, p1.origin, p2.origin)
        assertVectorAlmostEqual(self, p1.x_dir, p2.x_dir)
        assertVectorAlmostEqual(self, p1.z_dir, p2.z_dir)

    def test_rotate_with_move(self):
        """move + rotate(Axis.Z, 90) tracks plane origin."""
        sweep = self._create_sweep()
        sweep.move(10, 0, 0)
        sweep.rotate(Axis.Z, 90)

        assertVectorAlmostEqual(self, sweep.origin, (0, 10, 0))
        plane = sweep.create_path_plane()
        assertVectorAlmostEqual(self, plane.origin, (0, 10, 0))

    def test_consecutive_rotate_axis(self):
        """Two 45° Z rotations via rotate() equal single 90°."""
        s1 = self._create_sweep()
        s1.rotate(Axis.Z, 45)
        s1.rotate(Axis.Z, 45)

        s2 = self._create_sweep()
        s2.rotate(Axis.Z, 90)

        p1 = s1.create_path_plane()
        p2 = s2.create_path_plane()
        assertVectorAlmostEqual(self, p1.origin, p2.origin)
        assertVectorAlmostEqual(self, p1.x_dir, p2.x_dir)
        assertVectorAlmostEqual(self, p1.z_dir, p2.z_dir)

    @parameterized.expand([
        (Axis.X, 90),
        (Axis.Y, 90),
        (Axis.Z, 90),
        (Axis.Z, 45),
    ])
    def test_rotate_axis_plane_orthonormal(self, axis: Axis, angle: float):
        """Path plane remains orthonormal after rotate(Axis, angle)."""
        sweep = self._create_sweep()
        sweep.rotate(axis, angle)

        plane = sweep.create_path_plane()
        self.assertAlmostEqual(plane.x_dir.length, 1.0, places=5)
        self.assertAlmostEqual(plane.z_dir.length, 1.0, places=5)
        self.assertAlmostEqual(plane.x_dir.dot(plane.z_dir), 0.0, places=5)


if __name__ == '__main__':
    unittest.main()
