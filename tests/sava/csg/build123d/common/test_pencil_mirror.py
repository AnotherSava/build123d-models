import unittest

from build123d import Plane, Axis, Vector
from parameterized import parameterized

from sava.csg.build123d.common.pencil import Pencil


class TestPencilMirrorInCustomPlane(unittest.TestCase):
    """Test that Pencil mirroring works correctly in custom (non-XY) planes."""

    def test_mirror_in_xy_plane(self):
        """Baseline test: mirroring in standard XY plane should work."""
        pencil = Pencil(plane=Plane.XY)
        pencil.draw(50, 45)  # Draw at 45° from X axis

        face = pencil.create_mirrored_face(Axis.X)

        # Should create a valid face
        self.assertTrue(face.is_valid)

        # Should have vertices (at least 2, ideally more for a proper shape)
        vertices = face.vertices()
        self.assertGreaterEqual(len(vertices), 2)

    def test_mirror_in_xz_plane(self):
        """Test mirroring in XZ plane (rotated 90° from XY)."""
        pencil = Pencil(plane=Plane.XZ)
        pencil.draw(50, 45)  # Draw at 45° from X axis in XZ plane

        face = pencil.create_mirrored_face(Axis.X)

        # Should create a valid face
        self.assertTrue(face.is_valid)

        # Should have vertices
        vertices = face.vertices()
        self.assertGreaterEqual(len(vertices), 2)

    def test_mirror_in_yz_plane(self):
        """Test mirroring in YZ plane."""
        pencil = Pencil(plane=Plane.YZ)
        pencil.draw(50, 45)  # Draw at 45° from Y axis in YZ plane

        face = pencil.create_mirrored_face(Axis.X)

        # Should create a valid face
        self.assertTrue(face.is_valid)

        # Should have vertices
        vertices = face.vertices()
        self.assertGreaterEqual(len(vertices), 2)

    def test_mirror_in_tilted_plane(self):
        """Test mirroring in a custom tilted plane (not aligned with standard axes)."""
        # Create a plane tilted 45° around Y axis
        tilted_plane = Plane.XY.rotated((0, 45, 0))

        pencil = Pencil(plane=tilted_plane)
        pencil.draw(50, 45)  # Draw at 45° in the tilted plane

        face = pencil.create_mirrored_face(Axis.X)

        # Should create a valid face even in tilted plane
        self.assertTrue(face.is_valid, "Mirrored face should be valid in tilted plane")

        # Should have vertices
        vertices = face.vertices()
        self.assertGreaterEqual(len(vertices), 2)

    def test_mirror_in_diagonal_plane(self):
        """Test mirroring in a plane tilted diagonally."""
        # Create a plane tilted around multiple axes
        diagonal_plane = Plane.XY.rotated((30, 45, 15))

        pencil = Pencil(plane=diagonal_plane)
        pencil.draw(50, 45)

        face = pencil.create_mirrored_face(Axis.X)

        # Should create a valid face
        self.assertTrue(face.is_valid, "Mirrored face should be valid in diagonal plane")

        # Should have vertices
        vertices = face.vertices()
        self.assertGreaterEqual(len(vertices), 2)

    def test_mirrored_wires_are_coplanar(self):
        """Test that original and mirrored wires lie in the same plane."""
        # Use a tilted plane to make the test meaningful
        tilted_plane = Plane.XY.rotated((0, 30, 0))

        pencil = Pencil(plane=tilted_plane)
        pencil.draw(50, 45)

        # Get both wires
        original_wire = pencil.create_wire(False)
        mirrored_wire = pencil.mirror_wire(Axis.X)

        # Get all vertices from both wires
        orig_vertices = original_wire.vertices()
        mirror_vertices = mirrored_wire.vertices()

        # All vertices should lie in the same plane (the pencil's plane)
        # Check by calculating distance of each vertex from the plane
        for v in orig_vertices + mirror_vertices:
            # Project vertex onto plane and check if it's approximately on the plane
            # Note: Need to convert Vertex to Vector for to_local_coords() to work
            v_vec = Vector(v.X, v.Y, v.Z)
            point_on_plane = tilted_plane.to_local_coords(v_vec)
            # Z coordinate in local coords should be ~0 if point is on the plane
            self.assertAlmostEqual(point_on_plane.Z, 0.0, places=3,
                                 msg=f"Vertex {v} should lie on the plane")

    @parameterized.expand([
        ("xy_plane", Plane.XY),
        ("xz_plane", Plane.XZ),
        ("yz_plane", Plane.YZ),
        ("tilted_45y", Plane.XY.rotated((0, 45, 0))),
        ("tilted_diagonal", Plane.XY.rotated((30, 45, 60))),
    ])
    def test_mirror_axis_x_various_planes(self, name, plane):
        """Test mirroring across X axis in various plane orientations."""
        pencil = Pencil(plane=plane)
        pencil.draw(50, 45)

        face = pencil.create_mirrored_face(Axis.X)

        self.assertTrue(face.is_valid,
                       f"Mirrored face should be valid for {name}")
        self.assertGreaterEqual(len(face.vertices()), 2,
                              f"Should have vertices for {name}")


if __name__ == '__main__':
    unittest.main()
