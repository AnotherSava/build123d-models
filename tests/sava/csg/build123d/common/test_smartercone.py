import unittest

from build123d import Plane, Vector
from parameterized import parameterized

from sava.csg.build123d.common.geometry import MIN_SIZE_OCCT, are_points_too_close
from sava.csg.build123d.common.smartercone import SmarterCone


class TestSmarterConeShell(unittest.TestCase):

    def test_shell_positive_creates_correct_geometry(self):
        """Test that positive thickness creates outer shell with correct sections"""
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        shell = cone.create_shell(2)

        self.assertAlmostEqual(shell.sections[0].radius, 52, places=5)
        self.assertAlmostEqual(shell.sections[0].inner_radius, 50, places=5)
        self.assertAlmostEqual(shell.sections[1].radius, 32, places=5)
        self.assertAlmostEqual(shell.sections[1].inner_radius, 30, places=5)
        self.assertAlmostEqual(shell.height, 100)

    def test_shell_negative_creates_correct_geometry(self):
        """Test shell with negative thickness (inner shell)"""
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        shell = cone.create_shell(-2)

        self.assertAlmostEqual(shell.sections[0].radius, 50, places=5)
        self.assertAlmostEqual(shell.sections[0].inner_radius, 48, places=5)
        self.assertAlmostEqual(shell.sections[1].radius, 30, places=5)
        self.assertAlmostEqual(shell.sections[1].inner_radius, 28, places=5)
        self.assertAlmostEqual(shell.height, 100)

    def test_shell_prevents_double_shelling(self):
        """Test that shell cannot be called on already hollow cone"""
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        shell = cone.create_shell(2)

        with self.assertRaises(AssertionError) as context:
            shell.create_shell(1)

        self.assertIn("already hollow", str(context.exception).lower())

    def test_shell_requires_nonzero_thickness(self):
        """Test that thickness must be non-zero"""
        cone = SmarterCone.base(50).extend(radius=30, height=100)

        with self.assertRaises(AssertionError) as context:
            cone.create_shell(0)

        self.assertIn("non-zero", str(context.exception).lower())

    @parameterized.expand([
        (2,),
        (-2,),
        (5,),
        (-4,),
    ])
    def test_shell_valid_combinations(self, thickness):
        """Test shell with various valid thickness values"""
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        shell = cone.create_shell(thickness)
        self.assertTrue(shell.has_inner)

    def test_shell_returns_new_instance(self):
        """Test that shell returns new instance, not self"""
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        shell = cone.create_shell(2)
        self.assertIsNot(shell, cone)
        self.assertIsInstance(shell, SmarterCone)

    def test_shell_inherits_plane_and_angle(self):
        """Test that shell inherits plane and angle"""
        cone = SmarterCone.base(50, plane=Plane.XZ, angle=180).extend(radius=30, height=100)
        shell = cone.create_shell(2)
        self.assertEqual(shell.plane, Plane.XZ)
        self.assertEqual(shell.angle, 180)

    def test_copy_returns_smartercone(self):
        """Test that copy() returns a SmarterCone instance"""
        cone = SmarterCone.base(50, plane=Plane.XZ, angle=180).extend(radius=30, height=100)
        copied = cone.copy()

        self.assertIsInstance(copied, SmarterCone)
        self.assertAlmostEqual(copied.base_radius, cone.base_radius, places=5)
        self.assertAlmostEqual(copied.top_radius, cone.top_radius, places=5)
        self.assertAlmostEqual(copied.height, cone.height, places=5)
        self.assertEqual(copied.plane, cone.plane)
        self.assertEqual(copied.angle, cone.angle)


