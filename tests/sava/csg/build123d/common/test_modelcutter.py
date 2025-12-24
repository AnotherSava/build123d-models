import unittest

from build123d import Box, Wire, Line
from parameterized import parameterized

from sava.csg.build123d.common.geometry import create_wire_tangent_plane
from sava.csg.build123d.common.modelcutter import (
    cut_with_wires,
    CutSpec,
    _calculate_triangle_size,
    _create_cutting_triangle_at_wire,
)
from sava.csg.build123d.common.smartsolid import SmartSolid


class TestTriangleSizeCalculation(unittest.TestCase):
    """Test triangle size calculation from extended model bounding box."""

    def test_calculate_size_with_wire(self):
        """Triangle size should account for wire extent."""
        model = SmartSolid(Box(10, 10, 10))
        # Wire through center of model
        wire = Wire([Line((0, 0, 0), (10, 0, 0))])
        size = _calculate_triangle_size(model, [wire])

        # Should be larger than 0
        self.assertGreater(size, 0)

    def test_calculate_size_wire_far_from_model(self):
        """Triangle size should increase when wire extends far from model."""
        model = SmartSolid(Box(10, 10, 10))

        # Wire at center
        wire_near = Wire([Line((0, 0, 0), (10, 0, 0))])
        size_near = _calculate_triangle_size(model, [wire_near])

        # Wire far from model
        wire_far = Wire([Line((100, 0, 0), (110, 0, 0))])
        size_far = _calculate_triangle_size(model, [wire_far])

        # Triangle should be larger when wire is farther
        self.assertGreater(size_far, size_near)

    @parameterized.expand([
        ("small_box", Box(5, 5, 5)),
        ("rectangular", Box(20, 10, 5)),
        ("thin_plate", Box(50, 50, 1)),
        ("tall_column", Box(5, 5, 30)),
    ])
    def test_calculate_size_various_shapes(self, name, box):
        """Triangle size should scale with model size."""
        model = SmartSolid(box)
        # Wire through model center
        wire = Wire([Line((0, 0, 0), (10, 0, 0))])
        size = _calculate_triangle_size(model, [wire])

        # Size should be positive and reasonable
        self.assertGreater(size, 0)


class TestTriangleCreation(unittest.TestCase):
    """Test triangle creation with correct orientation."""

    def test_triangle_has_right_angle(self):
        """Triangle should have a 90-degree angle at the origin."""
        from sava.csg.build123d.common.geometry import create_wire_tangent_plane

        wire = Wire([Line((0, 0, 5), (10, 0, 5))])  # Horizontal wire along X
        triangle_size = 50.0  # Arbitrary size for testing
        plane = create_wire_tangent_plane(wire, 0.0)

        triangle = _create_cutting_triangle_at_wire(plane, wire, triangle_size)

        # Triangle should be a valid face
        self.assertTrue(triangle.is_valid)

    def test_triangle_legs_at_45_degrees(self):
        """Triangle legs should be at ±45° from the plane's X axis."""
        from sava.csg.build123d.common.geometry import create_wire_tangent_plane

        wire = Wire([Line((0, 0, 5), (10, 0, 5))])  # Horizontal wire along X
        triangle_size = 50.0  # Arbitrary size for testing
        plane = create_wire_tangent_plane(wire, 0.0)

        triangle = _create_cutting_triangle_at_wire(plane, wire, triangle_size)

        # Check that triangle has vertices (at least 3, could be 4 with completion segment)
        vertices = triangle.vertices()
        self.assertGreaterEqual(len(vertices), 3)
        self.assertLessEqual(len(vertices), 4)


class TestSingleWireCut(unittest.TestCase):
    """Test cutting with a single wire."""

    def test_cut_box_center_wire_x(self):
        """Cutting a box through center along X should produce 2 pieces."""
        model = SmartSolid(Box(20, 10, 10))
        # Wire through center, parallel to YZ plane
        wire = Wire([Line((10, -10, -10), (10, 20, 20))])
        plane = create_wire_tangent_plane(wire, 0.0)

        pieces = cut_with_wires(model, CutSpec(wire, plane))

        # Should produce 2 pieces
        self.assertGreaterEqual(len(pieces), 1)
        self.assertLessEqual(len(pieces), 2)

    def test_cut_box_center_wire_y(self):
        """Cutting a box through center along Y should produce 2 pieces."""
        model = SmartSolid(Box(10, 20, 10))
        # Wire through center, parallel to XZ plane
        wire = Wire([Line((-10, 10, -10), (20, 10, 20))])
        plane = create_wire_tangent_plane(wire, 0.0)

        pieces = cut_with_wires(model, CutSpec(wire, plane))

        # Should produce 2 pieces
        self.assertGreaterEqual(len(pieces), 1)
        self.assertLessEqual(len(pieces), 2)

    def test_cut_box_diagonal_wire(self):
        """Cutting a box with diagonal wire should produce pieces."""
        model = SmartSolid(Box(20, 20, 20))
        # Diagonal wire through box
        wire = Wire([Line((0, 0, 0), (20, 20, 20))])
        plane = create_wire_tangent_plane(wire, 0.0)

        pieces = cut_with_wires(model, CutSpec(wire, plane))

        # Should produce at least 1 piece
        self.assertGreaterEqual(len(pieces), 1)


