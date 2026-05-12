import unittest
from pathlib import Path

from sava.csg.build123d.reconstruct import reconstruct

DATA_DIR = Path(__file__).parent / 'data'
MESH_PATH = DATA_DIR / 'iris_blade.off'
EXPECTED_PATH = DATA_DIR / 'expected_iris_blade.py'


class TestIrisBladeReconstruction(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.result = reconstruct(str(MESH_PATH))

    def test_is_2d5_extrudable(self):
        self.assertTrue(self.result.is_2d5_extrudable)
        self.assertIsNone(self.result.error)

    def _assert_vector_close(self, actual, expected_xyz, places=2):
        self.assertAlmostEqual(actual.X, expected_xyz[0], places=places)
        self.assertAlmostEqual(actual.Y, expected_xyz[1], places=places)
        self.assertAlmostEqual(actual.Z, expected_xyz[2], places=places)

    def test_extrusion_axis(self):
        self._assert_vector_close(self.result.extrusion_axis, (0.683, -0.731, 0.0))

    def test_datum_frame_axes(self):
        self._assert_vector_close(self.result.z_dir, (0.683, -0.731, 0.0))
        self._assert_vector_close(self.result.y_dir, (0.0, 0.0, 1.0))
        self._assert_vector_close(self.result.x_dir, (0.731, 0.683, 0.0))

    def test_datum_contact_area(self):
        self.assertAlmostEqual(self.result.datum_contact_area, 74.87, places=1)

    def test_layer_depths(self):
        depths = sorted(L.depth for L in self.result.layers)
        expected = [-0.611, 0.889, 3.889, 7.889]
        self.assertEqual(len(depths), len(expected))
        for actual, ref in zip(depths, expected):
            self.assertAlmostEqual(actual, ref, places=2)

    def test_layer_names(self):
        names = {L.name for L in self.result.layers}
        self.assertEqual(names, {'front', 'back', 'back_protrusion', 'front_protrusion'})

    def test_layer_depths_by_name(self):
        """Each named layer sits at the depth expected from the source mesh."""
        depth_for = {L.name: L.depth for L in self.result.layers}
        self.assertAlmostEqual(depth_for['back_protrusion'], -0.611, places=2)
        self.assertAlmostEqual(depth_for['back'], 0.889, places=2)
        self.assertAlmostEqual(depth_for['front'], 3.889, places=2)
        self.assertAlmostEqual(depth_for['front_protrusion'], 7.889, places=2)

    def test_cylinder(self):
        self.assertEqual(len(self.result.cylinders), 1)
        cyl = self.result.cylinders[0]
        self.assertAlmostEqual(cyl.radius, 1.8, places=1)
        self.assertAlmostEqual(cyl.height, 4.0, places=1)
        # Cylinder base sits on the body's front face. After the shared-anchor
        # shift (15.637, 0) → (0, 0), the centroid (11.85, 1.70) becomes
        # (-3.78, 1.70). cz_base = body_thickness = 3.
        cu, cv, cz = cyl.base
        self.assertAlmostEqual(cu, -3.78, places=1)
        self.assertAlmostEqual(cv, 1.70, places=1)
        self.assertAlmostEqual(cz, 3.0, places=1)

    def test_emitted_code_matches_expected(self):
        expected = EXPECTED_PATH.read_text(encoding='utf-8').strip()
        actual = self.result.code.strip()
        self.assertEqual(actual, expected)

    def test_emitted_code_executes_and_reproduces_bbox(self):
        """Verify the emitted code runs and produces geometry matching the source mesh."""
        namespace = {}
        exec(self.result.code, namespace)
        blade = namespace['blade']

        bb = blade.solid.bounding_box()
        size_x = bb.max.X - bb.min.X
        size_y = bb.max.Y - bb.min.Y
        size_z = bb.max.Z - bb.min.Z
        # Source mesh bbox is 18.9 x 17.5 x 26.5 mm. Reconstructed cylinder is
        # an analytical primitive, so its bbox can overshoot the tessellated
        # mesh by ~0.1 mm — allow a 0.2 mm slack.
        self.assertAlmostEqual(size_x, 18.9, delta=0.2)
        self.assertAlmostEqual(size_y, 17.5, delta=0.2)
        self.assertAlmostEqual(size_z, 26.5, delta=0.2)

        # Volume = body + back rim + cylinder pin ~ 1044 + 39.5 + 41.6 ~ 1125 mm^3.
        self.assertAlmostEqual(blade.solid.volume, 1125, delta=50)

    def test_emitted_polygons_share_start_vertex(self):
        """The shared anchor vertex is folded into the local origin, so every
        emit-eligible polygon opens with a bare Pencil() (default Plane.XY)."""
        code = self.result.code
        self.assertIn("body = Pencil()", code)
        self.assertIn("back_protrusion = Pencil()", code)
        # And no stray `start=` for either:
        self.assertNotIn("body = Pencil(start=", code)
        self.assertNotIn("back_protrusion = Pencil(start=", code)


if __name__ == '__main__':
    unittest.main()