class TestSmarterConeCreateOffset(unittest.TestCase):

    def test_create_offset_positive_radius(self):
        """Test creating offset cone with positive radial thickness"""
        original = SmarterCone.base(50).extend(radius=30, height=100)
        offset = original.create_offset(2)

        self.assertAlmostEqual(offset.base_radius, 52, places=5)
        self.assertAlmostEqual(offset.top_radius, 32, places=5)
        self.assertEqual(offset.height, 100)

    def test_create_offset_negative_radius(self):
        """Test creating offset cone with negative radial thickness"""
        original = SmarterCone.base(50).extend(radius=30, height=100)
        offset = original.create_offset(-2)

        self.assertAlmostEqual(offset.base_radius, 48, places=5)
        self.assertAlmostEqual(offset.top_radius, 28, places=5)
        self.assertEqual(offset.height, 100)

    def test_create_offset_zero_allowed(self):
        """Test that zero offset is allowed"""
        original = SmarterCone.base(50).extend(radius=30, height=100)
        offset = original.create_offset(0)
        self.assertAlmostEqual(offset.base_radius, 50, places=5)
        self.assertAlmostEqual(offset.top_radius, 30, places=5)

    def test_create_offset_inherits_plane_and_angle(self):
        """Test that offset cone inherits plane and angle"""
        original = SmarterCone.base(50, plane=Plane.XZ, angle=180).extend(radius=30, height=100)
        offset = original.create_offset(2)
        self.assertEqual(offset.plane, Plane.XZ)
        self.assertEqual(offset.angle, 180)

    def test_create_offset_returns_smartercone(self):
        """Test that create_offset returns SmarterCone instance"""
        original = SmarterCone.base(50).extend(radius=30, height=100)
        offset = original.create_offset(2)
        self.assertIsInstance(offset, SmarterCone)

    def test_create_offset_inverted_cone(self):
        """Test create_offset on inverted cone (top > base)"""
        original = SmarterCone.base(30).extend(radius=50, height=100)
        offset = original.create_offset(2)
        self.assertAlmostEqual(offset.base_radius, 32, places=5)
        self.assertAlmostEqual(offset.top_radius, 52, places=5)

    def test_create_offset_positioning(self):
        """Test that offset cone is colocated with original"""
        original = SmarterCone.base(50).extend(radius=30, height=100)
        offset = original.create_offset(2)
        self.assertAlmostEqual(offset.z_min, original.z_min, places=3)
        self.assertAlmostEqual(offset.z_max, original.z_max, places=3)


class TestSmarterConeShift(unittest.TestCase):

    def test_shifted_cone_bounding_box(self):
        """Test that shifted cone has correct bounding box"""
        cone = SmarterCone.base(20).extend(radius=20, height=100, shift_x=30)
        self.assertAlmostEqual(cone.x_min, -20, places=1)
        self.assertAlmostEqual(cone.x_max, 50, places=1)
        self.assertAlmostEqual(cone.z_min, 0, places=1)
        self.assertAlmostEqual(cone.z_max, 100, places=1)

    def test_shifted_cone_partial_sector(self):
        """Test that shifted cone with angle < 360 creates valid geometry"""
        cone = SmarterCone.base(30, angle=180).extend(radius=20, height=80, shift_x=10)
        self.assertAlmostEqual(cone.z_min, 0, places=1)
        self.assertAlmostEqual(cone.z_max, 80, places=1)

    def test_shifted_cone_zero_top_radius(self):
        """Test shifted cone with radius approaching 0"""
        cone = SmarterCone.base(30).extend(radius=0.001, height=100, shift_x=15)
        self.assertAlmostEqual(cone.z_min, 0, places=1)
        self.assertAlmostEqual(cone.z_max, 100, places=1)

    @parameterized.expand([
        (0.0, Vector(0, 0, 0)),
        (0.5, Vector(5, 2.5, 50)),
        (1.0, Vector(10, 5, 100)),
    ])
    def test_center_interpolates_shift(self, position, expected):
        """Test that center() interpolates shift correctly"""
        cone = SmarterCone.base(30).extend(radius=20, height=100, shift_x=10, shift_y=5)
        result = cone.center(position)
        self.assertTrue(are_points_too_close(result, expected), f"Expected {expected}, got {result}")

    def test_copy_preserves_sections(self):
        """Test that copy() preserves sections including shifts"""
        cone = SmarterCone.base(50).extend(radius=30, height=100, shift_x=10, shift_y=5)
        copied = cone.copy()
        self.assertEqual(len(copied.sections), len(cone.sections))
        self.assertAlmostEqual(copied.sections[1].shift_x, 10)
        self.assertAlmostEqual(copied.sections[1].shift_y, 5)
        self.assertIsInstance(copied, SmarterCone)

    def test_create_offset_with_shift(self):
        """Test create_offset preserves shift in sections"""
        cone = SmarterCone.base(50).extend(radius=30, height=100, shift_x=20)
        offset = cone.create_offset(2)
        self.assertAlmostEqual(offset.sections[1].shift_x, 20)
        self.assertGreater(offset.base_radius, cone.base_radius)


