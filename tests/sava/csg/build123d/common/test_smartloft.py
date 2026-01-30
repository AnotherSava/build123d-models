"""Tests for SmartLoft profile tracking through transformations."""

import unittest

from build123d import Axis, Circle, Vector

from sava.csg.build123d.common.smartloft import SmartLoft
from tests.sava.csg.build123d.test_utils import assertVectorAlmostEqual


class TestSmartLoftProfileTracking(unittest.TestCase):
    """Tests for base_profile and target_profile tracking through move/rotate/orient."""

    def _create_smart_loft(self) -> SmartLoft:
        """Create a simple SmartLoft for testing."""
        base = Circle(10).face()
        target = Circle(5).face()
        return SmartLoft.create(base, target, height=20)

    def test_initial_profile_positions(self):
        """Test that profiles are at correct initial positions."""
        loft = self._create_smart_loft()

        assertVectorAlmostEqual(self, loft.base_profile.center(), Vector(0, 0, 0))
        assertVectorAlmostEqual(self, loft.target_profile.center(), Vector(0, 0, 20))

    def test_move_tracks_profiles(self):
        """Test that move() updates profile positions."""
        loft = self._create_smart_loft()
        loft.move(10, 20, 30)

        assertVectorAlmostEqual(self, loft.base_profile.center(), Vector(10, 20, 30))
        assertVectorAlmostEqual(self, loft.target_profile.center(), Vector(10, 20, 50))

    def test_rotate_z_tracks_profiles(self):
        """Test that rotate() around Z axis updates profile positions."""
        loft = self._create_smart_loft()
        # Move off-center first so rotation has visible effect on position
        loft.move(10, 0, 0)
        loft.rotate(Axis.Z, 90)

        # (10, 0, 0) rotated 90° around Z becomes (0, 10, 0)
        assertVectorAlmostEqual(self, loft.base_profile.center(), Vector(0, 10, 0))
        # (10, 0, 20) rotated 90° around Z becomes (0, 10, 20)
        assertVectorAlmostEqual(self, loft.target_profile.center(), Vector(0, 10, 20))

    def test_rotate_x_tracks_profiles(self):
        """Test that rotate() around X axis updates profile positions."""
        loft = self._create_smart_loft()
        loft.rotate(Axis.X, 90)

        # Base at origin stays at origin
        assertVectorAlmostEqual(self, loft.base_profile.center(), Vector(0, 0, 0))
        # (0, 0, 20) rotated 90° around X becomes (0, -20, 0)
        assertVectorAlmostEqual(self, loft.target_profile.center(), Vector(0, -20, 0))

    def test_orient_tracks_profiles(self):
        """Test that orient() updates profile orientations."""
        loft = self._create_smart_loft()
        loft.orient((90, 0, 0))

        # Orient rotates around object center, profiles should have same orientation
        self.assertEqual(loft.base_profile.orientation, Vector(90, 0, 0))
        self.assertEqual(loft.target_profile.orientation, Vector(90, 0, 0))

    def test_combined_move_rotate(self):
        """Test profiles track through move then rotate."""
        loft = self._create_smart_loft()
        loft.move(10, 0, 0)
        loft.rotate(Axis.Z, 90)

        assertVectorAlmostEqual(self, loft.base_profile.center(), Vector(0, 10, 0))
        assertVectorAlmostEqual(self, loft.target_profile.center(), Vector(0, 10, 20))

    def test_combined_rotate_move(self):
        """Test profiles track through rotate then move."""
        loft = self._create_smart_loft()
        loft.rotate(Axis.Z, 90)
        loft.move(10, 20, 30)

        # After rotate: base at (0,0,0), top at (0,0,20)
        # After move: base at (10,20,30), top at (10,20,50)
        assertVectorAlmostEqual(self, loft.base_profile.center(), Vector(10, 20, 30))
        assertVectorAlmostEqual(self, loft.target_profile.center(), Vector(10, 20, 50))

    def test_profiles_match_solid_center(self):
        """Test that profile centers stay aligned with solid after transformations."""
        loft = self._create_smart_loft()
        loft.move(5, 10, 15)
        loft.rotate(Axis.Z, 45)

        # The midpoint between base and top profile centers should match solid center
        mid_profile_z = (loft.base_profile.center().Z + loft.target_profile.center().Z) / 2
        self.assertAlmostEqual(mid_profile_z, loft.z_mid, places=5)


class TestSmartLoftExtrude(unittest.TestCase):
    """Tests for SmartLoft.extrude() profile tracking."""

    def test_extrude_initial_positions(self):
        """Test that extrude creates profiles at correct positions."""
        profile = Circle(10).face()
        loft = SmartLoft.extrude(profile, 30)

        assertVectorAlmostEqual(self, loft.base_profile.center(), Vector(0, 0, 0))
        assertVectorAlmostEqual(self, loft.target_profile.center(), Vector(0, 0, 30))

    def test_extrude_negative_direction(self):
        """Test extrude with negative Z direction."""
        profile = Circle(10).face()
        loft = SmartLoft.extrude(profile, 20, direction=(0, 0, -1))

        assertVectorAlmostEqual(self, loft.base_profile.center(), Vector(0, 0, 0))
        assertVectorAlmostEqual(self, loft.target_profile.center(), Vector(0, 0, -20))

    def test_extrude_move_tracks_profiles(self):
        """Test that move() works on extruded SmartLoft."""
        profile = Circle(10).face()
        loft = SmartLoft.extrude(profile, 30)
        loft.move(5, 10, 15)

        assertVectorAlmostEqual(self, loft.base_profile.center(), Vector(5, 10, 15))
        assertVectorAlmostEqual(self, loft.target_profile.center(), Vector(5, 10, 45))


if __name__ == "__main__":
    unittest.main()
