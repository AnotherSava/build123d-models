import unittest

from build123d import Plane
from parameterized import parameterized

from sava.csg.build123d.common.smartsphere import SmartSphere
from tests.sava.csg.build123d.test_utils import assertVectorAlmostEqual


class TestSmartSphereBasic(unittest.TestCase):

    def test_solid_sphere_creation(self):
        """Test creating a basic solid sphere"""
        radius = 50.0
        sphere = SmartSphere(radius)

        self.assertEqual(sphere.radius, radius)
        self.assertIsNone(sphere.internal_radius)
        self.assertEqual(sphere.angle, 360)
        self.assertIsNotNone(sphere.solid)

    def test_solid_sphere_dimensions(self):
        """Test that solid sphere has correct bounding box"""
        radius = 25.0
        sphere = SmartSphere(radius)

        self.assertAlmostEqual(sphere.x_size, radius * 2, places=5)
        self.assertAlmostEqual(sphere.y_size, radius * 2, places=5)
        self.assertAlmostEqual(sphere.z_size, radius * 2, places=5)

    def test_solid_sphere_centered(self):
        """Test that solid sphere is centered at origin"""
        radius = 30.0
        sphere = SmartSphere(radius)

        self.assertAlmostEqual(sphere.x_mid, 0, places=5)
        self.assertAlmostEqual(sphere.y_mid, 0, places=5)
        self.assertAlmostEqual(sphere.z_mid, 0, places=5)

    def test_hollow_sphere_creation(self):
        """Test creating a hollow sphere"""
        radius = 50.0
        internal_radius = 40.0
        sphere = SmartSphere(radius, internal_radius=internal_radius)

        self.assertEqual(sphere.radius, radius)
        self.assertEqual(sphere.internal_radius, internal_radius)
        self.assertIsNotNone(sphere.solid)

    def test_hollow_sphere_dimensions(self):
        """Test that hollow sphere has correct bounding box (based on outer radius)"""
        radius = 50.0
        internal_radius = 40.0
        sphere = SmartSphere(radius, internal_radius=internal_radius)

        self.assertAlmostEqual(sphere.x_size, radius * 2, places=5)
        self.assertAlmostEqual(sphere.y_size, radius * 2, places=5)
        self.assertAlmostEqual(sphere.z_size, radius * 2, places=5)

    def test_sphere_with_label(self):
        """Test creating sphere with a label"""
        sphere = SmartSphere(25.0, label="test_sphere")
        self.assertEqual(sphere.label, "test_sphere")

    @parameterized.expand([
        (10.0,),
        (25.0,),
        (50.0,),
        (100.0,),
    ])
    def test_various_radii(self, radius):
        """Test spheres with various radii"""
        sphere = SmartSphere(radius)

        self.assertEqual(sphere.radius, radius)
        self.assertAlmostEqual(sphere.x_size, radius * 2, places=5)


class TestSmartSphereCreateHollow(unittest.TestCase):

    def test_create_hollow_larger_first(self):
        """Test create_hollow with larger radius first"""
        sphere = SmartSphere.create_hollow(50.0, 40.0)

        self.assertEqual(sphere.radius, 50.0)
        self.assertEqual(sphere.internal_radius, 40.0)

    def test_create_hollow_smaller_first(self):
        """Test create_hollow with smaller radius first"""
        sphere = SmartSphere.create_hollow(40.0, 50.0)

        self.assertEqual(sphere.radius, 50.0)
        self.assertEqual(sphere.internal_radius, 40.0)

    def test_create_hollow_with_angle(self):
        """Test create_hollow with angle parameter"""
        sphere = SmartSphere.create_hollow(50.0, 40.0, angle=180)

        self.assertEqual(sphere.angle, 180)

    def test_create_hollow_with_label(self):
        """Test create_hollow with label parameter"""
        sphere = SmartSphere.create_hollow(50.0, 40.0, label="hollow")

        self.assertEqual(sphere.label, "hollow")


