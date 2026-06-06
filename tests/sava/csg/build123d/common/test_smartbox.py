import unittest
from math import atan, degrees

from build123d import Compound, Sphere, Vector
from parameterized import parameterized

from sava.csg.build123d.common.geometry import Direction
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartsolid import SmartSolid
from tests.sava.csg.build123d.test_utils import assertVectorAlmostEqual


class TestSmartBoxTaperingConstructor(unittest.TestCase):
    """Per-side tapering via the constructor."""

    def test_plain_box_not_tapered(self) -> None:
        box = SmartBox(100, 80, 50)
        self.assertFalse(box.tapered)
        self.assertEqual((box.tapered_length, box.tapered_width), (100, 80))

    def test_symmetric_tapered_length(self) -> None:
        box = SmartBox(100, 80, 50, tapered_length=80)
        self.assertTrue(box.tapered)
        self.assertAlmostEqual(box.tapered_length, 80)
        self.assertAlmostEqual(box.tapered_width, 80)  # untouched
        assertVectorAlmostEqual(self, box.bound_box.size, (100, 80, 50))  # base sets the footprint

    def test_symmetric_dimension_matches_equivalent_per_side_angles(self) -> None:
        # tapered_length=80 on length=100 over height=50 => each wall leans in by 10 over 50.
        angle = degrees(atan(50 / 10))
        by_dim = SmartBox(100, 80, 50, tapered_length=80)
        by_angle = SmartBox(100, 80, 50, angle_east=angle, angle_west=angle)
        self.assertAlmostEqual(by_dim.tapered_length, by_angle.tapered_length, places=4)
        assertVectorAlmostEqual(self, by_dim.bound_box.size, by_angle.bound_box.size)

    def test_vertical_angle_is_not_tapered(self) -> None:
        box = SmartBox(100, 80, 50, angle_east=90, angle_west=90)
        self.assertFalse(box.tapered)

    def test_asymmetric_angles_produce_offcenter_top(self) -> None:
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
    def test_redundant_symmetric_and_both_angles_rejected(self, _name, kwargs) -> None:
        with self.assertRaises(AssertionError):
            SmartBox(100, 80, 50, **kwargs)

    def test_per_side_angle_overrides_symmetric_for_its_side_only(self) -> None:
        # tapered_length governs west; angle_east overrides only the east wall.
        box = SmartBox(100, 80, 50, tapered_length=80, angle_east=90)
        self.assertAlmostEqual(box._top.x_max, 50)    # east vertical (angle 90)
        self.assertAlmostEqual(box._top.x_min, -40)   # west from tapered_length=80 => -80/2


class TestBevel(unittest.TestCase):
    """SmartSolid.bevel / beveled — angled planar cut of a side face."""

    def _removed_centroid_rel(self, model, side, direction, angle=70) -> Vector:
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
    def test_cuts_correct_world_face(self, _name, side, direction) -> None:
        # The removed wedge must sit on the world `side` face and deepen toward `direction`.
        c = self._removed_centroid_rel(SmartBox(40, 30, 20), side, direction)
        self.assertGreater(c.dot(side.value), 0.5)
        self.assertGreater(c.dot(direction.value), 0.5)

    def test_beveled_is_a_copy(self) -> None:
        model = SmartBox(40, 30, 20)
        v0 = model.solid.volume
        result = model.beveled(Direction.E, Direction.U, 60)
        self.assertAlmostEqual(model.solid.volume, v0, places=4)   # original untouched
        self.assertLess(result.solid.volume, v0)                   # material removed

    def test_bevel_mutates_in_place_and_returns_self(self) -> None:
        model = SmartBox(40, 30, 20)
        v0 = model.solid.volume
        result = model.bevel(Direction.E, Direction.U, 60)
        self.assertIs(result, model)
        self.assertLess(model.solid.volume, v0)

    @parameterized.expand([("E_E", Direction.E, Direction.E), ("N_S", Direction.N, Direction.S)])
    def test_requires_perpendicular(self, _name, side, direction) -> None:
        with self.assertRaises(AssertionError):
            SmartBox(10, 10, 10).bevel(side, direction, 45)

    def test_works_on_non_box_solid(self) -> None:
        sphere = SmartSolid(Sphere(10))
        v0 = sphere.solid.volume
        sphere.bevel(Direction.E, Direction.U, 60)
        self.assertLess(sphere.solid.volume, v0)

    @parameterized.expand([
        # 40x30x20 box (24000): bevel(E, U, 45) wall is x = 20 + offset - z
        ("no_offset", 0, 24000 - 6000),       # removed width z: triangle 0..20
        ("deeper", -5, 24000 - 9000),         # removed width 5+z: trapezoid 5..25
        ("shallower", 5, 24000 - 3375),       # removed width max(0, z-5): triangle 0..15
        ("past_face", 25, 24000),             # wall never enters the box: no cut
    ])
    def test_offset_volumes(self, _name, offset, expected_volume) -> None:
        model = SmartBox(40, 30, 20).bevel(Direction.E, Direction.U, 45, offset=offset)
        self.assertAlmostEqual(model.solid.volume, expected_volume, places=4)

    def test_45_on_solid_taller_than_wide(self) -> None:
        # 10x10x40: a 45° inset (40) exceeds the footprint (10) — the old taper-box
        # implementation could not build this cutter at all. Wall x = 5 - z, removed
        # width min(z, 10): 1/2*10*10 + 30*10 = 350, times y_size 10.
        model = SmartBox(10, 10, 40).bevel(Direction.E, Direction.U, 45)
        self.assertAlmostEqual(model.solid.volume, 4000 - 3500, places=4)


