import unittest
from math import atan, degrees

from build123d import Axis, Compound, Sphere, Vector
from parameterized import parameterized

from sava.csg.build123d.common.geometry import Direction
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartsolid import SmartSolid
from tests.sava.csg.build123d.test_utils import assertVectorAlmostEqual


class TestSmartBoxTaperingConstructor(unittest.TestCase):
    """Per-side tapering via the constructor."""

    def test_plain_box_not_tapered(self):
        box = SmartBox(100, 80, 50)
        self.assertFalse(box.tapered)
        self.assertEqual((box.tapered_length, box.tapered_width), (100, 80))

    def test_symmetric_tapered_length(self):
        box = SmartBox(100, 80, 50, tapered_length=80)
        self.assertTrue(box.tapered)
        self.assertAlmostEqual(box.tapered_length, 80)
        self.assertAlmostEqual(box.tapered_width, 80)  # untouched
        assertVectorAlmostEqual(self, box.bound_box.size, (100, 80, 50))  # base sets the footprint

    def test_symmetric_dimension_matches_equivalent_per_side_angles(self):
        # tapered_length=80 on length=100 over height=50 => each wall leans in by 10 over 50.
        angle = degrees(atan(50 / 10))
        by_dim = SmartBox(100, 80, 50, tapered_length=80)
        by_angle = SmartBox(100, 80, 50, angle_east=angle, angle_west=angle)
        self.assertAlmostEqual(by_dim.tapered_length, by_angle.tapered_length, places=4)
        assertVectorAlmostEqual(self, by_dim.bound_box.size, by_angle.bound_box.size)

    def test_vertical_angle_is_not_tapered(self):
        box = SmartBox(100, 80, 50, angle_east=90, angle_west=90)
        self.assertFalse(box.tapered)

    def test_asymmetric_angles_produce_offcenter_top(self):
        # East vertical, west leans in 45° over height 50 => west top edge moves in by 50.
        box = SmartBox(100, 80, 50, angle_east=90, angle_west=45)
        self.assertTrue(box.tapered)
        self.assertAlmostEqual(box._top.x_max, 50)    # east edge unchanged (length/2)
        self.assertAlmostEqual(box._top.x_min, 0)     # west edge moved inward by 50 from -50
        self.assertAlmostEqual(box.tapered_length, 50)

    @parameterized.expand([
        ("length_pair", {"tapered_length": 90, "angle_east": 80, "angle_west": 80}),
        ("width_pair", {"tapered_width": 70, "angle_north": 80, "angle_south": 80}),
    ])
    def test_redundant_symmetric_and_both_angles_rejected(self, _name, kwargs):
        with self.assertRaises(AssertionError):
            SmartBox(100, 80, 50, **kwargs)

    def test_per_side_angle_overrides_symmetric_for_its_side_only(self):
        # tapered_length governs west; angle_east overrides only the east wall.
        box = SmartBox(100, 80, 50, tapered_length=80, angle_east=90)
        self.assertAlmostEqual(box._top.x_max, 50)    # east vertical (angle 90)
        self.assertAlmostEqual(box._top.x_min, -40)   # west from tapered_length=80 => -80/2


