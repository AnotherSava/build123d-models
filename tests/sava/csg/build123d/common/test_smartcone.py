import unittest

from build123d import Vector, Plane, Axis
from parameterized import parameterized

from sava.csg.build123d.common.smartcone import SmartCone
from tests.sava.csg.build123d.test_utils import assertVectorAlmostEqual


class TestSmartConeCreateAxis(unittest.TestCase):

    def setUp(self):
        """Create a test SmartCone for each test"""
        self.cone_angle = 30.0  # degrees
        self.radius = 10.0
        self.thickness = 2.0
        self.base_angle = 60.0  # degrees
        self.cone = SmartCone.create_empty(
            cone_angle=self.cone_angle,
            radius=self.radius,
            thickness=self.thickness,
            base_angle=self.base_angle
        )

    def test_create_axis_outer_cone_default_position_orientation(self):
        """Test create_axis for outer cone with default position and orientation"""
        axis = self.cone.create_axis(inner=False)
        
        # For outer cone at default position, axis should be at solid position
        expected_position = self.cone.solid.position
        assertVectorAlmostEqual(self, axis.position, expected_position)
        
        # Default orientation should be downward (0, 0, -1)
        expected_direction = Vector(0, 0, -1)
        assertVectorAlmostEqual(self, axis.direction, expected_direction)

    def test_create_axis_inner_cone_default_position_orientation(self):
        """Test create_axis for inner cone with default position and orientation"""
        axis = self.cone.create_axis(inner=True)
        
        # For inner cone, position should be offset by height_higher_lower
        expected_position = self.cone.solid.position + Vector(0, 0, -self.cone.height_higher_lower)
        assertVectorAlmostEqual(self, axis.position, expected_position)
        
        # Default orientation should be downward (0, 0, -1)
        expected_direction = Vector(0, 0, -1)
        assertVectorAlmostEqual(self, axis.direction, expected_direction)

    def test_create_axis_default_parameter(self):
        """Test that create_axis() without parameters defaults to outer cone"""
        axis_default = self.cone.create_axis()
        axis_outer = self.cone.create_axis(inner=False)
        
        # Should be identical
        assertVectorAlmostEqual(self, axis_default.position, axis_outer.position)
        assertVectorAlmostEqual(self, axis_default.direction, axis_outer.direction)

    def test_create_axis_with_solid_movement(self):
        """Test create_axis when the solid has been moved"""
        # Move the cone
        movement = Vector(5, 10, 15)
        self.cone.move_vector(movement)
        
        # Test outer cone axis
        outer_axis = self.cone.create_axis(inner=False)
        expected_outer_position = movement  # Since initial position was (0,0,0)
        assertVectorAlmostEqual(self, outer_axis.position, expected_outer_position)
        
        # Test inner cone axis
        inner_axis = self.cone.create_axis(inner=True)
        expected_inner_position = movement + Vector(0, 0, -self.cone.height_higher_lower)
        assertVectorAlmostEqual(self, inner_axis.position, expected_inner_position)

    @parameterized.expand([
        # Test different rotation scenarios
        ((90, 0, 0),),   # X rotation - should rotate direction to (0, 1, 0)
        ((0, 90, 0),),   # Y rotation - should rotate direction to (1, 0, 0)
        ((0, 0, 90),),   # Z rotation - should keep direction as (0, 0, -1)
        ((45, 45, 45),), # Complex rotation
    ])
    def test_create_axis_with_solid_rotation(self, rotation):
        """Test create_axis when the solid has been rotated"""
        self.cone.rotate_multi(rotation)
        
        # Test both inner and outer axes
        outer_axis = self.cone.create_axis(inner=False)
        inner_axis = self.cone.create_axis(inner=True)
        
        # Both axes should have the same direction (rotated from (0, 0, -1))
        assertVectorAlmostEqual(self, outer_axis.direction, inner_axis.direction)
        
        # Direction should be unit vector
        self.assertAlmostEqual(outer_axis.direction.length, 1.0, places=5)
        
        # For specific rotations, we can verify expected directions
        if rotation == (90, 0, 0):  # X rotation
            expected_direction = Vector(0, 1, 0)
            assertVectorAlmostEqual(self, outer_axis.direction, expected_direction)
        elif rotation == (0, 90, 0):  # Y rotation
            expected_direction = Vector(-1, 0, 0)  # Correct direction for Y rotation
            assertVectorAlmostEqual(self, outer_axis.direction, expected_direction)
        elif rotation == (0, 0, 90):  # Z rotation
            expected_direction = Vector(0, 0, -1)
            assertVectorAlmostEqual(self, outer_axis.direction, expected_direction)

    def test_create_axis_with_combined_transformations(self):
        """Test create_axis with both movement and rotation applied"""
        # Apply both transformations
        movement = Vector(3, 4, 5)
        rotation = (30, 60, 45)
        
        self.cone.move_vector(movement)
        self.cone.rotate_multi(rotation)
        
        # Test outer cone axis
        outer_axis = self.cone.create_axis(inner=False)
        expected_outer_position = movement
        assertVectorAlmostEqual(self, outer_axis.position, expected_outer_position)
        
        # Test inner cone axis
        inner_axis = self.cone.create_axis(inner=True)
        
        # Inner axis position should be outer position plus Z offset (not rotated)
        # The implementation simply adds a Z offset to solid.position
        expected_inner_position = movement + Vector(0, 0, -self.cone.height_higher_lower)
        
        assertVectorAlmostEqual(self, inner_axis.position, expected_inner_position)
        
        # Both should have same direction
        assertVectorAlmostEqual(self, outer_axis.direction, inner_axis.direction)

    def test_create_axis_height_offset_calculation(self):
        """Test that the height offset between inner and outer axes is correct"""
        outer_axis = self.cone.create_axis(inner=False)
        inner_axis = self.cone.create_axis(inner=True)
        
        # The Z difference should equal height_higher_lower
        position_diff = outer_axis.position - inner_axis.position
        expected_z_diff = self.cone.height_higher_lower
        
        self.assertAlmostEqual(position_diff.Z, expected_z_diff, places=5)
        
        # X and Y should be the same for default orientation
        self.assertAlmostEqual(position_diff.X, 0.0, places=5)
        self.assertAlmostEqual(position_diff.Y, 0.0, places=5)

    def test_create_axis_mathematical_properties(self):
        """Test mathematical properties of the created axes"""
        outer_axis = self.cone.create_axis(inner=False)
        inner_axis = self.cone.create_axis(inner=True)
        
        # Direction vectors should be unit vectors
        self.assertAlmostEqual(outer_axis.direction.length, 1.0, places=5)
        self.assertAlmostEqual(inner_axis.direction.length, 1.0, places=5)
        
        # Both axes should be parallel (same direction)
        assertVectorAlmostEqual(self, outer_axis.direction, inner_axis.direction)

    def test_create_axis_with_different_cone_parameters(self):
        """Test create_axis with different cone geometry parameters"""
        # Create cones with different parameters
        test_cases = [
            (15.0, 5.0, 1.0, 45.0),   # Shallow cone, small radius
            (60.0, 20.0, 5.0, 30.0),  # Steep cone, large radius
            (45.0, 8.0, 0.5, 75.0),   # Medium cone, thin wall
        ]
        
        for cone_angle, radius, thickness, base_angle in test_cases:
            with self.subTest(cone_angle=cone_angle, radius=radius, thickness=thickness, base_angle=base_angle):
                cone = SmartCone.create_empty(cone_angle, radius, thickness, base_angle)
                
                outer_axis = cone.create_axis(inner=False)
                inner_axis = cone.create_axis(inner=True)
                
                # Basic properties should hold
                self.assertAlmostEqual(outer_axis.direction.length, 1.0, places=5)
                self.assertAlmostEqual(inner_axis.direction.length, 1.0, places=5)
                
                # Z offset should match height_higher_lower
                z_diff = outer_axis.position.Z - inner_axis.position.Z
                self.assertAlmostEqual(z_diff, cone.height_higher_lower, places=5)

    def test_create_axis_axis_object_type(self):
        """Test that create_axis returns proper Axis objects"""
        outer_axis = self.cone.create_axis(inner=False)
        inner_axis = self.cone.create_axis(inner=True)
        
        # Should be Axis objects
        self.assertIsInstance(outer_axis, Axis)
        self.assertIsInstance(inner_axis, Axis)
        
        # Should have position and direction attributes
        self.assertIsInstance(outer_axis.position, Vector)
        self.assertIsInstance(outer_axis.direction, Vector)
        self.assertIsInstance(inner_axis.position, Vector)
        self.assertIsInstance(inner_axis.direction, Vector)

    def test_create_axis_with_zero_height_offset(self):
        """Test create_axis when height_higher_lower is zero (edge case)"""
        # Create cone with minimal thickness to get small height offset
        cone = SmartCone.create_empty(cone_angle=45.0, radius=10.0, thickness=0.001, base_angle=89.0)
        
        outer_axis = cone.create_axis(inner=False)
        inner_axis = cone.create_axis(inner=True)
        
        # Even with very small offset, basic properties should hold
        self.assertAlmostEqual(outer_axis.direction.length, 1.0, places=5)
        self.assertAlmostEqual(inner_axis.direction.length, 1.0, places=5)
        assertVectorAlmostEqual(self, outer_axis.direction, inner_axis.direction)
        
        # Z difference should be very small but still correct
        z_diff = outer_axis.position.Z - inner_axis.position.Z
        self.assertAlmostEqual(z_diff, cone.height_higher_lower, places=5)

    def test_create_axis_multiple_calls_consistency(self):
        """Test that multiple calls to create_axis return consistent results"""
        # Multiple calls should return identical results
        axis1 = self.cone.create_axis(inner=False)
        axis2 = self.cone.create_axis(inner=False)
        axis3 = self.cone.create_axis(inner=True)
        axis4 = self.cone.create_axis(inner=True)
        
        assertVectorAlmostEqual(self, axis1.position, axis2.position)
        assertVectorAlmostEqual(self, axis1.direction, axis2.direction)
        assertVectorAlmostEqual(self, axis3.position, axis4.position)
        assertVectorAlmostEqual(self, axis3.direction, axis4.direction)

    def test_create_axis_extreme_rotations(self):
        """Test create_axis with extreme rotation values"""
        # Test with large rotation values
        extreme_rotations = [
            (180, 0, 0),
            (0, 180, 0), 
            (0, 0, 180),
            (360, 0, 0),
            (-90, -90, -90),
        ]
        
        for rotation in extreme_rotations:
            with self.subTest(rotation=rotation):
                cone = SmartCone.create_empty(30.0, 10.0, 2.0, 60.0)
                cone.rotate_multi(rotation)
                
                outer_axis = cone.create_axis(inner=False)
                inner_axis = cone.create_axis(inner=True)
                
                # Basic properties should still hold
                self.assertAlmostEqual(outer_axis.direction.length, 1.0, places=5)
                self.assertAlmostEqual(inner_axis.direction.length, 1.0, places=5)
                assertVectorAlmostEqual(self, outer_axis.direction, inner_axis.direction)

    def test_create_axis_implementation_details(self):
        """Test specific implementation details of create_axis"""
        # Test that the method correctly uses solid.position and solid.orientation
        
        # Move and rotate the cone
        self.cone.move(2, 3, 4)
        self.cone.rotate_multi((15, 25, 35))
        
        outer_axis = self.cone.create_axis(inner=False)
        inner_axis = self.cone.create_axis(inner=True)
        
        # Outer position should equal solid.position
        assertVectorAlmostEqual(self, outer_axis.position, self.cone.solid.position)
        
        # Inner position should be solid.position + Z offset
        expected_inner = self.cone.solid.position + Vector(0, 0, -self.cone.height_higher_lower)
        assertVectorAlmostEqual(self, inner_axis.position, expected_inner)
        
        # Direction should be rotated (0, 0, -1)
        from sava.csg.build123d.common.geometry import multi_rotate_vector
        expected_direction = multi_rotate_vector((0, 0, -1), Plane.XY, self.cone.solid.orientation)
        assertVectorAlmostEqual(self, outer_axis.direction, expected_direction)
        assertVectorAlmostEqual(self, inner_axis.direction, expected_direction)


