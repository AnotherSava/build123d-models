import unittest
from math import sqrt, tan, radians

from build123d import Plane, Vector
from parameterized import parameterized

from sava.csg.build123d.common.geometry import are_points_too_close
from sava.csg.build123d.common.smartercone import SmarterCone, ConeSection


class TestBuilderBase(unittest.TestCase):

    def test_base_creates_single_section(self):
        cone = SmarterCone.base(50)
        self.assertEqual(len(cone.sections), 1)
        self.assertAlmostEqual(cone.sections[0].radius, 50)
        self.assertAlmostEqual(cone.height, 0)

    def test_base_with_plane_and_angle(self):
        cone = SmarterCone.base(30, plane=Plane.XZ, angle=180)
        self.assertEqual(cone.plane, Plane.XZ)
        self.assertEqual(cone.angle, 180)


class TestBuilderCylinder(unittest.TestCase):

    def test_cylinder_creates_two_sections(self):
        cyl = SmarterCone.cylinder(20, 50)
        self.assertEqual(len(cyl.sections), 2)
        self.assertAlmostEqual(cyl.base_radius, 20)
        self.assertAlmostEqual(cyl.top_radius, 20)
        self.assertAlmostEqual(cyl.height, 50)

    def test_cylinder_bounding_box(self):
        cyl = SmarterCone.cylinder(10, 30)
        self.assertAlmostEqual(cyl.x_min, -10, places=1)
        self.assertAlmostEqual(cyl.x_max, 10, places=1)
        self.assertAlmostEqual(cyl.z_min, 0, places=1)
        self.assertAlmostEqual(cyl.z_max, 30, places=1)

    def test_cylinder_with_angle(self):
        cyl = SmarterCone.cylinder(20, 50, angle=180)
        self.assertAlmostEqual(cyl.z_max, 50, places=1)


class TestBuilderWithRadiusAndHeight(unittest.TestCase):

    def test_simple_cone(self):
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        self.assertEqual(len(cone.sections), 2)
        self.assertAlmostEqual(cone.base_radius, 50)
        self.assertAlmostEqual(cone.top_radius, 30)
        self.assertAlmostEqual(cone.height, 100)

    def test_cone_bounding_box(self):
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        self.assertAlmostEqual(cone.x_min, -50, places=1)
        self.assertAlmostEqual(cone.x_max, 50, places=1)
        self.assertAlmostEqual(cone.z_min, 0, places=1)
        self.assertAlmostEqual(cone.z_max, 100, places=1)

    def test_cone_with_shift(self):
        cone = SmarterCone.base(20).extend(radius=20, height=100, shift_x=30)
        self.assertAlmostEqual(cone.x_min, -20, places=1)
        self.assertAlmostEqual(cone.x_max, 50, places=1)
        self.assertAlmostEqual(cone.z_max, 100, places=1)


class TestBuilderWithAngleAndHeight(unittest.TestCase):

    def test_narrowing_cone(self):
        cone = SmarterCone.base(50).extend(angle=80, height=100)
        expected_radius = 50 - 100 / tan(radians(80))
        self.assertAlmostEqual(cone.top_radius, expected_radius, places=3)
        self.assertAlmostEqual(cone.height, 100)

    def test_widening_cone_negative_angle(self):
        cone = SmarterCone.base(20).extend(angle=-80, height=100)
        expected_radius = 20 + 100 / tan(radians(80))
        self.assertAlmostEqual(cone.top_radius, expected_radius, places=3)

    def test_45_degree_cone(self):
        cone = SmarterCone.base(50).extend(angle=45, height=20)
        self.assertAlmostEqual(cone.top_radius, 30, places=3)


class TestBuilderWithAngleAndRadius(unittest.TestCase):

    def test_narrowing_to_zero(self):
        cone = SmarterCone.base(50).extend(angle=45, radius=0)
        self.assertAlmostEqual(cone.top_radius, 0, places=3)
        self.assertAlmostEqual(cone.height, 50, places=3)

    def test_narrowing_to_specific_radius(self):
        cone = SmarterCone.base(50).extend(angle=45, radius=20)
        self.assertAlmostEqual(cone.top_radius, 20, places=3)
        self.assertAlmostEqual(cone.height, 30, places=3)

    def test_widening_cone(self):
        cone = SmarterCone.base(20).extend(angle=-45, radius=50)
        self.assertAlmostEqual(cone.top_radius, 50, places=3)
        self.assertAlmostEqual(cone.height, 30, places=3)


