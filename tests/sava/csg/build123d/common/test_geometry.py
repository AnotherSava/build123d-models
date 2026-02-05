import unittest
from math import sqrt, sin, cos, radians

from build123d import Vector, Axis, Plane, Box, Edge, ShapeList
from parameterized import parameterized

from sava.csg.build123d.common.geometry import rotate_vector, multi_rotate_vector, convert_orientation_to_rotations, orient_axis, calculate_orientation
from sava.csg.build123d.common.edgefilters import filter_edges_by_axis, filter_edges_by_position
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
        # Single-axis rotation tests
        ("single", Vector(1, 1, 1), Axis.X, 45),
        ("single", Vector(2, -1, 3), Axis.Y, 30),
        ("single", Vector(-1, 2, 0), Axis.Z, 60),
        ("single", Vector(0.5, 0.5, 0.5), Axis.X, 120),
        # Multi-axis rotation tests  
        ("multi", Vector(1, 1, 1), Plane.XY, Vector(45, 30, 60)),
        ("multi", Vector(2, -1, 3), Plane.XZ, Vector(90, 45, 30)),
        ("multi", Vector(-1, 2, 0), Plane.YZ, Vector(60, 90, 45)),
    ])
    def test_rotation_preserves_magnitude(self, rotation_type, vector, axis_or_plane, angle_or_rotations):
        """Test that both single and multi-axis rotations preserve vector magnitude"""
        original_magnitude = sqrt(vector.X**2 + vector.Y**2 + vector.Z**2)
        
        if rotation_type == "single":
            result = rotate_vector(vector, axis_or_plane, angle_or_rotations)
        else:  # multi
            result = multi_rotate_vector(vector, axis_or_plane, angle_or_rotations)
            
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