class TestSmarterConeInnerRadius(unittest.TestCase):

    def test_base_with_inner_radius(self):
        """Test that base().inner() creates section with inner_radius"""
        cone = SmarterCone.base(50).inner(40)
        self.assertAlmostEqual(cone.sections[0].inner_radius, 40)
        self.assertTrue(cone.has_inner)

    def test_cylinder_with_inner_radius(self):
        """Test that cylinder().inner() creates last section with inner_radius"""
        cone = SmarterCone.cylinder(50, 100).inner(40)
        self.assertAlmostEqual(cone.sections[1].inner_radius, 40)
        self.assertTrue(cone.has_inner)

    def test_extend_auto_propagates_inner_radius(self):
        """Test that extend auto-propagates inner_radius maintaining wall thickness"""
        cone = SmarterCone.base(50).inner(40).extend(radius=30, height=100)
        # Wall thickness = 50 - 40 = 10, so inner_radius = 30 - 10 = 20
        self.assertAlmostEqual(cone.sections[1].inner_radius, 20)

    def test_inner_overrides_auto_propagation(self):
        """Test that inner() overrides auto-propagated inner_radius"""
        cone = SmarterCone.base(50).inner(40).extend(radius=30, height=100).inner(25)
        self.assertAlmostEqual(cone.sections[1].inner_radius, 25)

    def test_inner_zero_stops_propagation(self):
        """Test that inner(0) stops propagation"""
        cone = SmarterCone.base(50).inner(40).extend(radius=30, height=100).inner(0)
        self.assertIsNone(cone.sections[1].inner_radius)

    def test_extend_no_propagation_without_prior_inner(self):
        """Test that extend without prior inner_radius leaves it as None"""
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        self.assertIsNone(cone.sections[1].inner_radius)

    def test_chained_extends_propagate_inner_radius(self):
        """Test that chained extends all propagate inner_radius"""
        cone = SmarterCone.base(50).inner(40).extend(radius=30, height=100).extend(radius=20, height=100)
        # Wall thickness = 10 throughout
        self.assertAlmostEqual(cone.sections[1].inner_radius, 20)  # 30 - 10
        self.assertAlmostEqual(cone.sections[2].inner_radius, 10)  # 20 - 10

    def test_extend_auto_propagate_clamps_to_min(self):
        """Test that auto-propagation clamps inner_radius to OCCT_MIN_SIZE"""
        # Wall thickness = 50 - 40 = 10, new radius = 8, so inner would be -2 → clamped
        cone = SmarterCone.base(50).inner(40).extend(radius=8, height=100)
        self.assertAlmostEqual(cone.sections[1].inner_radius, MIN_SIZE_OCCT)

    def test_fillet_sections_propagate_inner_radius(self):
        """Test that fillet sections get inner_radius when junction has it"""
        cone = SmarterCone.base(50).inner(40).extend(radius=50, height=50).extend(radius=30, height=50, fillet=5)
        # All sections between the fillet should have inner_radius
        for s in cone.sections:
            if s.inner_radius is not None:
                self.assertGreater(s.inner_radius, 0)
        self.assertTrue(cone.has_inner)

    def test_fillet_sections_no_inner_without_junction_inner(self):
        """Test that fillet sections don't get inner_radius when junction has none"""
        cone = SmarterCone.base(50).extend(radius=50, height=50).extend(radius=30, height=50, fillet=5)
        for s in cone.sections:
            self.assertIsNone(s.inner_radius)