class TestSmartSpherePlane(unittest.TestCase):

    def test_default_plane_is_xy(self):
        """Test that default plane is Plane.XY"""
        sphere = SmartSphere(25.0)
        self.assertEqual(sphere.plane, Plane.XY)

    def test_sphere_with_custom_plane(self):
        """Test creating sphere with custom plane"""
        custom_plane = Plane.XZ
        sphere = SmartSphere(25.0, plane=custom_plane)
        self.assertEqual(sphere.plane, custom_plane)


class TestSmartSphereAngle(unittest.TestCase):

    def test_default_angle_is_360(self):
        """Test that default angle is 360 (full sphere)"""
        sphere = SmartSphere(25.0)
        self.assertEqual(sphere.angle, 360)

    def test_hemisphere_creation(self):
        """Test creating a hemisphere (180 degree angle)"""
        radius = 50.0
        sphere = SmartSphere(radius, angle=180)

        self.assertEqual(sphere.angle, 180)
        self.assertAlmostEqual(sphere.z_size, radius * 2, places=5)
        # Hemisphere: angle3 sweeps around Z axis, so Y is halved while X stays full
        self.assertAlmostEqual(sphere.x_size, radius * 2, places=5)
        self.assertAlmostEqual(sphere.y_size, radius, places=5)

    def test_quarter_sphere_creation(self):
        """Test creating a quarter sphere (90 degree angle)"""
        radius = 50.0
        sphere = SmartSphere(radius, angle=90)

        self.assertEqual(sphere.angle, 90)

    @parameterized.expand([
        (90,),
        (180,),
        (270,),
        (360,),
    ])
    def test_various_angles(self, angle):
        """Test spheres with various angles"""
        sphere = SmartSphere(50.0, angle=angle)
        self.assertEqual(sphere.angle, angle)

    def test_hollow_partial_sphere(self):
        """Test creating a hollow partial sphere"""
        sphere = SmartSphere(50.0, internal_radius=40.0, angle=180)

        self.assertEqual(sphere.radius, 50.0)
        self.assertEqual(sphere.internal_radius, 40.0)
        self.assertEqual(sphere.angle, 180)


class TestSmartSphereCreateOffset(unittest.TestCase):

    def test_offset_external_positive(self):
        """Test increasing external radius"""
        sphere = SmartSphere(50.0)
        offset_sphere = sphere.create_offset(5.0)

        self.assertEqual(offset_sphere.radius, 55.0)
        self.assertIsNone(offset_sphere.internal_radius)

    def test_offset_external_negative(self):
        """Test decreasing external radius"""
        sphere = SmartSphere(50.0)
        offset_sphere = sphere.create_offset(-5.0)

        self.assertEqual(offset_sphere.radius, 45.0)
        self.assertIsNone(offset_sphere.internal_radius)

    def test_offset_internal_positive(self):
        """Test increasing internal radius"""
        sphere = SmartSphere(50.0, internal_radius=40.0)
        offset_sphere = sphere.create_offset(5.0, external=False)

        self.assertEqual(offset_sphere.radius, 50.0)
        self.assertEqual(offset_sphere.internal_radius, 45.0)

    def test_offset_internal_negative(self):
        """Test decreasing internal radius"""
        sphere = SmartSphere(50.0, internal_radius=40.0)
        offset_sphere = sphere.create_offset(-5.0, external=False)

        self.assertEqual(offset_sphere.radius, 50.0)
        self.assertEqual(offset_sphere.internal_radius, 35.0)

    def test_offset_internal_on_solid_sphere_raises(self):
        """Test that adjusting internal radius of solid sphere raises error"""
        sphere = SmartSphere(50.0)

        with self.assertRaises(ValueError) as context:
            sphere.create_offset(5.0, external=False)
        self.assertIn("solid sphere", str(context.exception))

    def test_offset_preserves_center(self):
        """Test that offset sphere is aligned to same center"""
        sphere = SmartSphere(50.0)
        sphere.move(10, 20, 30)
        offset_sphere = sphere.create_offset(5.0)

        assertVectorAlmostEqual(self, (offset_sphere.x_mid, offset_sphere.y_mid, offset_sphere.z_mid), (10, 20, 30))

    def test_offset_preserves_label(self):
        """Test that offset sphere preserves label"""
        sphere = SmartSphere(50.0, label="my_sphere")
        offset_sphere = sphere.create_offset(5.0)
        self.assertEqual(offset_sphere.label, "my_sphere")

    def test_offset_with_custom_label(self):
        """Test that offset sphere can have custom label"""
        sphere = SmartSphere(50.0, label="original")
        offset_sphere = sphere.create_offset(5.0, label="offset")
        self.assertEqual(offset_sphere.label, "offset")

    def test_offset_preserves_angle(self):
        """Test that offset sphere preserves angle"""
        sphere = SmartSphere(50.0, angle=180)
        offset_sphere = sphere.create_offset(5.0)
        self.assertEqual(offset_sphere.angle, 180)

    def test_offset_partial_sphere_preserves_rotation(self):
        """Test that offset on rotated partial sphere preserves orientation"""
        sphere = SmartSphere(50.0, angle=180)
        sphere.rotate_x(90)  # Flat side now faces +Z instead of +Y

        offset_sphere = sphere.create_offset(5.0)

        # After rotation, flat side is at z_min - offset should match
        self.assertAlmostEqual(sphere.z_min, offset_sphere.z_min, places=5)