class TestSmartBoxTaper(unittest.TestCase):
    """The taper() instance method."""

    def test_taper_at_origin_matches_constructor(self):
        base = SmartBox(100, 80, 50)
        tapered = base.taper(angle_east=90, angle_west=45)
        direct = SmartBox(100, 80, 50, angle_east=90, angle_west=45)
        assertVectorAlmostEqual(self, tapered.bound_box.size, direct.bound_box.size)
        assertVectorAlmostEqual(self, tapered.bound_box.center(), direct.bound_box.center())

    def test_taper_preserves_placement(self):
        moved = SmartBox(100, 80, 50).move(20, 30, 5)
        tapered = moved.taper(tapered_length=60, tapered_width=50)
        expected = SmartBox(100, 80, 50, tapered_length=60, tapered_width=50).move(20, 30, 5)
        assertVectorAlmostEqual(self, tapered.bound_box.center(), expected.bound_box.center())
        assertVectorAlmostEqual(self, tapered.bound_box.size, expected.bound_box.size)

    def test_taper_preserves_placement_when_rotated(self):
        rotated = SmartBox(40, 20, 10).move(5, 0, 0).rotate_z(30)
        tapered = rotated.taper(tapered_width=10)
        expected = SmartBox(40, 20, 10, tapered_width=10).move(5, 0, 0).rotate_z(30)
        assertVectorAlmostEqual(self, tapered.bound_box.center(), expected.bound_box.center())
        assertVectorAlmostEqual(self, tapered.bound_box.size, expected.bound_box.size)

    def test_taper_preserves_placement_on_reframed_box(self):
        # Regression: with_top() builds via a plane, so its _orientation doesn't track the
        # rotation; taper must copy the real location (colocate), not replay _orientation.
        # An inward taper leaves the base widest, so the outer AABB must equal the source.
        reframed = SmartBox(10, 20, 30).with_top(Direction.N)
        tapered = reframed.taper(tapered_length=8)
        assertVectorAlmostEqual(self, tapered.bound_box.size, reframed.bound_box.size)
        assertVectorAlmostEqual(self, tapered.bound_box.center(), reframed.bound_box.center())

    def test_taper_replaces_existing_taper_from_base(self):
        # Re-tapering uses the base footprint; the prior taper is discarded, not compounded.
        pre = SmartBox(100, 80, 50, tapered_length=70)
        retapered = pre.taper(tapered_width=60)
        fresh = SmartBox(100, 80, 50, tapered_width=60)
        assertVectorAlmostEqual(self, retapered.bound_box.size, fresh.bound_box.size)
        self.assertAlmostEqual(retapered.tapered_length, 100)  # length pair back to vertical
        self.assertAlmostEqual(retapered.tapered_width, 60)


class TestSmartBoxWithTop(unittest.TestCase):
    """with_top() re-frames which face is the top, keeping the same world occupancy."""

    # (direction, expected intrinsic length/width/height) for a 10x20x30 (L/W/H) box.
    @parameterized.expand([
        ("N", Direction.N, (10, 30, 20)),
        ("S", Direction.S, (10, 30, 20)),
        ("E", Direction.E, (20, 30, 10)),
        ("W", Direction.W, (20, 30, 10)),
        ("U", Direction.U, (10, 20, 30)),
        ("D", Direction.D, (10, 20, 30)),
    ])
    def test_reframes_dimensions(self, _name, direction, expected_lwh):
        result = SmartBox(10, 20, 30).with_top(direction)
        self.assertEqual((result.length, result.width, result.height), expected_lwh)

    @parameterized.expand([
        ("N", Direction.N), ("S", Direction.S), ("E", Direction.E),
        ("W", Direction.W), ("U", Direction.U), ("D", Direction.D),
    ])
    def test_occupies_same_space(self, _name, direction):
        base = SmartBox(10, 20, 30).move(5, 7, 11)
        result = base.with_top(direction)
        assertVectorAlmostEqual(self, result.bound_box.size, base.bound_box.size)
        assertVectorAlmostEqual(self, result.bound_box.center(), base.bound_box.center())
        self.assertAlmostEqual(result.solid.volume, base.solid.volume, places=4)

    def test_height_is_extent_along_direction(self):
        base = SmartBox(10, 20, 30)
        self.assertAlmostEqual(base.with_top(Direction.N).height, 20)  # Y extent
        self.assertAlmostEqual(base.with_top(Direction.E).height, 10)  # X extent
        self.assertAlmostEqual(base.with_top(Direction.U).height, 30)  # Z extent (unchanged)

    def test_up_is_noop_dimensions(self):
        base = SmartBox(10, 20, 30).move(1, 2, 3)
        result = base.with_top(Direction.U)
        self.assertEqual((result.length, result.width, result.height), (10, 20, 30))
        assertVectorAlmostEqual(self, result.bound_box.center(), base.bound_box.center())

    def test_result_has_honest_location_for_colocate(self):
        # with_top builds at the world origin then moves, so solid.location stays honest:
        # colocating another box onto the result reproduces its exact occupancy.
        reframed = SmartBox(10, 20, 30).with_top(Direction.N)
        fresh = SmartBox(reframed.length, reframed.width, reframed.height)
        fresh.colocate(reframed)
        assertVectorAlmostEqual(self, fresh.bound_box.size, reframed.bound_box.size)
        assertVectorAlmostEqual(self, fresh.bound_box.center(), reframed.bound_box.center())

    def test_orientation_invariant_holds(self):
        # with_top builds via a plane: __init__ must seed _orientation from solid.orientation
        # (not assume (0,0,0)), or rotate()/transform-replay would drop the plane rotation.
        reframed = SmartBox(10, 20, 30).with_top(Direction.N)
        assertVectorAlmostEqual(self, reframed._orientation, reframed.solid.orientation)

    def test_rotate_composes_with_reframe(self):
        # Regression: rotating a plane-constructed (reframed) box must compose with its baked
        # orientation, matching a direct rotation of the underlying solid.
        reframed = SmartBox(10, 20, 30).with_top(Direction.N)
        truth = reframed.solid.rotate(Axis.Z, 90).bounding_box()
        rotated = reframed.copy().rotate_z(90)
        assertVectorAlmostEqual(self, rotated.bound_box.size, truth.size)
        assertVectorAlmostEqual(self, rotated.bound_box.center(), truth.center())

    def test_rejects_tapered_box(self):
        with self.assertRaises(AssertionError):
            SmartBox(10, 20, 30, tapered_length=8).with_top(Direction.N)

    def test_rejects_rotated_box(self):
        with self.assertRaises(AssertionError):
            SmartBox(10, 20, 30).rotate_z(30).with_top(Direction.N)

    def test_label_inherited_and_overridable(self):
        box = SmartBox(4, 6, 8, label="part")
        self.assertEqual(box.with_top(Direction.E).label, "part")
        self.assertEqual(box.with_top(Direction.E, label="other").label, "other")


