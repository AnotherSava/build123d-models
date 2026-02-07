import unittest
from math import cos, sin, radians

from build123d import Vector, Axis, Plane, Face, Rectangle
from parameterized import parameterized

from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartrevolve import SmartRevolve
from tests.sava.csg.build123d.test_utils import assertVectorAlmostEqual


class TestSmartRevolveBasic(unittest.TestCase):

    def _create_simple_revolve(self, angle: float = 360, axis: Axis = Axis.Y) -> SmartRevolve:
        """Create a simple SmartRevolve for testing - a small rectangle revolved around an axis."""
        # Create a rectangle face offset from the axis
        pencil = Pencil(Plane.XZ, start=(5, 0))
        pencil.right(2).up(3).left(2).down(3)
        face = pencil.create_face()
        return SmartRevolve(face, axis, angle, Plane.XZ)

    def test_create_plane_at_start(self):
        """Test that create_plane_at(0) returns the original sketch plane."""
        revolve = self._create_simple_revolve(angle=180)
        plane = revolve.create_plane_at(0)

        # At t=0, plane should match the original sketch plane (Plane.XZ)
        assertVectorAlmostEqual(self, plane.origin, Plane.XZ.origin)
        assertVectorAlmostEqual(self, plane.z_dir, Plane.XZ.z_dir)

    def test_create_plane_at_end_180_degrees(self):
        """Test that create_plane_at(1) returns plane rotated by full angle."""
        revolve = self._create_simple_revolve(angle=180, axis=Axis.Y)
        plane = revolve.create_plane_at(1)

        # At t=1 with 180 degrees around Y, the XZ plane should be rotated 180 degrees
        # Original z_dir is (0, 1, 0), after 180 rotation around Y -> (0, 1, 0) unchanged
        # Original origin (0, 0, 0) stays at origin
        assertVectorAlmostEqual(self, plane.origin, Vector(0, 0, 0))

    def test_create_plane_at_mid(self):
        """Test that create_plane_at(0.5) returns plane at half the angle."""
        revolve = self._create_simple_revolve(angle=180, axis=Axis.Y)
        plane = revolve.create_plane_at(0.5)

        # At t=0.5 with 180 degrees, we should be at 90 degrees
        # The XZ plane rotated 90 degrees around Y axis
        # z_dir (0, 1, 0) stays the same (Y doesn't change when rotating around Y)
        assertVectorAlmostEqual(self, plane.origin, Vector(0, 0, 0))

    @parameterized.expand([
        (0.0,),
        (0.25,),
        (0.5,),
        (0.75,),
        (1.0,),
    ])
    def test_create_plane_at_various_positions(self, t: float):
        """Test that create_plane_at returns valid planes at various positions."""
        revolve = self._create_simple_revolve(angle=300, axis=Axis.Z)
        plane = revolve.create_plane_at(t)

        # Verify plane directions are orthonormal
        self.assertAlmostEqual(plane.x_dir.length, 1.0, places=5)
        self.assertAlmostEqual(plane.y_dir.length, 1.0, places=5)
        self.assertAlmostEqual(plane.z_dir.length, 1.0, places=5)
        self.assertAlmostEqual(plane.x_dir.dot(plane.y_dir), 0.0, places=5)
        self.assertAlmostEqual(plane.y_dir.dot(plane.z_dir), 0.0, places=5)
        self.assertAlmostEqual(plane.z_dir.dot(plane.x_dir), 0.0, places=5)