class TestBevelEdge(unittest.TestCase):
    """SmartSolid.bevel_edge / beveled_edge — flat wedge off a bound-box edge."""

    @parameterized.expand([
        # 40x30x20 box (24000); wedge cross-section = size_a * size_b / 2, prism along the third axis
        ("symmetric_EU", Direction.E, Direction.U, 5, None, 24000 - 5 * 5 / 2 * 30),
        ("asymmetric_EU", Direction.E, Direction.U, 5, 10, 24000 - 5 * 10 / 2 * 30),
        ("symmetric_NU", Direction.N, Direction.U, 4, None, 24000 - 4 * 4 / 2 * 40),
        ("vertical_edge_EN", Direction.E, Direction.N, 6, 3, 24000 - 6 * 3 / 2 * 20),
    ])
    def test_volumes(self, _name, side_a, side_b, size_a, size_b, expected_volume) -> None:
        model = SmartBox(40, 30, 20).bevel_edge(side_a, side_b, size_a, size_b)
        self.assertAlmostEqual(model.solid.volume, expected_volume, places=4)

    def test_removed_wedge_sits_on_the_edge(self) -> None:
        model = SmartBox(40, 30, 20)
        result = model.beveled_edge(Direction.E, Direction.U, 5)
        removed = model.solid.cut(result.wrap_solid())
        removed = Compound(removed) if hasattr(removed, "__len__") else removed
        center = Vector(removed.center())
        self.assertAlmostEqual(center.X, 20 - 5 / 3, places=4)   # triangle centroid off the east face
        self.assertAlmostEqual(center.Z, 20 - 5 / 3, places=4)   # and off the top face

    def test_size_order_matches_side_order(self) -> None:
        # size_a lies on the side_a face: swapping the sides swaps the legs
        swapped = SmartBox(40, 30, 20).bevel_edge(Direction.U, Direction.E, 10, 5)
        direct = SmartBox(40, 30, 20).bevel_edge(Direction.E, Direction.U, 5, 10)
        self.assertAlmostEqual(swapped.solid.volume, direct.solid.volume, places=4)
        self.assertAlmostEqual(Vector(swapped.solid.center()).X, Vector(direct.solid.center()).X, places=4)
        self.assertAlmostEqual(Vector(swapped.solid.center()).Z, Vector(direct.solid.center()).Z, places=4)

    def test_beveled_edge_is_a_copy(self) -> None:
        model = SmartBox(40, 30, 20)
        v0 = model.solid.volume
        result = model.beveled_edge(Direction.E, Direction.U, 5)
        self.assertAlmostEqual(model.solid.volume, v0, places=4)
        self.assertLess(result.solid.volume, v0)

    def test_requires_perpendicular(self) -> None:
        with self.assertRaises(AssertionError):
            SmartBox(10, 10, 10).bevel_edge(Direction.E, Direction.W, 2)

    def test_works_on_non_box_solid(self) -> None:
        # Legs of 8 put the cut plane at x + z = 12, inside the sphere's max of 10*sqrt(2)
        sphere = SmartSolid(Sphere(10))
        v0 = sphere.solid.volume
        sphere.bevel_edge(Direction.E, Direction.U, 8)
        self.assertLess(sphere.solid.volume, v0)


if __name__ == "__main__":
    unittest.main()
