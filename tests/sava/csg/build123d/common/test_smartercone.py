import unittest

from build123d import Plane
from parameterized import parameterized

from sava.csg.build123d.common.smartercone import SmarterCone


class TestSmarterConeShell(unittest.TestCase):

    def test_slope_property(self):
        """Test that slope property calculates correctly"""
        # Normal cone (narrows)
        cone1 = SmarterCone(50, 30, 100)
        self.assertAlmostEqual(cone1.slope, -0.2, places=5)

        # Cylinder (constant radius)
        cone2 = SmarterCone(50, 50, 100)
        self.assertAlmostEqual(cone2.slope, 0, places=5)

        # Inverted cone (widens)
        cone3 = SmarterCone(30, 50, 100)
        self.assertAlmostEqual(cone3.slope, 0.2, places=5)

    def test_shell_positive_updates_properties(self):
        """Test that positive thickness properly updates cone properties (outer shell)"""
        original_base = 50
        original_top = 30
        original_height = 100

        cone = SmarterCone(original_base, original_top, original_height)
        cone.create_shell(thickness_radius=2)

        # Should store thickness values
        self.assertEqual(cone.thickness_radius, 2)
        self.assertEqual(cone.thickness_base, 0)
        self.assertEqual(cone.thickness_top, 0)

        # For positive thickness (outer shell), properties should be updated to larger cone
        slope = (original_top - original_base) / original_height
        expected_base = original_base - slope * 0 + 2
        expected_top = original_top + slope * 0 + 2

        self.assertAlmostEqual(cone.base_radius, expected_base, places=5)
        self.assertAlmostEqual(cone.top_radius, expected_top, places=5)
        self.assertEqual(cone.height, original_height)

    def test_shell_negative_thickness(self):
        """Test shell with negative thickness (inner shell - hollow from inside)"""
        original_base = 50
        original_top = 30
        original_height = 100

        cone = SmarterCone(original_base, original_top, original_height)
        cone.create_shell(thickness_radius=-2, thickness_base=-1, thickness_top=-1)

        # Should store all thickness values
        self.assertEqual(cone.thickness_radius, -2)
        self.assertEqual(cone.thickness_base, -1)
        self.assertEqual(cone.thickness_top, -1)

        # For negative thickness (inner shell), original dimensions should remain
        self.assertAlmostEqual(cone.base_radius, original_base, places=5)
        self.assertAlmostEqual(cone.top_radius, original_top, places=5)
        self.assertAlmostEqual(cone.height, original_height, places=5)


    def test_shell_prevents_double_shelling(self):
        """Test that shell cannot be called twice"""
        cone = SmarterCone(50, 30, 100)
        cone.create_shell(thickness_radius=2)

        # Second call should raise assertion error
        with self.assertRaises(AssertionError) as context:
            cone.create_shell(thickness_radius=1)

        self.assertIn("Already a shell", str(context.exception))

    def test_shell_requires_nonzero_thickness(self):
        """Test that thickness must be non-zero"""
        cone = SmarterCone(50, 30, 100)

        with self.assertRaises(AssertionError) as context:
            cone.create_shell(thickness_radius=0)

        self.assertIn("thickness must be non-zero", str(context.exception))

    def test_shell_requires_consistent_signs_base(self):
        """Test that thickness_base must have same sign as thickness_radius"""
        cone = SmarterCone(50, 30, 100)

        # Positive radius, negative base should fail
        with self.assertRaises(AssertionError) as context:
            cone.create_shell(thickness_radius=2, thickness_base=-1)

        self.assertIn("thickness_base must have the same sign", str(context.exception))

    def test_shell_requires_consistent_signs_top(self):
        """Test that thickness_top must have same sign as thickness_radius"""
        cone = SmarterCone(50, 30, 100)

        # Positive radius, negative top should fail
        with self.assertRaises(AssertionError) as context:
            cone.create_shell(thickness_radius=2, thickness_top=-1)

        self.assertIn("thickness_top must have the same sign", str(context.exception))

    @parameterized.expand([
        (2, 1, 1),      # All positive
        (-2, -1, -1),   # All negative
        (5, 0, 0),      # Only radial thickness
        (3, 2, 0),      # Radial + base
        (3, 0, 2),      # Radial + top
        (-4, -2, 0),    # Negative radial + base
        (-4, 0, -2),    # Negative radial + top
    ])
    def test_shell_various_valid_combinations(self, thickness_radius, thickness_base, thickness_top):
        """Test shell with various valid thickness combinations"""
        cone = SmarterCone(50, 30, 100)
        cone.create_shell(thickness_radius=thickness_radius, thickness_base=thickness_base, thickness_top=thickness_top)

        self.assertEqual(cone.thickness_radius, thickness_radius)
        self.assertEqual(cone.thickness_base, thickness_base)
        self.assertEqual(cone.thickness_top, thickness_top)

    def test_shell_returns_self(self):
        """Test that shell returns self for method chaining"""
        cone = SmarterCone(50, 30, 100)
        result = cone.create_shell(thickness_radius=2)

        self.assertIs(result, cone)

    def test_shell_sets_inner_cone_positive_thickness(self):
        """Test that inner_cone is set correctly for positive thickness (outer shell)"""
        original_base = 50
        original_top = 30
        original_height = 100

        cone = SmarterCone(original_base, original_top, original_height)

        # Initially inner_cone should be None
        self.assertIsNone(cone.inner_cone)

        cone.create_shell(thickness_radius=2, thickness_base=1, thickness_top=1)

        # After shelling, inner_cone should be set to the original cone
        self.assertIsNotNone(cone.inner_cone)
        self.assertIsInstance(cone.inner_cone, SmarterCone)

        # Inner cone should have the original dimensions
        self.assertAlmostEqual(cone.inner_cone.base_radius, original_base, places=5)
        self.assertAlmostEqual(cone.inner_cone.top_radius, original_top, places=5)
        self.assertAlmostEqual(cone.inner_cone.height, original_height, places=5)

    def test_shell_sets_inner_cone_negative_thickness(self):
        """Test that inner_cone is set correctly for negative thickness (inner shell)"""
        original_base = 50
        original_top = 30
        original_height = 100

        cone = SmarterCone(original_base, original_top, original_height)

        # Initially inner_cone should be None
        self.assertIsNone(cone.inner_cone)

        cone.create_shell(thickness_radius=-2, thickness_base=-1, thickness_top=-1)

        # After shelling, inner_cone should be set to the offset cone
        self.assertIsNotNone(cone.inner_cone)
        self.assertIsInstance(cone.inner_cone, SmarterCone)

        # Inner cone should have the calculated offset dimensions
        slope = (original_top - original_base) / original_height
        expected_inner_base = original_base - slope * (-1) + (-2)
        expected_inner_top = original_top + slope * (-1) + (-2)
        expected_inner_height = original_height + (-1) + (-1)

        self.assertAlmostEqual(cone.inner_cone.base_radius, expected_inner_base, places=5)
        self.assertAlmostEqual(cone.inner_cone.top_radius, expected_inner_top, places=5)
        self.assertAlmostEqual(cone.inner_cone.height, expected_inner_height, places=5)

        # The main cone should keep original dimensions
        self.assertAlmostEqual(cone.base_radius, original_base, places=5)
        self.assertAlmostEqual(cone.top_radius, original_top, places=5)
        self.assertAlmostEqual(cone.height, original_height, places=5)

    def test_shell_inner_cone_inherits_properties(self):
        """Test that inner_cone inherits plane and angle from parent"""
        cone = SmarterCone(50, 30, 100, plane=Plane.XZ, angle=180)
        cone.create_shell(thickness_radius=2)

        # Inner cone should have same plane and angle
        self.assertEqual(cone.inner_cone.plane, Plane.XZ)
        self.assertEqual(cone.inner_cone.angle, 180)

    def test_copy_returns_smartercone(self):
        """Test that copy() returns a SmarterCone instance"""
        cone = SmarterCone(50, 30, 100, plane=Plane.XZ, angle=180)
        cone.create_shell(thickness_radius=2, thickness_base=1, thickness_top=1)

        copied = cone.copy()

        # Should be a SmarterCone
        self.assertIsInstance(copied, SmarterCone)

        # Should have same properties
        self.assertAlmostEqual(copied.base_radius, cone.base_radius, places=5)
        self.assertAlmostEqual(copied.top_radius, cone.top_radius, places=5)
        self.assertAlmostEqual(copied.height, cone.height, places=5)
        self.assertEqual(copied.plane, cone.plane)
        self.assertEqual(copied.angle, cone.angle)
        self.assertEqual(copied.thickness_radius, cone.thickness_radius)
        self.assertEqual(copied.thickness_base, cone.thickness_base)
        self.assertEqual(copied.thickness_top, cone.thickness_top)