class TestSmartSphereCreateShell(unittest.TestCase):

    def test_shell_external_positive(self):
        """Test creating shell outside solid sphere (positive offset)"""
        sphere = SmartSphere(50.0)
        shell = sphere.create_shell(5.0)

        self.assertEqual(shell.radius, 55.0)
        self.assertEqual(shell.internal_radius, 50.0)

    def test_shell_external_negative(self):
        """Test creating shell inside solid sphere (negative offset)"""
        sphere = SmartSphere(50.0)
        shell = sphere.create_shell(-5.0)

        self.assertEqual(shell.radius, 50.0)
        self.assertEqual(shell.internal_radius, 45.0)

    def test_shell_internal_positive(self):
        """Test creating shell on internal surface (into cavity)"""
        sphere = SmartSphere(50.0, internal_radius=40.0)
        shell = sphere.create_shell(5.0, external=False)

        self.assertEqual(shell.radius, 45.0)
        self.assertEqual(shell.internal_radius, 40.0)

    def test_shell_internal_negative(self):
        """Test creating shell on internal surface (into material)"""
        sphere = SmartSphere(50.0, internal_radius=40.0)
        shell = sphere.create_shell(-5.0, external=False)

        self.assertEqual(shell.radius, 40.0)
        self.assertEqual(shell.internal_radius, 35.0)

    def test_shell_internal_on_solid_raises(self):
        """Test that creating shell on internal surface of solid sphere raises error"""
        sphere = SmartSphere(50.0)

        with self.assertRaises(ValueError) as context:
            sphere.create_shell(5.0, external=False)
        self.assertIn("solid sphere", str(context.exception))

    def test_shell_preserves_center(self):
        """Test that shell sphere is aligned to same center"""
        sphere = SmartSphere(50.0)
        sphere.move(10, 20, 30)
        shell = sphere.create_shell(5.0)

        assertVectorAlmostEqual(self, (shell.x_mid, shell.y_mid, shell.z_mid), (10, 20, 30))

    @parameterized.expand([
        (2.0,),
        (5.0,),
        (10.0,),
    ])
    def test_shell_thickness(self, thickness):
        """Test shell with various thicknesses"""
        sphere = SmartSphere(50.0)
        shell = sphere.create_shell(thickness)

        self.assertEqual(shell.radius, 50.0 + thickness)
        self.assertEqual(shell.internal_radius, 50.0)

    def test_shell_preserves_angle(self):
        """Test that shell preserves angle"""
        sphere = SmartSphere(50.0, angle=180)
        shell = sphere.create_shell(5.0)
        self.assertEqual(shell.angle, 180)

    def test_shell_with_custom_label(self):
        """Test that shell can have custom label"""
        sphere = SmartSphere(50.0, label="original")
        shell = sphere.create_shell(5.0, label="shell")
        self.assertEqual(shell.label, "shell")

    def test_shell_partial_sphere_concentric(self):
        """Test that shell on partial sphere is concentric (shares geometric center)"""
        sphere = SmartSphere(50.0, angle=180)
        shell = sphere.create_shell(5.0)

        # For concentric hemispheres, the flat edge (y_min) should be at the same position
        self.assertAlmostEqual(sphere.y_min, shell.y_min, places=5)

    def test_shell_partial_sphere_preserves_rotation(self):
        """Test that shell on rotated partial sphere preserves orientation"""
        sphere = SmartSphere(50.0, angle=180)
        sphere.rotate_x(90)  # Flat side now faces +Z instead of +Y

        shell = sphere.create_shell(5.0)

        # After rotation, flat side is at z_min - shell should match
        self.assertAlmostEqual(sphere.z_min, shell.z_min, places=5)