class TestFilterEdgesByAxis(unittest.TestCase):

    def _create_edge_at_angle(self, angle_degrees: float, length: float = 10) -> Edge:
        """Create an edge in XY plane at given angle from X axis."""
        end_x = length * cos(radians(angle_degrees))
        end_y = length * sin(radians(angle_degrees))
        return Edge.make_line((0, 0, 0), (end_x, end_y, 0))

    def test_exact_alignment_passes(self):
        """Edge exactly aligned with axis should pass with any tolerance."""
        edge = Edge.make_line((0, 0, 0), (10, 0, 0))
        edges = ShapeList([edge])

        result = filter_edges_by_axis(edges, Axis.X, angle_tolerance=0)
        self.assertEqual(len(result), 1)

    def test_perpendicular_edge_fails(self):
        """Edge perpendicular to axis should fail."""
        edge = Edge.make_line((0, 0, 0), (0, 10, 0))  # Along Y axis
        edges = ShapeList([edge])

        result = filter_edges_by_axis(edges, Axis.X, angle_tolerance=45)
        self.assertEqual(len(result), 0)

    @parameterized.expand([
        (5, 10, 1),   # 5° edge with 10° tolerance -> passes
        (5, 5, 1),    # 5° edge with 5° tolerance -> passes (at boundary)
        (5, 4, 0),    # 5° edge with 4° tolerance -> fails
        (10, 15, 1),  # 10° edge with 15° tolerance -> passes
        (10, 10, 1),  # 10° edge with 10° tolerance -> passes (at boundary)
        (10, 9, 0),   # 10° edge with 9° tolerance -> fails
        (0.5, 1, 1),  # 0.5° edge with 1° tolerance -> passes
        (0.5, 0.4, 0),  # 0.5° edge with 0.4° tolerance -> fails
    ])
    def test_angle_tolerance_boundary(self, edge_angle, tolerance, expected_count):
        """Test that angle_tolerance correctly filters edges at various angles."""
        edge = self._create_edge_at_angle(edge_angle)
        edges = ShapeList([edge])

        result = filter_edges_by_axis(edges, Axis.X, angle_tolerance=tolerance)
        self.assertEqual(len(result), expected_count, f"Edge at {edge_angle}° with tolerance {tolerance}° should {'pass' if expected_count else 'fail'}")

    def test_multiple_edges_mixed_angles(self):
        """Test filtering multiple edges with different angles."""
        edges = ShapeList([
            self._create_edge_at_angle(0),   # exactly aligned
            self._create_edge_at_angle(3),   # 3° off
            self._create_edge_at_angle(7),   # 7° off
            self._create_edge_at_angle(12),  # 12° off
            self._create_edge_at_angle(45),  # 45° off
        ])

        # With 5° tolerance: only 0° and 3° should pass
        result = filter_edges_by_axis(edges, Axis.X, angle_tolerance=5)
        self.assertEqual(len(result), 2)

        # With 10° tolerance: 0°, 3°, and 7° should pass
        result = filter_edges_by_axis(edges, Axis.X, angle_tolerance=10)
        self.assertEqual(len(result), 3)

        # With 15° tolerance: 0°, 3°, 7°, and 12° should pass
        result = filter_edges_by_axis(edges, Axis.X, angle_tolerance=15)
        self.assertEqual(len(result), 4)

    def test_negative_angle_same_as_positive(self):
        """Edge at -5° should behave same as +5° (opposite direction)."""
        edge_pos = self._create_edge_at_angle(5)
        edge_neg = self._create_edge_at_angle(-5)

        result_pos = filter_edges_by_axis(ShapeList([edge_pos]), Axis.X, angle_tolerance=6)
        result_neg = filter_edges_by_axis(ShapeList([edge_neg]), Axis.X, angle_tolerance=6)

        self.assertEqual(len(result_pos), 1)
        self.assertEqual(len(result_neg), 1)

    def test_opposite_direction_passes(self):
        """Edge pointing opposite to axis direction should still pass (parallel)."""
        edge = Edge.make_line((0, 0, 0), (-10, 0, 0))  # Opposite to X axis
        edges = ShapeList([edge])

        result = filter_edges_by_axis(edges, Axis.X, angle_tolerance=0.001)
        self.assertEqual(len(result), 1)

    def test_3d_edge_angle(self):
        """Test edge at angle in 3D space."""
        # Edge at 45° in XZ plane (from X axis towards Z)
        edge = Edge.make_line((0, 0, 0), (10, 0, 10))
        edges = ShapeList([edge])

        result = filter_edges_by_axis(edges, Axis.X, angle_tolerance=44)
        self.assertEqual(len(result), 0)

        result = filter_edges_by_axis(edges, Axis.X, angle_tolerance=46)
        self.assertEqual(len(result), 1)

    def test_arc_with_curved_tangents_fails(self):
        """Test that arc edges are filtered by checking tangents at all points.

        An arc that curves significantly should fail because tangents along the
        arc deviate from the axis, even if endpoints might be aligned.
        """
        # Arc from (0,0,0) to (10,0,0) through (5,2,0) - endpoints are X-aligned
        # but the arc curves through Y, so tangents at the apex deviate from X
        arc = Edge.make_three_point_arc((0, 0, 0), (5, 2, 0), (10, 0, 0))
        edges = ShapeList([arc])

        # Even though endpoints are X-aligned, tangents at apex point ~44° off X
        # So with 5° tolerance it should fail
        result = filter_edges_by_axis(edges, Axis.X, angle_tolerance=5)
        self.assertEqual(len(result), 0)

        # With 45° tolerance it should pass (tangents deviate ~44° at apex)
        result = filter_edges_by_axis(edges, Axis.X, angle_tolerance=45)
        self.assertEqual(len(result), 1)

    def test_nearly_straight_arc_passes(self):
        """Test that a nearly-straight arc passes with appropriate tolerance."""
        # Arc with very slight curve - tangents stay close to X direction
        arc = Edge.make_three_point_arc((0, 0, 0), (5, 0.1, 0), (10, 0, 0))
        edges = ShapeList([arc])

        # Very small deviation, should pass with small tolerance
        result = filter_edges_by_axis(edges, Axis.X, angle_tolerance=3)
        self.assertEqual(len(result), 1)