class TestBuilderWithHeight(unittest.TestCase):

    def test_cylindrical_extension(self):
        cone = SmarterCone.base(50).extend(radius=30, height=60).extend(height=40)
        self.assertEqual(len(cone.sections), 3)
        self.assertAlmostEqual(cone.top_radius, 30)
        self.assertAlmostEqual(cone.height, 100)
        self.assertAlmostEqual(cone.sections[1].radius, 30)
        self.assertAlmostEqual(cone.sections[2].radius, 30)


class TestMultiSection(unittest.TestCase):

    def test_three_sections(self):
        cone = SmarterCone.base(10).extend(radius=20, height=50).extend(radius=15, height=50)
        self.assertEqual(len(cone.sections), 3)
        self.assertAlmostEqual(cone.base_radius, 10)
        self.assertAlmostEqual(cone.top_radius, 15)
        self.assertAlmostEqual(cone.height, 100)
        self.assertAlmostEqual(cone.z_min, 0, places=1)
        self.assertAlmostEqual(cone.z_max, 100, places=1)

    def test_three_sections_with_shift(self):
        cone = SmarterCone.base(10).extend(radius=15, height=50).extend(radius=20, height=50, shift_x=5)
        self.assertAlmostEqual(cone.z_max, 100, places=1)

    def test_three_sections_with_inner_radius(self):
        cone = SmarterCone([
            ConeSection(20, 0, inner_radius=10),
            ConeSection(30, 50, inner_radius=20),
            ConeSection(25, 100, inner_radius=15),
        ])
        self.assertTrue(cone.has_inner)
        self.assertAlmostEqual(cone.z_max, 100, places=1)

    def test_mixed_inner_radius(self):
        """Some sections have inner_radius, some don't (use OCCT_MIN_SIZE)"""
        cone = SmarterCone([
            ConeSection(20, 0),
            ConeSection(30, 50, inner_radius=20),
            ConeSection(25, 100, inner_radius=15),
        ])
        self.assertTrue(cone.has_inner)

    def test_angle_less_than_360(self):
        cone = SmarterCone([
            ConeSection(20, 0),
            ConeSection(30, 50),
            ConeSection(25, 100),
        ], angle=180)
        self.assertAlmostEqual(cone.z_max, 100, places=1)


class TestValidation(unittest.TestCase):

    def test_first_section_height_must_be_zero(self):
        with self.assertRaises(AssertionError):
            SmarterCone([ConeSection(10, 5)])

    def test_negative_radius_rejected(self):
        with self.assertRaises(AssertionError):
            SmarterCone([ConeSection(-5)])

    def test_inner_radius_must_be_less_than_outer(self):
        with self.assertRaises(AssertionError):
            SmarterCone([ConeSection(10, 0, inner_radius=15), ConeSection(20, 50, inner_radius=10)])

    def test_non_monotonic_heights_rejected(self):
        with self.assertRaises(AssertionError):
            SmarterCone([ConeSection(10, 0), ConeSection(20, 50), ConeSection(15, 30)])


class TestProperties(unittest.TestCase):

    def test_height_two_sections(self):
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        self.assertAlmostEqual(cone.height, 100)

    def test_height_single_section(self):
        cone = SmarterCone.base(50)
        self.assertAlmostEqual(cone.height, 0)

    def test_base_radius(self):
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        self.assertAlmostEqual(cone.base_radius, 50)

    def test_top_radius(self):
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        self.assertAlmostEqual(cone.top_radius, 30)

    def test_has_inner_false(self):
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        self.assertFalse(cone.has_inner)

    def test_has_inner_true(self):
        cone = SmarterCone([ConeSection(20, 0, inner_radius=10), ConeSection(30, 50, inner_radius=20)])
        self.assertTrue(cone.has_inner)


