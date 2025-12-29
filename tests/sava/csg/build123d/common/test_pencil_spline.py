import unittest

from build123d import Vector
from parameterized import parameterized

from sava.csg.build123d.common.pencil import Pencil


class TestPencilSpline(unittest.TestCase):
    """Test Pencil.spline() method with and without intermediate points."""

    def test_backward_compatibility_simple_spline(self):
        """Test that existing spline calls without intermediate_points still work."""
        pencil = Pencil()
        result = pencil.spline((50, 50), (1, 0))

        # Should return self for method chaining
        self.assertIs(result, pencil)

        # Should have one curve
        self.assertEqual(len(pencil.curves), 1)

        # Location should be updated to destination
        self.assertAlmostEqual(pencil.location.X, 50)
        self.assertAlmostEqual(pencil.location.Y, 50)

        # Curve should be valid
        edge = pencil.curves[0]
        self.assertTrue(edge.is_valid)

    def test_spline_with_single_intermediate_point(self):
        """Test spline with a single intermediate point."""
        pencil = Pencil()
        result = pencil.spline((50, 50), (1, 0), intermediate_points=[(25, 25)])

        # Should return self for method chaining
        self.assertIs(result, pencil)

        # Should have one curve
        self.assertEqual(len(pencil.curves), 1)

        # Location should be at destination
        self.assertAlmostEqual(pencil.location.X, 50)
        self.assertAlmostEqual(pencil.location.Y, 50)

        # Curve should be valid and should pass through intermediate point
        edge = pencil.curves[0]
        self.assertTrue(edge.is_valid)

    def test_spline_with_multiple_intermediate_points(self):
        """Test spline with multiple intermediate points."""
        pencil = Pencil()
        intermediate = [(20, 30), (40, 20), (45, 45)]
        result = pencil.spline((50, 50), (1, 0), intermediate_points=intermediate)

        # Should return self for method chaining
        self.assertIs(result, pencil)

        # Should have one curve
        self.assertEqual(len(pencil.curves), 1)

        # Location should be at destination
        self.assertAlmostEqual(pencil.location.X, 50)
        self.assertAlmostEqual(pencil.location.Y, 50)

        # Curve should be valid
        edge = pencil.curves[0]
        self.assertTrue(edge.is_valid)

    def test_spline_with_empty_intermediate_points_list(self):
        """Test that empty intermediate_points list behaves like None."""
        pencil1 = Pencil()
        pencil1.spline((50, 50), (1, 0), intermediate_points=[])

        pencil2 = Pencil()
        pencil2.spline((50, 50), (1, 0))

        # Both should have one curve
        self.assertEqual(len(pencil1.curves), 1)
        self.assertEqual(len(pencil2.curves), 1)

        # Both should end at same location
        self.assertAlmostEqual(pencil1.location.X, pencil2.location.X)
        self.assertAlmostEqual(pencil1.location.Y, pencil2.location.Y)

    def test_spline_with_none_intermediate_points(self):
        """Test that explicitly passing None works the same as not passing it."""
        pencil = Pencil()
        result = pencil.spline((50, 50), (1, 0), intermediate_points=None)

        # Should work just like original behavior
        self.assertIs(result, pencil)
        self.assertEqual(len(pencil.curves), 1)
        self.assertAlmostEqual(pencil.location.X, 50)
        self.assertAlmostEqual(pencil.location.Y, 50)

    def test_intermediate_points_are_relative_to_current_location(self):
        """Test that intermediate points are relative to current location, not origin."""
        pencil = Pencil(start=(10, 10))
        pencil.jump((20, 20))  # Move to (30, 30) absolute

        # Now draw spline with intermediate point relative to current location
        pencil.spline((50, 50), (1, 0), intermediate_points=[(25, 25)])

        # Final location should be current + destination = (30,30) + (50,50) = (80,80)
        self.assertAlmostEqual(pencil.location.X, 80)
        self.assertAlmostEqual(pencil.location.Y, 80)

    def test_very_close_intermediate_point_to_start_raises_error(self):
        """Test that intermediate point very close to start location raises ValueError."""
        pencil = Pencil()

        # Use a point extremely close to current location (should raise error)
        with self.assertRaises(ValueError) as context:
            pencil.spline((50, 50), (1, 0), intermediate_points=[(0.0000001, 0.0000001), (25, 25)])

        self.assertIn("start and intermediate point 0", str(context.exception))

    def test_very_close_intermediate_point_to_destination_raises_error(self):
        """Test that intermediate point very close to destination raises ValueError."""
        pencil = Pencil()

        # Use a point extremely close to destination (should raise error)
        with self.assertRaises(ValueError) as context:
            pencil.spline((50, 50), (1, 0), intermediate_points=[(25, 25), (49.9999999, 49.9999999)])

        self.assertIn("intermediate point 1 and destination", str(context.exception))

    def test_duplicate_intermediate_points_raises_error(self):
        """Test that duplicate intermediate points raise ValueError."""
        pencil = Pencil()

        # Use two intermediate points that are extremely close to each other
        with self.assertRaises(ValueError) as context:
            pencil.spline((50, 50), (1, 0), intermediate_points=[(25, 25), (25.0000001, 25.0000001)])

        self.assertIn("intermediate point 0 and intermediate point 1", str(context.exception))

    def test_spline_with_vector_intermediate_points(self):
        """Test that intermediate points can be Vector objects, not just tuples."""
        pencil = Pencil()
        intermediate = [Vector(20, 30), Vector(40, 20)]
        result = pencil.spline((50, 50), (1, 0), intermediate_points=intermediate)

        # Should work with Vector objects
        self.assertIs(result, pencil)
        self.assertEqual(len(pencil.curves), 1)
        self.assertTrue(pencil.curves[0].is_valid)

    def test_spline_with_mixed_intermediate_point_types(self):
        """Test that intermediate points can be a mix of tuples and Vectors."""
        pencil = Pencil()
        intermediate = [(20, 30), Vector(40, 20), (45, 45)]
        result = pencil.spline((50, 50), (1, 0), intermediate_points=intermediate)

        # Should work with mixed types
        self.assertIs(result, pencil)
        self.assertEqual(len(pencil.curves), 1)
        self.assertTrue(pencil.curves[0].is_valid)

    @parameterized.expand([
        ("no_intermediate", None, 1),
        ("empty_list", [], 1),
        ("one_point", [(25, 25)], 1),
        ("two_points", [(20, 30), (40, 20)], 1),
        ("three_points", [(15, 20), (30, 35), (45, 25)], 1),
    ])
    def test_spline_curve_count(self, name, intermediate, expected_curves):
        """Test that spline always creates exactly one curve regardless of intermediate points."""
        pencil = Pencil()
        pencil.spline((50, 50), (1, 0), intermediate_points=intermediate)

        self.assertEqual(len(pencil.curves), expected_curves,
                        f"Should have {expected_curves} curve(s) for {name}")

    def test_chaining_multiple_splines(self):
        """Test that multiple spline calls can be chained together."""
        pencil = Pencil()
        pencil.spline((25, 25), (1, 0)).spline((50, 0), (0, -1), intermediate_points=[(10, 10)])

        # Should have two curves
        self.assertEqual(len(pencil.curves), 2)

        # Both curves should be valid
        self.assertTrue(pencil.curves[0].is_valid)
        self.assertTrue(pencil.curves[1].is_valid)

        # Final location should be at second destination (25,25) + (50,0) = (75,25)
        self.assertAlmostEqual(pencil.location.X, 75)
        self.assertAlmostEqual(pencil.location.Y, 25)

    def test_spline_with_custom_start_tangent(self):
        """Test spline with custom start tangent."""
        pencil = Pencil()
        result = pencil.spline((50, 50), (1, 0), start_tangent=(0, 1))

        # Should return self for method chaining
        self.assertIs(result, pencil)

        # Should have one curve
        self.assertEqual(len(pencil.curves), 1)

        # Curve should be valid
        self.assertTrue(pencil.curves[0].is_valid)

        # Location should be at destination
        self.assertAlmostEqual(pencil.location.X, 50)
        self.assertAlmostEqual(pencil.location.Y, 50)

    def test_spline_with_start_tangent_and_intermediate_points(self):
        """Test spline with both custom start tangent and intermediate points."""
        pencil = Pencil()
        result = pencil.spline((50, 50), (1, 0), intermediate_points=[(25, 25)], start_tangent=(0, 1))

        # Should return self for method chaining
        self.assertIs(result, pencil)

        # Should have one curve
        self.assertEqual(len(pencil.curves), 1)

        # Curve should be valid
        self.assertTrue(pencil.curves[0].is_valid)

        # Location should be at destination
        self.assertAlmostEqual(pencil.location.X, 50)
        self.assertAlmostEqual(pencil.location.Y, 50)

    def test_spline_with_vector_start_tangent(self):
        """Test that start_tangent can be a Vector object."""
        pencil = Pencil()
        result = pencil.spline((50, 50), (1, 0), start_tangent=Vector(0, 1))

        # Should work with Vector object
        self.assertIs(result, pencil)
        self.assertEqual(len(pencil.curves), 1)
        self.assertTrue(pencil.curves[0].is_valid)

    def test_spline_start_tangent_overrides_calculated(self):
        """Test that start_tangent overrides the auto-calculated tangent from previous curve."""
        pencil = Pencil()

        # First spline ending with tangent pointing right (1, 0)
        pencil.spline((25, 25), (1, 0))

        # Second spline with custom start_tangent pointing up (0, 1),
        # which should override the calculated tangent from first curve
        pencil.spline((50, 0), (0, -1), start_tangent=(0, 1))

        # Should have two curves
        self.assertEqual(len(pencil.curves), 2)

        # Both curves should be valid
        self.assertTrue(pencil.curves[0].is_valid)
        self.assertTrue(pencil.curves[1].is_valid)


if __name__ == '__main__':
    unittest.main()
