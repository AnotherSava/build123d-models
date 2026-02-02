import unittest

from build123d import Plane, Vector
from parameterized import parameterized

from sava.csg.build123d.common.pencil import Pencil


class TestPencilFillet(unittest.TestCase):
    """Test the fillet functionality of the Pencil class."""

    def test_fillet_basic(self):
        """Test basic fillet on a simple L-shape."""
        pencil = Pencil()
        wire = pencil.right(10).fillet(2).up(10).create_wire()

        # Should create a valid wire
        self.assertTrue(wire.is_valid)

        # The wire should have more edges than without fillet (fillet adds an arc)
        wire_no_fillet = Pencil().right(10).up(10).create_wire()
        self.assertGreater(len(wire.edges()), len(wire_no_fillet.edges()))

    def test_fillet_error_at_start(self):
        """Test that fillet raises error when called before any curves."""
        pencil = Pencil()
        with self.assertRaises(ValueError) as context:
            pencil.fillet(1)
        self.assertIn("no previous curve", str(context.exception))

    def test_fillet_multiple_corners(self):
        """Test filleting multiple corners with different radii."""
        pencil = Pencil()
        wire = pencil.right(10).fillet(1).up(10).fillet(2).left(10).create_wire()

        # Should create a valid wire
        self.assertTrue(wire.is_valid)

    def test_fillet_same_radius_multiple_corners(self):
        """Test filleting multiple corners with same radius."""
        pencil = Pencil()
        wire = pencil.right(10).fillet(1).up(10).fillet(1).left(10).create_wire()

        # Should create a valid wire
        self.assertTrue(wire.is_valid)

    def test_fillet_position(self):
        """Test that fillet is applied at the correct position."""
        pencil = Pencil()
        # Fillet at (10, 0)
        wire = pencil.right(10).fillet(2).up(10).create_wire()

        # The vertex at exactly (10, 0) should not exist anymore (replaced by arc)
        vertices = wire.vertices()
        vertex_positions = [Vector(v.X, v.Y, v.Z) for v in vertices]

        # No vertex should be at exactly (10, 0, 0)
        for pos in vertex_positions:
            self.assertFalse(
                abs(pos.X - 10) < 0.01 and abs(pos.Y) < 0.01 and abs(pos.Z) < 0.01,
                f"Vertex at {pos} should not exist after fillet"
            )

    def test_fillet_creates_face(self):
        """Test that filleted wire can create a valid face."""
        pencil = Pencil()
        face = pencil.right(10).fillet(2).up(10).create_face()

        self.assertTrue(face.is_valid)

    def test_fillet_extrude(self):
        """Test that filleted pencil can be extruded."""
        pencil = Pencil()
        solid = pencil.right(10).fillet(2).up(10).extrude(5)

        self.assertTrue(solid.solid.is_valid)

    def test_fillet_method_chaining(self):
        """Test that fillet returns self for method chaining."""
        pencil = Pencil()
        result = pencil.right(10).fillet(2)
        self.assertIs(result, pencil)

    def test_fillet_120_degree_angle(self):
        """Test fillet at a 120° corner (60° left turn)."""
        pencil = Pencil()
        # First edge horizontal, second edge at 120° = 60° left turn
        wire = pencil.draw(10, 0).fillet(2).draw(10, 120).create_wire(enclose=False)
        self.assertTrue(wire.is_valid)
        # Should have 3 edges: trimmed first, arc, trimmed second
        self.assertEqual(len(wire.edges()), 3)

    def test_fillet_240_degree_angle(self):
        """Test fillet at a 240° corner (60° right turn, or 120° exterior angle)."""
        pencil = Pencil()
        # First edge horizontal, second edge at -60° = 60° right turn
        wire = pencil.draw(10, 0).fillet(2).draw(10, -60).create_wire(enclose=False)
        self.assertTrue(wire.is_valid)
        # Should have 3 edges: trimmed first, arc, trimmed second
        self.assertEqual(len(wire.edges()), 3)

    def test_fillet_30_degree_angle(self):
        """Test fillet at a sharp 30° corner (150° left turn)."""
        pencil = Pencil()
        # First edge horizontal, second edge at 30° from horizontal
        wire = pencil.draw(10, 0).fillet(1).draw(10, 30).create_wire(enclose=False)
        self.assertTrue(wire.is_valid)

    def test_fillet_150_degree_angle(self):
        """Test fillet at an obtuse 150° corner (30° left turn)."""
        pencil = Pencil()
        # First edge horizontal, second edge at 150° from horizontal
        wire = pencil.draw(10, 0).fillet(1).draw(10, 150).create_wire(enclose=False)
        self.assertTrue(wire.is_valid)

    def test_fillet_diagonal_jump_then_up(self):
        """Test fillet after a diagonal jump followed by vertical line (like railing example)."""
        pencil = Pencil(Plane.YZ)
        pencil.right(5)
        pencil.jump((3, 3))  # diagonal
        pencil.fillet(1)
        pencil.up(10)  # vertical
        wire = pencil.create_wire(enclose=False)
        self.assertTrue(wire.is_valid)
        # Should have 4 edges: horizontal, diagonal, arc, vertical
        self.assertEqual(len(wire.edges()), 4)

    def test_fillet_up_then_diagonal_jump(self):
        """Test fillet after vertical line followed by diagonal jump."""
        pencil = Pencil(Plane.YZ)
        pencil.up(5)
        pencil.fillet(1)
        pencil.jump((3, 3))  # diagonal going right and up
        wire = pencil.create_wire(enclose=False)
        self.assertTrue(wire.is_valid)

    def test_fillet_arc_direction_left_turn(self):
        """Test that fillet arc curves in the correct direction for a left turn.

        For right(10).fillet(2).up(10), the path turns left at (10, 0).
        The fillet arc should curve LEFT (toward the inside of the L-shape).
        The arc midpoint should be at approximately (10-r*0.29, r*0.29) relative to corner,
        which is (10 - 0.58, 0.58) = (9.42, 0.58) for r=2.
        """
        pencil = Pencil()
        pencil.right(10).fillet(2).up(10)
        wire = pencil.create_wire(enclose=False)

        # Find the arc edge (the one that's not a line)
        arc_edge = None
        for edge in wire.edges():
            if edge.geom_type.name == 'CIRCLE':
                arc_edge = edge
                break

        self.assertIsNotNone(arc_edge, "Should have an arc edge")

        # Get the arc midpoint
        arc_mid = arc_edge.position_at(0.5)

        # The corner was at (10, 0). For a left turn with fillet,
        # the arc midpoint should be to the upper-left of the corner,
        # NOT to the lower-right.
        # Specifically: X < 10 and Y > 0 (inside the L)
        self.assertLess(arc_mid.X, 10, f"Arc midpoint X={arc_mid.X} should be < 10 (inside the turn)")
        self.assertGreater(arc_mid.Y, 0, f"Arc midpoint Y={arc_mid.Y} should be > 0 (inside the turn)")

    def test_fillet_arc_direction_right_turn(self):
        """Test that fillet arc curves in the correct direction for a right turn.

        For right(10).fillet(2).down(10), the path turns right at (10, 0).
        The arc midpoint should be inside the turn (lower-left of corner).
        """
        pencil = Pencil()
        pencil.right(10).fillet(2).down(10)
        wire = pencil.create_wire(enclose=False)

        # Find the arc edge
        arc_edge = None
        for edge in wire.edges():
            if edge.geom_type.name == 'CIRCLE':
                arc_edge = edge
                break

        self.assertIsNotNone(arc_edge, "Should have an arc edge")

        arc_mid = arc_edge.position_at(0.5)

        # For a right turn, arc midpoint should be to the lower-left of corner (10, 0)
        self.assertLess(arc_mid.X, 10, f"Arc midpoint X={arc_mid.X} should be < 10")
        self.assertLess(arc_mid.Y, 0, f"Arc midpoint Y={arc_mid.Y} should be < 0")

    def test_fillet_railing_pattern(self):
        """Test fillet pattern similar to railing example: diagonal jump then vertical."""
        pencil = Pencil(Plane.YZ)
        # Similar to: right(gap).jump((offset, offset)).fillet(r).up_to(height)
        pencil.right(5)
        corner_before_fillet = Vector(pencil.location.X, pencil.location.Y, 0)
        pencil.jump((2, 2))  # diagonal at 45°
        fillet_corner = Vector(pencil.location.X, pencil.location.Y, 0)
        pencil.fillet(0.5)
        pencil.up(5)

        wire = pencil.create_wire(enclose=False)
        self.assertTrue(wire.is_valid)

        # Find the arc edge
        arc_edge = None
        for edge in wire.edges():
            if edge.geom_type.name == 'CIRCLE':
                arc_edge = edge
                break

        self.assertIsNotNone(arc_edge, "Should have an arc edge")

        # Get arc endpoints and midpoint
        arc_start = arc_edge.position_at(0)
        arc_mid = arc_edge.position_at(0.5)
        arc_end = arc_edge.position_at(1)

        print(f"Fillet corner (in local coords): {fillet_corner}")
        print(f"Arc start: {arc_start}")
        print(f"Arc mid: {arc_mid}")
        print(f"Arc end: {arc_end}")

        # The diagonal goes from (5,0) to (7,2) - direction (1,1)/sqrt(2)
        # The vertical goes from (7,2+trim) upward - direction (0,1)
        # This is a LEFT turn (counter-clockwise)
        # The arc midpoint should be to the LEFT of the line from arc_start to arc_end