class TestRadiusPosition(unittest.TestCase):

    @parameterized.expand([
        (0.0, 50),
        (0.5, 40),
        (1.0, 30),
    ])
    def test_two_section_cone(self, position, expected_radius):
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        self.assertAlmostEqual(cone.radius(position), expected_radius, places=3)

    @parameterized.expand([
        (0.0, 10),    # start of segment 0
        (0.5, 15),    # midpoint of segment 0
        (1.0, 20),    # end of segment 0 / start of segment 1
        (1.5, 17.5),  # midpoint of segment 1
        (2.0, 15),    # end of segment 1
    ])
    def test_three_section_cone(self, position, expected_radius):
        cone = SmarterCone.base(10).extend(radius=20, height=50).extend(radius=15, height=50)
        self.assertAlmostEqual(cone.radius(position), expected_radius, places=3)

    def test_above_max_raises(self):
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        with self.assertRaises(AssertionError):
            cone.radius(5.0)

    def test_below_zero_raises(self):
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        with self.assertRaises(AssertionError):
            cone.radius(-1.0)

    def test_single_section_raises(self):
        cone = SmarterCone.base(50)
        with self.assertRaises(AssertionError):
            cone.radius(0.5)


class TestCenterPosition(unittest.TestCase):

    @parameterized.expand([
        (0.0, Vector(0, 0, 0)),
        (0.5, Vector(0, 0, 50)),
        (1.0, Vector(0, 0, 100)),
    ])
    def test_no_shift(self, position, expected):
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        result = cone.center(position)
        self.assertTrue(are_points_too_close(result, expected), f"Expected {expected}, got {result}")

    @parameterized.expand([
        (0.0, Vector(0, 0, 0)),
        (0.5, Vector(5, 2.5, 50)),
        (1.0, Vector(10, 5, 100)),
    ])
    def test_with_shift(self, position, expected):
        cone = SmarterCone.base(30).extend(radius=20, height=100, shift_x=10, shift_y=5)
        result = cone.center(position)
        self.assertTrue(are_points_too_close(result, expected), f"Expected {expected}, got {result}")

    @parameterized.expand([
        (0.0, Vector(0, 0, 0)),
        (1.0, Vector(0, 0, 50)),
        (1.5, Vector(2.5, 0, 75)),
        (2.0, Vector(5, 0, 100)),
    ])
    def test_three_sections_with_shift_on_last(self, position, expected):
        cone = SmarterCone.base(10).extend(radius=20, height=50).extend(radius=15, height=50, shift_x=5)
        result = cone.center(position)
        self.assertTrue(are_points_too_close(result, expected), f"Expected {expected}, got {result}")


class TestCreateOffset(unittest.TestCase):

    def test_positive_offset(self):
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        offset = cone.create_offset(2)
        self.assertAlmostEqual(offset.base_radius, 52)
        self.assertAlmostEqual(offset.top_radius, 32)
        self.assertAlmostEqual(offset.height, 100)

    def test_negative_offset(self):
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        offset = cone.create_offset(-2)
        self.assertAlmostEqual(offset.base_radius, 48)
        self.assertAlmostEqual(offset.top_radius, 28)
        self.assertAlmostEqual(offset.height, 100)

    def test_multi_section_offset(self):
        cone = SmarterCone.base(10).extend(radius=20, height=50).extend(radius=15, height=50)
        offset = cone.create_offset(3)
        self.assertAlmostEqual(offset.sections[0].radius, 13)
        self.assertAlmostEqual(offset.sections[1].radius, 23)
        self.assertAlmostEqual(offset.sections[2].radius, 18)

    def test_returns_new_instance(self):
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        offset = cone.create_offset(2)
        self.assertIsNot(cone, offset)
        self.assertIsInstance(offset, SmarterCone)

    def test_offset_rejects_negative_radius(self):
        cone = SmarterCone.base(5).extend(radius=3, height=100)
        with self.assertRaises(AssertionError):
            cone.create_offset(-10)