class TestBevel(unittest.TestCase):
    """SmartSolid.bevel / beveled — angled cut of a side face (uses with_top + taper)."""

    def _removed_centroid_rel(self, model, side, direction, angle=70):
        """Centroid of the wedge bevel removes, relative to the model centre."""
        center = Vector(model.bound_box.center())
        result = model.beveled(side, direction, angle)
        removed = model.solid.cut(result.wrap_solid())
        removed = Compound(removed) if hasattr(removed, "__len__") else removed
        return Vector(removed.center()) - center

    @parameterized.expand([
        ("E_U", Direction.E, Direction.U), ("W_D", Direction.W, Direction.D),
        ("N_U", Direction.N, Direction.U), ("S_D", Direction.S, Direction.D),
        ("E_N", Direction.E, Direction.N), ("W_S", Direction.W, Direction.S),
        ("N_E", Direction.N, Direction.E), ("S_W", Direction.S, Direction.W),
    ])
    def test_cuts_correct_world_face(self, _name, side, direction):
        # The removed wedge must sit on the world `side` face and deepen toward `direction`.
        c = self._removed_centroid_rel(SmartBox(40, 30, 20), side, direction)
        self.assertGreater(c.dot(side.value), 0.5)
        self.assertGreater(c.dot(direction.value), 0.5)

    def test_beveled_is_a_copy(self):
        model = SmartBox(40, 30, 20)
        v0 = model.solid.volume
        result = model.beveled(Direction.E, Direction.U, 60)
        self.assertAlmostEqual(model.solid.volume, v0, places=4)   # original untouched
        self.assertLess(result.solid.volume, v0)                   # material removed

    def test_bevel_mutates_in_place_and_returns_self(self):
        model = SmartBox(40, 30, 20)
        v0 = model.solid.volume
        result = model.bevel(Direction.E, Direction.U, 60)
        self.assertIs(result, model)
        self.assertLess(model.solid.volume, v0)

    @parameterized.expand([("E_E", Direction.E, Direction.E), ("N_S", Direction.N, Direction.S)])
    def test_requires_perpendicular(self, _name, side, direction):
        with self.assertRaises(AssertionError):
            SmartBox(10, 10, 10).bevel(side, direction, 45)

    def test_works_on_non_box_solid(self):
        sphere = SmartSolid(Sphere(10))
        v0 = sphere.solid.volume
        sphere.bevel(Direction.E, Direction.U, 60)
        self.assertLess(sphere.solid.volume, v0)


if __name__ == "__main__":
    unittest.main()