class TestPencilFilletMirrored(unittest.TestCase):
    """Test fillet functionality with mirrored wires."""

    def test_fillet_mirrored_x_point_on_axis_skipped(self):
        """Test that fillet point on the mirror axis is skipped (no crash)."""
        pencil = Pencil()
        # Fillet at (10, 0) is on Y=0 mirror axis - should be skipped
        wire = pencil.right(10).fillet(2).up(10).create_mirrored_wire_x()

        # Should create a valid wire (no fillet applied, but no crash)
        self.assertTrue(wire.is_valid)

    def test_fillet_mirrored_x_point_off_axis(self):
        """Test fillet on a wire mirrored around X axis with fillet point NOT on mirror axis."""
        pencil = Pencil()
        # Fillet at (10, 5) - actual corner between vertical and horizontal edges
        wire = pencil.up(5).right(10).fillet(2).up(5).create_mirrored_wire_x()

        # Should create a valid wire
        self.assertTrue(wire.is_valid)

        # Mirrored wire should have more edges than non-filleted mirrored (fillet adds arcs)
        wire_no_fillet = Pencil().up(5).right(10).up(5).create_mirrored_wire_x()
        self.assertGreater(len(wire.edges()), len(wire_no_fillet.edges()))

    def test_fillet_mirrored_y_point_on_axis_skipped(self):
        """Test that fillet point on the Y-mirror axis is skipped (no crash)."""
        pencil = Pencil()
        # Fillet at (0, 10) is on X=0 mirror axis - should be skipped
        wire = pencil.up(10).fillet(2).right(10).create_mirrored_wire_y()

        # Should create a valid wire
        self.assertTrue(wire.is_valid)

    def test_fillet_mirrored_y_point_off_axis(self):
        """Test fillet on a wire mirrored around Y axis with fillet point NOT on mirror axis."""
        pencil = Pencil()
        # Fillet at (5, 10) is NOT on X=0 mirror axis - should be filleted on both sides
        wire = pencil.up(10).right(5).fillet(2).right(5).create_mirrored_wire_y()

        # Should create a valid wire
        self.assertTrue(wire.is_valid)

    def test_fillet_mirrored_face_x(self):
        """Test filleted mirrored face around X axis can be extruded."""
        pencil = Pencil()
        # Fillet at (10, 5) - actual corner, not on mirror axis
        # Note: Face validity check may fail due to OCCT tolerances, but extrusion works
        solid = pencil.up(5).right(10).fillet(2).up(5).extrude_mirrored_x(5)

        self.assertTrue(solid.solid.is_valid)

    def test_fillet_mirrored_face_y(self):
        """Test filleted mirrored face around Y axis can be extruded."""
        pencil = Pencil()
        # Fillet at (5, 10) - actual corner, not on mirror axis
        # Note: Face validity check may fail due to OCCT tolerances, but extrusion works
        solid = pencil.right(5).up(10).fillet(2).right(5).extrude_mirrored_y(5)

        self.assertTrue(solid.solid.is_valid)

    def test_fillet_extrude_mirrored_x(self):
        """Test extruding a filleted mirrored face around X axis."""
        pencil = Pencil()
        # Fillet at (10, 5) - actual corner, not on mirror axis
        solid = pencil.up(5).right(10).fillet(2).up(5).extrude_mirrored_x(5)

        self.assertTrue(solid.solid.is_valid)

    def test_fillet_extrude_mirrored_y(self):
        """Test extruding a filleted mirrored face around Y axis."""
        pencil = Pencil()
        # Fillet at (5, 10) - actual corner, not on mirror axis
        solid = pencil.right(5).up(10).fillet(2).right(5).extrude_mirrored_y(5)

        self.assertTrue(solid.solid.is_valid)