class TestSmarterConeInner(unittest.TestCase):

    def test_inner_sets_inner_radius_on_last_section(self):
        """Test that inner() sets inner_radius on the last section"""
        cone = SmarterCone.base(50).extend(radius=30, height=100).inner(20)
        self.assertAlmostEqual(cone.sections[-1].inner_radius, 20)

    def test_inner_zero_clears_all_inner_properties(self):
        """Test that inner(0) clears inner_radius and inner shifts"""
        cone = SmarterCone.base(50).extend(radius=30, height=100).inner(20, shift_x=5, shift_y=3)
        cone.inner(0)
        self.assertIsNone(cone.sections[-1].inner_radius)
        self.assertIsNone(cone.sections[-1].inner_shift_x)
        self.assertIsNone(cone.sections[-1].inner_shift_y)

    def test_inner_with_shifts(self):
        """Test that inner() sets shift_x and shift_y"""
        cone = SmarterCone.base(50).extend(radius=30, height=100).inner(20, shift_x=5, shift_y=3)
        self.assertAlmostEqual(cone.sections[-1].inner_radius, 20)
        self.assertAlmostEqual(cone.sections[-1].inner_shift_x, 5)
        self.assertAlmostEqual(cone.sections[-1].inner_shift_y, 3)

    def test_inner_returns_self(self):
        """Test that inner() returns self for chaining"""
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        result = cone.inner(20)
        self.assertIs(result, cone)

    def test_inner_on_base_section(self):
        """Test that inner() works on base section"""
        cone = SmarterCone.base(50).inner(40)
        self.assertAlmostEqual(cone.sections[0].inner_radius, 40)
        self.assertTrue(cone.has_inner)

    def test_inner_propagates_through_extend(self):
        """Test that inner radius and shifts propagate through extend"""
        cone = SmarterCone.base(50).extend(radius=50, height=50).inner(40, shift_x=5, shift_y=3).extend(radius=30, height=50)
        # Wall thickness = 50 - 40 = 10, so inner = 30 - 10 = 20
        self.assertAlmostEqual(cone.sections[-1].inner_radius, 20)
        # Inner shift offset = 5 - 0 = 5 (shift_x of section is 0), new shift_x = 0 + 5 = 5
        self.assertAlmostEqual(cone.sections[-1].inner_shift_x, 5)
        self.assertAlmostEqual(cone.sections[-1].inner_shift_y, 3)

    def test_none_inner_shifts_stay_none_through_propagation(self):
        """Test that None inner shifts stay None through propagation"""
        cone = SmarterCone.base(50).inner(40).extend(radius=30, height=100)
        self.assertIsNone(cone.sections[-1].inner_shift_x)
        self.assertIsNone(cone.sections[-1].inner_shift_y)

    def test_inner_zero_stops_propagation_through_chain(self):
        """Test that inner(0) stops propagation through chained extends"""
        cone = SmarterCone.base(50).inner(40).extend(radius=50, height=50).inner(0).extend(radius=30, height=50)
        self.assertIsNone(cone.sections[-1].inner_radius)

    def test_inner_invalid_radius_raises(self):
        """Test that inner_radius >= outer radius raises AssertionError"""
        with self.assertRaises(AssertionError):
            SmarterCone.base(50).extend(radius=30, height=100).inner(30)
        with self.assertRaises(AssertionError):
            SmarterCone.base(50).extend(radius=30, height=100).inner(35)

    def test_eccentric_hole_creates_valid_solid(self):
        """Test that eccentric inner hole creates a valid solid"""
        cone = SmarterCone.base(50).extend(radius=50, height=100).inner(20, shift_x=10)
        cone.assert_valid()
        self.assertTrue(cone.has_inner)

    def test_inner_shift_offset_propagates_through_fillet(self):
        """Test that inner shift offsets propagate through fillet sections"""
        cone = SmarterCone.base(50).inner(40).extend(radius=50, height=50).inner(40, shift_x=5).extend(radius=30, height=50, fillet=5)
        # All fillet sections should have inner_shift_x
        for s in cone.sections:
            if s.inner_radius is not None and s.inner_shift_x is not None:
                self.assertAlmostEqual(s.inner_shift_x - s.shift_x, 5, places=3)