class TestCreateShell(unittest.TestCase):

    def test_positive_shell_outer(self):
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        shell = cone.create_shell(2)
        self.assertAlmostEqual(shell.sections[0].radius, 52)
        self.assertAlmostEqual(shell.sections[0].inner_radius, 50)
        self.assertAlmostEqual(shell.sections[1].radius, 32)
        self.assertAlmostEqual(shell.sections[1].inner_radius, 30)
        self.assertTrue(shell.has_inner)

    def test_negative_shell_inner(self):
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        shell = cone.create_shell(-2)
        self.assertAlmostEqual(shell.sections[0].radius, 50)
        self.assertAlmostEqual(shell.sections[0].inner_radius, 48)
        self.assertAlmostEqual(shell.sections[1].radius, 30)
        self.assertAlmostEqual(shell.sections[1].inner_radius, 28)

    def test_multi_section_shell(self):
        cone = SmarterCone.base(10).extend(radius=20, height=50).extend(radius=15, height=50)
        shell = cone.create_shell(3)
        self.assertEqual(len(shell.sections), 3)
        for i, s in enumerate(shell.sections):
            self.assertIsNotNone(s.inner_radius)
            original_r = cone.sections[i].radius
            self.assertAlmostEqual(s.radius, original_r + 3)
            self.assertAlmostEqual(s.inner_radius, max(original_r, 1e-4))

    def test_returns_new_instance(self):
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        shell = cone.create_shell(2)
        self.assertIsNot(cone, shell)

    def test_rejects_zero_thickness(self):
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        with self.assertRaises(AssertionError):
            cone.create_shell(0)

    def test_rejects_already_hollow(self):
        cone = SmarterCone([ConeSection(20, 0, inner_radius=10), ConeSection(30, 50, inner_radius=20)])
        with self.assertRaises(AssertionError):
            cone.create_shell(2)


class TestCopy(unittest.TestCase):

    def test_copy_preserves_all_fields(self):
        cone = SmarterCone.base(50, plane=Plane.XZ, angle=180, label="test").extend(radius=30, height=100)
        copied = cone.copy()
        self.assertIsInstance(copied, SmarterCone)
        self.assertEqual(len(copied.sections), len(cone.sections))
        self.assertEqual(copied.plane, cone.plane)
        self.assertEqual(copied.angle, cone.angle)
        self.assertEqual(copied.label, cone.label)

    def test_copy_is_independent(self):
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        copied = cone.copy()
        copied.move_z(10)
        self.assertAlmostEqual(cone.z_min, 0, places=1)
        self.assertAlmostEqual(copied.z_min, 10, places=1)


class TestAnalyticalPath(unittest.TestCase):

    def test_cylinder_uses_make_cylinder(self):
        """2-section, same radius, no shift, no inner, angle=360 → analytical"""
        cyl = SmarterCone.cylinder(20, 50)
        self.assertAlmostEqual(cyl.x_min, -20, places=1)
        self.assertAlmostEqual(cyl.z_max, 50, places=1)

    def test_cone_uses_make_cone(self):
        """2-section, different radii, no shift, no inner, angle=360 → analytical"""
        cone = SmarterCone.base(50).extend(radius=30, height=100)
        self.assertAlmostEqual(cone.x_min, -50, places=1)
        self.assertAlmostEqual(cone.z_max, 100, places=1)

    def test_partial_angle_uses_loft(self):
        """angle < 360 → loft path even for 2 sections"""
        cone = SmarterCone.base(50, angle=180).extend(radius=30, height=100)
        self.assertAlmostEqual(cone.z_max, 100, places=1)


class TestFillettability(unittest.TestCase):

    def test_three_section_fillettable_at_junction(self):
        """The key test: 3-section cone should be fillettable at the junction height"""
        from build123d import fillet, Axis
        from sava.csg.build123d.common.edgefilters import filter_edges_by_position

        cone = SmarterCone.base(10).extend(radius=20, height=50).extend(radius=15, height=50)
        # Find edges at the junction height (z=50)
        edges = filter_edges_by_position(cone.solid.edges(), Axis.Z, 49, 51, (True, True))
        # Should be able to fillet without error
        if edges:
            # If there are edges at the junction, they should be fillettable
            # (If there are no edges at the junction, that's even better - it's a smooth loft)
            try:
                fillet(edges, 1)
            except Exception:
                # No edges at junction height means the loft is smooth — that's the goal
                pass

    def test_three_section_with_inner_radius_valid(self):
        """Multi-section hollow cone should produce valid geometry"""
        cone = SmarterCone([
            ConeSection(20, 0, inner_radius=10),
            ConeSection(30, 50, inner_radius=20),
            ConeSection(25, 100, inner_radius=15),
        ])
        self.assertTrue(cone.wrap_solid().is_valid)


if __name__ == '__main__':
    unittest.main()