class TestFilterEdgesByPosition(unittest.TestCase):

    def _create_edge_at_x(self, x: float, length: float = 2) -> Edge:
        """Create a vertical edge (along Z) centered at given X position."""
        return Edge.make_line((x, 0, 0), (x, 0, length))

    def _create_edge_at_y(self, y: float, length: float = 2) -> Edge:
        """Create a vertical edge (along Z) centered at given Y position."""
        return Edge.make_line((0, y, 0), (0, y, length))

    def _create_edge_at_z(self, z: float, length: float = 2) -> Edge:
        """Create a horizontal edge (along X) centered at given Z position."""
        return Edge.make_line((0, 0, z), (length, 0, z))

    def test_edge_inside_interval_passes(self):
        """Edge clearly inside the interval should pass."""
        edge = self._create_edge_at_x(5)
        edges = ShapeList([edge])

        result = filter_edges_by_position(edges, Axis.X, 0, 10, (True, True))
        self.assertEqual(len(result), 1)

    def test_edge_outside_interval_fails(self):
        """Edge clearly outside the interval should fail."""
        edge = self._create_edge_at_x(15)
        edges = ShapeList([edge])

        result = filter_edges_by_position(edges, Axis.X, 0, 10, (True, True))
        self.assertEqual(len(result), 0)

    def test_edge_below_minimum_fails(self):
        """Edge below the minimum should fail."""
        edge = self._create_edge_at_x(-5)
        edges = ShapeList([edge])

        result = filter_edges_by_position(edges, Axis.X, 0, 10, (True, True))
        self.assertEqual(len(result), 0)

    @parameterized.expand([
        (True, 1),   # Inclusive minimum -> passes
        (False, 0),  # Exclusive minimum -> fails
    ])
    def test_edge_at_minimum_boundary(self, include_min, expected_count):
        """Edge exactly at minimum should pass only if inclusive."""
        edge = self._create_edge_at_x(0)
        edges = ShapeList([edge])

        result = filter_edges_by_position(edges, Axis.X, 0, 10, (include_min, True))
        self.assertEqual(len(result), expected_count)

    @parameterized.expand([
        (True, 1),   # Inclusive maximum -> passes
        (False, 0),  # Exclusive maximum -> fails
    ])
    def test_edge_at_maximum_boundary(self, include_max, expected_count):
        """Edge exactly at maximum should pass only if inclusive."""
        edge = self._create_edge_at_x(10)
        edges = ShapeList([edge])

        result = filter_edges_by_position(edges, Axis.X, 0, 10, (True, include_max))
        self.assertEqual(len(result), expected_count)

    def test_edge_near_minimum_within_tolerance(self):
        """Edge very close to minimum should be treated as at minimum."""
        # Edge at position 1e-8, which is within default tolerance of 0
        edge = self._create_edge_at_x(1e-8)
        edges = ShapeList([edge])

        # With inclusive minimum, should pass (treated as at boundary)
        result = filter_edges_by_position(edges, Axis.X, 0, 10, (True, True))
        self.assertEqual(len(result), 1)

        # With exclusive minimum, should fail (treated as at boundary)
        result = filter_edges_by_position(edges, Axis.X, 0, 10, (False, True))
        self.assertEqual(len(result), 0)

    def test_edge_near_maximum_within_tolerance(self):
        """Edge very close to maximum should be treated as at maximum."""
        # Edge at position 10 - 1e-8, which is within default tolerance of 10
        edge = self._create_edge_at_x(10 - 1e-8)
        edges = ShapeList([edge])

        # With inclusive maximum, should pass (treated as at boundary)
        result = filter_edges_by_position(edges, Axis.X, 0, 10, (True, True))
        self.assertEqual(len(result), 1)

        # With exclusive maximum, should fail (treated as at boundary)
        result = filter_edges_by_position(edges, Axis.X, 0, 10, (True, False))
        self.assertEqual(len(result), 0)

    def test_filter_along_y_axis(self):
        """Test filtering edges by position along Y axis."""
        edges = ShapeList([
            self._create_edge_at_y(-5),  # Outside below
            self._create_edge_at_y(0),   # At minimum
            self._create_edge_at_y(5),   # Inside
            self._create_edge_at_y(10),  # At maximum
            self._create_edge_at_y(15),  # Outside above
        ])

        result = filter_edges_by_position(edges, Axis.Y, 0, 10, (True, True))
        self.assertEqual(len(result), 3)  # 0, 5, 10

        result = filter_edges_by_position(edges, Axis.Y, 0, 10, (False, False))
        self.assertEqual(len(result), 1)  # Only 5

    def test_filter_along_z_axis(self):
        """Test filtering edges by position along Z axis."""
        edges = ShapeList([
            self._create_edge_at_z(0),
            self._create_edge_at_z(5),
            self._create_edge_at_z(10),
        ])

        result = filter_edges_by_position(edges, Axis.Z, 2, 8, (True, True))
        self.assertEqual(len(result), 1)  # Only z=5

    def test_multiple_edges_mixed_positions(self):
        """Test filtering multiple edges at various positions."""
        edges = ShapeList([
            self._create_edge_at_x(0),
            self._create_edge_at_x(2),
            self._create_edge_at_x(5),
            self._create_edge_at_x(8),
            self._create_edge_at_x(10),
        ])

        # Narrow interval in the middle
        result = filter_edges_by_position(edges, Axis.X, 3, 7, (True, True))
        self.assertEqual(len(result), 1)  # Only x=5

        # Wider interval
        result = filter_edges_by_position(edges, Axis.X, 1, 9, (True, True))
        self.assertEqual(len(result), 3)  # x=2, 5, 8

    def test_negative_interval(self):
        """Test filtering with negative coordinate range."""
        edges = ShapeList([
            self._create_edge_at_x(-10),
            self._create_edge_at_x(-5),
            self._create_edge_at_x(0),
            self._create_edge_at_x(5),
        ])

        result = filter_edges_by_position(edges, Axis.X, -8, -2, (True, True))
        self.assertEqual(len(result), 1)  # Only x=-5

    def test_edge_center_used_for_position(self):
        """Test that edge center (not endpoints) determines position."""
        # Edge from x=0 to x=10, center at x=5
        edge = Edge.make_line((0, 0, 0), (10, 0, 0))
        edges = ShapeList([edge])

        # Interval excludes endpoints but includes center
        result = filter_edges_by_position(edges, Axis.X, 3, 7, (True, True))
        self.assertEqual(len(result), 1)

        # Interval excludes center
        result = filter_edges_by_position(edges, Axis.X, 6, 10, (True, True))
        self.assertEqual(len(result), 0)

    def test_empty_edge_list(self):
        """Test filtering an empty edge list."""
        edges = ShapeList([])

        result = filter_edges_by_position(edges, Axis.X, 0, 10, (True, True))
        self.assertEqual(len(result), 0)

    def test_all_inclusive_vs_all_exclusive(self):
        """Test the difference between all-inclusive and all-exclusive boundaries."""
        edges = ShapeList([
            self._create_edge_at_x(0),
            self._create_edge_at_x(5),
            self._create_edge_at_x(10),
        ])

        # All inclusive: 0, 5, 10 pass
        result = filter_edges_by_position(edges, Axis.X, 0, 10, (True, True))
        self.assertEqual(len(result), 3)

        # All exclusive: only 5 passes
        result = filter_edges_by_position(edges, Axis.X, 0, 10, (False, False))
        self.assertEqual(len(result), 1)


if __name__ == '__main__':
    unittest.main()