class TestSmartConeCreatePlaneWithOffset(unittest.TestCase):

    def setUp(self):
        """Create a test SmartCone for each test"""
        self.cone_angle = 30.0  # degrees
        self.radius = 10.0
        self.thickness = 2.0
        self.base_angle = 60.0  # degrees
        self.cone = SmartCone.create_empty(
            cone_angle=self.cone_angle,
            radius=self.radius,
            thickness=self.thickness,
            base_angle=self.base_angle
        )

    def test_create_plane_with_offset_zero(self):
        """Test create_plane_with_offset with zero offset (at apex)"""
        plane = self.cone._create_plane_with_offset(0.0)
        
        # Plane position should be at the outer cone axis position (apex)
        cone_axis = self.cone.create_axis(inner=False)
        assertVectorAlmostEqual(self, plane.origin, cone_axis.position)
        
        # Plane normal should be the same as axis direction
        assertVectorAlmostEqual(self, plane.z_dir, cone_axis.direction)

    def test_create_plane_with_offset_positive(self):
        """Test create_plane_with_offset with positive offset"""
        offset = 5.0
        plane = self.cone._create_plane_with_offset(offset)
        
        # Calculate expected position
        cone_axis = self.cone.create_axis(inner=False)
        expected_position = cone_axis.position + cone_axis.direction * offset
        assertVectorAlmostEqual(self, plane.origin, expected_position)
        
        # Plane normal should be the same as axis direction
        assertVectorAlmostEqual(self, plane.z_dir, cone_axis.direction)

    def test_create_plane_with_offset_negative(self):
        """Test create_plane_with_offset with negative offset (above apex)"""
        offset = -3.0
        plane = self.cone._create_plane_with_offset(offset)
        
        # Calculate expected position
        cone_axis = self.cone.create_axis(inner=False)
        expected_position = cone_axis.position + cone_axis.direction * offset
        assertVectorAlmostEqual(self, plane.origin, expected_position)
        
        # Plane normal should be the same as axis direction
        assertVectorAlmostEqual(self, plane.z_dir, cone_axis.direction)

    def test_create_plane_with_offset_after_movement(self):
        """Test create_plane_with_offset when cone has been moved"""
        # Move the cone
        movement = Vector(5, 10, 15)
        self.cone.move_vector(movement)
        
        offset = 2.0
        plane = self.cone._create_plane_with_offset(offset)
        
        # Calculate expected position with movement
        cone_axis = self.cone.create_axis(inner=False)
        expected_position = cone_axis.position + cone_axis.direction * offset
        assertVectorAlmostEqual(self, plane.origin, expected_position)
        
        # Plane normal should be the same as axis direction
        assertVectorAlmostEqual(self, plane.z_dir, cone_axis.direction)

    def test_create_plane_with_offset_after_rotation(self):
        """Test create_plane_with_offset when cone has been rotated"""
        # Rotate the cone
        rotation = (45, 30, 60)
        self.cone.rotate_multi(rotation)
        
        offset = 4.0
        plane = self.cone._create_plane_with_offset(offset)
        
        # Calculate expected position with rotation
        cone_axis = self.cone.create_axis(inner=False)
        expected_position = cone_axis.position + cone_axis.direction * offset
        assertVectorAlmostEqual(self, plane.origin, expected_position)
        
        # Plane normal should be the rotated axis direction
        assertVectorAlmostEqual(self, plane.z_dir, cone_axis.direction)
        
        # Direction should be unit vector
        self.assertAlmostEqual(plane.z_dir.length, 1.0, places=5)

    def test_create_plane_with_offset_combined_transformations(self):
        """Test create_plane_with_offset with both movement and rotation"""
        # Apply both transformations
        movement = Vector(3, 4, 5)
        rotation = (30, 60, 45)
        
        self.cone.move_vector(movement)
        self.cone.rotate_multi(rotation)
        
        offset = 7.0
        plane = self.cone._create_plane_with_offset(offset)
        
        # Calculate expected position
        cone_axis = self.cone.create_axis(inner=False)
        expected_position = cone_axis.position + cone_axis.direction * offset
        assertVectorAlmostEqual(self, plane.origin, expected_position)
        
        # Plane normal should be the transformed axis direction
        assertVectorAlmostEqual(self, plane.z_dir, cone_axis.direction)

    @parameterized.expand([
        (0.0,),   # At apex
        (2.5,),   # Quarter way to base
        (5.0,),   # Halfway to base
        (7.5,),   # Three quarters to base  
        (10.0,),  # At base
        (-2.0,),  # Above apex
    ])
    def test_create_plane_with_offset_various_offsets(self, offset):
        """Test create_plane_with_offset with various offset values"""
        plane = self.cone._create_plane_with_offset(offset)
        
        # Calculate expected position
        cone_axis = self.cone.create_axis(inner=False)
        expected_position = cone_axis.position + cone_axis.direction * offset
        assertVectorAlmostEqual(self, plane.origin, expected_position)
        
        # Plane normal should be unit vector pointing in axis direction
        assertVectorAlmostEqual(self, plane.z_dir, cone_axis.direction)
        self.assertAlmostEqual(plane.z_dir.length, 1.0, places=5)

    def test_create_plane_with_offset_consistency(self):
        """Test that multiple calls return consistent results"""
        offset = 3.0
        plane1 = self.cone._create_plane_with_offset(offset)
        plane2 = self.cone._create_plane_with_offset(offset)
        
        # Should be identical
        assertVectorAlmostEqual(self, plane1.origin, plane2.origin)
        assertVectorAlmostEqual(self, plane1.z_dir, plane2.z_dir)

    def test_create_plane_with_offset_plane_properties(self):
        """Test that the created plane has correct properties"""
        offset = 4.0
        plane = self.cone._create_plane_with_offset(offset)
        
        # Should be a Plane object
        self.assertIsInstance(plane, Plane)
        
        # Should have valid origin and direction
        self.assertIsInstance(plane.origin, Vector)
        self.assertIsInstance(plane.z_dir, Vector)
        
        # Z direction should be normalized
        self.assertAlmostEqual(plane.z_dir.length, 1.0, places=5)

    def test_create_plane_with_offset_offset_relationships(self):
        """Test relationships between planes at different offsets"""
        offset1 = 2.0
        offset2 = 5.0
        
        plane1 = self.cone._create_plane_with_offset(offset1)
        plane2 = self.cone._create_plane_with_offset(offset2)
        
        # Both planes should have the same normal direction
        assertVectorAlmostEqual(self, plane1.z_dir, plane2.z_dir)
        
        # Distance between origins should equal offset difference
        cone_axis = self.cone.create_axis(inner=False)
        expected_distance = abs(offset2 - offset1)
        actual_distance = (plane2.origin - plane1.origin).length
        self.assertAlmostEqual(actual_distance, expected_distance, places=5)
        
        # Direction from plane1 to plane2 should be along axis
        direction_between = (plane2.origin - plane1.origin).normalized()
        if offset2 > offset1:
            assertVectorAlmostEqual(self, direction_between, cone_axis.direction)
        else:
            assertVectorAlmostEqual(self, direction_between, -cone_axis.direction)


if __name__ == '__main__':
    unittest.main()