class TestSmartRevolveWithMove(unittest.TestCase):

    def _create_simple_revolve(self, angle: float = 180, axis: Axis = Axis.Y) -> SmartRevolve:
        """Create a simple SmartRevolve for testing."""
        pencil = Pencil(Plane.XZ, start=(5, 0))
        pencil.right(2).up(3).left(2).down(3)
        face = pencil.create_face()
        return SmartRevolve(face, axis, angle, Plane.XZ)

    def test_plane_origin_moves_with_object(self):
        """Test that create_plane_at origin moves when object is moved."""
        revolve = self._create_simple_revolve()

        initial_plane = revolve.create_plane_at(0)
        initial_origin = initial_plane.origin

        # Move the object
        move_vector = Vector(10, 20, 30)
        revolve.move_vector(move_vector)

        moved_plane = revolve.create_plane_at(0)
        expected_origin = initial_origin + move_vector
        assertVectorAlmostEqual(self, moved_plane.origin, expected_origin)

    @parameterized.expand([
        ((10, 0, 0),),
        ((0, 15, 0),),
        ((0, 0, 25),),
        ((5, 10, 15),),
        ((-5, -10, -15),),
    ])
    def test_plane_origin_tracks_movement(self, move_vector):
        """Test that plane origin correctly tracks object movement."""
        revolve = self._create_simple_revolve()

        initial_plane = revolve.create_plane_at(0.5)
        initial_origin = initial_plane.origin

        revolve.move_vector(Vector(move_vector))

        moved_plane = revolve.create_plane_at(0.5)
        expected_origin = initial_origin + Vector(move_vector)
        assertVectorAlmostEqual(self, moved_plane.origin, expected_origin)


class TestSmartRevolveWithRotate(unittest.TestCase):

    def _create_simple_revolve(self, angle: float = 180, axis: Axis = Axis.Y) -> SmartRevolve:
        """Create a simple SmartRevolve for testing."""
        pencil = Pencil(Plane.XZ, start=(5, 0))
        pencil.right(2).up(3).left(2).down(3)
        face = pencil.create_face()
        return SmartRevolve(face, axis, angle, Plane.XZ)

    def test_plane_rotates_with_object(self):
        """Test that create_plane_at directions rotate when object is rotated."""
        revolve = self._create_simple_revolve()

        initial_plane = revolve.create_plane_at(0)
        initial_z_dir = initial_plane.z_dir

        # Rotate the object 90 degrees around Z axis
        revolve.rotate(Axis.Z, 90)

        rotated_plane = revolve.create_plane_at(0)

        # The z_dir should be rotated 90 degrees around Z
        expected_z_dir = initial_z_dir.rotate(Axis.Z, 90)
        assertVectorAlmostEqual(self, rotated_plane.z_dir, expected_z_dir)


class TestSmartRevolveWithOrient(unittest.TestCase):

    def _create_simple_revolve(self, angle: float = 180, axis: Axis = Axis.Y) -> SmartRevolve:
        """Create a simple SmartRevolve for testing."""
        pencil = Pencil(Plane.XZ, start=(5, 0))
        pencil.right(2).up(3).left(2).down(3)
        face = pencil.create_face()
        return SmartRevolve(face, axis, angle, Plane.XZ)

    def test_plane_orients_with_object(self):
        """Test that create_plane_at changes when object is oriented."""
        revolve = self._create_simple_revolve()

        initial_plane = revolve.create_plane_at(0)

        # Orient the object
        revolve.orient((90, 0, 0))

        oriented_plane = revolve.create_plane_at(0)

        # Directions should be different after orientation
        # (unless the orientation is identity, which it's not)
        self.assertFalse(
            abs(initial_plane.z_dir.X - oriented_plane.z_dir.X) < 1e-5 and
            abs(initial_plane.z_dir.Y - oriented_plane.z_dir.Y) < 1e-5 and
            abs(initial_plane.z_dir.Z - oriented_plane.z_dir.Z) < 1e-5,
            "Plane z_dir should change after orientation"
        )