class TestSmarterConeCreateOffsetCone(unittest.TestCase):

    def test_create_offset_cone_positive_radius(self):
        """Test creating offset cone with positive radial thickness"""
        original = SmarterCone(50, 30, 100)
        offset = original.create_offset(thickness_radius=2)

        # Should be larger
        self.assertAlmostEqual(offset.base_radius, 52, places=5)
        self.assertAlmostEqual(offset.top_radius, 32, places=5)
        self.assertEqual(offset.height, 100)

    def test_create_offset_cone_negative_radius(self):
        """Test creating offset cone with negative radial thickness"""
        original = SmarterCone(50, 30, 100)
        offset = original.create_offset(thickness_radius=-2)

        # Should be smaller
        self.assertAlmostEqual(offset.base_radius, 48, places=5)
        self.assertAlmostEqual(offset.top_radius, 28, places=5)
        self.assertEqual(offset.height, 100)

    def test_create_offset_cone_with_base_and_top(self):
        """Test creating offset cone with base and top thickness"""
        original = SmarterCone(50, 30, 100)
        offset = original.create_offset(thickness_radius=2, thickness_base=5, thickness_top=10)

        # Calculate expected values
        slope = (30 - 50) / 100  # -0.2
        expected_base = 50 - slope * 5 + 2  # 50 + 1 + 2 = 53
        expected_top = 30 + slope * 10 + 2  # 30 - 2 + 2 = 30
        expected_height = 100 + 5 + 10  # 115

        self.assertAlmostEqual(offset.base_radius, expected_base, places=5)
        self.assertAlmostEqual(offset.top_radius, expected_top, places=5)
        self.assertEqual(offset.height, expected_height)

    def test_create_offset_cone_zero_thickness_allowed(self):
        """Test that create_offset_cone allows zero thickness (unlike shell)"""
        original = SmarterCone(50, 30, 100)

        # Should not raise an error (unlike shell method)
        offset = original.create_offset(thickness_radius=0)

        # Should have same dimensions
        self.assertAlmostEqual(offset.base_radius, 50, places=5)
        self.assertAlmostEqual(offset.top_radius, 30, places=5)
        self.assertEqual(offset.height, 100)

    def test_create_offset_cone_mixed_signs_allowed(self):
        """Test that create_offset_cone allows mixed signs (unlike shell)"""
        original = SmarterCone(50, 30, 100)

        # Should not raise an error (unlike shell method)
        offset = original.create_offset(thickness_radius=2, thickness_base=-1, thickness_top=1)

        # Calculate expected values
        slope = (30 - 50) / 100
        expected_base = 50 - slope * (-1) + 2
        expected_top = 30 + slope * 1 + 2
        expected_height = 100 + (-1) + 1

        self.assertAlmostEqual(offset.base_radius, expected_base, places=5)
        self.assertAlmostEqual(offset.top_radius, expected_top, places=5)
        self.assertEqual(offset.height, expected_height)

    def test_create_offset_cone_inherits_plane_and_angle(self):
        """Test that offset cone inherits plane and angle from original"""
        original = SmarterCone(50, 30, 100, plane=Plane.XZ, angle=180)
        offset = original.create_offset(thickness_radius=2)

        self.assertEqual(offset.plane, Plane.XZ)
        self.assertEqual(offset.angle, 180)

    def test_create_offset_cone_returns_smartercone(self):
        """Test that create_offset_cone returns SmarterCone instance"""
        original = SmarterCone(50, 30, 100)
        offset = original.create_offset(thickness_radius=2)

        self.assertIsInstance(offset, SmarterCone)

    def test_create_offset_cone_inverted_cone(self):
        """Test create_offset_cone on inverted cone (top > base)"""
        original = SmarterCone(30, 50, 100)
        offset = original.create_offset(thickness_radius=2, thickness_base=1, thickness_top=1)

        slope = (50 - 30) / 100  # 0.2
        expected_base = 30 - slope * 1 + 2  # 30 - 0.2 + 2 = 31.8
        expected_top = 50 + slope * 1 + 2   # 50 + 0.2 + 2 = 52.2
        expected_height = 100 + 1 + 1        # 102

        self.assertAlmostEqual(offset.base_radius, expected_base, places=5)
        self.assertAlmostEqual(offset.top_radius, expected_top, places=5)
        self.assertEqual(offset.height, expected_height)

    def test_create_offset_cone_negative_top_radius_adjustment(self):
        """Test that negative top radius is adjusted to 0 when thickness_top is 0"""
        # Create cone where large negative thickness_radius would make top negative
        original = SmarterCone(50, 30, 100)
        # thickness_radius = -40 would make top_radius = 30 + (-40) = -10
        offset = original.create_offset(thickness_radius=-40, thickness_top=0)

        # Top radius should be clamped to 0 (pointed cone)
        self.assertAlmostEqual(offset.top_radius, 0, places=5)

        # Base radius: 50 + (-40) = 10, should remain as is
        self.assertAlmostEqual(offset.base_radius, 10, places=5)

        # Height should be adjusted
        # Solve: 0 = 30 + slope * adjusted_thickness_top + (-40)
        # slope = (30 - 50) / 100 = -0.2
        # adjusted_thickness_top = -(30 + (-40)) / slope = -(-10) / -0.2 = -50
        slope = (30 - 50) / 100
        expected_thickness_top = -(30 + (-40)) / slope
        expected_height = 100 + 0 + expected_thickness_top
        self.assertAlmostEqual(offset.height, expected_height, places=3)

    def test_create_offset_cone_no_adjustment_when_thickness_specified(self):
        """Test that radii are NOT adjusted when corresponding thickness is non-zero"""
        original = SmarterCone(50, 30, 100)
        # If thickness_base/top are non-zero, don't adjust even if radii would be small
        # Use smaller negative thickness to keep radii positive
        offset = original.create_offset(thickness_radius=-10, thickness_base=1, thickness_top=1)

        # Radii calculation should proceed without adjustment
        slope = (30 - 50) / 100
        expected_base = 50 - slope * 1 + (-10)  # 50 + 0.2 - 10 = 40.2
        expected_top = 30 + slope * 1 + (-10)   # 30 - 0.2 - 10 = 19.8

        self.assertAlmostEqual(offset.base_radius, expected_base, places=5)
        self.assertAlmostEqual(offset.top_radius, expected_top, places=5)
        self.assertEqual(offset.height, 102)

    def test_create_offset_cone_pointed_cone_valid(self):
        """Test that creating a pointed cone (one radius = 0) is valid"""
        original = SmarterCone(50, 30, 100)
        # Create offset that makes top = 0 (pointed cone)
        offset = original.create_offset(thickness_radius=-30)

        # Top should be 0, base should be 20
        self.assertAlmostEqual(offset.top_radius, 0, places=5)
        self.assertAlmostEqual(offset.base_radius, 20, places=5)
        # This should be a valid cone (no adjustments needed)

    def test_create_offset_cone_positioning_positive_thickness(self):
        """Test that offset cone is positioned correctly with positive thickness"""
        original = SmarterCone(50, 30, 100)
        offset = original.create_offset(thickness_radius=2, thickness_base=5, thickness_top=3)

        # With positive thickness_base, offset cone should extend downward
        # Original base at z=0, offset should be at z=-5
        self.assertAlmostEqual(offset.z_min, original.z_min - 5, places=5)
        # Original top at z=100, offset should be at z=103
        self.assertAlmostEqual(offset.z_max, original.z_max + 3, places=5)

    def test_create_offset_cone_positioning_negative_thickness(self):
        """Test that offset cone is positioned correctly with negative thickness"""
        original = SmarterCone(50, 30, 100)
        offset = original.create_offset(thickness_radius=-2, thickness_base=-5, thickness_top=-3)

        # With negative thickness_base, offset cone should start higher
        # Original base at z=0, offset should be at z=+5
        self.assertAlmostEqual(offset.z_min, original.z_min + 5, places=5)
        # Original top at z=100, offset should be at z=97
        self.assertAlmostEqual(offset.z_max, original.z_max - 3, places=5)

    def test_create_offset_cone_positioning_pointed_base_negative_thickness(self):
        """Test positioning with pointed base (0 radius) and negative thickness"""
        # This is the specific case reported by the user
        original = SmarterCone(0, 50, 100)
        offset = original.create_offset(thickness_radius=-2, thickness_base=-5, thickness_top=-5)

        # Inner shell should be positioned INSIDE (higher z_min)
        self.assertAlmostEqual(offset.z_min, original.z_min + 5, places=5)
        self.assertAlmostEqual(offset.z_max, original.z_max - 5, places=5)


