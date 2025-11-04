import unittest
from math import sqrt

from build123d import Vector, Axis, Plane
from parameterized import parameterized

from sava.csg.build123d.common.geometry import rotate_vector, multi_rotate_vector, convert_orientation_to_rotations, orient_axis, calculate_orientation
from tests.sava.csg.build123d.test_utils import assertVectorAlmostEqual


class TestRotateVector(unittest.TestCase):

    @parameterized.expand([
        # Rotation around X-axis
        (Vector(1, 0, 0), Axis.X, 90, Vector(1, 0, 0)),  # X-axis vector unchanged
        (Vector(0, 1, 0), Axis.X, 90, Vector(0, 0, 1)),  # Y becomes Z
        (Vector(0, 0, 1), Axis.X, 90, Vector(0, -1, 0)), # Z becomes -Y
        (Vector(0, 1, 0), Axis.X, 180, Vector(0, -1, 0)), # Y becomes -Y
        (Vector(0, 0, 1), Axis.X, 180, Vector(0, 0, -1)), # Z becomes -Z
        
        # Rotation around Y-axis  
        (Vector(0, 1, 0), Axis.Y, 90, Vector(0, 1, 0)),  # Y-axis vector unchanged
        (Vector(1, 0, 0), Axis.Y, 90, Vector(0, 0, -1)), # X becomes -Z
        (Vector(0, 0, 1), Axis.Y, 90, Vector(1, 0, 0)),  # Z becomes X
        (Vector(1, 0, 0), Axis.Y, 180, Vector(-1, 0, 0)), # X becomes -X
        (Vector(0, 0, 1), Axis.Y, 180, Vector(0, 0, -1)), # Z becomes -Z
        
        # Rotation around Z-axis
        (Vector(0, 0, 1), Axis.Z, 90, Vector(0, 0, 1)),  # Z-axis vector unchanged
        (Vector(1, 0, 0), Axis.Z, 90, Vector(0, 1, 0)),  # X becomes Y
        (Vector(0, 1, 0), Axis.Z, 90, Vector(-1, 0, 0)), # Y becomes -X
        (Vector(1, 0, 0), Axis.Z, 180, Vector(-1, 0, 0)), # X becomes -X
        (Vector(0, 1, 0), Axis.Z, 180, Vector(0, -1, 0)), # Y becomes -Y
        
        # Zero rotation
        (Vector(1, 2, 3), Axis.X, 0, Vector(1, 2, 3)),
        (Vector(1, 2, 3), Axis.Y, 0, Vector(1, 2, 3)),
        (Vector(1, 2, 3), Axis.Z, 0, Vector(1, 2, 3)),
    ])
    def test_rotate_vector_basic_cases(self, vector, axis, angle, expected):
        """Test rotate_vector with basic rotation cases"""
        result = rotate_vector(vector, axis, angle)
        
        assertVectorAlmostEqual(self, result, expected)

    @parameterized.expand([
        (Vector(1, 1, 1), Axis.X, 45),
        (Vector(2, -1, 3), Axis.Y, 30),
        (Vector(-1, 2, 0), Axis.Z, 60),
        (Vector(0.5, 0.5, 0.5), Axis.X, 120),
    ])
    def test_rotate_vector_preserves_magnitude(self, vector, axis, angle):
        """Test that rotation preserves vector magnitude"""
        original_magnitude = sqrt(vector.X**2 + vector.Y**2 + vector.Z**2)
        result = rotate_vector(vector, axis, angle)
        result_magnitude = sqrt(result.X**2 + result.Y**2 + result.Z**2)
        
        self.assertAlmostEqual(original_magnitude, result_magnitude, places=5)

    def test_rotate_vector_sequential_rotations(self):
        """Test that multiple 90-degree rotations equal one 360-degree rotation"""
        vector = Vector(1, 2, 3)
        
        # Four 90-degree rotations around X-axis should return to original
        result = vector
        for _ in range(4):
            result = rotate_vector(result, Axis.X, 90)
        
        assertVectorAlmostEqual(self, result, vector)

    def test_rotate_vector_invalid_axis(self):
        """Test that invalid axis raises appropriate errors"""
        vector = Vector(1, 0, 0)
        
        # Test invalid non-Axis input
        with self.assertRaises(AttributeError):
            rotate_vector(vector, "invalid_axis", 90)

    @parameterized.expand([
        # Diagonal axis (1,1,1) - 120° rotation should cycle coordinates
        (Vector(1, 0, 0), Axis((0, 0, 0), (1, 1, 1)), 120, Vector(0, 1, 0)),
        (Vector(0, 1, 0), Axis((0, 0, 0), (1, 1, 1)), 120, Vector(0, 0, 1)),
        (Vector(0, 0, 1), Axis((0, 0, 0), (1, 1, 1)), 120, Vector(1, 0, 0)),
        
        # Arbitrary axis tests
        (Vector(1, 0, 0), Axis((0, 0, 0), (0, 1, 1)), 180, Vector(-1, 0, 0)),  # 180° rotation flips X component
        (Vector(1, 1, 0), Axis.Z, 90, Vector(-1, 1, 0)),  # Rotation around Z-axis
    ])
    def test_rotate_vector_arbitrary_axis(self, vector, axis, angle, expected):
        """Test rotate_vector with arbitrary axis objects"""
        result = rotate_vector(vector, axis, angle)
        
        assertVectorAlmostEqual(self, result, expected)

    def test_rotate_vector_custom_axis_equivalence(self):
        """Test that custom Axis gives same result as standard Axis"""
        vector = Vector(1, 2, 3)
        angle = 45
        
        # Test X-axis equivalence
        result_standard = rotate_vector(vector, Axis.X, angle)
        result_custom = rotate_vector(vector, Axis((0, 0, 0), (1, 0, 0)), angle)
        
        assertVectorAlmostEqual(self, result_standard, result_custom)

    def test_rotate_vector_axis_normalization(self):
        """Test that Axis automatically normalizes direction vectors"""
        vector = Vector(1, 0, 0)
        
        # Using unnormalized direction should give same result as normalized (Axis handles this)
        result1 = rotate_vector(vector, Axis((0, 0, 0), (2, 0, 0)), 90)  # 2x X-axis direction
        result2 = rotate_vector(vector, Axis((0, 0, 0), (1, 0, 0)), 90)  # 1x X-axis direction
        
        assertVectorAlmostEqual(self, result1, result2)