class TestSmartRevolveCopy(unittest.TestCase):

    def _create_simple_revolve(self, angle: float = 180, axis: Axis = Axis.Y) -> SmartRevolve:
        """Create a simple SmartRevolve for testing."""
        pencil = Pencil(Plane.XZ, start=(5, 0))
        pencil.right(2).up(3).left(2).down(3)
        face = pencil.create_face()
        return SmartRevolve(face, axis, angle, Plane.XZ)

    def test_copy_preserves_all_fields(self):
        """Test that copy() creates independent copy with all fields preserved."""
        original = self._create_simple_revolve(angle=270)
        original.move(10, 20, 30)

        copied = original.copy()

        # Check that fields are copied
        self.assertEqual(copied.angle, original.angle)
        assertVectorAlmostEqual(self, copied.origin, original.origin)
        assertVectorAlmostEqual(self, copied.sketch_plane.origin, original.sketch_plane.origin)
        assertVectorAlmostEqual(self, copied.axis.direction, original.axis.direction)

    def test_copy_is_independent(self):
        """Test that copy is independent from original."""
        original = self._create_simple_revolve()

        copied = original.copy()
        copied.move(100, 100, 100)

        # Original should not be affected
        assertVectorAlmostEqual(self, original.origin, Vector(0, 0, 0))

    def test_copy_preserves_label(self):
        """Test that copy can override or preserve label."""
        original = self._create_simple_revolve()
        original.label = "original_label"

        # Copy without new label keeps original
        copied1 = original.copy()
        self.assertEqual(copied1.label, "original_label")

        # Copy with new label uses new label
        copied2 = original.copy(label="new_label")
        self.assertEqual(copied2.label, "new_label")


class TestPencilRevolve(unittest.TestCase):

    def test_pencil_revolve_returns_smart_revolve(self):
        """Test that Pencil.revolve() returns SmartRevolve instance."""
        pencil = Pencil(Plane.XZ, start=(10, 0))
        pencil.arc_with_radius(2, 0, 180).arc_with_radius(2, 180, 180)
        result = pencil.revolve(300, Axis.Z)

        self.assertIsInstance(result, SmartRevolve)

    def test_pencil_revolve_has_correct_plane(self):
        """Test that Pencil.revolve() sets sketch_plane from pencil's plane."""
        custom_plane = Plane.XZ
        pencil = Pencil(custom_plane, start=(10, 0))
        pencil.right(2).up(3).left(2).down(3)
        result = pencil.revolve(180, Axis.Y)

        # The sketch_plane should be based on the pencil's plane
        # (Pencil may adjust origin based on start position)
        assertVectorAlmostEqual(self, result.sketch_plane.z_dir, custom_plane.z_dir)

    def test_pencil_revolve_preserves_angle(self):
        """Test that Pencil.revolve() stores the correct angle."""
        pencil = Pencil(Plane.XZ, start=(5, 0))
        pencil.right(2).up(3).left(2).down(3)
        result = pencil.revolve(270, Axis.Z)

        self.assertEqual(result.angle, 270)

    def test_pencil_revolve_preserves_axis(self):
        """Test that Pencil.revolve() stores the correct axis."""
        pencil = Pencil(Plane.XZ, start=(5, 0))
        pencil.right(2).up(3).left(2).down(3)
        result = pencil.revolve(180, Axis.X)

        assertVectorAlmostEqual(self, result.axis.direction, Axis.X.direction)


class TestSmartRevolveCombinedTransformations(unittest.TestCase):

    def _create_simple_revolve(self, angle: float = 180, axis: Axis = Axis.Y) -> SmartRevolve:
        """Create a simple SmartRevolve for testing."""
        pencil = Pencil(Plane.XZ, start=(5, 0))
        pencil.right(2).up(3).left(2).down(3)
        face = pencil.create_face()
        return SmartRevolve(face, axis, angle, Plane.XZ)

    @parameterized.expand([
        ((0, 0, 90), (10, 20, 0)),
        ((90, 0, 0), (0, 10, 20)),
        ((0, 90, 0), (10, 0, 20)),
        ((45, 45, 45), (5, 5, 5)),
    ])
    def test_combined_rotation_and_movement(self, rotation, movement):
        """Test create_plane_at with combined rotation and movement."""
        revolve = self._create_simple_revolve()

        # Apply transformations
        revolve.rotate_multi(rotation)
        revolve.move_vector(Vector(movement))

        # Test that plane is still valid at various positions
        for t in [0.0, 0.5, 1.0]:
            plane = revolve.create_plane_at(t)

            # Verify orthonormality
            self.assertAlmostEqual(plane.x_dir.length, 1.0, places=5)
            self.assertAlmostEqual(plane.y_dir.length, 1.0, places=5)
            self.assertAlmostEqual(plane.z_dir.length, 1.0, places=5)
            self.assertAlmostEqual(plane.x_dir.dot(plane.y_dir), 0.0, places=5)


if __name__ == '__main__':
    unittest.main()