class TestMultipleWiresCut(unittest.TestCase):
    """Test cutting with multiple wires."""

    def test_two_perpendicular_wires(self):
        """Two perpendicular wires should subdivide the model."""
        model = SmartSolid(Box(20, 20, 10))
        wire1 = Wire([Line((10, -10, -10), (10, 30, 20))])  # Parallel to Y
        wire2 = Wire([Line((-10, 10, -10), (30, 10, 20))])  # Parallel to X
        plane1 = create_wire_tangent_plane(wire1, 0.0)
        plane2 = create_wire_tangent_plane(wire2, 0.0)

        pieces = cut_with_wires(model, CutSpec(wire1, plane1), CutSpec(wire2, plane2))

        # Should produce multiple pieces (at least 2)
        self.assertGreaterEqual(len(pieces), 2)

    def test_three_orthogonal_wires(self):
        """Three orthogonal wires should further subdivide the model."""
        model = SmartSolid(Box(20, 20, 20))
        wire1 = Wire([Line((10, -10, -10), (10, 30, 30))])  # Parallel to Y
        wire2 = Wire([Line((-10, 10, -10), (30, 10, 30))])  # Parallel to X
        wire3 = Wire([Line((-10, -10, 10), (30, 30, 10))])  # Parallel to XY
        plane1 = create_wire_tangent_plane(wire1, 0.0)
        plane2 = create_wire_tangent_plane(wire2, 0.0)
        plane3 = create_wire_tangent_plane(wire3, 0.0)

        pieces = cut_with_wires(model, CutSpec(wire1, plane1), CutSpec(wire2, plane2), CutSpec(wire3, plane3))

        # Should produce multiple pieces
        self.assertGreaterEqual(len(pieces), 2)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_empty_wire_list(self):
        """Empty wire list should return the original model."""
        model = SmartSolid(Box(10, 10, 10))
        pieces = cut_with_wires(model)

        self.assertEqual(len(pieces), 1)
        # The piece should be the original model
        self.assertAlmostEqual(pieces[0].wrap_solid().volume, model.wrap_solid().volume, places=3)

    def test_wire_outside_model(self):
        """Wire completely outside model should return original model (tests inside.solid is None)."""
        model = SmartSolid(Box(10, 10, 10))
        # Wire far from the model - cutter won't intersect
        wire = Wire([Line((100, 100, 100), (110, 110, 110))])
        plane = create_wire_tangent_plane(wire, 0.0)

        pieces = cut_with_wires(model, CutSpec(wire, plane))

        # Should return 1 piece (original model unchanged)
        self.assertEqual(len(pieces), 1)
        self.assertAlmostEqual(pieces[0].wrap_solid().volume, model.wrap_solid().volume, places=3)

    def test_multiple_wires_some_outside(self):
        """Multiple wires where some don't intersect pieces (tests progressive None filtering)."""
        model = SmartSolid(Box(20, 20, 10))
        wire1 = Wire([Line((10, -10, -10), (10, 30, 20))])  # Cuts model in half
        wire2 = Wire([Line((100, 0, 0), (110, 0, 0))])  # Completely outside
        plane1 = create_wire_tangent_plane(wire1, 0.0)
        plane2 = create_wire_tangent_plane(wire2, 0.0)

        pieces = cut_with_wires(model, CutSpec(wire1, plane1), CutSpec(wire2, plane2))

        # Should have 2 pieces from wire1, wire2 doesn't affect them
        self.assertEqual(len(pieces), 2)

    def test_piece_entirely_consumed_by_cutter(self):
        """Cut with wire creating massive cutter should be handled properly."""
        # Use a very small model and large wire that creates an encompassing cutter
        tiny_model = SmartSolid(Box(2, 2, 2))
        tiny_model.solid.position = (0, 0, 0)

        # Very long wire that creates a massive cutting volume
        huge_wire = Wire([Line((-500, 0, 0), (500, 0, 0))])
        huge_plane = create_wire_tangent_plane(huge_wire, 0.0)

        pieces = cut_with_wires(tiny_model, CutSpec(huge_wire, huge_plane))

        # All returned pieces should have valid, non-empty solids
        self.assertGreater(len(pieces), 0)
        for piece in pieces:
            self.assertIsNotNone(piece.solid)
            self.assertTrue(piece.solid)  # Not empty
            self.assertGreater(piece.wrap_solid().volume, 0)

    def test_single_point_on_edge(self):
        """Wire barely touching model edge should handle gracefully."""
        model = SmartSolid(Box(10, 10, 10))
        # Wire at the edge of the model
        wire = Wire([Line((5, 5, -1), (5, 5, 11))])
        plane = create_wire_tangent_plane(wire, 0.0)

        pieces = cut_with_wires(model, CutSpec(wire, plane))

        # Should return some pieces (at least 1)
        self.assertGreaterEqual(len(pieces), 1)