class TestSmarterConeGetOuterInnerCone(unittest.TestCase):

    def test_get_outer_cone_strips_inner(self):
        """Test that get_outer_cone returns solid cone without inner radii"""
        cone = SmarterCone.base(50).inner(40).extend(radius=30, height=100)
        outer = cone.get_outer_cone()
        self.assertFalse(outer.has_inner)
        self.assertAlmostEqual(outer.base_radius, 50)
        self.assertAlmostEqual(outer.top_radius, 30)
        self.assertAlmostEqual(outer.height, 100)

    def test_get_outer_cone_preserves_shifts(self):
        """Test that get_outer_cone preserves shift_x/shift_y"""
        cone = SmarterCone.base(50).extend(radius=30, height=100, shift_x=10).inner(20)
        outer = cone.get_outer_cone()
        self.assertAlmostEqual(outer.sections[1].shift_x, 10)

    def test_get_outer_cone_on_solid_cone(self):
        """Test that get_outer_cone works on cone without inner (identity-like)"""
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        outer = cone.get_outer_cone()
        self.assertFalse(outer.has_inner)
        self.assertAlmostEqual(outer.base_radius, 50)

    def test_get_inner_cone_uses_inner_radii(self):
        """Test that get_inner_cone uses inner_radius as radius"""
        cone = SmarterCone.base(50).inner(40).extend(radius=30, height=100)
        inner = cone.get_inner_cone()
        self.assertFalse(inner.has_inner)
        self.assertAlmostEqual(inner.base_radius, 40)
        self.assertAlmostEqual(inner.top_radius, 20)  # wall=10, 30-10=20
        self.assertAlmostEqual(inner.height, 100)

    def test_get_inner_cone_uses_inner_shifts(self):
        """Test that get_inner_cone uses inner_shift as shift"""
        cone = SmarterCone.base(50).extend(radius=50, height=100).inner(30, shift_x=5, shift_y=3)
        inner = cone.get_inner_cone()
        self.assertAlmostEqual(inner.sections[1].shift_x, 5)
        self.assertAlmostEqual(inner.sections[1].shift_y, 3)

    def test_get_inner_cone_falls_back_to_outer_shift(self):
        """Test that get_inner_cone uses outer shift when inner shift is None"""
        cone = SmarterCone.base(50).inner(40).extend(radius=50, height=100, shift_x=10)
        inner = cone.get_inner_cone()
        self.assertAlmostEqual(inner.sections[1].shift_x, 10)

    def test_get_inner_cone_requires_inner(self):
        """Test that get_inner_cone raises on cone without inner"""
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        with self.assertRaises(AssertionError):
            cone.get_inner_cone()

    def test_get_outer_and_inner_colocated(self):
        """Test that outer and inner cones are colocated with original"""
        cone = SmarterCone.base(50).inner(40).extend(radius=30, height=100)
        outer = cone.get_outer_cone()
        inner = cone.get_inner_cone()
        self.assertAlmostEqual(outer.z_min, cone.z_min, places=3)
        self.assertAlmostEqual(outer.z_max, cone.z_max, places=3)
        self.assertAlmostEqual(inner.z_min, cone.z_min, places=3)
        self.assertAlmostEqual(inner.z_max, cone.z_max, places=3)


if __name__ == '__main__':
    unittest.main()