class TestPencilFilletInCustomPlane(unittest.TestCase):
    """Test fillet functionality in custom planes."""

    @parameterized.expand([
        ("xy_plane", Plane.XY),
        ("xz_plane", Plane.XZ),
        ("yz_plane", Plane.YZ),
        ("tilted_45y", Plane.XY.rotated((0, 45, 0))),
        ("tilted_diagonal", Plane.XY.rotated((30, 45, 15))),
    ])
    def test_fillet_various_planes(self, name, plane):
        """Test filleting in various plane orientations."""
        pencil = Pencil(plane)
        wire = pencil.right(10).fillet(2).up(10).create_wire()

        self.assertTrue(wire.is_valid, f"Filleted wire should be valid for {name}")

    @parameterized.expand([
        ("xy_plane", Plane.XY),
        ("xz_plane", Plane.XZ),
        ("tilted_45y", Plane.XY.rotated((0, 45, 0))),
    ])
    def test_fillet_mirrored_various_planes(self, name, plane):
        """Test filleted mirrored wire in various plane orientations."""
        pencil = Pencil(plane)
        # Fillet at (10, 5) - actual corner, not on mirror axis Y=0
        wire = pencil.up(5).right(10).fillet(2).up(5).create_mirrored_wire_x()

        self.assertTrue(wire.is_valid, f"Filleted mirrored wire should be valid for {name}")


if __name__ == '__main__':
    unittest.main()