class TestMultiRotateVector(unittest.TestCase):

    @parameterized.expand([
        # Basic rotations around XY plane axes
        (Vector(1, 0, 0), Plane.XY, Vector(90, 0, 0), Vector(1, 0, 0)),  # X-axis unchanged by X rotation
        (Vector(0, 1, 0), Plane.XY, Vector(90, 0, 0), Vector(0, 0, 1)),  # Y becomes Z
        (Vector(0, 0, 1), Plane.XY, Vector(90, 0, 0), Vector(0, -1, 0)), # Z becomes -Y
        
        (Vector(1, 0, 0), Plane.XY, Vector(0, 90, 0), Vector(0, 0, -1)), # X becomes -Z
        (Vector(0, 1, 0), Plane.XY, Vector(0, 90, 0), Vector(0, 1, 0)),  # Y-axis unchanged by Y rotation
        (Vector(0, 0, 1), Plane.XY, Vector(0, 90, 0), Vector(1, 0, 0)),  # Z becomes X
        
        (Vector(1, 0, 0), Plane.XY, Vector(0, 0, 90), Vector(0, 1, 0)),  # X becomes Y
        (Vector(0, 1, 0), Plane.XY, Vector(0, 0, 90), Vector(-1, 0, 0)), # Y becomes -X
        (Vector(0, 0, 1), Plane.XY, Vector(0, 0, 90), Vector(0, 0, 1)),  # Z-axis unchanged by Z rotation
        
        # Zero rotations
        (Vector(1, 2, 3), Plane.XY, Vector(0, 0, 0), Vector(1, 2, 3)),
        (Vector(1, 2, 3), Plane.XZ, Vector(0, 0, 0), Vector(1, 2, 3)),
        
        # Combined rotations
        (Vector(1, 0, 0), Plane.XY, Vector(90, 90, 0), Vector(0, 0, -1)),  # X->Y by Z, then Y->-Z by X
    ])
    def test_multi_rotate_vector_basic_cases(self, vector, plane, rotations, expected):
        """Test multi_rotate_vector with basic rotation cases"""
        result = multi_rotate_vector(vector, plane, rotations)
        
        assertVectorAlmostEqual(self, result, expected)

    @parameterized.expand([
        (Vector(1, 1, 1), Plane.XY, Vector(45, 30, 60)),
        (Vector(2, -1, 3), Plane.XZ, Vector(90, 45, 30)),
        (Vector(-1, 2, 0), Plane.YZ, Vector(60, 90, 45)),
    ])
    def test_multi_rotate_vector_preserves_magnitude(self, vector, plane, rotations):
        """Test that multi-rotation preserves vector magnitude"""
        original_magnitude = sqrt(vector.X**2 + vector.Y**2 + vector.Z**2)
        result = multi_rotate_vector(vector, plane, rotations)
        result_magnitude = sqrt(result.X**2 + result.Y**2 + result.Z**2)
        
        self.assertAlmostEqual(original_magnitude, result_magnitude, places=5)

    def test_multi_rotate_vector_sequential_equivalence(self):
        """Test that multi_rotate_vector equals sequential single rotations"""
        vector = Vector(1, 2, 3)
        plane = Plane.XY
        rotations = Vector(30, 45, 60)
        
        # Multi-rotation approach
        result_multi = multi_rotate_vector(vector, plane, rotations)
        
        # Sequential single rotations
        x_axis = Axis(plane.location.position, plane.x_dir)
        y_axis = Axis(plane.location.position, plane.y_dir)
        z_axis = Axis(plane.location.position, plane.z_dir)
        
        result_sequential = vector
        result_sequential = rotate_vector(result_sequential, x_axis, rotations.X)
        result_sequential = rotate_vector(result_sequential, y_axis, rotations.Y)
        result_sequential = rotate_vector(result_sequential, z_axis, rotations.Z)
        
        assertVectorAlmostEqual(self, result_multi, result_sequential)

    @parameterized.expand([
        (Plane.XY,),
        (Plane.XZ,),
        (Plane.YZ,),
    ])
    def test_multi_rotate_vector_different_planes(self, plane):
        """Test multi_rotate_vector with different planes"""
        vector = Vector(1, 0, 0)
        rotations = Vector(90, 0, 0)
        
        # Should not raise exceptions and should return valid result
        result = multi_rotate_vector(vector, plane, rotations)
        
        self.assertIsInstance(result, Vector)
        # Magnitude should be preserved
        original_mag = sqrt(vector.X**2 + vector.Y**2 + vector.Z**2)
        result_mag = sqrt(result.X**2 + result.Y**2 + result.Z**2)
        self.assertAlmostEqual(original_mag, result_mag, places=5)

    def test_multi_rotate_vector_vectorlike_inputs(self):
        """Test that function accepts VectorLike inputs"""
        # Test with tuples
        result1 = multi_rotate_vector((1, 2, 3), Plane.XY, (90, 0, 0))
        
        # Test with Vector objects
        result2 = multi_rotate_vector(Vector(1, 2, 3), Plane.XY, Vector(90, 0, 0))
        
        # Results should be identical
        assertVectorAlmostEqual(self, result1, result2)