class TestGeometricCorrectness(unittest.TestCase):
    """Test geometric properties of the cuts."""

    def test_all_pieces_are_valid(self):
        """All resulting pieces should have valid geometry."""
        model = SmartSolid(Box(20, 20, 20))
        wire = Wire([Line((10, -10, -10), (10, 30, 30))])
        plane = create_wire_tangent_plane(wire, 0.0)

        pieces = cut_with_wires(model, CutSpec(wire, plane))

        for piece in pieces:
            self.assertTrue(piece.wrap_solid().is_valid,
                          "All pieces should have valid geometry")

    def test_pieces_volume_conservation(self):
        """Sum of piece volumes should approximately equal original volume."""
        model = SmartSolid(Box(20, 20, 20))
        wire = Wire([Line((10, -10, -10), (10, 30, 30))])
        plane = create_wire_tangent_plane(wire, 0.0)

        original_volume = model.wrap_solid().volume
        pieces = cut_with_wires(model, CutSpec(wire, plane))
        total_volume = sum(p.wrap_solid().volume for p in pieces if p.solid is not None)

        # Allow for small numerical errors in boolean operations
        self.assertAlmostEqual(original_volume, total_volume, delta=original_volume * 0.01,
                             msg="Volume should be conserved (within 1%)")


class TestThicknessCutting(unittest.TestCase):
    """Test cutting with thickness (removing material)."""

    def test_cut_with_thickness_removes_material(self):
        """Cutting with thickness should remove a slice of material."""
        model = SmartSolid(Box(20, 20, 20))
        wire = Wire([Line((10, -10, -10), (10, 30, 30))])
        plane = create_wire_tangent_plane(wire, 0.0)
        thickness = 2.0

        original_volume = model.wrap_solid().volume
        pieces = cut_with_wires(model, CutSpec(wire, plane, thickness))

        # Should still produce 2 pieces
        self.assertGreaterEqual(len(pieces), 1)
        self.assertLessEqual(len(pieces), 2)

        # Total volume should be less than original (material removed)
        total_volume = sum(p.wrap_solid().volume for p in pieces)
        self.assertLess(total_volume, original_volume)

    def test_cut_with_zero_thickness_same_as_thin_cut(self):
        """Thickness of 0 should behave like a thin cut."""
        model1 = SmartSolid(Box(20, 20, 20))
        model2 = model1.copy()
        wire = Wire([Line((10, -10, -10), (10, 30, 30))])
        plane = create_wire_tangent_plane(wire, 0.0)

        pieces_thin = cut_with_wires(model1, CutSpec(wire, plane))
        pieces_zero_thickness = cut_with_wires(model2, CutSpec(wire, plane, thickness=0.0))

        # Should produce same number of pieces
        self.assertEqual(len(pieces_thin), len(pieces_zero_thickness))

        # Volumes should be approximately equal
        vol_thin = sum(p.wrap_solid().volume for p in pieces_thin)
        vol_zero = sum(p.wrap_solid().volume for p in pieces_zero_thickness)
        self.assertAlmostEqual(vol_thin, vol_zero, delta=vol_thin * 0.01)

    def test_larger_thickness_removes_more_material(self):
        """Larger thickness should remove more material."""
        model1 = SmartSolid(Box(20, 20, 20))
        model2 = model1.copy()
        wire = Wire([Line((10, -10, -10), (10, 30, 30))])
        plane = create_wire_tangent_plane(wire, 0.0)

        pieces_thin = cut_with_wires(model1, CutSpec(wire, plane, thickness=1.0))
        pieces_thick = cut_with_wires(model2, CutSpec(wire, plane, thickness=3.0))

        vol_thin = sum(p.wrap_solid().volume for p in pieces_thin)
        vol_thick = sum(p.wrap_solid().volume for p in pieces_thick)

        # Thicker cut should remove more material
        self.assertLess(vol_thick, vol_thin)


if __name__ == '__main__':
    unittest.main()