class TestSmarterConeThicknessSide(unittest.TestCase):

    def test_create_offset_cone_thickness_side_basic(self):
        """Test creating offset cone with thickness_side parameter"""
        from math import sqrt
        original = SmarterCone(50, 30, 100)
        offset = original.create_offset(thickness_side=2)

        # Calculate expected thickness_radius from thickness_side
        slope = (30 - 50) / 100  # -0.2
        expected_thickness_radius = 2 / sqrt(1 + slope * slope)

        # Should be larger by the converted amount
        self.assertAlmostEqual(offset.base_radius, 50 + expected_thickness_radius, places=5)
        self.assertAlmostEqual(offset.top_radius, 30 + expected_thickness_radius, places=5)

    def test_create_offset_cone_cannot_specify_both_thickness_types(self):
        """Test that specifying both thickness_radius and thickness_side raises error"""
        original = SmarterCone(50, 30, 100)

        with self.assertRaises(AssertionError) as context:
            original.create_offset(thickness_radius=2, thickness_side=2)

        self.assertIn("exactly one", str(context.exception))

    def test_create_offset_cone_must_specify_one_thickness_type(self):
        """Test that omitting both thickness_radius and thickness_side raises error"""
        original = SmarterCone(50, 30, 100)

        with self.assertRaises(AssertionError) as context:
            original.create_offset(thickness_base=1)

        self.assertIn("exactly one", str(context.exception))

    def test_shell_thickness_side_basic(self):
        """Test shell with thickness_side parameter"""
        from math import sqrt
        original = SmarterCone(50, 30, 100)
        cone = SmarterCone(50, 30, 100)
        cone.create_shell(thickness_side=2)

        # Should store converted thickness_radius
        slope = (30 - 50) / 100
        expected_thickness_radius = 2 / sqrt(1 + slope * slope)
        self.assertAlmostEqual(cone.thickness_radius, expected_thickness_radius, places=5)

    def test_shell_thickness_side_negative(self):
        """Test shell with negative thickness_side (inner shell)"""
        from math import sqrt
        cone = SmarterCone(50, 30, 100)
        cone.create_shell(thickness_base=-1, thickness_top=-1, thickness_side=-2)

        # Should store converted negative thickness_radius
        slope = (30 - 50) / 100
        expected_thickness_radius = -2 / sqrt(1 + slope * slope)
        self.assertAlmostEqual(cone.thickness_radius, expected_thickness_radius, places=5)

    def test_shell_cannot_specify_both_thickness_types(self):
        """Test that shell with both thickness types raises error"""
        cone = SmarterCone(50, 30, 100)

        with self.assertRaises(AssertionError) as context:
            cone.create_shell(thickness_radius=2, thickness_side=2)

        self.assertIn("exactly one", str(context.exception))

    def test_thickness_side_cylinder(self):
        """Test thickness_side on cylinder (slope=0)"""
        cone = SmarterCone(50, 50, 100)  # Cylinder
        offset = cone.create_offset(thickness_side=2)

        # For cylinder, slope=0, so thickness_side = thickness_radius
        # sqrt(1 + 0^2) = 1
        self.assertAlmostEqual(offset.base_radius, 52, places=5)
        self.assertAlmostEqual(offset.top_radius, 52, places=5)

    def test_thickness_side_steep_cone(self):
        """Test thickness_side on steep cone"""
        from math import sqrt
        cone = SmarterCone(50, 10, 100)
        offset = cone.create_offset(thickness_side=5)

        # Calculate expected conversion
        slope = (10 - 50) / 100  # -0.4
        expected_thickness_radius = 5 / sqrt(1 + slope * slope)

        self.assertAlmostEqual(offset.base_radius, 50 + expected_thickness_radius, places=4)
        self.assertAlmostEqual(offset.top_radius, 10 + expected_thickness_radius, places=4)


if __name__ == '__main__':
    unittest.main()