class TestSmartSphereCopy(unittest.TestCase):

    def test_copy_solid_sphere(self):
        """Test copying a solid sphere"""
        sphere = SmartSphere(50.0, label="original")
        copied = sphere.copy()

        self.assertEqual(copied.radius, 50.0)
        self.assertIsNone(copied.internal_radius)
        self.assertEqual(copied.angle, 360)
        self.assertEqual(copied.label, "original")
        self.assertEqual(copied.plane, sphere.plane)

    def test_copy_partial_sphere(self):
        """Test copying a partial sphere preserves angle"""
        sphere = SmartSphere(50.0, angle=180)
        copied = sphere.copy()

        self.assertEqual(copied.angle, 180)

    def test_copy_hollow_sphere(self):
        """Test copying a hollow sphere"""
        sphere = SmartSphere(50.0, internal_radius=40.0)
        copied = sphere.copy()

        self.assertEqual(copied.radius, 50.0)
        self.assertEqual(copied.internal_radius, 40.0)

    def test_copy_with_new_label(self):
        """Test copying with a new label"""
        sphere = SmartSphere(50.0, label="original")
        copied = sphere.copy(label="copied")

        self.assertEqual(copied.label, "copied")

    def test_copy_independence(self):
        """Test that copy is independent from original"""
        sphere = SmartSphere(50.0)
        copied = sphere.copy()

        sphere.move(10, 10, 10)

        assertVectorAlmostEqual(self, (copied.x_mid, copied.y_mid, copied.z_mid), (0, 0, 0))


class TestSmartSphereTransformations(unittest.TestCase):

    def test_move(self):
        """Test moving a sphere"""
        sphere = SmartSphere(25.0)
        sphere.move(10, 20, 30)

        assertVectorAlmostEqual(self, (sphere.x_mid, sphere.y_mid, sphere.z_mid), (10, 20, 30))

    def test_rotate(self):
        """Test rotating a sphere (should maintain shape for sphere)"""
        sphere = SmartSphere(25.0)
        sphere.move(10, 0, 0)
        sphere.rotate_z(90)

        self.assertAlmostEqual(sphere.x_mid, 0, places=5)
        self.assertAlmostEqual(sphere.y_mid, 10, places=5)

    def test_scale(self):
        """Test scaling a sphere"""
        sphere = SmartSphere(25.0)
        sphere.scale(2.0)

        self.assertAlmostEqual(sphere.x_size, 100.0, places=5)


if __name__ == '__main__':
    unittest.main()