class TestConvertOrientationToRotations(unittest.TestCase):

    @parameterized.expand([
        # Basic single-axis orientations
        (Vector(90, 0, 0), Vector(90, 0, 0)),  # X-axis rotation only
        (Vector(0, 90, 0), Vector(0, 90, 0)),  # Y-axis rotation only
        (Vector(0, 0, 90), Vector(0, 0, 90)),  # Z-axis rotation only

        # Zero orientation
        (Vector(0, 0, 0), Vector(0, 0, 0)),
        
        # Multiple axis orientations
        (Vector(90, 0, -90), Vector(90, 90, 0)),
    ])
    def test_convert_orientation_to_rotations_basic(self, orientation: Vector, expected_rotations: Vector):
        """Test convert_orientation_to_rotations with basic cases"""
        result = convert_orientation_to_rotations(orientation)

        message = f"Input orientation: {orientation}, resulted rotations: {result}, expected rotations: {expected_rotations}"
        self.assertAlmostEqual(result.X, expected_rotations.X, 1, message)
        self.assertAlmostEqual(result.Y, expected_rotations.Y, 1, message)
        self.assertAlmostEqual(result.Z, expected_rotations.Z, 1, message)


class TestCalculateOrientation(unittest.TestCase):

    def test_calculate_orientation_axes_consistency(self):
        """Test that calculate_orientation produces orientations that yield the same axes"""
        import random
        
        # Set seed for reproducible tests
        random.seed(42)
        
        # Test with multiple random orientations
        for _ in range(20):
            # Generate three random numbers between -180 and 180
            random_x = random.uniform(-180, 180)
            random_y = random.uniform(-180, 180) 
            random_z = random.uniform(-180, 180)
            original_orientation = Vector(random_x, random_y, random_z)
            
            # Apply orient_axis to get three axes
            saved_x_axis, saved_y_axis, saved_z_axis = orient_axis(original_orientation)
            
            # Call calculate_orientation with those axes to get (possibly different) numbers
            calculated_orientation = calculate_orientation(saved_x_axis, saved_y_axis, saved_z_axis)
            
            # Call orient_axis with the calculated orientation
            result_x_axis, result_y_axis, result_z_axis = orient_axis(calculated_orientation)
            
            # Check that the output axes match the saved ones
            with self.subTest(original=original_orientation, calculated=calculated_orientation):
                self.assertAlmostEqual(saved_x_axis.direction.X, result_x_axis.direction.X, places=5)
                self.assertAlmostEqual(saved_x_axis.direction.Y, result_x_axis.direction.Y, places=5)
                self.assertAlmostEqual(saved_x_axis.direction.Z, result_x_axis.direction.Z, places=5)
                
                self.assertAlmostEqual(saved_y_axis.direction.X, result_y_axis.direction.X, places=5)
                self.assertAlmostEqual(saved_y_axis.direction.Y, result_y_axis.direction.Y, places=5)
                self.assertAlmostEqual(saved_y_axis.direction.Z, result_y_axis.direction.Z, places=5)
                
                self.assertAlmostEqual(saved_z_axis.direction.X, result_z_axis.direction.X, places=5)
                self.assertAlmostEqual(saved_z_axis.direction.Y, result_z_axis.direction.Y, places=5)
                self.assertAlmostEqual(saved_z_axis.direction.Z, result_z_axis.direction.Z, places=5)

    def test_calculate_orientation_standard_axes(self):
        """Test with standard XYZ axes should return zero orientation"""
        result = calculate_orientation(Axis.X, Axis.Y, Axis.Z)
        
        self.assertAlmostEqual(result.X, 0, places=5)
        self.assertAlmostEqual(result.Y, 0, places=5)
        self.assertAlmostEqual(result.Z, 0, places=5)

    @parameterized.expand([
        # Test specific known transformations
        (Axis.X, Axis.Z, Axis((0,0,0), (0,-1,0)), Vector(90, 0, 0)),  # 90° X rotation
        (Axis((0,0,0), (0,0,-1)), Axis.Y, Axis.X, Vector(0, 90, 0)),  # 90° Y rotation  
        (Axis.Y, Axis((0,0,0), (-1,0,0)), Axis.Z, Vector(0, 0, 90)),  # 90° Z rotation
    ])
    def test_calculate_orientation_known_cases(self, x_axis, y_axis, z_axis, expected):
        """Test calculate_orientation with known axis configurations"""
        result = calculate_orientation(x_axis, y_axis, z_axis)
        
        # Allow for equivalent angle representations (e.g., 270° = -90°)
        def normalize_angle(angle):
            return ((angle + 180) % 360) - 180
        
        self.assertAlmostEqual(normalize_angle(result.X), normalize_angle(expected.X), places=1)
        self.assertAlmostEqual(normalize_angle(result.Y), normalize_angle(expected.Y), places=1)
        self.assertAlmostEqual(normalize_angle(result.Z), normalize_angle(expected.Z), places=1)


if __name__ == '__main__':
    unittest.main()